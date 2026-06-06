#!/usr/bin/env python3
"""Golden-fixture eval harness for SPA skills."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from spa.skills.runner import run_skill  # noqa: E402
from spa.skills.verifiers import run_verifiers  # noqa: E402

SKILLS = {
    "meeting-synth": "evals/fixtures/meeting_sample.md",
    "ticket-draft": "evals/fixtures/ticket_input.md",
    "policy-redline": "evals/fixtures/policy_change.md",
    "csf-crosswalk": "evals/fixtures/crosswalk_input.md",
    "daily-brief": "evals/fixtures/daily_brief_context.md",
    "evidence-pack": "evals/fixtures/evidence_pack_input.md",
}

M3_MIN_FIRST_PASS_RATE = float(os.environ.get("SPA_M3_MIN_FIRST_PASS_RATE", "1.0"))


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


def _ensure_isolated_state_paths() -> None:
    """Point audit/data writes outside the repo tree unless already overridden."""
    defaults = {
        "SPA_DATA_DIR": "/tmp/spa_d",
        "SPA_AUDIT_DIR": "/tmp/spa_a",
    }
    for key, path in defaults.items():
        if key not in os.environ:
            os.environ[key] = path
        Path(os.environ[key]).mkdir(parents=True, exist_ok=True)


def _run_verifiers_first_pass(skill: str, fixture_path: Path) -> tuple[dict, list[dict], bool]:
    from spa.skills.runner import _load_skill_fn

    content = fixture_path.read_text(encoding="utf-8")
    skill_fn = _load_skill_fn(skill)
    with tempfile.TemporaryDirectory() as tmp:
        output = skill_fn(content, context={"output_dir": Path(tmp)})
    serialized = json.dumps(output, indent=2, default=str)
    _, verifications = run_verifiers(skill, output, serialized, retry_fn=lambda: output)
    first_pass = all(v.get("passed") for v in verifications)
    return output, verifications, first_pass


def _write_m3_report(records: list[dict]) -> Path:
    history_dir = ROOT / "governance" / "eval-history"
    history_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = history_dir / f"m3-{stamp}.json"
    passed = sum(1 for r in records if r["first_pass"])
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metric": "M3",
        "first_pass_count": passed,
        "total_skills": len(records),
        "first_pass_rate": passed / len(records) if records else 0.0,
        "skills": records,
    }
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def main() -> int:
    _ensure_isolated_state_paths()
    all_errors: list[str] = []
    m3_records: list[dict] = []

    for skill, fixture in SKILLS.items():
        fixture_path = ROOT / fixture
        _, verifications, first_pass = _run_verifiers_first_pass(skill, fixture_path)
        m3_records.append(
            {
                "skill": skill,
                "first_pass": first_pass,
                "verifiers": verifications,
            }
        )

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

    m3_path = _write_m3_report(m3_records)
    passed = sum(1 for r in m3_records if r["first_pass"])
    rate = passed / len(m3_records) if m3_records else 0.0
    print(f"M3 first-attempt pass rate: {passed}/{len(m3_records)} ({rate:.0%})")
    print(f"M3 report: {m3_path}")

    if rate < M3_MIN_FIRST_PASS_RATE:
        all_errors.append(
            f"M3 first-pass rate {rate:.0%} below minimum {M3_MIN_FIRST_PASS_RATE:.0%}"
        )

    if all_errors:
        print(f"\nevals: {len(all_errors)} failure(s)")
        return 1
    print("\nevals: all skills passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
