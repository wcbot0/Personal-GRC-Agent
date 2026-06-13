"""Linear live ticket connector tests (mocked network)."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from connectors.registry import LiveWriteDisabledError, get_ticket_provider
from connectors.tickets.linear.client import LinearGraphQLClient
from connectors.tickets.linear.config import LinearConfig, LinearConfigError
from connectors.tickets.linear.provider import LinearTicketProvider
from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import ApprovalQueue
from spa.governance.policy import AutonomyPolicy
from spa.tools.guard import ToolBlockedError, ToolGuard


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
def guard_setup(tmp_path: Path):
    queue_dir = tmp_path / "approval-queue"
    audit_dir = tmp_path / "audit"
    audit = AuditLogger(log_dir=audit_dir)
    queue = ApprovalQueue(queue_dir=queue_dir, audit=audit)
    guard = ToolGuard(queue=queue, audit=audit)
    return guard, queue, audit_dir


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
    yield policy


def _issues_response() -> dict[str, Any]:
    return {
        "data": {
            "team": {
                "issues": {
                    "nodes": [
                        {
                            "id": "issue-uuid-1",
                            "identifier": "GRC-101",
                            "title": "Access review gap",
                            "description": "Quarterly review overdue",
                            "url": "https://linear.app/acme/issue/GRC-101",
                            "state": {"name": "Todo"},
                            "assignee": None,
                        }
                    ]
                }
            }
        }
    }


def _create_response() -> dict[str, Any]:
    return {
        "data": {
            "issueCreate": {
                "success": True,
                "issue": {
                    "id": "issue-uuid-new",
                    "identifier": "GRC-202",
                    "url": "https://linear.app/acme/issue/GRC-202",
                    "title": "New GRC ticket",
                    "assignee": None,
                },
            }
        }
    }


def _assign_response() -> dict[str, Any]:
    return {
        "data": {
            "issueUpdate": {
                "success": True,
                "issue": {
                    "id": "issue-uuid-1",
                    "identifier": "GRC-101",
                    "url": "https://linear.app/acme/issue/GRC-101",
                    "assignee": {"id": "user-alice", "name": "alice"},
                },
            }
        }
    }


def _mock_response(payload: dict[str, Any]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=payload)
    return resp


def _make_create_live_cpo(queue: ApprovalQueue, ticket: dict[str, Any] | None = None) -> dict[str, Any]:
    ticket = ticket or {"id": "AI-2", "title": "New GRC ticket", "description": "From CPO"}
    return queue.create(
        action_class="A4",
        action_type="create_ticket_live",
        title="Create live Linear ticket",
        description="Authoritative ticket write",
        risk_rationale="Creates issue in Linear",
        proposed_change={
            "ticket": ticket,
            "provenance": {"skill": "ticket-draft", "input_sha256": "abc", "run_id": "run-1"},
        },
    )


def _make_assign_cpo(queue: ApprovalQueue) -> dict[str, Any]:
    return queue.create(
        action_class="A3",
        action_type="assign_human",
        title="Assign ticket to Alice",
        description="Human workflow change",
        risk_rationale="Assignee would change from unassigned",
        proposed_change={"assignee": "user-alice"},
    )


def test_linear_provider_contract_enabled(linear_config, mock_http_client):
    client = LinearGraphQLClient(linear_config.api_key, http_client=mock_http_client)
    provider = LinearTicketProvider(config=linear_config, client=client)
    contract = provider.contract()
    assert provider.enabled is True
    assert contract["capabilities"]["read"] is True
    assert contract["capabilities"]["create_live"] is True
    assert contract["gated_capabilities"] == ["create_live", "assign", "transition"]


def test_read_tickets_scoped_to_fixed_team(guard_setup, linear_config, mock_http_client):
    _, _, _ = guard_setup
    mock_http_client.post.return_value = _mock_response(_issues_response())
    client = LinearGraphQLClient(linear_config.api_key, http_client=mock_http_client)
    provider = LinearTicketProvider(config=linear_config, client=client)

    tickets = provider.read_tickets()

    assert len(tickets) == 1
    assert tickets[0]["id"] == "GRC-101"
    assert tickets[0]["team_id"] == linear_config.team_id
    assert tickets[0]["assignee"] == "unassigned"
    mock_http_client.post.assert_called_once()
    call_kwargs = mock_http_client.post.call_args.kwargs
    assert call_kwargs["json"]["variables"]["teamId"] == linear_config.team_id


def test_create_live_without_approved_cpo_refuses_zero_api_calls(
    guard_setup, linear_config, mock_http_client
):
    guard, _, audit_dir = guard_setup
    mock_http_client.post.return_value = _mock_response(_create_response())
    client = LinearGraphQLClient(linear_config.api_key, http_client=mock_http_client)
    provider = LinearTicketProvider(guard=guard, config=linear_config, client=client)

    with pytest.raises(ToolBlockedError):
        provider.create_live({"id": "AI-1", "title": "Blocked"})

    mock_http_client.post.assert_not_called()
    events = _read_audit_events(audit_dir)
    refused = [e for e in events if e["event_type"] == "ticket_create_live"]
    assert len(refused) == 1
    assert refused[0]["outputs"]["status"] == "refused"


def _route_create_with_label_and_comment(mock_http_client: MagicMock) -> None:
    def _post(url, **kwargs):
        query = kwargs["json"]["query"]
        if "TeamLabels" in query:
            return _mock_response(
                {"data": {"team": {"labels": {"nodes": [{"id": "label-ai", "name": "AI-Proposed"}]}}}}
            )
        if "issueCreate" in query:
            return _mock_response(_create_response())
        if "issueAddLabel" in query:
            return _mock_response({"data": {"issueAddLabel": {"success": True}}})
        if "CommentCreate" in query:
            return _mock_response(
                {"data": {"commentCreate": {"success": True, "comment": {"id": "c1", "body": "prov"}}}}
            )
        return _mock_response({"data": {}})

    mock_http_client.post.side_effect = _post


def test_create_live_with_approved_cpo_issues_to_fixed_team(
    guard_setup, linear_config, mock_http_client
):
    guard, queue, audit_dir = guard_setup
    cpo = _make_create_live_cpo(queue)
    queue.approve(cpo["id"])
    _route_create_with_label_and_comment(mock_http_client)
    client = LinearGraphQLClient(linear_config.api_key, http_client=mock_http_client)
    provider = LinearTicketProvider(guard=guard, config=linear_config, client=client)

    result = provider.create_live(
        {
            "id": "AI-2",
            "title": "New GRC ticket",
            "description": "From CPO",
            "provenance": {"skill": "ticket-draft", "input_sha256": "deadbeef", "run_id": "run-test"},
        },
        cpo_id=cpo["id"],
    )

    assert result["provider"] == "linear"
    assert result["ticket"]["id"] == "GRC-202"
    assert result["ticket"]["team_id"] == linear_config.team_id
    assert result["ticket"]["assignee"] == "unassigned"
    assert result["ticket"]["label"] == "AI-Proposed"
    assert mock_http_client.post.call_count >= 3
    mutation_vars = mock_http_client.post.call_args_list[0].kwargs["json"]["variables"]["input"]
    assert mutation_vars["teamId"] == linear_config.team_id
    assert mutation_vars["projectId"] == linear_config.project_id
    events = _read_audit_events(audit_dir)
    executed = [e for e in events if e["event_type"] == "ticket_create_live"]
    assert any(e["outputs"]["status"] == "executed" for e in executed)
    assert "tool_complete" in [e["event_type"] for e in events]
    assert any(
        e["event_type"] == "tool_notify" and "add_provenance_comment" in e.get("tools_called", [])
        for e in events
    )


def test_assign_without_approved_cpo_refuses_zero_api_calls(
    guard_setup, linear_config, mock_http_client
):
    guard, _, audit_dir = guard_setup
    mock_http_client.post.return_value = _mock_response(_assign_response())
    client = LinearGraphQLClient(linear_config.api_key, http_client=mock_http_client)
    provider = LinearTicketProvider(guard=guard, config=linear_config, client=client)

    with pytest.raises(ToolBlockedError):
        provider.assign("issue-uuid-1", "user-alice")

    mock_http_client.post.assert_not_called()
    events = _read_audit_events(audit_dir)
    refused = [e for e in events if e["event_type"] == "ticket_assign"]
    assert len(refused) == 1
    assert refused[0]["outputs"]["status"] == "refused"


def test_assign_with_approved_cpo_executes(
    guard_setup, linear_config, mock_http_client
):
    guard, queue, audit_dir = guard_setup
    cpo = _make_assign_cpo(queue)
    queue.approve(cpo["id"])
    mock_http_client.post.return_value = _mock_response(_assign_response())
    client = LinearGraphQLClient(linear_config.api_key, http_client=mock_http_client)
    provider = LinearTicketProvider(guard=guard, config=linear_config, client=client)

    result = provider.assign("issue-uuid-1", "user-alice", cpo_id=cpo["id"])

    assert result["assignee"] == "alice"
    mock_http_client.post.assert_called_once()
    mutation_vars = mock_http_client.post.call_args.kwargs["json"]["variables"]
    assert mutation_vars["id"] == "issue-uuid-1"
    assert mutation_vars["input"]["assigneeId"] == "user-alice"
    events = _read_audit_events(audit_dir)
    executed = [e for e in events if e["event_type"] == "ticket_assign"]
    assert any(e["outputs"]["status"] == "executed" for e in executed)


def test_registry_blocks_linear_when_live_write_disabled(monkeypatch):
    AutonomyPolicy.clear_cache()
    monkeypatch.setenv("TICKET_PROVIDER", "linear")
    monkeypatch.setenv("LINEAR_API_KEY", "test-key")
    monkeypatch.setenv("LINEAR_TEAM_ID", "team-abc")
    with pytest.raises(LiveWriteDisabledError):
        get_ticket_provider()
    AutonomyPolicy.clear_cache()


def test_registry_selects_linear_when_live_writes_enabled(
    monkeypatch, live_ticket_policy, linear_env
):
    provider = get_ticket_provider()
    assert provider.__class__ is LinearTicketProvider
    assert provider.enabled is True


def test_missing_linear_api_key_raises_config_error(monkeypatch, mock_http_client):
    monkeypatch.setenv("LINEAR_TEAM_ID", "team-abc")
    monkeypatch.delenv("LINEAR_API_KEY", raising=False)
    client = LinearGraphQLClient("fallback", http_client=mock_http_client)
    provider = LinearTicketProvider(client=client)

    with pytest.raises(LinearConfigError, match="LINEAR_API_KEY"):
        provider.read_tickets()


def test_missing_linear_team_id_raises_config_error(monkeypatch, mock_http_client):
    monkeypatch.setenv("LINEAR_API_KEY", "test-key")
    monkeypatch.delenv("LINEAR_TEAM_ID", raising=False)
    client = LinearGraphQLClient("test-key", http_client=mock_http_client)
    provider = LinearTicketProvider(client=client)

    with pytest.raises(LinearConfigError, match="LINEAR_TEAM_ID"):
        provider.read_tickets()
