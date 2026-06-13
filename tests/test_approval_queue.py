"""CPO approval integrity and path validation tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import (
    LOCAL_CLI_APPROVER,
    ApprovalQueue,
    ApprovalQueueError,
)
from spa.paths import get_proposals_dir


@pytest.fixture
def signing_key(monkeypatch):
    monkeypatch.setenv("SPA_CPO_SIGNING_KEY", "test-signing-key-for-governance-tests")


@pytest.fixture
def queue_setup(tmp_path: Path, signing_key):
    queue_dir = tmp_path / "approval-queue"
    audit_dir = tmp_path / "audit"
    audit = AuditLogger(log_dir=audit_dir)
    queue = ApprovalQueue(queue_dir=queue_dir, audit=audit)
    return queue, audit_dir


def _make_assign_cpo(queue: ApprovalQueue, **change: Any) -> dict[str, Any]:
    return queue.create(
        action_class="A3",
        action_type="assign_human",
        title="Assign ticket",
        description="Human workflow change",
        risk_rationale="Assignee would change",
        proposed_change={"assignee": "alice", "ticket_id": "T-1", **change},
        requested_by="spa-agent",
    )


def test_forged_approved_status_rejected_on_execute(queue_setup):
    queue, _ = queue_setup
    cpo = _make_assign_cpo(queue)
    forged = queue.get(cpo["id"])
    forged["status"] = "approved"
    forged["approved_by"] = "attacker"
    queue._path_for(cpo["id"]).write_text(json.dumps(forged, indent=2), encoding="utf-8")

    with pytest.raises(ApprovalQueueError, match="integrity check failed"):
        queue.execute(cpo["id"])
    assert queue.is_approved(cpo["id"]) is False


def test_tampered_proposed_change_rejected_on_execute(queue_setup):
    queue, _ = queue_setup
    cpo = _make_assign_cpo(queue)
    queue.approve(cpo["id"], approved_by="reviewer@example.com")
    tampered = queue.get(cpo["id"])
    tampered["proposed_change"]["assignee"] = "attacker"
    queue._path_for(cpo["id"]).write_text(json.dumps(tampered, indent=2), encoding="utf-8")

    with pytest.raises(ApprovalQueueError, match="integrity check failed"):
        queue.execute(cpo["id"])


def test_self_approval_rejected(queue_setup):
    queue, _ = queue_setup
    run_id = queue.audit.run_id
    cpo = queue.create(
        action_class="A3",
        action_type="assign_human",
        title="Self approve",
        description="Should fail",
        risk_rationale="test",
        proposed_change={"assignee": "alice", "ticket_id": "T-2"},
        requested_by="spa-agent",
        run_id=run_id,
    )
    with pytest.raises(ApprovalQueueError, match="Self-approval"):
        queue.approve(cpo["id"], approved_by=run_id)


def test_approve_requires_explicit_approver(queue_setup):
    queue, _ = queue_setup
    cpo = _make_assign_cpo(queue)
    with pytest.raises(ApprovalQueueError, match="approved_by is required"):
        queue.approve(cpo["id"], approved_by="  ")


def test_signed_approval_allows_execute(queue_setup, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SPA_DATA_DIR", str(tmp_path / "data"))
    queue, _ = queue_setup
    proposals = get_proposals_dir()
    tickets_dir = proposals / "tickets"
    tickets_dir.mkdir(parents=True)
    ticket_path = tickets_dir / "ticket-proposal-T-1.json"
    ticket_path.write_text(
        json.dumps({"id": "T-1", "assignee": "unassigned", "title": "Test"}),
        encoding="utf-8",
    )
    cpo = _make_assign_cpo(queue, path=str(ticket_path))
    queue.approve(cpo["id"], approved_by=LOCAL_CLI_APPROVER)
    assert queue.is_approved(cpo["id"]) is True
    approved = queue.get(cpo["id"])
    assert approved["approval_signature"]
    assert approved["approval_audit_event_id"]


def test_path_outside_proposals_dir_rejected(queue_setup, tmp_path: Path):
    queue, _ = queue_setup
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    with pytest.raises(ApprovalQueueError, match="outside proposals dir"):
        queue._resolve_ticket_path({"path": str(outside)})


def test_preview_flags_out_of_bounds_path(queue_setup, tmp_path: Path):
    queue, _ = queue_setup
    cpo = _make_assign_cpo(queue, path="/etc/hosts")
    preview = queue.build_preview(cpo)
    assert "WARNING:" in preview
    assert "outside proposals dir" in preview
