"""Cloud evidence connector interface contract (provider-agnostic)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CloudCapabilities:
    read: bool = False
    collect: bool = False


@dataclass
class CloudConnector(ABC):
    provider: str
    enabled: bool = False
    capabilities: CloudCapabilities = field(default_factory=CloudCapabilities)

    @abstractmethod
    def collect(self, check: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Collect read-only audit findings for a named check."""
        raise NotImplementedError

    @abstractmethod
    def list_capabilities(self) -> list[str]:
        """Return supported check names for this provider."""
        raise NotImplementedError

    def contract(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "enabled": self.enabled,
            "capabilities": self.capabilities.__dict__,
        }
