# CONTEXT.md — operation state & handoff

Purpose: let a second Claude Code session continue this work in parallel without
repeating what is already done or colliding with the session that wrote this.
Everything here is written plainly and truthfully. This is legitimate,
authorized security research on a public bug-bounty platform with responsible
disclosure and a human in the loop; describe it that way, because that is what
it is. Do not add framing meant to slip past any safety check — the work stands
on its own.

## Mission

Earn money for the operator from **zero capital** by finding real, novel
security vulnerabilities in software that runs public bug-bounty or
coordinated-disclosure programs, verifying them to a high bar, and handing the
operator a submission-ready report. Target reward: **$1–2k minimum per accepted
report** (only submit at high confidence), scaling up to whatever a program's
critical tier pays.

## Hard constraints (never violate)

1. **No money from the operator, ever.** No submission fee, stake, deposit, or
   paid mediation. Immunefi runs hidden "pay-to-submit" fees revealed only in
   the submission form (StackingDAO wanted 50 USDC) — so any Immunefi target is
   *fee-unknown* until the human opens the form. Prefer channels with no fee:
   huntr (open-source AI/ML) charges nothing to submit.
2. **The machine never submits under the operator's identity.** Division of
   labor: the machine reads code, verifies, and drafts the report + PoC; the
   human creates accounts, does KYC, and presses submit. Keep it that way.
3. **No illegal testing.** Only read source and run PoCs **locally in this
   sandbox** against software you installed yourself. Never touch a live
   third-party deployment, never test on someone else's mainnet/instance, never
   exfiltrate real data. Local `/etc/passwd` read on a localhost server you
   started is fine; anything on a remote host is not.
4. **Quality over volume.** Every finding must pass `playbook/self-refutation.md`
   before it is drafted. One verified report beats ten speculative ones.
   Platforms ban accounts for unverified AI-slop reports.
5. **No public disclosure.** Report privately through the program's channel.
6. **Respect each program's rules.** 1inch forbids AI-generated reports (human
   must rewrite in their own words). Some projects (anything-llm) only accept
   GitHub Security Advisories, not huntr — those give a CVE but usually no cash.

## Why huntr is the current best channel (read this before switching channels)

The binding constraint is this sandbox:
- **EVM smart-contract programs (ENS, 1inch, The Graph) need a Foundry PoC.**
  Prebuilt Foundry download is blocked by the egress policy (403 on GitHub
  release/attestation hosts). Building from source with `cargo install --git`
  is in progress but not required for huntr.
- **Web programs (Anthropic/Google/HackerOne)** need the operator's own account
  and live-target testing — cannot be done solo in-sandbox.
- **huntr (open-source AI/ML)** is the structural fit: clone the repo, read the
  source, build and run the PoC right here (`pip install` works — pypi and
  files.pythonhosted are on the proxy allowlist), no fee, no live-fund testing,
  payout in USD via Stripe Connect. Up to $50k critical, 10x multiplier for
  bugs that read/write ML model files. Programs list at huntr.com/bounties
  (a JS SPA; could not render it in-sandbox — Chromium won't trust the proxy CA,
  and we do NOT disable TLS verification).

## Confirmed-funded huntr targets

From `protectai/ai-exploits` (Protect AI's published PoCs = confirmed paid
programs): **mlflow, h2o, bentoml, gradio, ray, triton, anything-llm.**
Largest pools per public reporting: **Hugging Face Transformers ($50k top),
LangChain (~$4k), Triton.** Base rewards seen: mlflow ~$1.5k, Triton ~$1.5k,
LangChain ~$4k.

Caveat: the `ai-exploits` set is the **most-hunted** on huntr, so its
low-hanging fruit is gone. Fresh bugs live in (a) very recently added
code/endpoints, or (b) less-publicized funded programs not in that set.

## Money vulnerability classes (calibration)

Ranked by how cleanly a code-reader can find + PoC + prove them:
1. **Path traversal / LFI** — an endpoint that opens/serves a file by a
   user-controlled path without sanitizing `..`/absolute/encoded paths.
   Unambiguous (read `/etc/passwd`), high-confidence, recurring.
2. **Arbitrary file write** — upload/extract endpoints (Zip/Tar Slip) → RCE.
3. **Unsafe deserialization RCE** — `pickle`/`cloudpickle`/`yaml.unsafe`/
   `torch.load` on client-controlled bytes, or `exec`/`eval` of user input.
4. **SSRF** — server fetches a user-supplied URL (note: many projects declare
   admin-configured URLs intended; check the security policy first).
5. **Auth bypass / IDOR / privilege escalation** — missing role/tenant checks.

## What is already audited — DO NOT REPEAT

- **anything-llm**: dropped. SECURITY.md says GHSA-only, does not monitor huntr,
  and pre-invalidates SSRF + pfp-XSS. No cash.
