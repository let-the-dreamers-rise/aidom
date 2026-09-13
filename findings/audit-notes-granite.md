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
