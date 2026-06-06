"""Slack adapter stub — DISABLED in MVP (conversation ingestion deferred)."""
from __future__ import annotations

from typing import Any

from connectors.interfaces.comms import CommsConnector
from connectors.messages import disabled_post_mvp_message

_DISABLED = disabled_post_mvp_message("slack", "COMMS_PROVIDER")


class SlackCommsProvider(CommsConnector):
    def __init__(self) -> None:
        super().__init__(provider="slack", enabled=False)

    def read_messages(self, channel: str, limit: int = 50) -> list[dict[str, Any]]:
        raise RuntimeError(_DISABLED)
