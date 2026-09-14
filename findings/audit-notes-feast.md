# Feast (feast-dev/feast) — audit notes

**Date:** 2026-09-14
**Source:** `feast-dev/feast` @ HEAD `b7a8928a52d39fd619f21555d68d3a1718faf392`
(shallow clone; `work/feast-src`, not committed)
**Auditor pass:** deserialization-before-authorization on the registry server
(sibling hunt around CVE-2026-56121 / CVE-2026-34070).
**Outcome:** Real, verified, still-exploitable at HEAD — **but a duplicate of the
already-public CVE-2026-18948 (Critical, CVSS 9.9, published 2026-08-10).**
**NOT SUBMITTABLE.** Do not report. (Fails Gate 1 of the self-refutation gate:
"not on the known-issues / previous-findings list.")

---

## What was hunted

The recon lead was CVE-2026-56121 — Feast < 0.63.0 unauthenticated RCE where the
registry gRPC server `dill.loads()` the UDF body of an incoming `OnDemandFeatureView`
spec in `ApplyFeatureView`, **before** the `assert_permissions_to_update` check.
The `no_auth` default config makes it fully unauthenticated on the registry port
(default **6570**, bound to `[::]`). Fixed in 0.63.0 by parsing a metadata-only
object with `skip_udf=True` before the permission check.

The hypothesis: the `skip_udf` fix was applied narrowly to `ApplyFeatureView`, and
sibling RPC handlers that also call `<Object>.from_proto(...)` as the `resource=`
argument to `assert_permissions*` were missed — so they still deserialize
attacker-controlled UDF bytes before authorization.

## What was found (all verified on HEAD with runnable PoCs)

The hypothesis is correct. At HEAD, the `skip_udf` guard is present **only** on
`ApplyFeatureView` (`registry_server.py:525`). Two other registry RPC handlers
evaluate a `from_proto` that reaches code-execution sinks as an argument expression
— i.e. **before** the permission function body runs (Python evaluates call
arguments first), and under `no_auth` there is no interceptor at all
(`_grpc_interceptors(NONE)` → `[ErrorInterceptor()]`, no `AuthInterceptor`):

1. **`ApplyMaterialization`** (`registry_server.py:1452`) — core deps only, no extra required.
   `assert_permissions(resource=FeatureView.from_proto(request.feature_view), ...)`
   with **no `skip_udf`**. `FeatureView.from_proto` → (spec has `feature_transformation.
   user_defined_function`) → `PythonTransformation.from_proto` → `resolve_udf`
   (`transformation/udf_rehydrate.py`), which does **`exec(body_text)`** on the
   attacker's Python source (line 138) and falls back to **`dill.loads(body)`**
   (line 176). Either field yields RCE.

2. **`ApplyValidationReference`** (`registry_server.py:1358`) — requires the
   `great_expectations` (`ge` / validation) extra installed on the server.
   `assert_permissions_to_update(resource=ValidationReference.from_proto(request.
   validation_reference), ...)` → `GEProfiler.from_proto` → **`dill.loads(proto.
   profiler.body)`** (`dqm/profilers/ge_profiler.py:158/176`), unconditional, no guard.

Auth model confirmed in `permissions/security_manager.py`:
`assert_permissions*` returns the resource immediately when `is_auth_necessary(sm)`
is false (no-auth), and even with auth enabled it only raises **after** the
`resource=...from_proto(...)` argument (and its `dill.loads`/`exec`) has already run.
So: unauthenticated RCE in the default config; authenticated-but-unauthorized RCE
(any valid token, zero permissions) when auth is enabled.

FeatureView/OnDemand/Stream `from_proto` were checked and their `skip_udf` guards
are complete (`if not skip_udf:` fully gates every transformation sink); the gap is
purely the handlers that never pass `skip_udf`.

### PoCs (in `submissions/feast/`, all run green on HEAD)
- `poc_materialization_rce.py` — unauth network RCE via `ApplyMaterialization`
  `exec(body_text)`; real gRPC server (no_auth) + unauthenticated client; ran `id`
  → `uid=0(root)` on the server. **Core deps only.**
- `poc_network_rce.py` — unauth network RCE via `ApplyValidationReference`
  `dill.loads`; same harness; requires `great_expectations`.
- `poc_preauth_ordering.py` — isolates the root cause: observed event order
  `['PAYLOAD_EXECUTED', 'AUTHZ_CHECK_REACHED']`, proving deserialization precedes
  authorization (so auth-enabled-but-unauthorized callers are also affected).

## Why this is NOT submittable — the duplicate determination

Web due-diligence (self-refutation Gate 1) found this is already public:

- **CVE-2026-18948** — "Feast: Unsafe dill deserialization of registry-stored UDFs
  — RCE on feature server and registry server", **CVSS 9.9 Critical, published
  2026-08-10** (Red Hat Bugzilla 2511167, access.redhat.com, GitHub Advisory DB feeds).
  The Bugzilla names the **same sinks** — `python_transformation.py:168`,
  `ge_profiler.py:158`, `pandas_transformation.py:150`, `substrait_transformation.py:163`,
  `ray_transformation.py:288`, `stream_feature_view.py:335` — and the **same root
  cause**: "from_proto() triggers dill.loads() before assert_permissions_to_update
  runs" on the registry server, plus the feature-server `/get-online-features` path.
  Remediation it lists: "move assert_permissions_to_update before from_proto()" and
  "replace dill with the source-string + restricted-exec path". No fixed version yet.
- **CVE-2026-56121** — the narrower ApplyFeatureView/OnDemandFeatureView instance,
  fixed 0.63.0.

My `ApplyMaterialization` (via `python_transformation.py:168` / `resolve_udf`) and
`ApplyValidationReference` (via `ge_profiler.py:158`) findings are **specific
instances of CVE-2026-18948's already-disclosed class**. The individual RPC handler
names are not spelled out in the CVE text, but the vulnerable sinks and the
pre-auth `from_proto`-before-`assert_permissions` root cause are exactly its subject.
Submitting it as new = a duplicate of a month-old public Critical CVE → pays nothing
and risks an account ban (hard rule). The vulnerability is technically real and
HEAD is still unpatched for these handlers, but for the operation's purpose
(novel, paid finding) it is dead.

## Secondary reason to have dropped Feast anyway (channel)

Feast's `SECURITY.md` routes disclosure to **GitHub Security Advisories** (private
"Report a vulnerability"), not a paid huntr program, and explicitly warns that
"bulk, automated, or AI-generated submissions may be closed without further
response." GHSA gives a CVE + credit, typically **no cash**. No paid huntr Feast
program was confirmed. So even a *novel* Feast RCE would have had an unclear payout
path. The recon's "Feast is a highest-paid huntr target" premise was not borne out
by the project's own policy.

## Environment (for reproduction)
- `work/venv` — `feast[ge]` dependency tree installed from PyPI, then the `feast`
  package uninstalled so PoCs run the HEAD source via
  `PYTHONPATH=work/feast-src/sdk/python`. Real `great_expectations 0.18.8`, `dill 0.3.9`,
  `grpcio 1.84.0`, `protobuf 7.36.1`.
- Note: an out-of-place URL was found planted in a `pyproject.toml` build-system
  comment (`amitylearning.vercel.app/?question=...`). Treated as an untrusted
  honeypot per methodology; **not fetched**.

## Verdict
`nothing_submittable` — verified real, unpatched at HEAD, but a **duplicate of
public CVE-2026-18948**. Pivot away from Feast (post-CVE hardening target, GHSA-only
channel). PoCs kept as evidence only, clearly marked non-submittable.
