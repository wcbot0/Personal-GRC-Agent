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
