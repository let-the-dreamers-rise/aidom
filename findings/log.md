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
| 2026-09-13 | Granite Protocol (live SPSX722/SP119 sets) | on-chain Clarity, Aug-2026 redeploy + Pyth Lazer oracle, not yet on scope page | 3 observations (5-min stateless price window; de-listed collateral stuck; staker-interest timing) | 0 (design / governance / dust) | nothing_found | — |
| 2026-09-13 | StackingDAO | on-chain Clarity, 36 listed + post-scope versions, PoX-5 stBTC launch (Aug 2026) | 2 verified: (1) stBTC gets 0.004% of the sBTC reward stream, High-tier argument, ~USD 21.6k short to date; (2) ungated save-pending-rewards bricks claims on deactivated positions, Low today | 1 (report 01 clears all four gates) | submitted 2026-09-13 by direct private disclosure (email to team, PDF + verifier attached); Immunefi form demanded 50 USDC. Report 02 held in reserve. Follow-up: DM @StackingDAO on X if no reply by 2026-09-18 | pending |

Status values: `auditing` · `nothing_found` · `drafting` · `awaiting_human_signoff` · `submitted` · `accepted` · `paid` · `rejected` · `duplicate`

No row moves to `submitted` until it has cleared every gate in
`../playbook/self-refutation.md` and a human has read the proof of concept.

## 2026-09-12 — ENS first pass

Read the money path and the freshly-changed resolution machinery on the live
mainnet scope (repo head 121dc23, 2026-09-11). No hypothesis cleared Gate 2 of
the self-refutation gate, so nothing is being drafted. This is an honest
"nothing found yet", not a finished audit — see `audit-notes-ens.md` for what
was covered, what was not, and the one lead worth continuing.
| 2026-09-14 | huntr channel pivot | protectai/ai-exploits calibration | — | — | scoped | broadened beyond Stacks to open-source AI/ML (fee-free, PoC-able in-sandbox) |
| 2026-09-14 | mlflow (huntr) | mlflow-src HEAD 7c8c3f8 (FastAPI server, jobs/scorers) | artifact traversal; model source LFI; jobs→scorer deserialization RCE | 0 | nothing_found | scorer exec databricks-gated; third-party import closed-set; builtin getattr has no dangerous callable; artifact/source hardened |
| 2026-09-14 | bentoml (huntr) | bentoml-src HEAD 517b343 | pickle serde RCE (CVE-2024-2912 class) | 0 | nothing_found | main server rejects application/vnd.bentoml+pickle ("DO NOT REMOVE"); exact dict lookup, no bypass; pickle only on internal runner servers |
| 2026-09-14 | gradio (huntr) | gradio-src HEAD d99a49a v6.27.0 | file-route path traversal (in progress) | — | auditing | GET /file={path} + is_in_or_equal guard |
| 2026-09-14 | transformers (huntr $50k) | transformers-src HEAD f24b457 v5.18 | deserialization on load path; chat-template SSTI | 0 | nothing_found | torch.load gated (weights_only/check_torch_load_is_safe); pickle behind TRUST_REMOTE_CODE; chat templates use ImmutableSandboxedEnvironment |
| 2026-09-14 | mlflow assistant/sandbox + gateway | mlflow-src HEAD 7c8c3f8 | unauth RCE via assistant; gateway SSRF sibling | 0 | nothing_found | assistant remote-access opt-in + safe-provider gate + XFF-safe localhost check; gateway SSRF has dedicated ssrf.py (public-only resolver, IP-literal canonicalization, write-time api_base validation) |
| 2026-09-14 | ray dashboard (channel: security@anyscale.com; huntr cash unconfirmed) | ray-src HEAD 65127d7 | log/file path traversal (LFI) | 0 | nothing_found | _resolve_filename blocks ../ + absolute via abspath+relative_to; symlink-follow is deliberate/local-only; aiohttp static default-guarded |
| 2026-09-14 | Zest V2 Strategy Vault (Clarity, my edge) | work/zest zv-engine/ops/state | share-price/NAV manip; redeem wrong-token withdrawal; fee dilution | 0 | nothing_found | dead-shares vs inflation; redeem token pinned to stBTC + engine-gated; min(quoted,claimable); conservative rounding |
| 2026-09-14 | Zest V2 lending core (Clarity) | work/zest v0-8-market liquidation | healthy-liquidation; liquidator over-seize; close-factor bypass | 0 | nothing_found | health check (ltv>=partial), close-factor cap, same-block guard, EOA-only, conservative rounding, dust handling all correct |
