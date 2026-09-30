"""Validate Afterlife flow YAMLs with GitLab's own flow validator.

Runs the same FlowValidator that the Duo Workflow Service uses for
ValidateFlowConfig (component construction, routing, tool-name resolution,
prompt-variable checks), then applies the extra restrictions the docs list for
*custom* flows, and checks every tool name exists in the real ToolsRegistry.

Usage (from a checkout of gitlab-org/modelops/applied-ml/code-suggestions/ai-assist
with its poetry deps installed):

    cd ai-assist && .venv/bin/python /path/to/validate_flows.py /path/to/flows/*.yml
"""

import sys
import types
from pathlib import Path
from unittest.mock import Mock

import yaml

# The profiler's native extension is irrelevant to validation and often fails
# to build locally; stub it so ai_gateway imports cleanly.
sys.modules.setdefault(
    "googlecloudprofiler", types.SimpleNamespace(start=lambda **_: None)
)

from ai_gateway.prompts.registry import LocalPromptRegistry
from duo_workflow_service.agent_platform.utils.validation import FlowValidator
from duo_workflow_service.agent_platform.v1.flows.validation import (
    _make_validation_tools_registry,
)

# https://docs.gitlab.com/user/duo_agent_platform/flows/custom_flows_schema/
FORBIDDEN_TOP_LEVEL = {"name", "description", "product_group"}


def custom_flow_errors(cfg: dict) -> list[str]:
    errors = []
    if cfg.get("environment") != "ambient":
        errors.append("custom flows must use environment: ambient")
    for key in FORBIDDEN_TOP_LEVEL & cfg.keys():
        errors.append(f"top-level '{key}' is not allowed in custom flows")
    for comp in cfg.get("components", []):
        name = comp.get("name")
        if comp.get("type") == "AgentComponent" and (
            "response_schema_id" in comp or "response_schema_version" in comp
        ):
            errors.append(f"{name}: response_schema_* not allowed in custom flows")
        if comp.get("type") == "OneOffComponent" and "ui_role_as" in comp:
            errors.append(f"{name}: ui_role_as not allowed on OneOffComponent")
    for prompt in cfg.get("prompts", []):
        if "model" in prompt:
            errors.append(f"prompt {prompt.get('prompt_id')}: 'model' not allowed")
        if "stop" in (prompt.get("params") or {}):
            errors.append(f"prompt {prompt.get('prompt_id')}: params.stop not allowed")
    return errors


def unknown_tools(cfg: dict, registry) -> list[str]:
    missing = []
    for comp in cfg.get("components", []):
        names = []
        for entry in comp.get("toolset") or []:
            names.extend(entry if isinstance(entry, dict) else [entry])
        if comp.get("tool_name"):
            names.append(comp["tool_name"])
        missing += [
            f"{comp.get('name')}: unknown tool '{n}'"
            for n in names
            if registry.get(n) is None
        ]
    return missing


def main(paths: list[str]) -> int:
    registry = _make_validation_tools_registry()
    validator = FlowValidator(
        prompt_registry=LocalPromptRegistry(
            prompt_template_factories={},
            model_factories={},
            internal_event_client=Mock(),
            model_limits=Mock(),
            custom_models_enabled=False,
        )
    )
    failed = 0
    for path in paths:
        text = Path(path).read_text()
        cfg = yaml.safe_load(text)
        errors = custom_flow_errors(cfg) + unknown_tools(cfg, registry)
        try:
            validator.validate(text)
        except Exception as exc:  # FlowValidationError carries .errors
            errors += list(getattr(exc, "errors", None) or [str(exc)])
        if errors:
            failed += 1
            print(f"FAIL {path}")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"ok   {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
