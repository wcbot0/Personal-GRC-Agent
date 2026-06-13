"""Reliability metrics M1/M2/M3 tests."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from spa.governance.reliability_metrics import (
    compute_all_metrics,
    compute_m1_first_pass_acceptance,
    compute_m2_time_to_detect,
    load_m3_verifier_pass_rate,
)
from spa.skills.daily_brief import run


def _write_audit(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def test_m1_computed_from_skill_audit_events(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    events = [
        {"event_type": "skill_complete", "timestamp": "2026-06-01T10:00:00+00:00"},
        {"event_type": "skill_complete", "timestamp": "2026-06-01T11:00:00+00:00"},
        {"event_type": "skill_failed", "timestamp": "2026-06-01T12:00:00+00:00"},
    ]
    _write_audit(audit_dir / "audit-2026-06-01.jsonl", events)
    m1 = compute_m1_first_pass_acceptance(events)
    assert m1["accepted"] == 2
    assert m1["total"] == 3
    assert abs(m1["rate"] - 2 / 3) < 0.01


def test_m2_computed_from_finding_to_cpo_delta(tmp_path: Path):
    events = [
        {"event_type": "ticket_draft_created", "timestamp": "2026-06-01T10:00:00+00:00"},
        {"event_type": "cpo_created", "timestamp": "2026-06-01T14:00:00+00:00"},
        {"event_type": "cloud_scan_complete", "timestamp": "2026-06-02T08:00:00+00:00"},
        {"event_type": "cpo_created", "timestamp": "2026-06-02T10:00:00+00:00"},
    ]
    m2 = compute_m2_time_to_detect(events)
    assert m2["samples"] == 2
    assert m2["mean_hours"] == 3.0


def test_m3_loads_latest_eval_history(tmp_path: Path):
    history = tmp_path / "eval-history"
    history.mkdir()
    (history / "m3-20260101T000000Z.json").write_text(json.dumps({"first_pass_rate": 0.5}), encoding="utf-8")
    (history / "m3-20260202T000000Z.json").write_text(
        json.dumps({"first_pass_rate": 1.0, "first_pass_count": 9, "total_skills": 9}),
        encoding="utf-8",
    )
    m3 = load_m3_verifier_pass_rate(history)
    assert m3["rate"] == 1.0
    assert m3["total_skills"] == 9


def test_daily_brief_uses_approval_queue_dir_override(tmp_path: Path, monkeypatch):
    custom_queue = tmp_path / "custom-queue"
    custom_queue.mkdir()
    pending_cpo = {
        "id": "cpo-test-001",
        "status": "pending",
        "title": "Custom queue CPO",
        "action_class": "A3",
    }
    (custom_queue / "cpo-test-001.json").write_text(json.dumps(pending_cpo), encoding="utf-8")

    monkeypatch.setenv("SPA_APPROVAL_QUEUE_DIR", str(custom_queue))
    monkeypatch.setattr("spa.skills.daily_brief.get_audit_logs_dir", lambda: tmp_path / "audit")

    output = run("Morning triage", context={"output_dir": tmp_path / "out"})
    assert output["pending_approvals"] == 1
    assert "Custom queue CPO" in output["brief_markdown"]


def test_daily_brief_renders_m1_m2_m3(tmp_path: Path, monkeypatch):
    audit_dir = tmp_path / "audit"
    history = tmp_path / "eval-history"
    history.mkdir()
    (history / "m3-20260613T120000Z.json").write_text(
        json.dumps({"first_pass_rate": 1.0, "first_pass_count": 9, "total_skills": 9}),
        encoding="utf-8",
    )
    _write_audit(
        audit_dir / "audit-2026-06-13.jsonl",
        [
            {"event_type": "skill_complete", "timestamp": datetime.now(timezone.utc).isoformat()},
            {"event_type": "ticket_draft_created", "timestamp": "2026-06-13T08:00:00+00:00"},
            {"event_type": "cpo_created", "timestamp": "2026-06-13T09:00:00+00:00"},
        ],
    )
    monkeypatch.setattr("spa.skills.daily_brief.get_audit_logs_dir", lambda: audit_dir)
    monkeypatch.setattr("spa.governance.reliability_metrics.EVAL_HISTORY_DIR", history)

    output = run("Morning triage", context={"output_dir": tmp_path / "out"})
    assert "M1 first-pass acceptance" in output["brief_markdown"]
    assert "M2 mean time to detect" in output["brief_markdown"]
    assert "M3 verifier pass rate" in output["brief_markdown"]
    assert "M1" in output["reliability_metrics"]


def test_compute_all_metrics_persists_report(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    history = tmp_path / "eval-history"
    history.mkdir()
    (history / "m3-test.json").write_text(json.dumps({"first_pass_rate": 0.9, "first_pass_count": 8, "total_skills": 9}), encoding="utf-8")
    _write_audit(audit_dir / "audit.jsonl", [{"event_type": "skill_complete", "timestamp": "2026-06-01T10:00:00+00:00"}])
    report = compute_all_metrics(audit_dir=audit_dir, history_dir=history, persist=True)
    assert "persisted_to" in report
    assert list(history.glob("m1-m2-*.json"))
