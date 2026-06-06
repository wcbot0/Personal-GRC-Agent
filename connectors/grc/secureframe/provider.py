"""Secureframe adapter stub — DISABLED in MVP."""
from __future__ import annotations

from typing import Any

from connectors.interfaces.grc import GrcCapabilities, GrcConnector
from connectors.messages import disabled_post_mvp_message

_DISABLED = disabled_post_mvp_message("secureframe", "GRC_PROVIDER")


class SecureframeGrcProvider(GrcConnector):
    def __init__(self, guard=None) -> None:
        super().__init__(
            provider="secureframe",
            enabled=False,
            capabilities=GrcCapabilities(read_controls=True, write_evidence=False),
            gated_capabilities=["write_evidence", "publish_policy"],
        )

    def read_controls(self) -> list[dict[str, Any]]:
        raise RuntimeError(_DISABLED)

    def draft_evidence(self, control_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(_DISABLED)
