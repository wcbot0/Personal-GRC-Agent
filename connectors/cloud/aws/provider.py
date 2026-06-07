"""AWS cloud evidence provider — read-only via official AWS MCP Server."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from connectors.cloud.aws.client import AwsMcpClient
from connectors.cloud.aws.config import AwsCloudConfig, AwsCloudConfigError
from connectors.interfaces.cloud import CloudCapabilities, CloudConnector, apply_command_params
from spa.memory.redaction import redact_obj

if TYPE_CHECKING:
    from spa.tools.guard import ToolGuard

# Named checks mapped to read-only AWS CLI fragments (no mutating operations).
READ_ONLY_CHECKS: dict[str, str] = {
    "iam_account_summary": "iam get-account-summary",
    "iam_password_policy": "iam get-account-password-policy",
    "cloudtrail_trails": "cloudtrail describe-trails",
    "config_recorders": "configservice describe-configuration-recorders",
    "guardduty_detectors": "guardduty list-detectors",
}


class AwsCloudProvider(CloudConnector):
    def __init__(
        self,
        guard: "ToolGuard | None" = None,
        *,
        config: AwsCloudConfig | None = None,
        client: AwsMcpClient | None = None,
    ) -> None:
        cfg = config or AwsCloudConfig.load()
        super().__init__(
            provider="aws",
            enabled=cfg.mcp_enabled,
            capabilities=CloudCapabilities(read=True, collect=True),
        )
        self.guard = guard
        self._config = cfg
        self._client = client

    def _get_client(self) -> AwsMcpClient:
        if self._client is None:
            self._client = AwsMcpClient(self._config)
        return self._client

    def _emit_collect_audit(self, check: str, *, finding_count: int, status: str = "executed") -> None:
        if not self.guard:
            return
        self.guard.audit.emit(
            "cloud_collect",
            task_class="connector",
            risk_class="A0",
            tools_called=["call_aws"],
            outputs=redact_obj(
                {
                    "status": status,
                    "provider": self.provider,
                    "check": check,
                    "finding_count": finding_count,
                }
            ),
        )

    def list_capabilities(self) -> list[str]:
        return sorted(READ_ONLY_CHECKS.keys())

    def collect(self, check: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        self._config.require_mcp_enabled()
        self._config.require_auth()

        command = READ_ONLY_CHECKS.get(check)
        if not command:
            supported = ", ".join(sorted(READ_ONLY_CHECKS))
            raise ValueError(f"Unknown cloud check '{check}'. Supported checks: {supported}")

        command = apply_command_params(command, params or {})

        try:
            raw = self._get_client().call_aws(command)
        except AwsCloudConfigError:
            raise
        except Exception as exc:  # noqa: BLE001
            self._emit_collect_audit(check, finding_count=0, status="error")
            raise RuntimeError(f"AWS MCP collect failed for check '{check}': {exc}") from exc

        findings = self._normalize_findings(check, raw)
        findings = redact_obj(findings)
        self._emit_collect_audit(check, finding_count=len(findings))
        return findings

    @staticmethod
    def _normalize_findings(check: str, raw: dict[str, Any]) -> list[dict[str, Any]]:
        payload = raw.get("output") if isinstance(raw.get("output"), dict) else raw
        if not isinstance(payload, dict):
            return [
                {
                    "check": check,
                    "severity": "info",
                    "status": "collected",
                    "detail": payload,
                }
            ]

        summary = payload.get("Summary") or payload.get("summary")
        if isinstance(summary, dict):
            return [
                {
                    "check": check,
                    "severity": "info",
                    "status": "collected",
                    "metric": key,
                    "value": value,
                }
                for key, value in summary.items()
            ]

        trails = payload.get("trailList") or payload.get("Trails")
        if isinstance(trails, list):
            return [
                {
                    "check": check,
                    "severity": "info",
                    "status": "collected",
                    "resource": item.get("TrailARN") or item.get("Arn") or item.get("Name"),
                    "detail": item,
                }
                for item in trails
                if isinstance(item, dict)
            ]

        detectors = payload.get("DetectorIds")
        if isinstance(detectors, list):
            return [
                {
                    "check": check,
                    "severity": "info",
                    "status": "collected",
                    "resource": detector_id,
                }
                for detector_id in detectors
            ]

        recorders = payload.get("ConfigurationRecorders")
        if isinstance(recorders, list):
            return [
                {
                    "check": check,
                    "severity": "info",
                    "status": "collected",
                    "resource": item.get("arn") or item.get("name"),
                    "detail": item,
                }
                for item in recorders
                if isinstance(item, dict)
            ]

        policy = payload.get("PasswordPolicy")
        if isinstance(policy, dict):
            return [
                {
                    "check": check,
                    "severity": "info",
                    "status": "collected",
                    "detail": policy,
                }
            ]

        return [
            {
                "check": check,
                "severity": "info",
                "status": "collected",
                "detail": payload,
            }
        ]


