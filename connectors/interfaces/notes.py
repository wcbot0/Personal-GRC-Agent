"""Notes/knowledge connector interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class NotesConnector(ABC):
    provider: str
    enabled: bool = True

    @abstractmethod
    def read(self, path: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def list_sources(self) -> list[str]:
        raise NotImplementedError

    def contract(self) -> dict[str, Any]:
        return {"provider": self.provider, "enabled": self.enabled}
