# Granite Protocol audit notes — 2026-09-13 (ACTIVE TARGET, in progress)

Target: Granite Protocol bug bounty (Immunefi), $100k cap, **no submission
fee**, KYC at payout, PoC required. A Bitcoin liquidity/lending protocol on
Stacks written in **Clarity** — a far smaller researcher pool than Solidity,
which is the edge. Incubated by Trust Machines. Borrow stablecoin (aeUSDC)
against sBTC collateral; soft/partial liquidations; no rehypothecation.

Why this target: fresh (updated 2026-07-25), fee-free, and Clarity is
under-competed. This is the higher-EV pool after ENS and 1inch came up empty.

## Source of truth

In-scope assets are **deployed on-chain**, pinned by address on the bounty
page. Source fetched directly from the Stacks API (Hiro
`/v2/contracts/source/...`), which returns the exact deployed Clarity. Not a
GitHub checkout — the on-chain code is authoritative for this program.

In-scope borrower is `SP26NGV9AFZBX7XBDBS2C7EC7FCPSAV9PKREQNMVS.borrower-v1`,
which wires to state/math/interest at `SP35E2...` and staking/constants at
`SP3BJR4...`. All three principals host same-named contracts; the coherent
live wiring is the one the in-scope borrower references by hardcoded principal.

## Coverage so far

Read closely: borrower-v1 (borrow/repay/add+remove-collateral), math-v1,
constants-v1/v2, flash-loan-v1, liquidity-provider-v1 (deposit/withdraw/redeem),
liquidator-v1 (the full liquidation path), pyth-adapter-v1 (oracle).

**Not yet read (highest remaining risk):** state-v1 (935 lines — the actual
balance mutations: `add-assets`/`remove-assets`/`update-borrow-state`/
`update-repay-state`/`update-liquidate-collateral-state`/`transfer-to`/
`transfer-from`/`socialize-user-bad-debt`), linear-kinked-ir-v1 (204, interest
accrual), staking-v1 / staking-reward-v1, withdrawal-caps-v1 (318),
governance-v1 (1304, the Pyth/wormhole governance). A real critical, if one
exists, most likely lives in state-v1's share accounting or the interest model.

## Candidate finding (LOW / defense-in-depth — not a claimed critical)

**Zero-priced collateral can be fully seized for zero repayment in
liquidation.** Chain of three facts:

1. `pyth-adapter-v1.check-confidence` returns `(ok true)` when `price == u0`
   (explicit `(is-eq u0 price)` branch), so `read-price` can return 0 with no
   non-zero guard downstream. `convert-res` can also floor a tiny price to 0
   when the feed exponent is more negative than the 8-digit resolution.
2. `liquidator-v1.liquidate`: when `repay-amount == u0` it sets
   `collateral-to-give = deposited-collateral-amount` (the borrower's ENTIRE
   balance of that collateral), skipping `calc-collateral-to-give`.
3. `liquidator-v1.ensure-non-zero-repay-amount`: when `collateral-price <= u0`
   it returns SUCCESS for ANY repay amount, so a liquidator passing
   `liquidator-repay-amount = 0` is not rejected.

Together: if a supported collateral's oracle price reads 0, a liquidator can
seize 100% of that collateral for 0 debt repayment (position must be unhealthy,
which a 0-priced collateral tends to cause). The post-liquidation health check
(`position-health <= LIQUIDATION-BUFFER + MINIMUM_HEALTH_RATIO`) does not stop
it — seizing collateral for no repayment only lowers health, staying under the
cap.

