"""Vanta adapter stub — DISABLED in MVP."""
from __future__ import annotations

from typing import Any

from connectors.interfaces.grc import GrcCapabilities, GrcConnector


class VantaGrcProvider(GrcConnector):
    def __init__(self) -> None:
        super().__init__(
            provider="vanta",
            enabled=False,
            capabilities=GrcCapabilities(read_controls=True, write_evidence=False),
            gated_capabilities=["write_evidence", "publish_policy"],
        )

    def read_controls(self) -> list[dict[str, Any]]:
        raise RuntimeError("Vanta provider disabled in MVP.")

    def draft_evidence(self, control_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("Vanta writes disabled in MVP.")
