"""End-to-end autonomous loop: ingest -> meeting-synth -> CPO -> approve -> connector assign."""
from __future__ import annotations

import builtins
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from connectors.tickets.none.provider import NoneTicketProvider
from spa.audit.chain import verify_chain
from spa.cli import main
from spa.governance.approval_queue import ApprovalQueue, ApprovalQueueError
from spa.ingest import ingest_file
from spa.memory.episodic import EpisodicMemory
from spa.paths import ROOT, get_approval_queue_dir, get_audit_logs_dir
from spa.tools.guard import ToolBlockedError, ToolGuard


CANARY_SECRET = "SUPER_SECRET_TOKEN_LOOP_TEST"
FIXTURE = ROOT / "evals/fixtures/meeting_autonomous_loop.md"

EXPECTED_SUBSEQUENCE = [
    "ingest_start",
    "ticket_draft_created",
    "cpo_created",
    "ingest_complete",
    "cpo_approved",
    "tool_preview",
    "tool_complete",
    "cpo_executed",
]


def _read_audit_events(audit_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(audit_dir.glob("audit-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


def _event_types(events: list[dict[str, Any]]) -> list[str]:
    return [e["event_type"] for e in events]


def _assert_subsequence(actual: list[str], expected: list[str]) -> None:
    idx = 0
    for item in actual:
        if idx < len(expected) and item == expected[idx]:
            idx += 1
    assert idx == len(expected), f"Expected subsequence {expected}, got {actual}"


def _force_offline_semantic(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def fail_qdrant_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith("qdrant_client"):
            raise ImportError("force offline fallback")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_qdrant_import)


@pytest.fixture
def mock_ticket_assign(monkeypatch: pytest.MonkeyPatch):
    """Track TicketConnector.assign calls without network or vendor APIs."""
    tracker = {"count": 0, "calls": []}
    real_assign = NoneTicketProvider.assign

    def tracked_assign(self, ticket_id, assignee, **kwargs):
        tracker["count"] += 1
        tracker["calls"].append({"ticket_id": ticket_id, "assignee": assignee, **kwargs})
        return real_assign(self, ticket_id, assignee, **kwargs)

    monkeypatch.setattr(NoneTicketProvider, "assign", tracked_assign)
    return tracker


def test_autonomous_loop_end_to_end(tmp_path, monkeypatch, mock_ticket_assign):
    _force_offline_semantic(monkeypatch)
    monkeypatch.setenv("TICKET_PROVIDER", "none")
    monkeypatch.setenv("GRC_PROVIDER", "none")

    inbox_fixture = tmp_path / "inbox" / "meeting.md"
    inbox_fixture.parent.mkdir(parents=True)
    shutil.copy(FIXTURE, inbox_fixture)

    result = ingest_file(inbox_fixture)

    assert result["meeting_synth"] is not None
    assert result["meeting_synth"]["decisions"]
    assert result["meeting_synth"]["risks"]
    assert result["meeting_synth"]["action_items"]
    assert result["meeting_synth"]["control_tags"]
    assert len(result["ticket_proposals"]) == 1
    assert len(result["pending_cpos"]) == 1
    assert mock_ticket_assign["count"] == 0

    cpo_id = result["pending_cpos"][0]
    queue = ApprovalQueue()
    cpo = queue.get(cpo_id)
    assert cpo["status"] == "pending"
    assert cpo["action_class"] == "A3"
    assert cpo["action_type"] == "assign_human"

    proposal = result["ticket_proposals"][0]
    assert proposal["ticket"]["assignee"] == "unassigned"

    guard = ToolGuard(queue=queue, audit=queue.audit)
    executed = {"called": False}

    def must_not_run() -> None:
        executed["called"] = True

    with pytest.raises(ToolBlockedError):
        guard.execute("assign_human", must_not_run, cpo_id=cpo_id)
    assert not executed["called"]
    assert mock_ticket_assign["count"] == 0

    with pytest.raises(ApprovalQueueError, match="must be approved"):
        queue.execute(cpo_id)
    assert mock_ticket_assign["count"] == 0

    events_before = _read_audit_events(get_audit_logs_dir())
    types_before = _event_types(events_before)
    assert "cpo_created" in types_before
    assert "cpo_approved" not in types_before
    assert "cpo_executed" not in types_before

    runner = CliRunner()
    approve_result = runner.invoke(main, ["proposals", "approve", cpo_id])
    assert approve_result.exit_code == 0, approve_result.output

    assert queue.get(cpo_id)["status"] == "approved"
    assert mock_ticket_assign["count"] == 1
    call = mock_ticket_assign["calls"][0]
    assert call["ticket_id"] == proposal["ticket"]["id"]
    assert call["assignee"] == proposal["ticket"]["suggested_owner"]
    assert call["cpo_approved"] is True
    assert call["cpo_id"] == cpo_id

    events = _read_audit_events(get_audit_logs_dir())
    types = _event_types(events)
    _assert_subsequence(types, EXPECTED_SUBSEQUENCE)

    approved_idx = types.index("cpo_approved")
    executed_idx = types.index("cpo_executed")
    assert approved_idx < executed_idx

    assign_completes = [
        e
        for e in events
        if e["event_type"] == "tool_complete" and "assign_human" in (e.get("tools_called") or [])
    ]
    assert len(assign_completes) == 1

    chain = verify_chain(get_audit_logs_dir())
    assert chain.valid is True
    assert chain.event_count >= len(EXPECTED_SUBSEQUENCE)

    episodic = EpisodicMemory()
    record = episodic.get(result["episodic_id"])
    assert record is not None
    assert CANARY_SECRET not in record["content"]
    assert "SUPER_SECRET_TOKEN" not in record["content"]

    semantic_path = tmp_path / "data" / "semantic_fallback.jsonl"
    assert semantic_path.exists()
    semantic_raw = semantic_path.read_text(encoding="utf-8")
    assert CANARY_SECRET not in semantic_raw
    assert "SUPER_SECRET_TOKEN" not in semantic_raw

    queue_dir = get_approval_queue_dir()
    assert queue_dir.is_relative_to(tmp_path) or str(queue_dir).startswith(str(tmp_path))
