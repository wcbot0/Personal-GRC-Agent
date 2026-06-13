"""Governed MCP server — all tools route through ToolGuard + audit trail."""
from __future__ import annotations

import json
import sys
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
from spa.paths import BRAIN_DIR, EVALS_DIR, INBOX_DIR, ROOT, WORKSPACE_DIR, get_audit_logs_dir
from spa.skills.runner import run_skill
from spa.tools.guard import ToolBlockedError, ToolGuard

_READ_ROOTS = (
    INBOX_DIR,
    BRAIN_DIR,
    WORKSPACE_DIR,
    EVALS_DIR,
)
_WRITE_ROOTS = (
    WORKSPACE_DIR,
    BRAIN_DIR / "evidence",
)

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


def _resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve()


def _confine(path: str | Path, allowed_roots: tuple[Path, ...], *, label: str = "path") -> Path:
    resolved = _resolve_repo_path(path)
    root = ROOT.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{label} must be under repository root")
    roots = tuple(r.resolve() for r in allowed_roots)
    if not any(resolved.is_relative_to(r) for r in roots):
        allowed = ", ".join(str(r.relative_to(root)) for r in roots)
        raise ValueError(f"{label} must be under one of: {allowed}")
    return resolved


def _ensure_known_tool(tool_name: str, guard: ToolGuard) -> None:
    if tool_name not in MCP_TOOL_NAMES:
        guard.classify(tool_name)
        guard.check_allowed(tool_name)


def _execute_human_gate(
    tool_name: str,
    fn: Any,
    *,
    confirm: bool,
    guard: ToolGuard | None = None,
    cpo_id: str | None = None,
) -> Any:
    """A3 human-gate actions: require explicit confirm and emit audit events.

    `confirm=true` is client-asserted — the audit `human_confirmed` metadata records
    the MCP client's claim, not independent human verification.
    """
    # Intentionally bypass ToolGuard.check_allowed: approve/reject are A3 tools that
    # would otherwise require a CPO to approve a CPO (circular). Re-implement the A5
    # block check and audit emission here instead. Keep this path aligned with
    # guard.py policy semantics when autonomy-policy.yaml or ToolGuard changes.
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

    cpo_label = f" cpo_id={cpo_id}" if cpo_id else ""
    print(
        f"WARNING [PGA MCP]: Client asserted human confirmation for action={tool_name}{cpo_label} "
        "(client-asserted only; not independent verification)",
        file=sys.stderr,
    )

    guard.audit.emit(
        "tool_start",
        task_class="mcp",
        risk_class=action_class,
        tools_called=[tool_name],
        approval_required=True,
        metadata={"human_confirmed": True, "cpo_id": cpo_id} if cpo_id else {"human_confirmed": True},
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
    try:
        file_path = _confine(path, _READ_ROOTS, label="path")
    except ValueError as exc:
        return _json_result({"error": str(exc)})

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
    try:
        in_path = _confine(input_path, _READ_ROOTS, label="input_path")
        confined_output_dir: str | None = None
        if output_dir is not None:
            confined_output_dir = str(_confine(output_dir, _WRITE_ROOTS, label="output_dir"))
    except ValueError as exc:
        return _json_result({"error": str(exc)})

    def _run() -> dict[str, Any]:
        return run_skill(
            skill,
            in_path,
            output_dir=confined_output_dir,
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
        result = _execute_human_gate(
            "pga_proposals_approve", _approve, confirm=confirm, guard=guard, cpo_id=id
        )
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
        result = _execute_human_gate(
            "pga_proposals_reject", _reject, confirm=confirm, guard=guard, cpo_id=id
        )
    except ApprovalQueueError as exc:
        return _json_result({"error": str(exc)})
    return _json_result(result)


@mcp.tool()
def pga_audit_verify(
    from_date: str | None = None, to_date: str | None = None, allow_legacy: bool = False
) -> str:
    """Verify hash chain integrity of audit JSONL logs (allow_legacy mirrors CLI --allow-legacy)."""
    guard = _guard()

    def _verify() -> dict[str, Any]:
        start, end = parse_export_dates(from_date, to_date)
        result = verify_chain(
            get_audit_logs_dir(), start=start, end=end, require_full_chain=not allow_legacy
        )
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
