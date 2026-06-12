"""Skill verifier suite: schema, control-mapping, secrets, self-critique."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

RetryFn = Callable[[list[dict[str, Any]]], dict[str, Any]]

import jsonschema

from spa.lint.secrets import PATTERNS
from spa.memory.redaction import redact_text
from spa.paths import SKILLS_DIR


def verify_schema(output: dict[str, Any], schema_path: Path) -> dict[str, Any]:
    schema = json.loads(schema_path.read_text())
    try:
        jsonschema.validate(output, schema)
        return {"name": "schema", "passed": True, "detail": "Output matches schema"}
    except jsonschema.ValidationError as exc:
        return {"name": "schema", "passed": False, "detail": str(exc.message)}


def verify_control_mapping(output: dict[str, Any]) -> dict[str, Any]:
    tags = output.get("control_tags") or output.get("framework_tags") or []
    mappings = output.get("control_mappings") or output.get("mappings") or []
    has_tags = bool(tags) or bool(mappings)
    return {
        "name": "control_mapping_present",
        "passed": has_tags,
        "detail": "control tags present" if has_tags else "missing control_tags/mappings",
    }


def verify_secrets_scan(content: str) -> dict[str, Any]:
    text = redact_text(content)
    for pattern, label in PATTERNS:
        if pattern.search(content) and not pattern.search(text):
            continue
        if pattern.search(content):
            return {"name": "secrets_scan", "passed": False, "detail": f"Potential secret: {label}"}
    if "SUPER_SECRET_TOKEN" in content:
        return {"name": "secrets_scan", "passed": False, "detail": "Denylist term present"}
    return {"name": "secrets_scan", "passed": True, "detail": "No obvious secrets"}


def verify_self_critique(output: dict[str, Any], rubric_path: Path) -> dict[str, Any]:
    rubric = rubric_path.read_text(encoding="utf-8") if rubric_path.exists() else ""
    required_fields = []
    for line in rubric.splitlines():
        if line.strip().startswith("- require:"):
            required_fields.append(line.split("require:", 1)[1].strip())
    missing = [f for f in required_fields if f not in output or not output[f]]
    passed = len(missing) == 0
    return {
        "name": "self_critique",
        "passed": passed,
        "detail": "rubric satisfied" if passed else f"missing: {', '.join(missing)}",
    }


def run_verifiers(
    skill_name: str,
    output: dict[str, Any],
    serialized: str,
    *,
    retry_fn: RetryFn | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    skill_dir = SKILLS_DIR / skill_name
    schema_path = skill_dir / "output.schema.json"
    rubric_path = skill_dir / "verifiers" / "rubric.md"

    results = []
    if schema_path.exists():
        results.append(verify_schema(output, schema_path))
    results.append(verify_control_mapping(output))
    results.append(verify_secrets_scan(serialized))
    results.append(verify_self_critique(output, rubric_path))

    if all(r["passed"] for r in results):
        return output, results

    if retry_fn is not None:
        output2 = retry_fn(results)
        serialized2 = json.dumps(output2, indent=2)
        results2 = []
        if schema_path.exists():
            results2.append(verify_schema(output2, schema_path))
        results2.append(verify_control_mapping(output2))
        results2.append(verify_secrets_scan(serialized2))
        results2.append(verify_self_critique(output2, rubric_path))
        if all(r["passed"] for r in results2):
            return output2, results2
        return output2, results2

    return output, results
