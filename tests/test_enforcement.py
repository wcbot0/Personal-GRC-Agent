"""Governance enforcement integration tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from connectors.registry import LiveWriteDisabledError, get_ticket_provider
from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import ApprovalQueue
from spa.governance.policy import AutonomyPolicy
from spa.ingest import ingest_file
from spa.paths import ROOT
from spa.skills.runner import VerifierFailedError, run_skill
from spa.tools.guard import ToolBlockedError, ToolGuard


def _read_audit_events(audit_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(audit_dir.glob("audit-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


@pytest.fixture
def guard_setup(tmp_path: Path):
    queue_dir = tmp_path / "approval-queue"
    audit_dir = tmp_path / "audit"
    audit = AuditLogger(log_dir=audit_dir)
    queue = ApprovalQueue(queue_dir=queue_dir, audit=audit)
    guard = ToolGuard(queue=queue, audit=audit)
    return guard, queue, audit_dir


def test_a2_create_ticket_draft_emits_tool_notify(guard_setup, tmp_path, monkeypatch):
    guard, _, audit_dir = guard_setup
    monkeypatch.setenv("SPA_DATA_DIR", str(tmp_path / "data"))

    provider = get_ticket_provider(guard=guard)
    provider.create_draft({"id": "NOTIFY-1", "title": "Notify test"})

    event_types = [e["event_type"] for e in _read_audit_events(audit_dir)]
    assert "tool_notify" in event_types


def test_unknown_tool_blocked_at_a5(guard_setup):
    guard, _, audit_dir = guard_setup
    with pytest.raises(ToolBlockedError):
        guard.check_allowed("totally_unknown_tool_xyz")

    blocked = [e for e in _read_audit_events(audit_dir) if e["event_type"] == "tool_blocked"]
    assert blocked
    assert blocked[0]["risk_class"] == "A5"


def test_live_write_disabled_blocks_vendor_provider(monkeypatch):
    AutonomyPolicy.clear_cache()
    monkeypatch.setenv("TICKET_PROVIDER", "linear")
    with pytest.raises(LiveWriteDisabledError):
        get_ticket_provider()


def test_verifier_failure_produces_no_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv("SPA_DATA_DIR", str(tmp_path / "data"))
    audit_dir = tmp_path / "audit"
    queue_dir = tmp_path / "queue"
    audit = AuditLogger(log_dir=audit_dir)
    queue = ApprovalQueue(queue_dir=queue_dir, audit=audit)
    guard = ToolGuard(queue=queue, audit=audit)
    fixture = ROOT / "evals/fixtures/meeting_sample.md"
    out_dir = tmp_path / "out"

    def fail_verifiers(*args, **kwargs):
        return ({"skill": "meeting-synth", "control_tags": []}, [{"name": "schema", "passed": False, "detail": "test"}])

    with patch("spa.skills.runner.run_verifiers", side_effect=fail_verifiers):
        with pytest.raises(VerifierFailedError):
            run_skill("meeting-synth", fixture, output_dir=out_dir, audit=audit, guard=guard)

    assert list(out_dir.glob("meeting-synth-*.json")) == []
    assert list(queue_dir.glob("cpo-*.json"))


def test_ingest_emits_guarded_memory_events(tmp_path, monkeypatch):
    monkeypatch.setenv("SPA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SPA_AUDIT_DIR", str(tmp_path / "audit"))
    fixture = ROOT / "evals/fixtures/meeting_sample.md"
    ingest_file(fixture)

    audit_dir = tmp_path / "audit"
    event_types = [e["event_type"] for e in _read_audit_events(audit_dir)]
    assert "tool_preview" in event_types
    assert "tool_notify" in event_types
    assert "ingest_complete" in event_types
