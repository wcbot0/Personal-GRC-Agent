"""Propose publishing AI-Proposed ticket drafts to external systems (A2 notify + A4 CPO)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from spa.governance.approval_queue import ApprovalQueue
from spa.governance.policy import AutonomyPolicy
from spa.paths import get_proposals_dir
from spa.tools.guard import ToolBlockedError, ToolGuard

AI_PROPOSED_LABEL = "AI-Proposed"


def _resolve_ticket_proposal(path: str | Path | None = None, ticket_id: str | None = None) -> tuple[dict[str, Any], Path]:
    if path:
        proposal_path = Path(path)
        if not proposal_path.exists():
            raise FileNotFoundError(f"Ticket proposal not found: {proposal_path}")
        ticket = json.loads(proposal_path.read_text(encoding="utf-8"))
        return ticket, proposal_path

    if not ticket_id:
        raise ValueError("ticket_id or path is required")

    tickets_dir = get_proposals_dir() / "tickets"
    safe_id = str(ticket_id).replace("/", "-")
    matches = sorted(tickets_dir.glob(f"*{safe_id}*.json"))
    if matches:
        proposal_path = matches[0]
    else:
        proposal_path = tickets_dir / f"ticket-proposal-{safe_id}.json"
    if not proposal_path.exists():
        raise FileNotFoundError(f"Ticket proposal not found: {proposal_path}")
    ticket = json.loads(proposal_path.read_text(encoding="utf-8"))
    return ticket, proposal_path


def _input_sha256(proposal_path: Path) -> str:
    return hashlib.sha256(proposal_path.read_bytes()).hexdigest()


def propose_ai_proposed_ticket_cpo(
    *,
    guard: ToolGuard,
    queue: ApprovalQueue,
    path: str | Path | None = None,
    ticket_id: str | None = None,
    skill: str = "ticket-draft",
    run_id: str | None = None,
) -> str:
    """Emit A2 notify, then create pending A4 CPO for live ticket publish (never executes)."""
    ticket, proposal_path = _resolve_ticket_proposal(path=path, ticket_id=ticket_id)
    tid = ticket.get("id") or ticket_id or proposal_path.stem
    provenance = {
        "skill": skill,
        "input_sha256": _input_sha256(proposal_path),
        "run_id": run_id or guard.audit.run_id,
        "label": AI_PROPOSED_LABEL,
    }

    guard.execute(
        "create_ai_proposed_ticket",
        lambda: {"ticket_id": tid, "path": str(proposal_path)},
        preview=f"ticket_id={tid}",
        audit_outputs=lambda _: {
            "ticket_id": tid,
            "path": str(proposal_path),
            "live_write_enabled": AutonomyPolicy.load().live_writes_enabled("ticket"),
        },
    )

    try:
        guard.execute(
            "create_ticket_live",
            lambda: None,
            create_cpo=lambda: queue.create(
                action_class="A4",
                action_type="create_ticket_live",
                title=f"Publish {tid} to external ticket system",
                description=(
                    f"Create live issue for AI-Proposed ticket '{ticket.get('title', tid)}' "
                    f"with {AI_PROPOSED_LABEL} label and provenance comment."
                ),
                risk_rationale="Authoritative external ticket write requires human approval",
                proposed_change={
                    "ticket": ticket,
                    "path": str(proposal_path),
                    "provenance": provenance,
                },
                control_tags=ticket.get("control_tags", []),
                run_id=provenance["run_id"],
            ),
        )
    except ToolBlockedError as exc:
        if exc.cpo_id:
            return exc.cpo_id
        raise

    raise RuntimeError("create_ticket_live should always block with pending CPO")
