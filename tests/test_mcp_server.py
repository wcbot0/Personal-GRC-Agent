"""Governed MCP server tests."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from spa.audit.chain import verify_chain
from spa.audit.logger import AuditLogger
from spa.governance.policy import AutonomyPolicy
from spa.mcp_server import MCP_TOOL_NAMES, mcp, memory_search, pga_proposals_approve
from spa.paths import ROOT
from spa.tools.guard import ToolBlockedError, ToolGuard


def _read_audit_events(audit_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(audit_dir.glob("audit-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


@pytest.fixture
def mcp_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    audit_dir = tmp_path / "audit"
    queue_dir = tmp_path / "queue"
    proposals_dir = data_dir / "proposals"
    drafts_dir = data_dir / "drafts"
    for path in (data_dir, audit_dir, queue_dir, proposals_dir, drafts_dir):
        path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPA_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SPA_AUDIT_DIR", str(audit_dir))
    monkeypatch.setenv("SPA_APPROVAL_QUEUE_DIR", str(queue_dir))
    AutonomyPolicy.clear_cache()
    return {"data_dir": data_dir, "audit_dir": audit_dir, "queue_dir": queue_dir}


def test_mcp_tool_registry_matches_spec():
    registered = {tool.name for tool in mcp._tool_manager.list_tools()}  # noqa: SLF001
    assert registered == set(MCP_TOOL_NAMES)


def test_unknown_mcp_tool_classified_a5_blocked(mcp_env):
    guard = ToolGuard(audit=AuditLogger(log_dir=mcp_env["audit_dir"]))
    with pytest.raises(ToolBlockedError):
        guard.check_allowed("pga_totally_unknown_tool")
    blocked = [e for e in _read_audit_events(mcp_env["audit_dir"]) if e["event_type"] == "tool_blocked"]
    assert blocked
    assert blocked[0]["risk_class"] == "A5"


def test_pga_proposals_approve_without_confirm_fails(mcp_env):
    with pytest.raises(ValueError, match="confirm=true required"):
        pga_proposals_approve("cpo-does-not-matter", confirm=False)

    events = _read_audit_events(mcp_env["audit_dir"])
    blocked = [e for e in events if e["event_type"] == "tool_blocked"]
    assert blocked
    assert blocked[0]["tools_called"] == ["pga_proposals_approve"]
    assert "confirm" in blocked[0]["outputs"]["reason"]


def test_mcp_ingest_and_run_skill_produce_audited_artifacts(mcp_env):
    from spa.mcp_server import pga_ingest, pga_proposals_list, pga_run_skill

    fixture = ROOT / "evals/fixtures/meeting_sample.md"
    ingest_payload = json.loads(pga_ingest(str(fixture)))
    assert ingest_payload["meeting_synth"] is not None

    out_dir = ROOT / "workspace" / "drafts" / "meeting-synth-mcp-test"
    out_dir.mkdir(parents=True, exist_ok=True)
    skill_payload = json.loads(
        pga_run_skill("meeting-synth", str(fixture), output_dir=str(out_dir))
    )
    assert skill_payload["skill"] == "meeting-synth"
    assert Path(skill_payload["artifact"]).exists()

    proposals = json.loads(pga_proposals_list(status="all"))
    assert isinstance(proposals, list)

    events = _read_audit_events(mcp_env["audit_dir"])
    event_types = [e["event_type"] for e in events]
    assert "tool_start" in event_types
    assert "tool_complete" in event_types

    chain = verify_chain(mcp_env["audit_dir"])
    assert chain.valid
    assert chain.event_count >= 2


def test_memory_search_offline_fallback(mcp_env):
    guard = ToolGuard(audit=AuditLogger(log_dir=mcp_env["audit_dir"]))
    result = memory_search("meeting", k=3, guard=guard)
    assert "episodic" in result
    assert "semantic" in result
    events = _read_audit_events(mcp_env["audit_dir"])
    assert any(e["tools_called"] == ["pga_memory_search"] for e in events)


@pytest.mark.anyio
async def test_mcp_stdio_round_trip(mcp_env):
    """Scripted MCP client: ingest fixture → run meeting-synth → list proposals."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    python = sys.executable
    server_params = StdioServerParameters(
        command=python,
        args=["-m", "spa.mcp_server"],
        env={
            "SPA_DATA_DIR": str(mcp_env["data_dir"]),
            "SPA_AUDIT_DIR": str(mcp_env["audit_dir"]),
            "SPA_APPROVAL_QUEUE_DIR": str(mcp_env["queue_dir"]),
        },
        cwd=str(ROOT),
    )
    fixture = ROOT / "evals/fixtures/meeting_sample.md"
    out_dir = ROOT / "workspace" / "drafts" / "meeting-synth-stdio-test"
    out_dir.mkdir(parents=True, exist_ok=True)

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = {t.name for t in tools.tools}
            assert tool_names == set(MCP_TOOL_NAMES)

            ingest_result = await session.call_tool("pga_ingest", arguments={"path": str(fixture)})
            ingest_text = ingest_result.content[0].text
            assert "meeting_synth" in ingest_text

            skill_result = await session.call_tool(
                "pga_run_skill",
                arguments={
                    "skill": "meeting-synth",
                    "input_path": str(fixture),
                    "output_dir": str(out_dir),
                },
            )
            assert "meeting-synth" in skill_result.content[0].text

            list_result = await session.call_tool("pga_proposals_list", arguments={"status": "all"})
            assert list_result.content[0].text.startswith("[")

    chain = verify_chain(mcp_env["audit_dir"])
    assert chain.valid


