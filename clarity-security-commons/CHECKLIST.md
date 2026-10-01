# Clarity DeFi security checklist

Ten bug classes that came up while reviewing the deployed contracts of ten
Stacks DeFi protocols (AMMs, lending markets, liquid stacking, stablecoins,
bonding curves, intent verifiers) in September 2026. Each entry gives the
unsafe pattern, a safer one, and the question to ask in review.

Examples are simplified. They name no protocol: where a class came from a
real issue, that issue was reported privately to its team.

Contents

1. Share vaults that price shares from a donatable balance
2. Replay or nonce maps keyed without the owner
3. Public functions that act on another user's state
4. Unsigned subtraction that aborts and locks funds
5. Deactivated or migrated positions that stop being claimable
6. Caller-supplied trait contracts that aren't bound to a registry
7. Rounding that favours the user instead of the protocol
8. Proportional splits that round a recipient to zero
9. Iterative math that can stop early
10. Configurable branches nobody exercises

---

## 1. Share vaults that price shares from a donatable balance

A vault or staking pool that mints shares as
`amount * total-shares / total-assets`, where `total-assets` is the contract's
live token balance, can be inflated. At low supply an attacker mints one
share, transfers ("donates") a large amount directly to the contract, and the
next depositor's shares round down to zero.

Unsafe:

```clarity
(define-public (stake (amount uint))
  (let (
    (assets (unwrap-panic (contract-call? .token get-balance (as-contract tx-sender))))
    (supply (ft-get-supply shares))
    (minted (if (is-eq supply u0) amount (/ (* amount supply) assets)))
  )
    (try! (contract-call? .token transfer amount tx-sender (as-contract tx-sender) none))
    (ft-mint? shares minted tx-sender)))
```

Safer: track assets in a data variable that only deposits, withdrawals and
reward accrual change, so a direct transfer can't move the price. Also mint
dead shares on the first deposit, or use a virtual offset
(`(assets + 1)` and `(supply + 1)`), and reject a mint that rounds to zero.

```clarity
(define-data-var total-assets uint u0)

(define-public (stake (amount uint))
  (let (
    (supply (ft-get-supply shares))
    (minted (/ (* amount (+ supply u1)) (+ (var-get total-assets) u1)))
  )
    (asserts! (> minted u0) ERR-ZERO-SHARES)
    (try! (contract-call? .token transfer amount tx-sender (as-contract tx-sender) none))
    (var-set total-assets (+ (var-get total-assets) amount))
    (ft-mint? shares minted tx-sender)))
```

Ask: what does the share price read, and can anyone change it without minting
or burning shares?

## 2. Replay or nonce maps keyed without the owner

An intent or signature verifier that records used IDs in a map keyed only on
the ID lets anyone consume someone else's ID. The attacker signs their own
valid message carrying the victim's ID, submits it first, and the victim's
real message reverts as "already used". With signed intents broadcast before
they land on-chain, the ID is public in advance.

Unsafe:

```clarity
(define-map used-ids (string-ascii 36) bool)

(define-public (execute (signature (buff 65)) (payload (buff 128)) (id (string-ascii 36)))
  (if (map-insert used-ids id true)
    (verify payload id signature)
    ERR-ID-USED))
```

Safer: recover the signer first, then key the map on `{ signer, id }`, so each
signer has their own ID space.

```clarity
(define-map used-ids { signer: principal, id: (string-ascii 36) } bool)

(define-public (execute (signature (buff 65)) (payload (buff 128)) (id (string-ascii 36)))
  (let ((signer (try! (verify payload id signature))))
    (asserts! (map-insert used-ids { signer: signer, id: id } true) ERR-ID-USED)
    (ok signer)))
```

Ask: can two unrelated users collide on the same key? Is the key ever
revealed before it is consumed?

## 3. Public functions that act on another user's state

A `define-public` function that takes a `holder` argument and updates that
holder's checkpoint, saved rewards or position, with no check that
`tx-sender` is the holder or a protocol contract, lets anyone change other
users' accounting at a moment of their choosing. Often harmless, but combined
with class 4 or 5 it can freeze funds.

Unsafe:

```clarity
(define-public (save-pending-rewards (holder principal))
  (begin
    (map-set saved holder (get-pending holder))
    (map-set checkpoint holder (var-get global-index))
    (ok true)))
```

Safer: gate on the holder or on a protocol caller, or make the update
provably harmless for every state the holder can be in (including the
deactivated and migrated states in class 5).

```clarity
(define-public (save-pending-rewards (holder principal))
  (begin
    (asserts! (or (is-eq tx-sender holder) (is-protocol contract-caller)) ERR-NOT-AUTHORIZED)
    (map-set saved holder (get-pending holder))
    (map-set checkpoint holder (var-get global-index))
    (ok true)))
```

Ask: for each public function taking a principal, what happens if a stranger
calls it with my address, at the worst possible time?

## 4. Unsigned subtraction that aborts and locks funds

