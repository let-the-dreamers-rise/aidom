# ALEX AMM v2 (Stacks) — audit notes

Date: 2026-09-30
Program: ALEX has a live Immunefi program (fee-unknown until form, per hard
constraint #1). $8M+ historical exploits (2023 orderbook, 2024 self-listing/
bridge) — but those were key-compromise / peripheral, not the AMM core.
Source: deployed Clarity via boomcrypto mirror. Deployer
SP102V8P0F7JX67ARQ77WEA3D3CFB5XW39REDT0AM.

## Scope covered
- `amm-vault-v2-01` (fund custody), `amm-pool-v2-01` (AMM logic, 621 lines,
  incl. permissionless self-listing create-pool), `amm-registry-v2-01`
  (per-pool state), `token-amm-pool-v2-01` (LP semi-fungible token).

## Result: sound (no fund-loss path found)
- **Vault** is a dumb custodian gated by `is-dao-or-extension`
  (tx-sender=executor-dao OR contract-caller is a registered DAO extension).
  Only extensions (the pool) can move funds; flash-loan enforces repayment
  (final transfer-fixed of amount+fee back, else revert). Sound.
- **Fake-token drain (the classic self-listing attack) is defended.** The
  vault commingles each token across pools, BUT per-pool balances live in the
  registry and every swap/withdraw is bounded by the pool's own tracked
  balance-x/balance-y, with `max-out-ratio` asserting output < balance * ratio
  (<1). So a pool can never instruct the vault to pay out more of a token than
  that pool holds → a malicious self-listed pool (real token vs attacker's
  fake token) cannot reach other pools' funds. dx < balance-x always.
- **Swap conservation**: full dx enters the vault; balance-x += dx-net-fees +
  fee-rebate; reserve += (fee - fee-rebate). Output bounded by a spot-price
  assertion (`dy/dx <= spot`). Balanced.
- **LP token** mint/burn gated by is-dao-or-extension (pool-only). 
- **Registry create-pool** rejects duplicates in BOTH token orderings
  (ERR-POOL-ALREADY-EXISTS) — no overwrite/hijack of an existing pool.
- Self-listing param setters (fee-rate, thresholds, ratios, start/end block)
  are gated to `pool-owner OR dao`, and only affect that owner's own pool —
  LPing into an attacker-owned pool is the LP's risk (by design), not a
  protocol-wide drain.

Core weighted-AMM math (get-y-given-x-internal etc., pow/exp/ln fixed-point)
is the long-audited ALEX engine; conservation + bounds hold at the call sites.
No high-confidence finding. Consistent with a heavily-audited protocol.

## UPDATE — v1 self-listing pool + sponsor wrapper (less-audited surface)
- `SP3K8BC0…amm-swap-pool-v1-1` (v1 self-listing, 1070 lines): SAME architecture
  as v2 — `.alex-vault-v1-1` custody + map-tracked per-pool balances +
  `.token-amm-swap-pool-v1-1` LP token. create-pool is permissionless (self-
  listing) and seeds via add-to-position with total-supply=0; initial LP =
  invariant(dx,dy), subsequent = proportional (total-supply*dx/balance-x). No
  first-deposit inflation attack: balance-x is map-tracked, not the vault's raw
  balance, so a donation can't inflate share price. Conservation identical to
  v2. Sound.
- `sponsored-amm-swap-pool-v1-1`: thin meta-tx wrapper — prepays a sponsor fee
  (tx-sponsor?) then forwards to the v1 pool; tx-sender preserved, no auth/fund
  bug.
- The many per-user `amm-swap-pool-v1-1` copies under other deployers are small
  owner-gated (`tx-sender == A`) personal scripts, not protocol surface.

## Overall ALEX verdict: sound. No payable finding.
