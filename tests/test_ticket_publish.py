"""End-to-end ticket publish workflow (proposal → CPO → Linear)."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from connectors.tickets.linear.client import LinearGraphQLClient
from connectors.tickets.linear.config import LinearConfig
from connectors.tickets.linear.provider import LinearTicketProvider
from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import ApprovalQueue, ApprovalQueueError
from spa.governance.policy import AutonomyPolicy
from spa.tools.guard import ToolBlockedError, ToolGuard
from spa.workflows.ticket_publish import propose_ai_proposed_ticket_cpo


def _read_audit_events(audit_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(audit_dir.glob("audit-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


def _policy_with_live_ticket_writes() -> AutonomyPolicy:
    policy = AutonomyPolicy.load()
    data = copy.deepcopy(policy.data)
    data["connectors"]["ticket"]["live_write_enabled"] = True
    return AutonomyPolicy(data)


@pytest.fixture
def guard_setup(tmp_path: Path, monkeypatch):
    queue_dir = tmp_path / "approval-queue"
    audit_dir = tmp_path / "audit"
    audit = AuditLogger(log_dir=audit_dir)
    queue = ApprovalQueue(queue_dir=queue_dir, audit=audit)
    guard = ToolGuard(queue=queue, audit=audit)
    proposals_dir = tmp_path / "proposals" / "tickets"
    proposals_dir.mkdir(parents=True)
    monkeypatch.setattr("spa.workflows.ticket_publish.get_proposals_dir", lambda: tmp_path / "proposals")
    monkeypatch.setattr("spa.governance.approval_queue.get_proposals_dir", lambda: tmp_path / "proposals")
    return guard, queue, audit_dir, proposals_dir


@pytest.fixture
def linear_config() -> LinearConfig:
    return LinearConfig(api_key="test-api-key", team_id="team-fixed-abc", project_id="proj-optional")


@pytest.fixture
def mock_http_client() -> MagicMock:
    client = MagicMock(spec=httpx.Client)
    client.post = MagicMock()
    return client


@pytest.fixture
def linear_env(monkeypatch, linear_config):
    monkeypatch.setenv("TICKET_PROVIDER", "linear")
    monkeypatch.setenv("LINEAR_API_KEY", linear_config.api_key)
    monkeypatch.setenv("LINEAR_TEAM_ID", linear_config.team_id)
    monkeypatch.setenv("LINEAR_PROJECT_ID", linear_config.project_id or "")


@pytest.fixture
def live_ticket_policy(monkeypatch):
    AutonomyPolicy.clear_cache()
    policy = _policy_with_live_ticket_writes()
    monkeypatch.setattr("spa.governance.policy.AutonomyPolicy.load", lambda: policy)
    return policy


def _sample_ticket() -> dict[str, Any]:
    return {
        "id": "AI-PROPOSED-001",
        "title": "Enable MFA for admin console",
        "description": "Quarterly access review found MFA gap",
        "status": "ai_proposed",
        "assignee": "unassigned",
        "control_tags": ["SOC2:CC6.1"],
    }


def _mock_response(payload: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=payload)
    return resp


def _route_linear_api(mock_http_client: MagicMock) -> None:
    def _post(url, **kwargs):
        query = kwargs["json"]["query"]
        if "TeamLabels" in query:
            return _mock_response(
                {"data": {"team": {"labels": {"nodes": [{"id": "label-ai", "name": "AI-Proposed"}]}}}}
            )
        if "issueCreate" in query:
            return _mock_response(
                {
                    "data": {
                        "issueCreate": {
                            "success": True,
                            "issue": {
                                "id": "issue-uuid-new",
                                "identifier": "GRC-202",
                                "url": "https://linear.app/acme/issue/GRC-202",
                                "title": "Enable MFA for admin console",
                                "assignee": None,
                            },
                        }
                    }
                }
            )
        if "issueAddLabel" in query:
            return _mock_response({"data": {"issueAddLabel": {"success": True}}})
        if "CommentCreate" in query:
            return _mock_response(
                {"data": {"commentCreate": {"success": True, "comment": {"id": "comment-1", "body": "provenance"}}}}
            )
        return _mock_response({"data": {}})

    mock_http_client.post.side_effect = _post


def test_publish_write_disabled_creates_cpo_zero_network(guard_setup, monkeypatch):
    guard, queue, audit_dir, proposals_dir = guard_setup
    AutonomyPolicy.clear_cache()
    ticket = _sample_ticket()
    proposal_path = proposals_dir / "ticket-proposal-AI-PROPOSED-001.json"
    proposal_path.write_text(json.dumps(ticket), encoding="utf-8")

    cpo_id = propose_ai_proposed_ticket_cpo(guard=guard, queue=queue, path=proposal_path)

    cpo = queue.get(cpo_id)
    assert cpo["status"] == "pending"
    assert cpo["action_type"] == "create_ticket_live"
    assert cpo["proposed_change"]["ticket"]["id"] == "AI-PROPOSED-001"
    assert "input_sha256" in cpo["proposed_change"]["provenance"]

    events = _read_audit_events(audit_dir)
    notify = [
        e
        for e in events
        if e["event_type"] == "tool_notify" and "create_ai_proposed_ticket" in e.get("tools_called", [])
    ]
    assert len(notify) == 1

    queue.approve(cpo_id)
    result = queue.execute(cpo_id)
    assert result["status"] == "deferred"
    assert "live_write_enabled" in result["reason"]


def test_publish_write_enabled_unapproved_blocked(guard_setup, live_ticket_policy, linear_env):
    guard, queue, _, proposals_dir = guard_setup
    ticket = _sample_ticket()
    proposal_path = proposals_dir / "ticket-proposal-AI-PROPOSED-001.json"
    proposal_path.write_text(json.dumps(ticket), encoding="utf-8")

    cpo_id = propose_ai_proposed_ticket_cpo(guard=guard, queue=queue, path=proposal_path)

    with pytest.raises(ApprovalQueueError, match="must be approved"):
        queue.execute(cpo_id)


def test_publish_write_enabled_approved_creates_labeled_issue_with_provenance(
    guard_setup,
    live_ticket_policy,
    linear_env,
    linear_config,
    mock_http_client,
    monkeypatch,
):
    guard, queue, audit_dir, proposals_dir = guard_setup
    _route_linear_api(mock_http_client)
    client = LinearGraphQLClient(linear_config.api_key, http_client=mock_http_client)
    provider = LinearTicketProvider(guard=guard, config=linear_config, client=client)

    ticket = _sample_ticket()
    proposal_path = proposals_dir / "ticket-proposal-AI-PROPOSED-001.json"
    proposal_path.write_text(json.dumps(ticket), encoding="utf-8")

    cpo_id = propose_ai_proposed_ticket_cpo(guard=guard, queue=queue, path=proposal_path)
    queue.approve(cpo_id)

    monkeypatch.setattr(
        "connectors.registry.get_ticket_provider",
        lambda guard=None, require_live_writes=True: provider,
    )
    result = queue.execute(cpo_id)

    assert result["provider"] == "linear"
    assert result["ticket"]["id"] == "GRC-202"
    assert result["ticket"]["label"] == "AI-Proposed"

    calls = mock_http_client.post.call_args_list
    queries = [c.kwargs["json"]["query"] for c in calls]
    assert any("issueCreate" in q for q in queries)
    assert any("issueAddLabel" in q for q in queries)
    assert any("CommentCreate" in q for q in queries)
    assert len(calls) >= 3

    events = _read_audit_events(audit_dir)
    assert any(e["event_type"] == "ticket_create_live" and e["outputs"].get("status") == "executed" for e in events)
    assert any(
        e["event_type"] == "tool_notify" and "add_provenance_comment" in e.get("tools_called", [])
        for e in events
    )
    assert "cpo_executed" in [e["event_type"] for e in events]
