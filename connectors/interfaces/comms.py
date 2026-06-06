"""Comms connector interface (Slack, email — disabled in MVP)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class CommsConnector(ABC):
    provider: str
    enabled: bool = False

    @abstractmethod
    def read_messages(self, channel: str, limit: int = 50) -> list[dict[str, Any]]:
        raise NotImplementedError

    def send_message(self, *args, **kwargs) -> dict[str, Any]:
        raise PermissionError("Outbound comms blocked in MVP")

    def contract(self) -> dict[str, Any]:
        return {"provider": self.provider, "enabled": self.enabled}
