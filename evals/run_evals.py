#!/usr/bin/env python3
"""Golden-fixture eval harness for SPA skills."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from spa.skills.runner import run_skill  # noqa: E402

SKILLS = {
    "meeting-synth": "evals/fixtures/meeting_sample.md",
    "ticket-draft": "evals/fixtures/ticket_input.md",
    "policy-redline": "evals/fixtures/policy_change.md",
    "csf-crosswalk": "evals/fixtures/crosswalk_input.md",
    "daily-brief": "evals/fixtures/daily_brief_context.md",
    "evidence-pack": "evals/fixtures/evidence_pack_input.md",
}


def load_golden(skill: str) -> dict:
    path = ROOT / "evals" / "golden-outputs" / f"{skill}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def score_output(skill: str, output: dict, verifications: list[dict]) -> list[str]:
    errors = []
    golden = load_golden(skill)

    for field in golden.get("required_fields", []):
        if field not in output:
            errors.append(f"{skill}: missing field {field}")

    if skill == "meeting-synth":
        if len(output.get("proposed_tickets", [])) < golden.get("min_tickets", 1):
            errors.append(f"{skill}: expected min tickets")
        if len(output.get("control_tags", [])) < golden.get("min_control_tags", 1):
            errors.append(f"{skill}: expected control tags")

    if skill == "ticket-draft":
        ticket = output.get("ticket", {})
        expected = golden.get("ticket", {})
        for k, v in expected.items():
            if ticket.get(k) != v:
                errors.append(f"{skill}: ticket.{k} expected {v}, got {ticket.get(k)}")

    if skill == "policy-redline":
        needle = golden.get("redline_file_contains", "")
        if needle and needle not in output.get("redline_file", ""):
            errors.append(f"{skill}: redline_file path unexpected")

    if skill == "csf-crosswalk":
        if len(output.get("control_mappings", [])) < golden.get("min_mappings", 1):
            errors.append(f"{skill}: expected control mappings")

    if skill == "daily-brief":
        brief = output.get("brief_markdown", "")
        for phrase in golden.get("brief_contains", []):
            if phrase not in brief:
                errors.append(f"{skill}: brief missing '{phrase}'")

    if skill == "evidence-pack":
        expected_control = golden.get("control_id")
        if expected_control and output.get("control_id") != expected_control:
            errors.append(
                f"{skill}: control_id expected {expected_control}, got {output.get('control_id')}"
            )
        needle = golden.get("index_file_contains", "")
        if needle and needle not in output.get("index_file", ""):
            errors.append(f"{skill}: index_file path unexpected")
        if len(output.get("control_tags", [])) < golden.get("min_control_tags", 1):
            errors.append(f"{skill}: expected control tags")

    failed_verifiers = [v for v in verifications if not v.get("passed")]
    if failed_verifiers:
        errors.append(f"{skill}: verifiers failed: {failed_verifiers}")

    return errors


def main() -> int:
    all_errors: list[str] = []
    for skill, fixture in SKILLS.items():
        fixture_path = ROOT / fixture
        with tempfile.TemporaryDirectory() as tmp:
            result = run_skill(skill, fixture_path, output_dir=Path(tmp))
            errs = score_output(skill, result["output"], result["verifications"])
            if errs:
                all_errors.extend(errs)
                print(f"eval {skill}: FAIL")
                for e in errs:
                    print(f"  - {e}")
            else:
                print(f"eval {skill}: PASS")

    if all_errors:
        print(f"\nevals: {len(all_errors)} failure(s)")
        return 1
    print("\nevals: all skills passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
