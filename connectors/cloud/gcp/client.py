"""GCP MCP client — read-only run_gcloud transport (injectable for tests)."""
from __future__ import annotations

from typing import Any, Callable

from connectors.cloud.gcp.config import GcpCloudConfig

McpInvoke = Callable[[str, dict[str, Any]], Any]


class GcpMcpClientError(RuntimeError):
    pass


class GcpMcpClient:
    """Thin MCP client for GCP read-only evidence collection.

    Production use requires a running GCP MCP server configured in mcp/gcp.json.
    Tests inject ``invoke`` to mock all network/MCP I/O. The transport tool name
    (``run_gcloud``) is stable so the backing MCP server can be swapped without
    changing provider behavior.
    """

    READ_ONLY_TOOLS = frozenset({"run_gcloud", "search_documentation", "read_documentation"})

    def __init__(
        self,
        config: GcpCloudConfig,
        *,
        invoke: McpInvoke | None = None,
    ) -> None:
        self._config = config
        self._invoke = invoke

    def run_gcloud(self, gcloud_command: str) -> dict[str, Any]:
        if self._invoke is None:
            raise GcpMcpClientError(
                "GCP MCP transport is not configured. Enable mcp/gcp.json and run the "
                "GCP MCP Server, or inject invoke= for isolated testing."
            )
        cli_command = f"gcloud {gcloud_command}"
        if self._config.project_id and "--project" not in cli_command:
            cli_command = f"{cli_command} --project {self._config.project_id}"
        if self._config.organization_id and "--organization" not in cli_command:
            if gcloud_command.startswith("scc ") or gcloud_command.startswith("resource-manager org-policies"):
                cli_command = f"{cli_command} --organization {self._config.organization_id}"
        result = self._invoke("run_gcloud", {"cli_command": cli_command})
        if not isinstance(result, dict):
            raise GcpMcpClientError(f"Unexpected MCP run_gcloud response type: {type(result)!r}")
        return result

    def list_mcp_tools(self) -> list[str]:
        if self._invoke is None:
            return sorted(self.READ_ONLY_TOOLS)
        result = self._invoke("tools/list", {})
        tools = result.get("tools") if isinstance(result, dict) else None
        if isinstance(tools, list):
            return [str(name) for name in tools]
        return sorted(self.READ_ONLY_TOOLS)
