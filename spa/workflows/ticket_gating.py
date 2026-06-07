"""Propose gated ticket actions (A3+) after A2 drafts — CPO pending, no execution."""
from __future__ import annotations

from typing import Any

from spa.governance.approval_queue import ApprovalQueue
from spa.tools.guard import ToolBlockedError, ToolGuard


def propose_assign_human_cpos(
    proposals: list[dict[str, Any]],
    *,
    guard: ToolGuard,
    queue: ApprovalQueue,
) -> list[str]:
    """Attempt assign_human for each draft; ToolGuard creates pending CPO, never executes."""
    cpo_ids: list[str] = []
    for proposal in proposals:
        ticket = proposal.get("ticket") or {}
        suggested = ticket.get("suggested_owner")
        if not suggested or suggested == "unassigned":
            continue

        ticket_id = ticket.get("id")
        if not ticket_id:
            continue

        try:
            guard.execute(
                "assign_human",
                lambda: None,
                create_cpo=lambda: queue.create(
                    action_class="A3",
                    action_type="assign_human",
                    title=f"Assign {ticket_id} to {suggested}",
                    description=f"Proposed assignment from meeting action item: {ticket.get('title', ticket_id)}",
                    risk_rationale="Assignee would change from unassigned to a human owner",
                    proposed_change={
                        "ticket_id": ticket_id,
                        "assignee": suggested,
                        "path": proposal.get("path"),
                    },
                    control_tags=ticket.get("control_tags", []),
                ),
            )
        except ToolBlockedError as exc:
            if exc.cpo_id:
                cpo_ids.append(exc.cpo_id)
    return cpo_ids
