"""Safe default cloud provider — no external cloud access."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from connectors.interfaces.cloud import CloudCapabilities, CloudConnector

if TYPE_CHECKING:
    from spa.tools.guard import ToolGuard

_NO_PROVIDER_MSG = (
    "No cloud provider configured. Set CLOUD_PROVIDER=aws or CLOUD_PROVIDER=gcp "
    "and enable the provider in autonomy-policy.yaml to collect cloud evidence."
)


class NoneCloudProvider(CloudConnector):
    def __init__(self, guard: "ToolGuard | None" = None) -> None:
        super().__init__(
            provider="none",
            enabled=True,
            capabilities=CloudCapabilities(read=False, collect=False),
        )
        self.guard = guard

    def collect(self, check: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        raise RuntimeError(_NO_PROVIDER_MSG)

    def list_capabilities(self) -> list[str]:
        return []
