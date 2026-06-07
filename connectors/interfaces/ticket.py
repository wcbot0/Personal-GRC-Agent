"""Ticket connector interface contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TicketCapabilities:
    read: bool = False
    create_draft: bool = False
    create_live: bool = False
    assign: bool = False
    transition: bool = False


@dataclass
class TicketConnector(ABC):
    provider: str
    enabled: bool = False
    capabilities: TicketCapabilities = field(default_factory=TicketCapabilities)
    gated_capabilities: list[str] = field(default_factory=list)

    @abstractmethod
    def read_tickets(self, query: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def create_draft(self, ticket: dict[str, Any]) -> dict[str, Any]:
        """MVP: write AI-Proposed unassigned ticket as local file."""
        raise NotImplementedError

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
        raise PermissionError("assign requires A3 + approved CPO")

    def contract(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "enabled": self.enabled,
            "capabilities": self.capabilities.__dict__,
            "gated_capabilities": self.gated_capabilities,
        }
