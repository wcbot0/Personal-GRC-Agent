"""File-only ticket provider (MVP default)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from connectors.interfaces.ticket import TicketCapabilities, TicketConnector
from spa.paths import get_proposals_dir





class NoneTicketProvider(TicketConnector):
    def __init__(self) -> None:
        super().__init__(
            provider="none",
            enabled=True,
            capabilities=TicketCapabilities(read=False, create_draft=True),
            gated_capabilities=["assign", "transition", "create_live"],
        )
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
        self.out_dir.mkdir(parents=True, exist_ok=True)
        ticket = dict(ticket)
        ticket.setdefault("status", "ai_proposed")
        ticket.setdefault("assignee", "unassigned")
        ticket_id = ticket.get("id", "ai-proposed").replace("/", "-")
        fname = f"ticket-proposal-{ticket_id}.json"
        path = self.out_dir / fname
        path.write_text(json.dumps(ticket, indent=2), encoding="utf-8")
        return {"provider": "none", "path": str(path), "ticket": ticket}
