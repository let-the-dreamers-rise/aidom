# The Graph — audit notes

Program: Immunefi standing bounty (https://immunefi.com/bug-bounty/thegraph/information/)
Scope ref: graphprotocol/contracts @ 1c9eefd (deployment/mainnet/2026-08-26/gip-0089)
Reward tiers: Critical $15k–$50k (10% of funds affected), reproducible-script PoC required, local-fork only.
Pass date: 2026-09-17

## Strategy
The repo is a large, long-audited monorepo. EV is only positive on the *freshest*
code (fewest prior eyes). Targeted the Graph Horizon payments + rewards surface and
the genuinely-novel (not a legacy port) `issuance` package. Legacy `packages/contracts`
(Staking/Curation/GNS/etc.) deliberately not re-audited — heavily reviewed, stale.

## Covered this pass (money-flow + signature surfaces)

### horizon/payments
- **GraphPayments.collect** — protocol→dataService→delegation→receiver split. Order/rounding
  (`mulPPMRoundUp` on remainder each step) cannot underflow; cuts validated PPM. Clean.
- **PaymentsEscrow** — escrow keyed (payer, collector, receiver). `collect` gated to
  `msg.sender == collector`; balance-invariant check via balanceOf before/after; thaw/withdraw
  min-capped; collection takes priority over thaw (caps tokensThawing to new balance). Clean.
- **GraphTallyCollector** — EIP-712 RAV, monotonic `valueAggregate`, per-(dataService,collectionId,
  receiver,payer) collected tracker, partial-collect bounded by `RAV - alreadyCollected`. OZ ECDSA
  (reverts on malleable/zero sig). Provision check (`getProviderTokensAvailable>0`) blocks
  signer-as-dataService siphon. Clean.
- **RecurringCollector (1425 lines, freshest payments)** — RCA/RCAU EIP-712 with chainId; nonce
  monotonic on updates; agreementId = keccak(payer,dataService,serviceProvider,deadline,nonce);
  rate cap `min(tokens, maxOngoingTokensPerSecond*min(elapsed,maxSecondsPerCollection) + maxInitialTokens`
  once). Initial bonus consumable once (lastCollectionAt gate). Post-cancel window collapses
  (collectionStart>collectionEnd → not collectable) so no repeat final collect. Payer callbacks are
  gas-capped (MAX_PAYER_CALLBACK_GAS, 63/64 precheck) and returndata-bounded; eligibility failure is
  fail-open by design (documented). All state-changing entrypoints require `msg.sender == dataService`.
  No over-collection or replay found.
- **Authorizable** — signer→one-authorizer-ever mapping (no cross-authorizer reuse); proof binds
  chainid+address(this)+deadline+msg.sender; thaw/revoke gated to authorizer. Clean.

### subgraph-service
- **AllocationHandler (freshest single file, 2026-05-29)** — port of legacy allocation/rewards.
  Allocation proof requires `ECDSA.recover == allocationId` (anti-frontrun). presentPOI snapshots
  rewards before distribute (no double-count); condition machine take/reclaim/defer correct
  (TOO_YOUNG/DENIED early-return without snapshot to preserve rewards). Delegation split via
  `mulPPM`; over-alloc auto-downsize. No reward-inflation path found.

### issuance (NOVEL — best EV, examined closely)
- **IssuanceAllocator.distributeIssuance()** — permissionless, intentionally NO reentrancy guard.
  Hypothesis: double-distribution via reentrancy before `lastDistributionBlock` is set post-mint.
  REFUTED: distribution loops only call `GRAPH_TOKEN.mint(target,amount)`; GRT is a plain ERC-20
  (no ERC-777/transfer hooks), so minting never yields control to a target. The only target-callback
  path (`_notifyTarget`) is reached solely from GOVERNOR_ROLE + nonReentrant functions
  (setIssuancePerBlock/notifyTarget). selfMintingOffset reconciliation: permissionless path always
  full-catches-up (offset→0); partial catch-up is governor-only. 100%-allocation invariant held via
  default target absorbing remainder. No double-mint / over-issuance found.

## Not covered (candidate future passes)
- `HorizonStaking` (23 files) delegation/thaw/slash math — large, partly legacy, not this pass.
- `DisputeManager` slashing/arbitration economics.
- `issuance/RecurringAgreementManager` (1073 lines) and `RewardsEligibilityOracle` internals.
- Scope caveat: confirm on the live Immunefi asset list that the `issuance` package + Horizon
  contracts are pinned in-scope by deployed address before any report — GIP-era contracts may not
  yet be listed (same stale-scope pattern seen on Granite).

## Verdict
No hypothesis cleared Gate 2 on this pass. Honest `nothing_found` for the Horizon payments/rewards
+ issuance surface. Highest remaining EV if revisited: `issuance/RecurringAgreementManager` and the
HorizonStaking delegation/slashing math, each with a Foundry fork harness.