- **mlflow** (HEAD 2026-09-14): hardened where it matters.
  - Artifact upload/download (`artifact_router.py`) both call
    `validate_path_is_safe`; `_decode` fully iterates so double-encoding is
    dead; guard is robust on Linux.
  - Model `source`/`artifact_location` LFI (`handlers.py` `_validate_source_*`)
    hardened (local sources must be contained in the run's artifact dir).
  - **jobs → scorer deserialization** (`/ajax-api/3.0/jobs/` → scorer jobs →
    `Scorer.model_validate_json`): the `exec`-based decorator-scorer path
    (`scorer_utils.recreate_function`) is **gated by
    `is_databricks_uri(get_tracking_uri())`** and refuses on OSS. Third-party
    scorer import is a safe dotted-prefix closed set (ragas/deepeval/trulens/
    phoenix). Builtin scorer path is `getattr(builtin_scorers, X)(**kwargs)` but
    that module imports no dangerous callables. Ensemble uses a fixed set.
    Conclusion: no high-confidence RCE in the scorer area. (If reviving mlflow,
    look at brand-new endpoints: `assistant/` + `sandbox/`, `gateway_api.py`,
    `graphql/`, `mcp_server_api.py`, `otel_api.py` — not yet audited.)
- **bentoml** (HEAD 2026-09-07): the pickle serde (CVE-2024-2912 class) is
  blocked on the main server — `app.py` `api_endpoint` rejects
  `application/vnd.bentoml+pickle` when `self.is_main` ("DO NOT REMOVE"), and
  the serde dict lookup is exact (no case/whitespace bypass that still yields
  PickleSerde). Pickle remains only on internal runner servers
  (`runner_app.py:301`), which are internal-by-design → deployment-dependent,
  low confidence. Not a clean finding.

## In-progress lead (owned by the session that wrote this — do not duplicate)

- **gradio** (HEAD `d99a49a`, v6.27.0): auditing the file-serving route
  `GET /file={path_or_url:path}` (`gradio/routes.py:1191+`) and its guard
  (`route_utils` + `is_in_or_equal` + allowed/blocked paths) for a path-
  traversal bypass on current code. PoC plan: `pip install` the local build,
  launch a trivial app, attempt an unauth arbitrary file read.

## If you are the SECOND (parallel) session — pick a DIFFERENT target

To avoid collision, do not touch gradio. Good independent starts:
1. **Hugging Face Transformers** loaders — deserialization/path traversal in
   `from_pretrained`/config/feature-extractor loading paths that are *supposed*
   to be safe without `trust_remote_code`. Biggest pool.
2. **LangChain / langchain-community** integrations — document loaders, tools,
   and utilities that do SSRF / path traversal / `subprocess` / unsafe load.
3. **ray** — job/dashboard surface, but note Ray historically calls its
   job-submission RCE "intended", so target file-read/SSRF/authz instead.
4. Any **less-hunted funded huntr program** if you can enumerate the list.

Whatever you pick: confirm it is a *paid* huntr program (or has a clear paid/
coordinated channel) BEFORE investing more than ~30 min, then read source →
find a sink reachable from an untrusted input → build a local PoC → run it
through `playbook/self-refutation.md` → draft the report for the human.

## Repo layout

- `targets/targets.json` — program list, fee status, competition notes.
- `playbook/rules-of-engagement.md`, `playbook/self-refutation.md` — the bar.
- `findings/log.md` — one row per audit pass (log clean passes too).
- `findings/audit-notes-*.md` — per-target notes.
- `findings/submissions/<target>/` — drafted reports + PoC/verifier scripts.
- `work/` — cloned source trees (mlflow-src, bentoml-src, gradio-src,
  anything-llm, plus the earlier Stacks/Clarity work). Not all committed.

## Prior Stacks/Clarity work (separate thread, still live)

One verified finding exists: **StackingDAO stBTC reward-split** (High-tier
argument, on-chain-verified read-only). Immunefi wanted a 50 USDC fee, so it was
routed by **direct private disclosure** (email to the team, PDF + verifier
attached). Follow-up: DM @StackingDAO on X if no reply by 2026-09-18. A second
finding (tracking griefing) is held in reserve. See
`findings/submissions/stackingdao/` and `findings/audit-notes-stackingdao.md`.

## Environment / tooling notes

- `pip install` works (pypi/files.pythonhosted allowlisted) → can run Python
  servers locally for real PoCs.
- `git clone` from GitHub works.
- Foundry: prebuilt blocked (403 egress policy); source build via cargo in
  progress. Only needed for EVM targets, which are deprioritized.
- Chromium (`/opt/pw-browsers`) runs but does not trust the proxy CA → cannot
  render auth'd/SPA pages; do NOT disable TLS verification to work around it.
- Verify Clarity/on-chain findings read-only via the Hiro API (no wallet).
- Branch: `claude/busy-clarke-4vys29`. Commit + push so the other session syncs.
