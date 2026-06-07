"""GCP cloud evidence provider — read-only via MCP run_gcloud transport."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from connectors.cloud.gcp.client import GcpMcpClient
from connectors.cloud.gcp.config import GcpCloudConfig, GcpCloudConfigError
from connectors.interfaces.cloud import CloudCapabilities, CloudConnector, apply_command_params
from spa.memory.redaction import redact_obj

if TYPE_CHECKING:
    from spa.tools.guard import ToolGuard

# Named checks mapped to read-only gcloud fragments (no mutating operations).
READ_ONLY_CHECKS: dict[str, str] = {
    "iam_mfa_enforced": "resource-manager org-policies list",
    "service_account_key_inventory": "iam service-accounts list",
    "super_admin_inventory": "projects get-iam-policy",
    "cloud_storage_public_access": "storage buckets list --format=json",
    "firewall_open_ingress": "compute firewall-rules list --format=json",
    "cloud_storage_encryption_default": "storage buckets list --format=json",
    "compute_disk_encryption_default": "compute disks list --format=json",
    "security_command_center_enabled": "services list --enabled --filter=name:securitycenter.googleapis.com",
    "asset_inventory_enabled": "services list --enabled --filter=name:cloudasset.googleapis.com",
    "cloud_audit_logging_enabled": "logging logs list",
    "log_sink_configured": "logging sinks list",
    "security_command_center_detectors": "scc sources list",
}

RELEVANT_FIELDS: dict[str, str] = {
    "cloud_storage_public_access": "iamConfiguration.publicAccessPrevention",
    "cloud_storage_encryption_default": "encryption.defaultKmsKeyName",
    "compute_disk_encryption_default": "diskEncryptionKey.kmsKeyName",
}


class GcpCloudProvider(CloudConnector):
    def __init__(
        self,
        guard: "ToolGuard | None" = None,
        *,
        config: GcpCloudConfig | None = None,
        client: GcpMcpClient | None = None,
    ) -> None:
        cfg = config or GcpCloudConfig.load()
        super().__init__(
            provider="gcp",
            enabled=cfg.mcp_enabled,
            capabilities=CloudCapabilities(read=True, collect=True),
        )
        self.guard = guard
        self._config = cfg
        self._client = client

    def _get_client(self) -> GcpMcpClient:
        if self._client is None:
            self._client = GcpMcpClient(self._config)
        return self._client

    def _emit_collect_audit(self, check: str, *, finding_count: int, status: str = "executed") -> None:
        if not self.guard:
            return
        self.guard.audit.emit(
            "cloud_collect",
            task_class="connector",
            risk_class="A0",
            tools_called=["run_gcloud"],
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
            raw = self._get_client().run_gcloud(command)
        except GcpCloudConfigError:
            raise
        except Exception as exc:  # noqa: BLE001
            self._emit_collect_audit(check, finding_count=0, status="error")
            raise RuntimeError(f"GCP MCP collect failed for check '{check}': {exc}") from exc

        findings = self._normalize_findings(check, raw)
        findings = redact_obj(findings)
        self._emit_collect_audit(check, finding_count=len(findings))
        return findings

    @staticmethod
    def _normalize_findings(check: str, raw: dict[str, Any]) -> list[dict[str, Any]]:
        payload = raw.get("output") if isinstance(raw.get("output"), (dict, list)) else raw
        if isinstance(payload, list):
            return [
                {
                    "check": check,
                    "severity": "info",
                    "status": "collected",
                    "resource": _resource_name(item),
                    "detail": item,
                    **_relevant_evidence(check, item),
                }
                for item in payload
                if isinstance(item, dict)
            ]

        if not isinstance(payload, dict):
            return [
                {
                    "check": check,
                    "severity": "info",
                    "status": "collected",
                    "detail": payload,
                }
            ]

        bindings = payload.get("bindings")
        if isinstance(bindings, list):
            return [
                {
                    "check": check,
                    "severity": "info",
                    "status": "collected",
                    "resource": item.get("role"),
                    "detail": item,
                }
                for item in bindings
                if isinstance(item, dict)
            ]

        items = payload.get("items") or payload.get("accounts") or payload.get("sinks")
        if isinstance(items, list):
            return [
                {
                    "check": check,
                    "severity": "info",
                    "status": "collected",
                    "resource": _resource_name(item),
                    "detail": item,
                    **_relevant_evidence(check, item),
                }
                for item in items
                if isinstance(item, dict)
            ]

        policies = payload.get("policies") or payload.get("sources") or payload.get("services")
        if isinstance(policies, list):
            return [
                {
                    "check": check,
                    "severity": "info",
                    "status": "collected",
                    "resource": _resource_name(item),
                    "detail": item,
                    **_relevant_evidence(check, item),
                }
                for item in policies
                if isinstance(item, dict)
            ]

        buckets = payload.get("buckets")
        if isinstance(buckets, list):
            return [
                {
                    "check": check,
                    "severity": "info",
                    "status": "collected",
                    "resource": item.get("name") or item.get("id"),
                    "detail": item,
                    **_relevant_evidence(check, item),
                }
                for item in buckets
                if isinstance(item, dict)
            ]

        rules = payload.get("firewallRules")
        if isinstance(rules, list) and check == "firewall_open_ingress":
            return [
                {
                    "check": check,
                    "severity": "info",
                    "status": "collected",
                    "resource": item.get("name") or item.get("id"),
                    "detail": item,
                    **_relevant_evidence(check, item),
                }
                for item in rules
                if isinstance(item, dict)
            ]

        return [
            {
                "check": check,
                "severity": "info",
                "status": "collected",
                "detail": payload,
            }
        ]


def _resource_name(item: dict[str, Any]) -> str | None:
    for key in ("name", "email", "displayName", "id"):
        if key in item:
            return str(item[key])
    config = item.get("config")
    if isinstance(config, dict) and config.get("name"):
        return str(config["name"])
    return None


def _relevant_evidence(check: str, item: dict[str, Any]) -> dict[str, Any]:
    field = RELEVANT_FIELDS.get(check)
    if not field:
        return {}
    return {
        "evidence_field": field,
        "evidence_value": _nested_value(item, field),
    }


def _nested_value(item: dict[str, Any], path: str) -> Any:
    current: Any = item
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current
