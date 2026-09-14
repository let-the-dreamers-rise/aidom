# Feast PoCs — ⛔ NOT FOR SUBMISSION (verified DUPLICATE)

These three scripts reproduce a **real, still-unpatched-at-HEAD** pre-authorization
RCE on the Feast registry gRPC server. They all run green. **Do not submit them
anywhere.**

They are a **duplicate of the already-public [CVE-2026-18948](https://access.redhat.com/security/cve/cve-2026-18948)**
("Feast: Unsafe dill deserialization of registry-stored UDFs — RCE on feature
server and registry server", CVSS 9.9 Critical, published **2026-08-10**), which
names the same sinks (`python_transformation.py:168`, `ge_profiler.py:158`, …) and
the same root cause (`from_proto()` → `dill.loads()`/`exec()` before
`assert_permissions_to_update`). See `../../audit-notes-feast.md` for the full
determination.

Submitting a duplicate of a month-old public Critical CVE pays nothing and risks a
platform ban (see `playbook/self-refutation.md`, Gate 1 and the hard rules). These
files are kept **as audit evidence only** — proof that the CVE class is still
exploitable on the current default (`no_auth`) registry server.

## The scripts
| File | RPC path | Sink | Precondition |
|---|---|---|---|
| `poc_materialization_rce.py` | `ApplyMaterialization` | `exec(body_text)` / `dill.loads(body)` in `resolve_udf` | core deps only |
| `poc_network_rce.py` | `ApplyValidationReference` | `dill.loads` in `GEProfiler.from_proto` | `great_expectations` extra |
| `poc_preauth_ordering.py` | (ordering proof) | shows payload runs before authz | core deps only |

## How to run (evidence reproduction only)
```bash
cd ../../../work            # repo work/ dir
python3 -m venv venv && ./venv/bin/pip install "feast[ge]" grpcio-health-checking grpcio-reflection
./venv/bin/pip uninstall -y feast          # keep deps, run HEAD source instead
cd ../findings/submissions/feast
PYTHONPATH=../../../work/feast-src/sdk/python ../../../work/venv/bin/python poc_materialization_rce.py
```
Payloads are local-only (write a marker file in the temp dir, run `id`). Nothing
external is touched.
