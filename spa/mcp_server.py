"""Governed MCP server — all tools route through ToolGuard + audit trail."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from spa.audit.chain import verify_chain
from spa.audit.logger import AuditLogger
from spa.evidence.export import parse_export_dates
from spa.governance.approval_queue import ApprovalQueue, ApprovalQueueError
from spa.ingest import ingest_file
from spa.memory.episodic import EpisodicMemory
from spa.memory.semantic import SemanticMemory
from spa.paths import ROOT, get_audit_logs_dir
from spa.skills.runner import run_skill
from spa.tools.guard import ToolBlockedError, ToolGuard

MCP_TOOL_NAMES = frozenset(
    {
        "pga_ingest",
        "pga_run_skill",
        "pga_proposals_list",
        "pga_proposals_show",
        "pga_proposals_approve",
        "pga_proposals_reject",
        "pga_audit_verify",
        "pga_memory_search",
    }
)

mcp = FastMCP(
    "pga-governed",
    instructions=(
        "Personal GRC Agent governed tools. All writes pass ToolGuard, verifiers, "
        "and hash-chained audit. Approve/reject require confirm=true — surface to the human."
    ),
)


def _guard() -> ToolGuard:
    return ToolGuard(audit=AuditLogger())


def _json_result(payload: Any) -> str:
    return json.dumps(payload, indent=2, default=str)


def _ensure_known_tool(tool_name: str, guard: ToolGuard) -> None:
    if tool_name not in MCP_TOOL_NAMES:
        guard.classify(tool_name)
        guard.check_allowed(tool_name)


def _execute_human_gate(tool_name: str, fn: Any, *, confirm: bool, guard: ToolGuard | None = None) -> Any:
    """A3 human-gate actions: require explicit confirm and emit audit events.

    Intentionally bypasses ToolGuard.check_allowed: approving a CPO via ToolGuard
    would require a CPO to approve the CPO (circular). This path re-implements the
    A5 block check and audit emission directly — keep semantics in sync with guard.py.

    confirm=true is client-asserted; audit metadata human_confirmed records the
    client's claim, not independent server-side verification of human intent.
    """
    guard = guard or _guard()
    _ensure_known_tool(tool_name, guard)
    if not confirm:
        guard.audit.emit(
            "tool_blocked",
            task_class="mcp",
            risk_class=guard.classify(tool_name),
            tools_called=[tool_name],
            approval_required=True,
            outputs={"reason": "confirm=true required — MCP client must surface to human"},
        )
        raise ValueError("confirm=true required — MCP clients must surface this to the human")

    action_class = guard.classify(tool_name)
    if guard.policy.is_blocked(action_class):
        guard.audit.emit(
            "tool_blocked",
            task_class="mcp",
            risk_class=action_class,
            tools_called=[tool_name],
            approval_required=True,
            outputs={"reason": "A5 blocked by policy"},
        )
        raise ToolBlockedError(f"Tool '{tool_name}' blocked (class {action_class})")

    guard.audit.emit(
        "tool_start",
        task_class="mcp",
        risk_class=action_class,
        tools_called=[tool_name],
        approval_required=True,
        metadata={"human_confirmed": True},
    )
    result = fn()
    guard.audit.emit(
        "tool_complete",
        task_class="mcp",
        risk_class=action_class,
        tools_called=[tool_name],
        outputs=result if isinstance(result, (dict, list, str)) else {"result": str(result)},
    )
    return result


def memory_search(query: str, k: int = 5, guard: ToolGuard | None = None) -> dict[str, Any]:
    guard = guard or _guard()

    def _search() -> dict[str, Any]:
        episodic = EpisodicMemory().search(query, limit=k)
        semantic = SemanticMemory().query(query, limit=k)
        return {
            "query": query,
            "k": k,
            "episodic": episodic,
            "semantic": semantic,
        }

    return guard.execute(
        "pga_memory_search",
        _search,
        task_class="mcp",
        audit_outputs=lambda payload: {
            "query": query,
            "k": k,
            "episodic_count": len(payload["episodic"]),
            "semantic_count": len(payload["semantic"]),
        },
    )


@mcp.tool()
def pga_ingest(path: str) -> str:
    """Ingest a file into episodic + semantic memory (and auto-pipeline when meeting signals match)."""
    guard = _guard()
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = ROOT / file_path

    def _ingest() -> dict[str, Any]:
        return ingest_file(file_path, audit=guard.audit)

    result = guard.execute(
        "pga_ingest",
        _ingest,
        preview=f"path={file_path.name}",
        task_class="mcp",
        audit_outputs=lambda payload: {
            "source": payload.get("source"),
            "episodic_id": payload.get("episodic_id"),
            "meeting_synth": payload.get("meeting_synth") is not None,
            "ticket_count": len(payload.get("ticket_proposals") or []),
        },
    )
    return _json_result(result)


@mcp.tool()
def pga_run_skill(skill: str, input_path: str, output_dir: str | None = None) -> str:
    """Run a drafting skill with verifiers and audit trail."""
    guard = _guard()
    in_path = Path(input_path)
    if not in_path.is_absolute():
        in_path = ROOT / in_path

    def _run() -> dict[str, Any]:
        return run_skill(
            skill,
            in_path,
            output_dir=output_dir,
            audit=guard.audit,
            guard=guard,
        )

    result = guard.execute(
        "pga_run_skill",
        _run,
        preview=f"skill={skill} input={in_path.name}",
        task_class="mcp",
        audit_outputs=lambda payload: {
            "skill": payload.get("skill"),
            "artifact": payload.get("artifact"),
        },
    )
    return _json_result(result)


@mcp.tool()
def pga_proposals_list(status: str = "pending") -> str:
    """List change proposal objects (CPOs) in the approval queue."""
    guard = _guard()

    def _list() -> list[dict[str, str]]:
        queue = ApprovalQueue(audit=guard.audit)
        filter_status = None if status == "all" else status
        return [ApprovalQueue.summary_row(cpo) for cpo in queue.list_proposals(status=filter_status)]

    rows = guard.execute("pga_proposals_list", _list, task_class="mcp")
    return _json_result(rows)


@mcp.tool()
def pga_proposals_show(id: str) -> str:
    """Show a single CPO with preview."""
    guard = _guard()

    def _show() -> dict[str, Any]:
        queue = ApprovalQueue(audit=guard.audit)
        return queue.get_detail(id)

    try:
        detail = guard.execute("pga_proposals_show", _show, task_class="mcp", preview=f"cpo={id}")
    except ApprovalQueueError as exc:
        return _json_result({"error": str(exc)})
    return _json_result(detail)


@mcp.tool()
def pga_proposals_approve(id: str, confirm: bool = False) -> str:
    """Approve a pending CPO (A3 human gate — confirm=true required)."""
    guard = _guard()
    queue = ApprovalQueue(audit=guard.audit)

    def _approve() -> dict[str, Any]:
        return queue.approve_and_execute(id)

    try:
        result = _execute_human_gate("pga_proposals_approve", _approve, confirm=confirm, guard=guard)
    except ApprovalQueueError as exc:
        return _json_result({"error": str(exc)})
    return _json_result(result)


@mcp.tool()
def pga_proposals_reject(id: str, reason: str, confirm: bool = False) -> str:
    """Reject a pending CPO (A3 human gate — confirm=true required)."""
    guard = _guard()
    queue = ApprovalQueue(audit=guard.audit)

    def _reject() -> dict[str, Any]:
        cpo = queue.reject(id, reason=reason)
        return {"cpo": cpo}

    try:
        result = _execute_human_gate("pga_proposals_reject", _reject, confirm=confirm, guard=guard)
    except ApprovalQueueError as exc:
        return _json_result({"error": str(exc)})
    return _json_result(result)


@mcp.tool()
def pga_audit_verify(from_date: str | None = None, to_date: str | None = None) -> str:
    """Verify hash chain integrity of audit JSONL logs."""
    guard = _guard()

    def _verify() -> dict[str, Any]:
        start, end = parse_export_dates(from_date, to_date)
        result = verify_chain(get_audit_logs_dir(), start=start, end=end)
        return {
            "valid": result.valid,
            "event_count": result.event_count,
            "legacy_count": result.legacy_count,
            "chain_starts": result.chain_starts,
            "breaks": [
                {"event_id": b.event_id, "line": b.line_number, "reason": b.reason}
                for b in result.breaks
            ],
            "warnings": result.warnings,
        }

    payload = guard.execute("pga_audit_verify", _verify, task_class="mcp")
    return _json_result(payload)


@mcp.tool()
def pga_memory_search(query: str, k: int = 5) -> str:
    """Search episodic FTS + semantic memory."""
    return _json_result(memory_search(query, k=k))


def serve_stdio() -> None:
    """Run the governed MCP server on stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    serve_stdio()
