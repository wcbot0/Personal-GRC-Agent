"""GRC connector interface contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GrcCapabilities:
    read_controls: bool = False
    read_evidence: bool = False
    write_evidence: bool = False
    publish_policy: bool = False


@dataclass
class GrcConnector(ABC):
    provider: str
    enabled: bool = False
    capabilities: GrcCapabilities = field(default_factory=GrcCapabilities)
    gated_capabilities: list[str] = field(default_factory=list)

    @abstractmethod
    def read_controls(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def draft_evidence(self, control_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def write_evidence(self, control_id: str, payload: dict[str, Any], *, cpo_approved: bool = False) -> dict[str, Any]:
        raise PermissionError("GRC write requires A4 + approved CPO (disabled in MVP)")

    def contract(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "enabled": self.enabled,
            "capabilities": self.capabilities.__dict__,
            "gated_capabilities": self.gated_capabilities,
        }
