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

## 2026-09-13 addendum — limit-order-protocol core read

Read the LOP @ 4.3.2 core that the escrow factory builds on: OrderMixin
(fill/cancel/invalidator flow), OrderLib (EIP-712 hashing, amount getters,
`isValidExtension`), ExtensionLib and OffsetsLib (the offset-packed extension
parser). This is the highest-value surface in the 1inch scope and it is also
the most audited. Findings: none that clear the gate.

Notes for the record (all standard, accepted 1inch design, not bugs):
- Signature is verified only on the first fill (`remaining == makingAmount`);
  later partial fills are gated by the remaining-invalidator. Maker-permit
  first-fill path has an explicit reentrancy check on the remaining slot.
- The order invalidator is written BEFORE the maker->taker / taker->maker
  transfers and interaction hooks, which is the correct ordering for
  reentrancy safety.
- `isValidExtension` binds only the low 160 bits of keccak(extension) to the
  low 160 bits of the salt; a second extension colliding there is a 160-bit
  search, infeasible, and a malicious maker only signs against their own order.
- `OffsetsLib.get` checks `end <= concat.length` but not `begin <= end`; a
  malformed offset table underflows `length`. The offset table is part of the
  maker-signed extension, so a maker can only craft it against their own order
  (extension is hash-bound to the salt); it is not a taker-fund vector. Noted
  as understood, not a finding.
- `unchecked { makingAmount * takingAmount == 0 }` can only wrap to zero for
  factors with huge 2-adic valuation, which fails safe (reverts), never opens
  a zero-amount swap.

Conclusion: 1inch is exhausted for this operation's purposes at a read level.
Marqueree, heavily-audited protocols (ENS, 1inch) are the wrong pool. Pivoting
to newer, smaller, less-competed programs.

## Solana `rescue_funds_for_order` (src escrow) — CLEARED, out of scope (2026-09-13)

Observed: any whitelisted resolver can call `rescue_funds_for_order` for any
`mint` once `rescue_start` (order creation + RESCUE_DELAY 8 days) has passed;
there is no expired/closed check, and an escrow with empty data rescues at
once. Refutation: the caller must be a **whitelisted resolver** (a KYC'd,
permissioned role), which Immunefi's default rules put out of scope
("attacks requiring access to privileged addresses"); rescue is the intended
recovery path for tokens stuck after the swap window; the maker can
`cancel_order` before day 8, and expired orders are cancellable by resolvers
for the premium by design. No unprivileged path. Not a finding.
