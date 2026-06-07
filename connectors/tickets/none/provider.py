"""File-only ticket provider (MVP default)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from connectors.interfaces.ticket import TicketCapabilities, TicketConnector
from spa.paths import get_proposals_dir
from spa.tools.write import guarded_write

if TYPE_CHECKING:
    from spa.tools.guard import ToolGuard


class NoneTicketProvider(TicketConnector):
    def __init__(self, guard: "ToolGuard | None" = None) -> None:
        super().__init__(
            provider="none",
            enabled=True,
            capabilities=TicketCapabilities(read=False, create_draft=True),
            gated_capabilities=["assign", "transition", "create_live"],
        )
        self.guard = guard
        self.out_dir = get_proposals_dir() / "tickets"

    def read_tickets(self, query: str | None = None) -> list[dict[str, Any]]:
        if not self.out_dir.exists():
            return []
        tickets = []
        for path in self.out_dir.glob("*.json"):
            tickets.append(json.loads(path.read_text(encoding="utf-8")))
        if query:
            q = query.lower()
            tickets = [t for t in tickets if q in json.dumps(t).lower()]
        return tickets

    def create_draft(self, ticket: dict[str, Any]) -> dict[str, Any]:
        def _write() -> dict[str, Any]:
            self.out_dir.mkdir(parents=True, exist_ok=True)
            record = dict(ticket)
            record.setdefault("status", "ai_proposed")
            record.setdefault("assignee", "unassigned")
            ticket_id = record.get("id", "ai-proposed").replace("/", "-")
            fname = f"ticket-proposal-{ticket_id}.json"
            path = self.out_dir / fname
            path.write_text(json.dumps(record, indent=2), encoding="utf-8")
            return {"provider": "none", "path": str(path), "ticket": record}

        if self.guard:
            return guarded_write(
                self.guard,
                "create_ticket_draft",
                _write,
                preview=ticket.get("id", "ticket"),
                audit_outputs=lambda result: {
                    "provider": result["provider"],
                    "path": result["path"],
                    "ticket_id": result["ticket"].get("id"),
                },
            )
        return _write()

    def _resolve_ticket_path(self, ticket_id: str, path: str | Path | None = None) -> Path | None:
        if path:
            return Path(path)
        safe_id = str(ticket_id).replace("/", "-")
        matches = sorted(self.out_dir.glob(f"*{safe_id}*.json"))
        if matches:
            return matches[0]
        candidate = self.out_dir / f"ticket-proposal-{safe_id}.json"
        return candidate if candidate.exists() else None

    def assign(
        self,
        ticket_id: str,
        assignee: str,
        *,
        cpo_approved: bool = False,
        cpo_id: str | None = None,
        path: str | Path | None = None,
        status: str = "assigned",
    ) -> dict[str, Any]:
        if not cpo_approved or not cpo_id:
            raise PermissionError("assign requires A3 + approved CPO")

        def _write() -> dict[str, Any]:
            ticket_path = self._resolve_ticket_path(ticket_id, path)
            if ticket_path is None or not ticket_path.exists():
                return {"assignee": assignee, "ticket_id": ticket_id, "status": status}

            ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
            before = ticket.get("assignee", "unassigned")
            ticket["assignee"] = assignee
            ticket["status"] = status
            ticket_path.parent.mkdir(parents=True, exist_ok=True)
            ticket_path.write_text(json.dumps(ticket, indent=2), encoding="utf-8")
            return {
                "provider": self.provider,
                "assignee": assignee,
                "ticket_id": ticket.get("id", ticket_id),
                "path": str(ticket_path),
                "previous_assignee": before,
                "status": ticket["status"],
            }

        if self.guard:
            return self.guard.execute(
                "assign_human",
                _write,
                cpo_id=cpo_id,
                preview=f"ticket_id={ticket_id} assignee={assignee}",
                audit_outputs=lambda result: {
                    "provider": result.get("provider", self.provider),
                    "ticket_id": result.get("ticket_id", ticket_id),
                    "assignee": result.get("assignee", assignee),
                    "path": result.get("path"),
                },
            )
        return _write()
