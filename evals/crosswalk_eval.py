"""Dedicated multi-scenario eval harness for csf-crosswalk."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Callable

import yaml

from spa.skills.runner import _load_skill_fn, run_skill
from spa.skills.verifiers import run_verifiers

CROSSWALK_DIR = Path(__file__).resolve().parent / "crosswalk"
SCENARIOS_PATH = CROSSWALK_DIR / "scenarios.yaml"
SKILL = "csf-crosswalk"


def load_scenarios(manifest_path: Path | None = None) -> list[dict[str, Any]]:
    path = manifest_path or SCENARIOS_PATH
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    scenarios = data.get("scenarios") or []
    resolved: list[dict[str, Any]] = []
    for item in scenarios:
        scenario_id = item["id"]
        fixture = CROSSWALK_DIR / item["fixture"]
        golden = CROSSWALK_DIR / item["golden"]
        resolved.append(
            {
                "id": scenario_id,
                "description": item.get("description", ""),
                "fixture": fixture,
                "golden": golden,
            }
        )
    return resolved


def load_golden(golden_path: Path) -> dict[str, Any]:
    return json.loads(golden_path.read_text(encoding="utf-8"))


def _mapping_field_nonempty(mappings: list[dict[str, Any]], field: str) -> bool:
    return any(str(row.get(field) or "").strip() for row in mappings)


def _mapping_field_all_empty(mappings: list[dict[str, Any]], field: str) -> bool:
    return all(not str(row.get(field) or "").strip() for row in mappings)


def score_crosswalk_output(
    output: dict[str, Any],
    golden: dict[str, Any],
    verifications: list[dict[str, Any]],
    *,
    scenario_id: str = "csf-crosswalk",
) -> list[str]:
    """Return a list of error strings; empty list means pass."""
    errors: list[str] = []
    prefix = f"{SKILL}/{scenario_id}"

    for field in golden.get("required_fields", []):
        if field not in output:
            errors.append(f"{prefix}: missing field {field}")

    mappings = output.get("control_mappings") or []
    if len(mappings) < golden.get("min_mappings", 1):
        errors.append(f"{prefix}: expected >= {golden.get('min_mappings', 1)} control mappings")

    gaps = output.get("gaps") or []
    if len(gaps) < golden.get("min_gaps", 0):
        errors.append(f"{prefix}: expected >= {golden.get('min_gaps', 0)} gaps")

    tags = output.get("control_tags") or []
    for tag_prefix in golden.get("control_tags_include_prefixes") or []:
        if not any(str(tag).startswith(tag_prefix) for tag in tags):
            errors.append(f"{prefix}: control_tags missing prefix {tag_prefix}")

    for field in golden.get("require_nonempty_fields") or []:
        if not _mapping_field_nonempty(mappings, field):
            errors.append(f"{prefix}: expected at least one mapping with non-empty {field}")

    for field in golden.get("absent_or_empty_fields") or []:
        if mappings and not _mapping_field_all_empty(mappings, field):
            errors.append(f"{prefix}: expected all mappings to omit or leave empty {field}")

    failed_verifiers = [v for v in verifications if not v.get("passed")]
    if failed_verifiers:
        errors.append(f"{prefix}: verifiers failed: {failed_verifiers}")

    return errors


def run_scenario(
    scenario: dict[str, Any],
    *,
    output_dir: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    fixture_path = scenario["fixture"]
    golden = load_golden(scenario["golden"])
    content = fixture_path.read_text(encoding="utf-8")
    skill_fn = _load_skill_fn(SKILL)

    if output_dir is None:
        with tempfile.TemporaryDirectory() as tmp:
            output = skill_fn(content, context={"output_dir": Path(tmp)})
    else:
        output = skill_fn(content, context={"output_dir": output_dir})

    serialized = json.dumps(output, indent=2, default=str)
    _, verifications = run_verifiers(SKILL, output, serialized, retry_fn=lambda _: output)
    errors = score_crosswalk_output(
        output,
        golden,
        verifications,
        scenario_id=scenario["id"],
    )
    return output, verifications, errors


def run_scenario_with_runner(scenario: dict[str, Any], output_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    fixture_path = scenario["fixture"]
    golden = load_golden(scenario["golden"])
    result = run_skill(SKILL, fixture_path, output_dir=output_dir)
    errors = score_crosswalk_output(
        result["output"],
        golden,
        result["verifications"],
        scenario_id=scenario["id"],
    )
    return result["output"], result["verifications"], errors


def run_all_crosswalk_evals(
    *,
    use_runner: bool = True,
    scenario_filter: str | None = None,
    on_scenario: Callable[[str, bool, list[str]], None] | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Run every registered crosswalk scenario. Returns (errors, records)."""
    all_errors: list[str] = []
    records: list[dict[str, Any]] = []

    for scenario in load_scenarios():
        if scenario_filter and scenario["id"] != scenario_filter:
            continue

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            if use_runner:
                output, verifications, errors = run_scenario_with_runner(scenario, tmp_path)
            else:
                output, verifications, errors = run_scenario(scenario, output_dir=tmp_path)

        passed = not errors
        record = {
            "skill": SKILL,
            "scenario": scenario["id"],
            "description": scenario.get("description", ""),
            "passed": passed,
            "first_pass": all(v.get("passed") for v in verifications),
            "verifiers": verifications,
        }
        records.append(record)

        if on_scenario:
            on_scenario(scenario["id"], passed, errors)
        if errors:
            all_errors.extend(errors)

    return all_errors, records


def main(argv: list[str] | None = None) -> int:
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Run csf-crosswalk scenario evals")
    parser.add_argument("--scenario", help="Run a single scenario id")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List registered scenarios and exit",
    )
    args = parser.parse_args(argv)

    if args.list:
        for scenario in load_scenarios():
            print(f"{scenario['id']}: {scenario.get('description', '')}")
        return 0

    if "SPA_NO_LLM" not in os.environ:
        os.environ.setdefault("SPA_NO_LLM", "1")

    def _print_result(scenario_id: str, passed: bool, errors: list[str]) -> None:
        status = "PASS" if passed else "FAIL"
        print(f"eval {SKILL}/{scenario_id}: {status}")
        for error in errors:
            print(f"  - {error}")

    errors, records = run_all_crosswalk_evals(
        scenario_filter=args.scenario,
        on_scenario=_print_result,
    )

    passed = sum(1 for r in records if r["passed"])
    total = len(records)
    print(f"\ncrosswalk scenarios: {passed}/{total} passed")

    if errors:
        print(f"crosswalk eval: {len(errors)} failure(s)")
        return 1
    print("crosswalk eval: all scenarios passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