Clarity `uint` subtraction aborts the whole transaction on underflow. That
stops theft, but if a read-only helper used by `claim` or `withdraw` can be
driven into `(- a b)` with `b > a`, every later claim aborts and the funds are
stuck until an admin repairs the state.

Unsafe:

```clarity
(define-read-only (get-pending (holder principal))
  (* (- (var-get index) (default-to u0 (map-get? checkpoint holder))) (balance-of holder)))
```

Safer: make the invariant `checkpoint <= index` impossible to break (see
classes 3 and 5). Where it can't be guaranteed, clamp and handle the zero
case explicitly instead of aborting.

```clarity
(define-read-only (get-pending (holder principal))
  (let ((idx (var-get index)) (cp (default-to u0 (map-get? checkpoint holder))))
    (if (> idx cp) (* (- idx cp) (balance-of holder)) u0)))
```

Ask: for every subtraction on the claim and withdraw paths, who controls each
operand, and can the right side ever be larger?

## 5. Deactivated or migrated positions that stop being claimable

When a protocol migrates to a new adapter, pool or market, it usually freezes
the old one's reward index so holders can still claim what they earned. Code
written for active positions then runs against the frozen value. Mixing a
frozen index with a live checkpoint is how class 4 becomes reachable.

Ask, for every migration path:

- Can every holder still claim and withdraw from the old position?
- Does any function that runs on active positions also run, unguarded, on
  deactivated ones?
- Is there a test that deactivates a position, adds more rewards globally,
  then calls every public function on the old position?

## 6. Caller-supplied trait contracts that aren't bound to a registry

Functions that take a `<pool-trait>` or `<ft-trait>` argument will call
whatever contract the user passes. If the function then reads or writes
shared state (vault balances, a registry entry) based on that call, an
attacker-deployed contract can return made-up values.

Unsafe:

```clarity
(define-public (swap (pool <pool-trait>) (amount-in uint))
  (let ((user tx-sender) (out (try! (contract-call? pool get-amount-out amount-in))))
    (as-contract (contract-call? .vault transfer-out out user))))
```

Safer: look the trait's principal up in a registry the protocol controls,
and keep per-pool balances so one pool can never pay out more than it holds.

```clarity
(define-public (swap (pool <pool-trait>) (amount-in uint))
  (let (
    (user tx-sender)
    (pool-info (unwrap! (map-get? pools (contract-of pool)) ERR-UNKNOWN-POOL))
    (out (try! (contract-call? pool get-amount-out amount-in)))
  )
    (asserts! (< out (get balance-y pool-info)) ERR-INSUFFICIENT-BALANCE)
    (map-set pools (contract-of pool) (merge pool-info { balance-y: (- (get balance-y pool-info) out) }))
    ;; Capture the user before as-contract: inside it, tx-sender is this contract.
    (as-contract (contract-call? .vault transfer-out out user))))
```

Ask: for each trait argument, is `contract-of` checked against stored state
before its answer is trusted? Inside `as-contract`, who is `tx-sender` now?

## 7. Rounding that favours the user instead of the protocol

Integer division rounds down. Mint, redeem, borrow, repay and liquidation
amounts should each round in the direction that keeps the protocol solvent:
shares minted and assets paid out round down; shares burned and debt owed
round up.

```clarity
;; Ceiling division for amounts the user owes the protocol.
(define-read-only (div-up (a uint) (b uint))
  (if (is-eq a u0) u0 (+ u1 (/ (- a u1) b))))
```

Ask: for each conversion, if the user repeats it many times with tiny
amounts, does the protocol lose a unit each time?

## 8. Proportional splits that round a recipient to zero

Reward splits computed as `total * weight / sum-of-weights` can starve a
recipient when weights are in different units or precisions, or when one
weight is tiny next to the others. Nothing aborts; one recipient just gets nearly nothing.

Ask:

- Are all weights in the same unit and precision?
- Does a test assert each recipient's expected share at realistic mainnet
  sizes, not just that the shares sum to the total?

## 9. Iterative math that can stop early

Clarity has no unbounded loops, so stableswap and similar solvers iterate
with `fold` over a fixed list. If the loop ends before converging and the
code returns the last value (or zero) as if it were the answer, a swap can
pay out the wrong amount.

Ask: what happens when the fixed iteration count runs out? A safe solver
either proves convergence within the bound for every allowed input (and
enforces input caps that guarantee it) or aborts when it has not converged.
Simulating the exact integer math off-chain at the input caps is cheap and
answers this quickly.

## 10. Configurable branches nobody exercises

Fee switches, admin flags and pause states change which branch runs. A branch
that is inverted against its own comment (for example, an admin-fee check
that charges non-admins nothing) survives because tests only ran with the
default setting.

Ask: for every `data-var` an admin can change, is there a test for each
value, and does the behaviour match the comment and the docs?

---

## How these were found

Every class above came from reading deployed mainnet source and checking
live state with read-only calls; no transaction was sent to any protocol.
The read-only checks are in [`verifier/`](verifier/).

License: MIT.
