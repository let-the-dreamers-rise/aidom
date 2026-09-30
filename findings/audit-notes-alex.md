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
