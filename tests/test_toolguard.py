"""ToolGuard integration with signed CPO approvals."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import LOCAL_CLI_APPROVER, ApprovalQueue
from spa.tools.guard import ToolBlockedError, ToolGuard


@pytest.fixture(autouse=True)
def _signing_key(monkeypatch):
    monkeypatch.setenv("SPA_CPO_SIGNING_KEY", "test-signing-key-for-toolguard-tests")


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


def test_a3_assign_human_with_signed_approved_cpo_executes(guard_setup):
    guard, queue, audit_dir = guard_setup
    cpo = _make_assign_cpo(queue)
    queue.approve(cpo["id"], approved_by=LOCAL_CLI_APPROVER)
    assert queue.is_approved(cpo["id"])

    result = guard.execute(
        "assign_human",
        lambda: {"assignee": "alice", "status": "assigned"},
        cpo_id=cpo["id"],
    )

    assert result == {"assignee": "alice", "status": "assigned"}


def test_a3_assign_human_forged_approval_refused(guard_setup):
    guard, queue, _ = guard_setup
    cpo = _make_assign_cpo(queue)
    forged = queue.get(cpo["id"])
    forged["status"] = "approved"
    forged["approved_by"] = "attacker"
    queue._path_for(cpo["id"]).write_text(json.dumps(forged, indent=2), encoding="utf-8")

    executed = {"called": False}

    def must_not_run() -> None:
        executed["called"] = True

    with pytest.raises(ToolBlockedError):
        guard.execute("assign_human", must_not_run, cpo_id=cpo["id"])

    assert not executed["called"]
    assert queue.is_approved(cpo["id"]) is False
