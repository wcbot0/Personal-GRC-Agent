"""A3+ tool guard and approval queue integration tests (T5)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import ApprovalQueue
from spa.tools.guard import ToolBlockedError, ToolGuard


def _read_audit_events(audit_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(audit_dir.glob("audit-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


def _event_types(events: list[dict[str, Any]]) -> list[str]:
    return [e["event_type"] for e in events]


@pytest.fixture
def guard_setup(tmp_path: Path):
    queue_dir = tmp_path / "approval-queue"
    audit_dir = tmp_path / "audit"
    audit = AuditLogger(log_dir=audit_dir)
    queue = ApprovalQueue(queue_dir=queue_dir, audit=audit)
    guard = ToolGuard(queue=queue, audit=audit)
    return guard, queue, audit_dir


def _make_assign_cpo(queue: ApprovalQueue) -> dict[str, Any]:
    return queue.create(
        action_class="A3",
        action_type="assign_human",
        title="Assign ticket to Alice",
        description="Human workflow change",
        risk_rationale="Assignee would change from unassigned",
        proposed_change={"assignee": "alice"},
    )


def test_a3_assign_human_without_cpo_raises_and_creates_pending_cpo(guard_setup):
    guard, queue, audit_dir = guard_setup

    with pytest.raises(ToolBlockedError) as exc_info:
        guard.check_allowed("assign_human", create_cpo=lambda: _make_assign_cpo(queue))

    assert exc_info.value.cpo_id is not None
    pending = queue.list_proposals(status="pending")
    assert len(pending) == 1
    assert pending[0]["id"] == exc_info.value.cpo_id
    assert pending[0]["action_class"] == "A3"
    assert pending[0]["status"] == "pending"

    events = _event_types(_read_audit_events(audit_dir))
    assert "cpo_created" in events
    assert "tool_blocked" not in events
    assert "tool_complete" not in events


def test_a3_assign_human_with_approved_cpo_executes(guard_setup):
    guard, queue, audit_dir = guard_setup
    cpo = _make_assign_cpo(queue)
    queue.approve(cpo["id"])

    result = guard.execute(
        "assign_human",
        lambda: {"assignee": "alice", "status": "assigned"},
        cpo_id=cpo["id"],
    )

    assert result == {"assignee": "alice", "status": "assigned"}
    events = _event_types(_read_audit_events(audit_dir))
    assert events.count("cpo_created") == 1
    assert events.count("cpo_approved") == 1
    assert "tool_start" in events
    assert "tool_complete" in events


def test_a3_assign_human_with_unapproved_cpo_refused(guard_setup):
    guard, queue, audit_dir = guard_setup
    cpo = _make_assign_cpo(queue)

    executed = {"called": False}

    def must_not_run() -> None:
        executed["called"] = True

    with pytest.raises(ToolBlockedError) as exc_info:
        guard.execute("assign_human", must_not_run, cpo_id=cpo["id"])

    assert not executed["called"]

    assert exc_info.value.cpo_id == cpo["id"]
    assert queue.get(cpo["id"])["status"] == "pending"

    events = _event_types(_read_audit_events(audit_dir))
    assert "cpo_created" in events
    assert "cpo_approved" not in events
    assert "tool_start" not in events
    assert "tool_complete" not in events


def test_a5_prod_iam_change_blocked_without_cpo(guard_setup):
    guard, queue, audit_dir = guard_setup

    with pytest.raises(ToolBlockedError) as exc_info:
        guard.check_allowed("prod_iam_change")

    assert exc_info.value.cpo_id is None
    assert queue.list_proposals(status="pending") == []
    assert queue.list_proposals(status=None) == []

    events = _read_audit_events(audit_dir)
    blocked = [e for e in events if e["event_type"] == "tool_blocked"]
    assert len(blocked) == 1
    assert blocked[0]["tools_called"] == ["prod_iam_change"]
    assert blocked[0]["risk_class"] == "A5"
    assert blocked[0]["outputs"] == {"reason": "A5 blocked by policy"}
    assert "cpo_created" not in _event_types(events)