**Why it is LOW, stated honestly:** the two configured feeds are sBTC and
aeUSDC; Pyth will not sign a 0 price for either, and collaterals are
governance-gated (must have `max-ltv > 0`), so an attacker cannot introduce a
token with a manipulable/zero feed. The `ensure-non-zero-repay-amount` comment
("if collateral price is zero, we don't care about repay amount, anything is
accepted") shows the developers considered price==0 deliberately, so they may
treat it as a degenerate-case non-issue. It becomes real only if a future
collateral uses a feed that can legitimately read 0 or round to 0. Report it as
an informational/low hardening item (reject `price == 0` in the adapter, or
require `repay-amount > 0` unconditionally), not as a critical. Do not submit it
as a critical.

## Checked and currently believed sound (not findings)

- `borrow` and `remove-collateral` both recompute total max-LTV over the
  position's collaterals at fresh oracle prices and assert
  `debt-adjusted <= total-max-ltv` after the state change; a zero price there
  only *reduces* borrowing power (safe direction).
- `repay` allows repaying on behalf of anyone, which is benign (attacker
  spends their own funds to reduce someone's debt).
- Soft-liquidation is enforced by the post-health upper-bound cap, preventing
  over-liquidation of healthy-enough positions.
- `flash-loan` is gated by a governance-managed contract allowlist
  (`allow-any` defaults false), so it is not an open flash-loan primitive.

## Next actions

1. Read state-v1 in full — the balance/share mutations are the real
   fund-safety surface and are unread. Focus on `convert-to-shares` /
   `convert-to-assets` rounding at `add-assets`/`remove-assets` (first-depositor
   / share-inflation class), and whether `transfer-to`/`transfer-from` gate the
   caller (only borrower/lp/liquidator/flash-loan should move pool funds).
2. Read linear-kinked-ir-v1 (interest accrual: can `accrue-interest` be
   front-run or repeated to mint interest, or underflow open-interest?).
3. Only if a hypothesis clears Gate 2, build a Clarinet/`clarinet` unit test as
   the PoC (Clarity's test harness), or a `clarity-repl` script, against the
   fetched sources.

Verdict so far: one low/defense-in-depth candidate, no gate-clearing critical
yet. The accounting core (state-v1) is unread and is where to look next.

## Live on-chain parameters (read 2026-09-13 via Hiro call-read on state-v1)

- sBTC collateral: decimals 8, max-ltv 50%, liquidation-ltv 65%,
  liquidation-premium 10% (all at SCALING-FACTOR 1e8).
- LP pool: total-assets 97,730,902,048 (aeUSDC, 6 dp ≈ $97.7k),
  total-shares 93,765,796,947. Pool is NOT empty → first-depositor
  share-inflation is not live-exploitable now (only relevant for a fresh
  market).
- Debt: open-interest 43,157,180,372 (≈ $43.2k), total-debt-shares
  29,032,383,023. Borrowable balance ≈ $55.5k.
- Governance principal = governance-v1 (contract, not an EOA).

**Soft-liquidation denominator check with live numbers:**
`SCALING - (SCALING + premium) * liq_ltv / SCALING = 1e8 - 1.1e8*0.65 = 0.285e8 > 0`.
No underflow at current settings. It would underflow only if
`(1 + premium) * liq_ltv >= 1` (e.g. liq_ltv ≥ 90.9% with a 10% premium),
which is a governance-parameter-validation issue the program lists as a
KNOWN ISSUE. Not reportable.

**Payout sizing:** Immunefi critical here is 10% of funds affected with a
$25k floor and $100k cap; with ~$97k TVL the floor dominates, so any real
critical pays ~$25k.

**PoC tooling:** `clarinet` cannot be installed in this session (GitHub
releases and crates.io API both 403 behind the egress policy). A Clarity PoC
must be built in an unrestricted environment: `clarinet` project with the
fetched `.clar` sources + a unit test, or `clarity-repl`.

## state-v1 access control — CHECKED, CLEAN (2026-09-13)

Extracted every `define-public` in state-v1 and its gate. Result: every
fund-moving or position-mutating function is behind
`(try! (is-allowed-contract contract-caller))` (governance-managed allowlist
of trusted contracts: borrower, lp, liquidator, flash-loan) or
`(asserts! (is-governance) ...)`. Specifically confirmed gated:
transfer-from (100), transfer-to (108), add-assets (119), remove-assets (138),
update-borrow-state (703), update-repay-state (738), update-add-collateral
(764), update-user-collateral (774), update-remove-collateral (782),
update-liquidate-collateral-state (821), socialize-user-bad-debt (912),
set-accrued-interest (685, allowed-or-governance). `transfer` (442) is the
SIP-010 LP-token transfer with the standard sender check. The
"unprivileged caller erases their own debt" hypothesis is refuted.

Reinforcing detail for the zero-price finding: update-liquidate-collateral-state
line 849 `(if (> repay-amount u0) (transfer-from ...) SUCCESS)` deliberately
skips pulling repayment when repay-amount is 0 while line 847 unconditionally
transfers collateral-to-give to the liquidator. So the state layer has no
independent guard; the only thing preventing a zero-repay seizure is the
liquidator's price-gated `ensure-non-zero-repay-amount`. Severity unchanged
(LOW) because price==0 is not reachable for sBTC/aeUSDC.

Also noted (sound): line 824 forbids liquidating in the same block as the
borrow; the uint subtractions at 745/826/835 underflow-panic in the safe
direction.

Agent fan-out attempted at the user's request was killed by the account's
session rate limit (429, resets 16:30 UTC); continued solo.

## Interest model, staking-reward, withdrawal caps — CHECKED, CLEAN (2026-09-13)

- linear-kinked-ir-v1 `accrue-interest`: elapsed = (prev-block time + 5s) −
  last-accrued; last-accrued is always a previous such value, so no
  underflow; elapsed==0 or accrual-disabled returns unchanged values (no double
  accrual). Compounding is a 6-term Taylor of e^x in 12-dp fixed point; the
  intermediate `(* x x_5)` overflows uint128 only for x ≳ 1000 (e.g. 100% APR
  for 1000 years) — unreachable. Taylor truncation *under*-estimates e^x for
  large x, i.e. under-accrues (hurts LPs marginally, not exploitable).
  `calc-total-interest` `(- ir one-12)` is safe since taylor-6 ≥ one-12.
- Theoretical freeze: `utilization-calc` divides by `total-assets` guarded only
  by `(> (+ total-assets open-interest) u0)`; total-assets==0 with
  open-interest>0 would panic every accrual and freeze all actions. Requires a
  fully drained pool with outstanding debt (degenerate state, not attacker
  reachable). Noted, not reportable.
- Governance-param DoS class (KNOWN ISSUE per program, not reportable): if
  staking-reward% > 100% (slope-1 unbounded, base < 1e8 only), line 106
  `(- lp-interest staked-interest)` underflows and freezes accrual.
- staking-reward-v1: int math guarded; init-once then governance-only setter.
- withdrawal-caps-v1: token-bucket limiter; every check/inflow entrypoint is
  gated to the exact calling contract (LP / borrower / liquidator); refill and
  decay subtractions are guarded by their branch conditions. Deposits credit
  the bucket (inflow), which weakens the limiter as a defense-in-depth but
  cannot exceed a caller's own share balance (state-v1 remove-assets checks
  shares). Unknown collateral tokens no-op the cap (factor 0) and are rejected
  later by state-v1. Design, not a bug.

## governance-v1 + meta-governance-v1 — CHECKED, CLEAN (2026-09-13)

Every vote/execute entrypoint (`approve` 1149, `deny` 1169, `close` 1193,
`execute` 1229, every `initiate-proposal-to-*` via `create-proposal` 296) does
`(try! (is-governance-member contract-caller))`, which resolves to
meta-governance-v1's `governance-accounts` map. Double-vote is blocked by
`has-submitted-vote`; double-execute by `closed`/`executed` flags; votes are
refused once `execute-at` is set (time-lock armed). Proposal ids are keccak of
(sender, nonce, action, expires-in, data) with a monotonic nonce, and
`create-proposal` rejects duplicates. Threshold is integer `approve*100/total
>= 60`; `total` can never reach 0 (remove-member asserts `>= 1` remains).
meta-governance's `initialize-governance` is deployer-only, once. Only
observation: `ACTION_TRANSFER_FUNDS` and `ACTION_UPDATE_PYTH_TOKEN_FEED` are
not in the `time-locked` map, so a 60% multisig can move funds / repoint the
oracle instantly — a privileged-actor design choice, out of scope. No
unprivileged path. Refuted.

## staking-v1 (SP3BJR4...) — REAL BUG FOUND, ALREADY FIXED BY THE PROJECT (2026-09-13)

**Bug.** `slash-total-staked-lp-tokens` (line 200) splits a slash between the
active pool and the unfinalized-withdrawal pool using a lossy two-step
rounding: `rate = floor(W*1e8/T)`, `to-slash = floor(lp*rate/1e8)`. Whenever
`W > 0` and `T` does not divide `W*1e8` (essentially always), `to-slash < W`
in the wipeout case `lp == T`, so `active-to-slash = T - to-slash > A` and
`(- total-lp-tokens-staked active-to-slash)` (line 210) **underflows**. Clarity
uint underflow is a runtime abort, so the whole liquidation transaction
reverts. Reachability: liquidator-v1 `socialize-bad-debt` (504–549) calls
state-v1 `socialize-user-bad-debt` → `slash-staked-lp-tokens` (870) which, when
remaining bad debt ≥ total staked, burns all `T` LP tokens and returns
`tokens-slashed = T`; the liquidator then calls staking `slash` with exactly
`T` (line 549). So the final clean-up liquidation of ANY bad-debt position
larger than the staking pool aborts. Any user can force the precondition
`W > 0` by staking dust and calling `initiate-unstake` without finalizing.
Mainnet state of that contract when checked: T = 99,564,830, A = 99,564,781,
W = 49 → `rate 49, to-slash 48, underflow by 1` (reproduced in Python with
the exact integer ops). `reconcile-lp-token-balance` has the same family of
underflow (`(- staked (accounted - balance))` when deficit > active).

**Why it is NOT submittable (honest verdict).** Reading state-v1's event log
showed the protocol **migrated both markets in Aug 2026**:

- aeUSDC market (state SP35E2...): `set-allowed-contract` for a new set at
  `SP119QJ4NVE3RQP8RXJVW5EXAV3XD4CJZWRCEEAAR.*` on 2026-08-16 (block 8,776,553),
  `remove-allowed-contract` for the Immunefi-listed `SP26NGV9...` and
  `SP3BJR4...` contracts on 2026-08-20, `update-governance` to
  `SP119...governance-v1` on 2026-08-24.
- USDCx market (state SP3M2BYF7..., total-assets ≈ $5.0M, the real TVL):
  same pattern, new set at `SPSX722NK9V3A8D3CVQT0CDY4EBQ3E9FSDDE61FT.*`, old
  `SP3M2...` liquidator/staking/borrower/lp/flash-loan de-allowlisted.

The new staking-v1 (SP119 / SPSX722, both 15.9 KB, same code line) computes
`to-slash = lp*W/T` in one division with a zero guard, which is exactly the
fix, and the new liquidator passes `effective-staked-lp-tokens`. So the bug
was found and fixed by the team before I got there; the in-scope contract
that still carries it is de-allowlisted (its liquidator can no longer call
state-v1, so the path is dead), and the only residual is ~$103 of stuck
stakers in the old contract. A report would be closed as fixed/no-impact.
Recorded as a **true positive that was pre-empted**, which is useful
calibration: the method finds real bugs; the target was stale.

**Scope consequence.** The Immunefi page ("Last Updated 25 July 2026", 31
assets) predates the migration and lists only the OLD contract sets
(SP26NGV9, SP3BJR4, SP3M2BYF7, SP35E2 core, plus Pyth/wormhole). The live
money sits in `SPSX722.*` (USDCx, ~$5M) and `SP119.*` (aeUSDC, ~$97k), which
are not listed. Those are fresh (published ~Aug 2026), lightly exposed, and
the program page has not caught up — the best remaining EV on this target.
Any submission there must state plainly that the scope page lists the
predecessor deployment; acceptance is at the project's discretion.
