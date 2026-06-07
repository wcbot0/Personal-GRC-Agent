"""AWS MCP Server client — read-only call_aws transport (injectable for tests)."""
from __future__ import annotations

from typing import Any, Callable

from connectors.cloud.aws.config import AwsCloudConfig

McpInvoke = Callable[[str, dict[str, Any]], Any]


class AwsMcpClientError(RuntimeError):
    pass


class AwsMcpClient:
    """Thin MCP client for the official AWS MCP Server (awslabs, GA).

    Production use requires a running MCP server configured in mcp/aws.json.
    Tests inject ``invoke`` to mock all network/MCP I/O.
    """

    READ_ONLY_TOOLS = frozenset({"call_aws", "search_documentation", "read_documentation"})

    def __init__(
        self,
        config: AwsCloudConfig,
        *,
        invoke: McpInvoke | None = None,
    ) -> None:
        self._config = config
        self._invoke = invoke

    def call_aws(self, service_command: str) -> dict[str, Any]:
        if self._invoke is None:
            raise AwsMcpClientError(
                "AWS MCP transport is not configured. Enable mcp/aws.json and run the "
                "AWS MCP Server, or inject invoke= for isolated testing."
            )
        cli_command = f"aws {service_command}"
        if self._config.region and "--region" not in cli_command:
            cli_command = f"{cli_command} --region {self._config.region}"
        result = self._invoke("call_aws", {"cli_command": cli_command})
        if not isinstance(result, dict):
            raise AwsMcpClientError(f"Unexpected MCP call_aws response type: {type(result)!r}")
        return result

    def list_mcp_tools(self) -> list[str]:
        if self._invoke is None:
            return sorted(self.READ_ONLY_TOOLS)
        result = self._invoke("tools/list", {})
        tools = result.get("tools") if isinstance(result, dict) else None
        if isinstance(tools, list):
            return [str(name) for name in tools]
        return sorted(self.READ_ONLY_TOOLS)