def test_pga_ingest_rejects_path_outside_allowlist(mcp_env):
    from spa.mcp_server import pga_ingest

    payload = json.loads(pga_ingest("/etc/passwd"))
    assert "error" in payload

    payload = json.loads(pga_ingest("../../etc/passwd"))
    assert "error" in payload


def test_pga_run_skill_rejects_unsafe_paths(mcp_env):
    from spa.mcp_server import pga_run_skill

    fixture = ROOT / "evals/fixtures/meeting_sample.md"

    read_payload = json.loads(pga_run_skill("meeting-synth", "/etc/passwd"))
    assert "error" in read_payload

    write_payload = json.loads(
        pga_run_skill("meeting-synth", str(fixture), output_dir="/tmp/pga-escape")
    )
    assert "error" in write_payload

    traversal_payload = json.loads(
        pga_run_skill("meeting-synth", str(fixture), output_dir="../../..")
    )
    assert "error" in traversal_payload


def test_pga_proposals_approve_with_confirm_logs_warning(mcp_env, capsys):
    from spa.governance.approval_queue import ApprovalQueue
    from spa.mcp_server import pga_proposals_approve

    queue = ApprovalQueue(audit=AuditLogger(log_dir=mcp_env["audit_dir"]))
    cpo = queue.create(
        action_class="A3",
        action_type="assign_human",
        title="Test assign",
        description="Human workflow change",
        risk_rationale="Test CPO for MCP warning audit",
        proposed_change={"assignee": "alice"},
    )
    cpo_id = cpo["id"]

    pga_proposals_approve(cpo_id, confirm=True)

    captured = capsys.readouterr()
    assert "WARNING [PGA MCP]" in captured.err
    assert "pga_proposals_approve" in captured.err
    assert cpo_id in captured.err


def test_pga_audit_verify_allow_legacy(mcp_env):
    from spa.audit.logger import AuditLogger
    from spa.mcp_server import pga_audit_verify

    legacy_event = {
        "event_id": "legacy-1",
        "run_id": "r1",
        "timestamp": "2026-06-05T10:00:00+00:00",
        "event_type": "old",
        "task_class": "test",
        "risk_class": "A0",
    }
    legacy_file = mcp_env["audit_dir"] / "audit-2026-06-05.jsonl"
    legacy_file.write_text(json.dumps(legacy_event) + "\n", encoding="utf-8")

    AuditLogger(log_dir=mcp_env["audit_dir"]).emit("new", task_class="test", risk_class="A0")

    allowed = json.loads(pga_audit_verify(allow_legacy=True))
    assert allowed["valid"] is True
    assert allowed["legacy_count"] == 1
    assert allowed["warnings"]

    default = json.loads(pga_audit_verify())
    assert default["valid"] is False
    assert any("legacy event without hash" in b["reason"] for b in default["breaks"])
