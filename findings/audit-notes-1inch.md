# 1inch cross-chain-swap audit notes — 2026-09-13

Target: 1inch smart contracts bug bounty (Immunefi), $500k cap, no fee, KYC at
payout. Program prohibits AI-generated reports, so any actual report here must
be authored and submitted by the human in their own words from the verified
finding and PoC. These notes are internal working material, not a report.

Scope is 8 repos at their latest tag/release. This pass covered the
cross-chain atomic-swap core on both chains.

## Source read closely (no gate-clearing finding)

- **EVM cross-chain-swap @ 1.1.0** (deployed on mainnet; the mainnet
  EscrowFactory broadcast is at commit fcfdb91, tag 1.1.0): BaseEscrow,
  Escrow, EscrowSrc, EscrowDst, BaseEscrowFactory, EscrowFactory,
  MerkleStorageInvalidator, TimelocksLib, ImmutablesLib, ProxyHashLib.
- **EVM deps in scope's call path**: limit-order-protocol @ 4.3.2
  FeeTaker + AmountGetterWithFee (fee/whitelist parsing), fusion-protocol
  @ 3.1.1 SimpleSettlement (auction + whitelist override).
- **Solana cross-chain @ 1.1.0**: cross-chain-escrow-src, -dst, whitelist,
  auction, merkle_tree, and the shared common crate (escrow, timelocks). All
  three programs confirmed live on mainnet under the upgradeable BPF loader.

## Two suspicious things checked and cleared

1. **Partial-fill index parity between EVM and Solana.** The two
   `is_valid_partial_fill` implementations use different constant offsets
   (EVM: `+1` normal / `+2` final; Solana: `+0` / `+1`). This looks like a
   discrepancy but is consistent: EVM's MerkleStorageInvalidator stores
   `ValidationData(idx + 1, ...)` so its `validatedIndex` is already
   `idx + 1`, while Solana passes `proof.index` directly. Reduced, both
   require `proof_index == calculatedIndex` for a normal fill and
   `== calculatedIndex + 1` for the final complete fill. Not a bug.

2. **Safety-deposit vs. rent accounting on Solana public_withdraw /
   public_cancel.** The safety deposit is carved out of the escrow account's
   own rent (`safety_deposit <= rent_exempt_reserve` enforced at creation).
   On a public action the body does `escrow.sub_lamports(safety_deposit)` to
   the public caller and Anchor's `close = taker` sends the remaining
   `rent - safety_deposit` to the taker. Since `safety_deposit <= rent` and
   the escrow holds exactly its rent, there is no overdraft or double-pay.
   Not a bug.

## Honest coverage boundary (not yet read)

limit-order-protocol core (OrderMixin and the bit-packed traits libraries),
token-plugins, farming, delegating, and solana-fusion. The LOP OrderMixin is
the largest and most intricate surface and is the highest-value place to look
next; it was only read at the FeeTaker/settlement edges touched by the escrow
factory.

## PoC environment is ready

The Solana workspace uses `solana-program-test` with a full harness in
`common/tests` (order/escrow creation, `set_time` clock warping, resolver
whitelisting, balance-change assertions). `cargo fetch` already succeeded in
this environment, so a finding in the Solana programs could be turned into a
runnable test quickly. The EVM repos use Foundry (`forge`), which is blocked
by the session egress policy (403 on the GitHub attestation host); an EVM PoC
would need Foundry installed in a less restricted environment, or a Hardhat
harness built against the npm dependency set.

## Verdict

No hypothesis cleared Gate 2 of the self-refutation gate on the code read so
far. Nothing drafted. The next pass should read the LOP OrderMixin core.
