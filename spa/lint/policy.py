"""Validate autonomy-policy.yaml and JSON schemas."""
from __future__ import annotations

import json
import sys

import jsonschema
import yaml

from spa.governance.policy import AutonomyPolicy
from spa.paths import (
    AUDIT_EVENT_SCHEMA,
    AUTONOMY_POLICY,
    CPO_SCHEMA,
    MEMORY_OBJECT_SCHEMA,
    REDACTION_RULES,
)


def validate_schema(path, name: str) -> list[str]:
    errors = []
    try:
        schema = json.loads(path.read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{name}: {exc}")
    return errors


def main() -> int:
    errors: list[str] = []

    if not AUTONOMY_POLICY.exists():
        errors.append("Missing agent/autonomy-policy.yaml")
    else:
        data = yaml.safe_load(AUTONOMY_POLICY.read_text())
        for cls in ("A0", "A1", "A2", "A3", "A4", "A5"):
            if cls not in data.get("action_classes", {}):
                errors.append(f"autonomy-policy missing action class {cls}")

    try:
        AutonomyPolicy.load()
    except Exception as exc:  # noqa: BLE001
        errors.append(f"AutonomyPolicy load failed: {exc}")

    if not REDACTION_RULES.exists():
        errors.append("Missing governance/redaction-rules.yaml")

    for path, name in [
        (MEMORY_OBJECT_SCHEMA, "memory-object"),
        (CPO_SCHEMA, "cpo"),
        (AUDIT_EVENT_SCHEMA, "audit-event"),
    ]:
        errors.extend(validate_schema(path, name))

    if errors:
        for err in errors:
            print(f"policy-lint ERROR: {err}", file=sys.stderr)
        return 1

    print("policy-lint OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
