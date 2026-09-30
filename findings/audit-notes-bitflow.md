# Bitflow (Stacks AMM) — audit notes

Date: 2026-09-29
Auditor session: thread "bug bounty / pay for yourself"
Source: deployed Clarity, read from `boomcrypto/clarity-deployed-contracts`
mirror (api.hiro.so and all Stacks nodes are now BLOCKED by the sandbox
egress proxy — see CONTEXT env update; on-chain state could NOT be read).

## Scope covered
Primary deployer `SPQC38PW542EQJ5M11CR25P7BS1CA6QT4TBXGB3M`, xyk deployer
`SM1793C4R5PZ4NS4VQ4WMP7SKKYVH8JZEWSZ9HCCR`.
- `stableswap-stx-ststx-v-1-2` (flagship pool, OLD design) — full read + math sim
- `stableswap-{usda-susdt,aeusdc-susdt,usda-aeusdc-v-1-4,abtc-xbtc}-v-1-2` — fee-model diff only
- `xyk-core-v-1-1`, `xyk-pool-stx-aeusdc-v-1-1`, `xyk-pool-trait-v-1-1`
- `router-stx-ststx-bitflow-xyk-v-1-1` (+ scanned `router-xyk-alex-v-1-2`)

## Refuted hypotheses (self-refutation gate)
1. **Solver returns 0 on non-convergence → drains entire y balance.**
   REFUTED. Ported get-D / get-y integer math to Python (`sim.py`, faithful
   floor-div + underflow-abort). The Newton iteration converges within the
   384-step index list even at the `< 10x balance` swap cap; `get-y` never
   returned 0. Balanced 1M/1M pool, A=100.
2. **Per-swap value extraction / invariant loss.** REFUTED. D is
   non-decreasing on every swap tested (dD >= 0). The implementation's
   "double-count" convention (get-y is passed the already-updated balance
   AND the delta) is *conservative*: it rounds in the pool's favour, so the
   swapper receives slightly LESS than an ideal stableswap, never more. Not
   exploitable by the swapper.
3. **xyk-core theft / fake-pool injection.** REFUTED. Standard UniV2 math,
   fee-on-input, dead-shares protection (`MINIMUM_SHARES` = 1e6 minted to the
   pool contract at creation), and `is-valid-pool` binds the caller-supplied
   pool-trait to the registered `pools` entry, so a malicious pool contract
   can only affect its own (self-funded) pool.
4. **Router wrong-recipient / unchecked-hop theft.** REFUTED. The router uses
   plain `contract-call?` (no `as-contract`), so `tx-sender` = user on every
   hop; tokens flow directly user↔pool and it never custodies funds. Final
   `min-received` guards the whole atomic path.

## Standing observation (NOT submission-ready)
**stx-ststx-v-1-2 admin swap-fee branch is inverted vs. its own comment.**
Lines 331-343 / 453-465:
```clarity
;; Admins pay no fees on swaps
(swap-fee-lps (if (is-some (index-of (var-get admins) tx-sender))
    (get lps (var-get buy-fees))        ;; admin  -> normal fee
    (get lps (var-get admin-swap-fees)) ;; NON-admin -> admin-swap-fees
))
```
`admin-swap-fees` is initialised to `{lps:0, stacking-dao:0, bitflow:0}`.
As written, an admin pays the normal fee and every **non-admin (i.e. every
ordinary user) pays the admin-swap-fee = 0**. That is the exact inverse of
the stated intent ("admins pay no fees"). Effect if live with the default
var value: all user swaps on the flagship STX/stSTX pool are fee-free — LPs
and protocol earn nothing, and the 195 bps `sell-fees` stacking-dao
component (the stSTX→STX de-peg protection) is not collected.

Evidence it is a genuine bug, not intent: the **newer pools**
(`abtc-xbtc`, `usda-*`, `aeusdc-*`) dropped the admin-fee branch entirely
and use a flat `swap-fees {lps, protocol}` applied to everyone — consistent
with the broken branch having been removed in the redesign.

### Why this is NOT being drafted as a report
- Severity is fee-revenue loss (likely Low/Medium), not theft of principal;
  many programs treat protocol-fee-loss from a logic slip as low/out-of-scope.
- It depends on the **mutable** `admin-swap-fees` var still being `{0,0,0}`
  on-chain. An admin may have set it to the real fee as a workaround, which
  would fully neutralise the bug. **This sandbox cannot read on-chain state**
  (all Stacks/Hiro hosts 403 at the proxy; WebFetch needs operator URL
  approval), so it cannot be verified.
- It may already be known given it is an older contract version superseded by
  the redesigned pools.

### To take this further (needs the operator / a node)
1. Read live `admin-swap-fees` on `stableswap-stx-ststx-v-1-2`; only a
   `{0,0,0}` (or otherwise-below-intended) value keeps the bug alive.
2. Confirm the pool still holds meaningful TVL and is the current stx-ststx
   pool (not deprecated by a v-1-3+).
3. If both hold, a clarinet-sdk (WASM) simnet PoC demonstrating
   `non-admin swap pays 0 fee` vs `admin swap pays full fee` would make it
   concrete. Draft only then, framed as broken sell-fee peg protection.

Conclusion: no high-confidence, submission-ready finding on Bitflow from an
in-sandbox source audit. Core swap/liquidity/router logic is sound.

## UPDATE 2026-09-29 #2 — expanded scope (Bitflow runs a LIVE $100k Immunefi program)
Immunefi re-launched a Bitflow bug bounty at $100k (Immunefi announcement
2026). So a real fund-loss bug pays big — audited the authorization + reward
layer that a critical would live in. All sound:
- **stx-ststx-lp-token-v-1-2**: `mint` gated to `approved-supply-controller`
  (the core, set by CONTRACT-OWNER; core calls via `as-contract` so tx-sender
  = core). `burn` requires tx-sender==burner (self-only). No unauthorized mint.
- **xyk-pool-stx-aeusdc-v-1-1**: every mutator (`pool-mint`, `pool-burn`,
  `pool-transfer`, `update-pool-balances`, `create-pool`, `set-*`) asserts
  `caller == CORE_ADDRESS` (a compile-time constant = .xyk-core-v-1-1). Core
  calls via `as-contract`. No direct drain/mint path.
- **earn-stx-ststx-v-1-2 (staking & rewards, where LP fees pool)**: sound.
  - Staking credits only FUTURE cycles (current-cycle+1 .. +cycles), never the
    current or a past cycle → cannot flash-stake to grab already-accrued fees.
  - Reward = fee_K * user_staked_K / total_staked_K for a PAST cycle only
    (`cycle < current-cycle`), `reward-claimed` flag per (user,cycle) blocks
    double-claim in both claim-cycle and claim-all paths.
  - Conservation: each stake adds `amount` to BOTH the user's per-cycle stake
    and DataPerCycleMap[cycle] (denominator), so per-cycle user shares sum to
    the tracked total; the STX to pay them is physically forwarded by the pool
    (`x-amount-fee-lps` → staking contract) and matches CycleDataMap. No
    over-claim beyond fees received (rounding only ever under-pays).
  - Unstake is locked until `current-cycle+cycles+1`; accounting matches stake.

Net: Bitflow's swap / liquidity / LP-token / pool / router / staking layers are
all well-built. No Critical/High found. The only deviation is the stx-ststx
admin-fee inversion (Low/Med, loss of protocol fee revenue, state-dependent,
evidently removed in the newer pool redesign) — not a $100k-tier bug and not
verifiable on live state from this sandbox. Honest result: this protocol is
solid, which is consistent with it carrying a $100k program + prior audits.
