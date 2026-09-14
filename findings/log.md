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
| 2026-09-14 | feast (feast-dev/feast) | feast-src HEAD b7a8928 (registry gRPC server, no_auth default) | 2 pre-auth RCE handlers: ApplyMaterialization (exec/dill via resolve_udf, core-only) + ApplyValidationReference (dill via GEProfiler, needs ge extra) | 0 (verified real + 3 runnable PoCs, but DUPLICATE of public CVE-2026-18948) | nothing_submittable | — |

## 2026-09-14 — feast: real pre-auth RCE, but duplicate of CVE-2026-18948

Hunted siblings of CVE-2026-56121 (ApplyFeatureView dill.loads-before-authz, fixed
0.63.0 via skip_udf). Found the skip_udf fix was applied only to ApplyFeatureView:
`ApplyMaterialization` and `ApplyValidationReference` still evaluate
`<Object>.from_proto(request...)` as the `resource=` argument to `assert_permissions*`,
so attacker UDF bytes hit `exec(body_text)`/`dill.loads(body)` (via `resolve_udf`)
and `dill.loads` (via `GEProfiler`) before authorization. Default `no_auth` config =
unauthenticated; auth-enabled = any authenticated principal. Verified end-to-end on
HEAD with three runnable PoCs (unauth network RCE as uid=0 on the real gRPC server;
plus an ordering proof). Still unpatched at HEAD.

Killed at the self-refutation duplicate gate: this is a specific instance of
**CVE-2026-18948** ("Unsafe dill deserialization of registry-stored UDFs", CVSS 9.9,
published 2026-08-10), which names the same sinks (python_transformation.py:168,
ge_profiler.py:158, …) and the same "from_proto before assert_permissions_to_update"
root cause. Submitting = duplicate of a public Critical CVE → no pay, ban risk. Not
submitted. Also: Feast discloses via GHSA (no confirmed paid channel), and its
SECURITY.md rejects AI-generated reports. Pivot away from Feast. See
`audit-notes-feast.md`; PoCs kept as evidence in `submissions/feast/` (marked
NON-SUBMITTABLE).
| 2026-09-14 | lollms (parisneo/lollms) | lollms-src HEAD a744154 (FastAPI social app, backend/routers) | 1 (DM reactions IDOR: read any private DM + write reactions, unreported) | 1 (cleared Gates 1-3, PoC runs real endpoint) | awaiting_human_signoff | pending |

## 2026-09-14 — lollms: DM reactions IDOR (SUBMITTABLE)

Applied the Feast lesson: duplicate-check-FIRST recon picked lollms — a fresh,
funded, fast-moving FastAPI social app that keeps earning 2026 huntr bounties
(path traversal, SSRF, friends IDOR, prompts XSS), with a maintainer who patches
one endpoint and leaves siblings. Hunted siblings of CVE-2026-0562 (friends IDOR).

Found: `POST /api/dm/messages/{message_id}/reactions` (`toggle_dm_reaction`,
backend/routers/social/dm.py) fetches a DirectMessage by integer PK with NO
participant check and returns DirectMessagePublic (incl. content). Any
authenticated user reads EVERY private DM by enumerating the id, and writes
reactions to arbitrary messages. Registration open by default. Verified on today's
HEAD with a PoC that runs the real endpoint (attacker eve read alice→bob content +
wrote her reaction). High, CVSS ~7.1 (sibling friends IDOR was 8.3). Duplicate-
checked: no CVE covers this endpoint. See audit-notes-lollms.md + submissions/lollms/.
Awaiting Gate 4 (human reproduces + rewrites in own words + submits). File-read
class found largely hardened (secure_filename + containment everywhere now).
| 2026-09-14 | GitLab (gitlab-org/gitlab, HackerOne) | gitlab-src 19.4.0-pre master | GraphQL authz gaps | 0 | nothing_found | Defense-in-depth: type-level authorize gates resolver .find; bulk runner ops authorize per-object in service; new AI mutations use authorize_granular_token. Hardened. Pivoted to Mattermost. |
