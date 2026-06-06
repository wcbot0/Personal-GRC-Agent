"""No-op comms provider — MVP default (file-only ingestion)."""
from __future__ import annotations

from typing import Any

from connectors.interfaces.comms import CommsConnector


class NoneCommsProvider(CommsConnector):
    def __init__(self) -> None:
        super().__init__(provider="none", enabled=True)

    def read_messages(self, channel: str, limit: int = 50) -> list[dict[str, Any]]:
        return []
