# Findings log

One row per audit pass. Log every pass, including the ones that found nothing —
a clean "nothing found" is a real result and stops the target being re-audited
blindly. Only a row that reaches `submitted` involved a human pressing send.

| Date | Target | Scope ref | Candidates | Survived gate | Status | Payout |
|---|---|---|---|---|---|---|
| 2026-09-12 | ENS standing bounty | ens-contracts @ 121dc23 | 1 (CCIP batch error handling) | 0 (refuted) | nothing_found | — |
| 2026-09-13 | 1inch smart contracts | cross-chain-swap @ 1.1.0 (EVM + Solana) | 2 (partial-fill index parity; Solana safety-deposit accounting) | 0 (both cleared) | nothing_found | — |
| 2026-09-13 | 1inch smart contracts | limit-order-protocol @ 4.3.2 (OrderMixin core) | 0 | 0 | nothing_found | — |
| 2026-09-13 | Granite Protocol (Immunefi-listed sets) | on-chain Clarity, 15 contracts + meta-governance | 2 (zero-price liquidation seize, LOW; staking slash rounding underflow, real but pre-fixed) | 0 (LOW not worth a report; slash bug fixed by project in Aug-2026 redeploy, listed contracts de-allowlisted) | nothing_submittable | — |
| 2026-09-13 | Granite Protocol (live SPSX722/SP119 sets) | on-chain Clarity, Aug-2026 redeploy, not yet on scope page | 0 | 0 | auditing | — |

Status values: `auditing` · `nothing_found` · `drafting` · `awaiting_human_signoff` · `submitted` · `accepted` · `paid` · `rejected` · `duplicate`

No row moves to `submitted` until it has cleared every gate in
`../playbook/self-refutation.md` and a human has read the proof of concept.

## 2026-09-12 — ENS first pass

Read the money path and the freshly-changed resolution machinery on the live
mainnet scope (repo head 121dc23, 2026-09-11). No hypothesis cleared Gate 2 of
the self-refutation gate, so nothing is being drafted. This is an honest
"nothing found yet", not a finished audit — see `audit-notes-ens.md` for what
was covered, what was not, and the one lead worth continuing.
