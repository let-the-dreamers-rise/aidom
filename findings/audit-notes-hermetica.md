# Hermetica audit notes — 2026-09-14

Target: Hermetica (USDh Bitcoin-backed synthetic dollar + hBTC vault) on Stacks.
Program: Immunefi, up to $100k, Primacy of Impact (added 2026-03-31), live since
2026-02-12, PoC required. Fee status unknown (Immunefi may fee-wall at submit
time, like StackingDAO — direct disclosure is the fallback).
Deployer: SPN5AKG35QZSK2M8GAMR4AFX45659RJHDW353HSG.
Source: github.com/hermetica-fi/hermetica-contracts @ 5e13e43 (2026-04-02).
Deployed code cross-checked against Hiro (repo uses versionless refs; on-chain
uses -v1 names — DEPLOYED staking-v1-1 confirmed to match the audited logic).

## Audited, well-built (no high-confidence bug)

- **USDh mint/redeem** (`minting-auto-v1-2`, `minting-v1`): fully permissioned.
  `is-minter`/`is-redeemer`/`whitelisted` gates; `confirm-mint`/`confirm-redeem`
  gated to `minter`/`redeemer` trader roles. Pyth pricing with confidence +
  staleness (`publish-time > delayed-block-time`) checks. The `none` price-feed
  branch defaults to 1.0 but is bound to `price-feed-id == 0x00` assets only
  (stablecoins) via the `ERR_PRICE_FEED_MISMATCH` assert, so it can't misprice a
  real asset. Slippage and rounding both favor the protocol. Not externally
  callable for unbacked mint.
- **staking-silo-v1-1**: `create-claim` gated to `.staking`; `withdraw` pays the
  stored recipient (no theft by triggering others' claims); transfer-then-delete
  is safe (no Clarity reentrancy hook); `withdraw-many` over duplicate ids can't
  double-spend (2nd application returns an error value without rolling back).
- **hBTC vault-v1-2**: tracks `total-assets` as an INTERNAL accumulator via
  `update-state` (not a live balance read) → immune to the donation inflation
  attack. `cancel-redeem` asserts `(is-none assets)` (no cancel-after-fund),
  `process-claim` asserts `(is-none assets)` (no double-fund), `redeem-peg-out`
  spends the user's own sBTC (tx-sender), not the vault's → no double-spend.

## Finding (Low today; conditional High) — sUSDh staking lacks inflation protection

`staking-v1-1.get-usdh-per-susdh` computes the share ratio as
`usdh-balance(staking-reserve-v1) * 1e8 / susdh-total-supply`, reading the
reserve's LIVE token balance. `stake` mints `amount * 1e8 / ratio` sUSDh
(rounds down); there are no dead shares / virtual offset. Because the reserve
balance is a live read, anyone can inflate `ratio` by transferring USDh directly
to `staking-reserve-v1` (a permissionless SIP-010 transfer). Classic
first-depositor / donation inflation attack: at low supply an attacker mints 1
sUSDh, donates a large amount, and later stakers' share amounts round to 0 while
the attacker's single share captures their deposits.

Severity is CONDITIONAL:
- NOT currently exploitable: live sUSDh supply is ~1.06M (0x6327461cd0b9 base
  units). At that supply the attacker recovers only their dust pro-rata share of
  any donation → unprofitable.
- Becomes HIGH ("theft of staker deposits") on any fresh staking redeploy
  (supply starts at 0) or if supply is ever drawn down near zero.
- Notably, Hermetica's OWN hBTC vault avoids this by using internal accounting.
  The staking contract is the inconsistent one.

Fix: seed dead shares on first stake, use a virtual offset (assets+1/shares+1),
or track staked USDh as an internal accumulator like the hBTC vault does, rather
than reading the donatable reserve balance.

Honest read: this is a real, verifiable design gap but Low on the live protocol
(no current impact), so a bounty may treat it as informational. Worth a quiet
direct disclosure; do not oversell it as a confident payout.

## Not yet audited (continuation)

`controller-v1-1`, `hbtc/state-v1` (`convert-to-shares`/share-price internals),
`hbtc/reserve-v1`, the Granite/Zest interfaces (`granite-interface-v1`,
`zest-interface-v1`, `hermetica-interface-v1`) — cross-protocol accounting is
the most bug-prone remaining surface.
