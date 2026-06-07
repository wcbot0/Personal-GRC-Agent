"""GCP cloud connector configuration (MCP + auth from env)."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from connectors.interfaces.cloud import CloudConfigError
from spa.paths import ROOT


class GcpCloudConfigError(CloudConfigError):
    pass


_PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_ORGANIZATION_ID_RE = re.compile(r"^[0-9]{1,20}$")
_SERVICE_ACCOUNT_EMAIL_RE = re.compile(
    r"^[a-z][a-z0-9-]{4,28}[a-z0-9]@[a-z][a-z0-9-]{4,28}[a-z0-9]\.iam\.gserviceaccount\.com$"
)


@dataclass(frozen=True)
class GcpCloudConfig:
    project_id: str | None
    credentials_path: str | None
    organization_id: str | None
    region: str
    mcp_enabled: bool
    service_account_email: str | None = None

    @classmethod
    def load(cls, *, mcp_path: Path | None = None) -> GcpCloudConfig:
        path = mcp_path or (ROOT / "mcp" / "gcp.json")
        mcp_enabled = False
        region = os.getenv("GCP_REGION", os.getenv("GOOGLE_CLOUD_REGION", "us-central1")).strip()

        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            mcp_enabled = bool(data.get("enabled", False))
            env_cfg = data.get("env") or {}
            read_only = str(env_cfg.get("READ_OPERATIONS_ONLY", "true")).strip().lower()
            if read_only != "true":
                raise GcpCloudConfigError("GCP MCP config must keep READ_OPERATIONS_ONLY=true")
            args = data.get("args") or []
            for idx, arg in enumerate(args):
                if arg == "--region" and idx + 1 < len(args):
                    region = str(args[idx + 1])
                    break

        project_id = os.getenv("GCP_PROJECT", os.getenv("GOOGLE_CLOUD_PROJECT", "")).strip() or None
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip() or None
        organization_id = os.getenv("GCP_ORGANIZATION_ID", "").strip() or None
        service_account_email = os.getenv("GCP_SERVICE_ACCOUNT_EMAIL", "").strip() or None
        return cls(
            project_id=project_id,
            credentials_path=credentials_path,
            organization_id=organization_id,
            service_account_email=service_account_email,
            region=region,
            mcp_enabled=mcp_enabled,
        )

    def require_auth(self) -> None:
        if not self.project_id:
            raise GcpCloudConfigError(
                "Missing GCP config: set GCP_PROJECT (or GOOGLE_CLOUD_PROJECT) in the environment"
            )
        if not _PROJECT_ID_RE.fullmatch(self.project_id) or "--" in self.project_id:
            raise GcpCloudConfigError("Invalid GCP project id: set GCP_PROJECT to a canonical project id")
        if self.organization_id and not _ORGANIZATION_ID_RE.fullmatch(self.organization_id):
            raise GcpCloudConfigError("Invalid GCP organization id: set GCP_ORGANIZATION_ID to digits only")
        if (
            self.service_account_email
            and (not _SERVICE_ACCOUNT_EMAIL_RE.fullmatch(self.service_account_email) or "--" in self.service_account_email)
        ):
            raise GcpCloudConfigError(
                "Invalid GCP service account email: set GCP_SERVICE_ACCOUNT_EMAIL to a gserviceaccount.com address"
            )
        if not self.credentials_path and not self.service_account_email:
            raise GcpCloudConfigError(
                "Missing GCP auth config: set GOOGLE_APPLICATION_CREDENTIALS or GCP_SERVICE_ACCOUNT_EMAIL"
            )

    def require_mcp_enabled(self) -> None:
        if not self.mcp_enabled:
            raise GcpCloudConfigError(
                "GCP MCP config is disabled. Rename mcp/gcp.json.disabled to mcp/gcp.json "
                "and set enabled=true before collecting cloud evidence."
            )
