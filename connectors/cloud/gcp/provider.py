"""GCP cloud connector stub — deferred to H9."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from connectors.interfaces.cloud import CloudCapabilities, CloudConnector

if TYPE_CHECKING:
    from spa.tools.guard import ToolGuard

_DEFERRED_MSG = "GCP cloud connector — deferred to H9"


class GcpCloudProvider(CloudConnector):
    def __init__(self, guard: "ToolGuard | None" = None) -> None:
        super().__init__(
            provider="gcp",
            enabled=False,
            capabilities=CloudCapabilities(read=False, collect=False),
        )
        self.guard = guard

    def collect(self, check: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise RuntimeError(_DEFERRED_MSG)

    def list_capabilities(self) -> list[str]:
        raise RuntimeError(_DEFERRED_MSG)
