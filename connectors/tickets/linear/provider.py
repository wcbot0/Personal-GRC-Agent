"""Linear adapter stub — DISABLED in MVP (no live writes)."""
from __future__ import annotations

from typing import Any

from connectors.interfaces.ticket import TicketCapabilities, TicketConnector
from connectors.messages import disabled_post_mvp_message

_DISABLED = disabled_post_mvp_message("linear", "TICKET_PROVIDER")


class LinearTicketProvider(TicketConnector):
    def __init__(self) -> None:
        super().__init__(
            provider="linear",
            enabled=False,
            capabilities=TicketCapabilities(read=True, create_draft=False, create_live=False),
            gated_capabilities=["create_live", "assign", "transition"],
        )

    def read_tickets(self, query: str | None = None) -> list[dict[str, Any]]:
        raise RuntimeError(_DISABLED)

    def create_draft(self, ticket: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(_DISABLED)
