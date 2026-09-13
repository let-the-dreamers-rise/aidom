# StackingDAO audit notes — 2026-09-13 (ACTIVE TARGET, in progress)

Target: StackingDAO (Immunefi), $100k cap, Critical min $20k, High $1k–$20k,
**no KYC, no fee text, PoC required, Primacy of Impact** for Critical/High
(any StackingDAO contract with an in-scope impact counts). Liquid stacking on
Stacks in Clarity: stSTX (~45.2M supply, ratio 1.185 STX), stSTXbtc (~27.7M,
1:1 STX-backed, sBTC rewards via a cumulative tracker), and the new **stBTC**
(152.5 BTC supply, launched 2026-08-13, deposits closed 2026-09-04 as
"capacity filled"). stx-reserve-v2 holds 9.14M STX idle + 71.3M STX staked.

## Source of truth and inventory

On-chain source via Hiro for the 36 listed assets plus every newer version
the deployer published after the scope snapshot (work/stackingdao/, 4,860
lines; older still-active versions in work/stackingdao/old/; PoX-5 boot
contract in work/pox5/). Public GitHub lags (last commit 2026-04), so the
chain is authoritative. The DAO registry was swept with `get-contract-active`
for ~100 names: 55 active, including legacy `reserve-v1`, `commission-v1/v2`,
`stacker-1/2/10`, `rewards-v2/v3`, `data-core-v2`, `strategy-v4`,
`stacking-dao-core-stx-v1`, `stacking-dao-core-ststxbtc-v1` (all shut via
their own flags), `signer-manager-bond-*-v1` (not approved in strategy-v6, so
inert). Live cores: core-stx-v2 (all open), core-ststxbtc-v2 (all open),
core-stbtc-v1 (deposits shut, withdrawals open).

## Prior audit (Clarity Alliance, 2026-08-13, PoX-5 review) — read in full

31 findings; 7 Critical, 5 High, 10 Medium, 8 Low. All Critical/High marked
Resolved. Acknowledged/partial (ineligible): L-05 no DAO admin timelock, L-07
cooldown may mature before liquidity, L-08 withdrawal fees cause immediate
ratio jumps (deposit-before-large-withdrawal MEV). Fix verification on the
live code:

- C-03/C-04/H-01/M-07: every core calls `process-rewards` before reading the
  ratio; stBTC uses `pending-shares`, stSTX uses escrow-core balances, to
  exclude pending withdrawals; 1000 dead shares on first deposit; ratio
  rounded up on deposit and down on exit; `min-shares-out` everywhere. ✓
- C-06 (pending stSTXbtc withdrawals double-counted): live `escrow-cores` in
  stx-reserve-v2 lists only dead cores (btc-v1/v2/v3, ststxbtc-v1); the live
  core-ststxbtc-v2 is deliberately NOT listed, so its 45,956 STX of pending
  withdrawals stay inside the earmark and are never double-counted. I
  recomputed the live ratio from the raw buckets and it matches the contract
  (1.185394), so the accounting is currently consistent. ✓
- H-02: both reward streams fold only when the keeper calls. ✓
- M-03: withdraw fee stored per NFT. ✓  M-09: stSTX payouts must leave the
  stSTXbtc idle bucket intact. ✓  M-10: stSTXbtc fees go to a treasury. ✓
- M-06/L-02: the `dao` contract is the 2024 original (immutable), still
  authorises on `tx-sender`; "resolved" only operationally. Admin-side
  phishing risk, out of scope.

## Bucket-invariant analysis of stx-reserve-v2 (all 15 flows)

Walked deposit / init-withdraw / withdraw / withdraw-idle for stSTX and
stSTXbtc, both swap directions (v5), request-stx-to-stack, request-stx-for-
staking, both return paths, rewards and get-stx against the invariants
B ≥ W_s + I, I ≥ W_b, E = supply_b − escrow_b. Every flow preserves them;
swaps are ratio-neutral for stSTX (burn a, mint a·r stSTXbtc, earmark +a·r)
and rounding always favours the protocol. Donating tokens to a listed escrow
core or STX to the reserve only helps other holders. No manipulation path.

## stBTC path (new code)

deposit/init-withdraw/withdraw/withdraw-idle mirror stSTX with sBTC; every
reserve mutator is `check-is-protocol`-gated; bonds pull sBTC and co-bond STX
from the reserves via strategy-v6 (manager-gated, approved signer managers
only); `unstake-sbtc`/`claim-rewards` in PoX-5 are staker/signer-manager
scoped. Rewards from all three signer managers land in rewards-pox5-v1 and
stream over 2100 burn blocks; stBTC's share is the remainder after the
stSTXbtc/stSTX bps.

**Observation (not a security finding): the post-audit
`reward-split-calculator-v2` (2026-08-30) sets `ststx-bps = 10000 −
ststxbtc-bps`, so the stBTC remainder is always 0.** The audited v1 computed
`ststx-bps = w_ststx / w_sum` and left stBTC the remainder. The live split is
3291/6709 (sum 10000) and the stBTC reserve has received no stream share
recently; the stBTC ratio has moved 0.117% since launch. v2 has never been
invoked on-chain yet, so this may be a latent misallocation rather than an
active one, and it is DAO/keeper-triggered, not attacker-driven — worth a
courtesy note to the team, not a bounty report.

## Still to check

PoX-5 signer/staker reward split for the protocol's own staker contracts
(whether staker-side rewards are claimable by the signer managers they use).
