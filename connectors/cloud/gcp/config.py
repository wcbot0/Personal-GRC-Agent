"""GCP cloud connector configuration (MCP + auth from env)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from spa.paths import ROOT


class GcpCloudConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class GcpCloudConfig:
    project_id: str | None
    credentials_path: str | None
    organization_id: str | None
    region: str
    mcp_enabled: bool
    read_operations_only: bool = True

    @classmethod
    def load(cls, *, mcp_path: Path | None = None) -> GcpCloudConfig:
        path = mcp_path or (ROOT / "mcp" / "gcp.json")
        mcp_enabled = False
        read_operations_only = True
        region = os.getenv("GCP_REGION", os.getenv("GOOGLE_CLOUD_REGION", "us-central1")).strip()

        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            mcp_enabled = bool(data.get("enabled", False))
            env_cfg = data.get("env") or {}
            if env_cfg.get("READ_OPERATIONS_ONLY", "true").lower() == "true":
                read_operations_only = True
            args = data.get("args") or []
            for idx, arg in enumerate(args):
                if arg == "--region" and idx + 1 < len(args):
                    region = str(args[idx + 1])
                    break

        project_id = os.getenv("GCP_PROJECT", os.getenv("GOOGLE_CLOUD_PROJECT", "")).strip() or None
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip() or None
        organization_id = os.getenv("GCP_ORGANIZATION_ID", "").strip() or None
        return cls(
            project_id=project_id,
            credentials_path=credentials_path,
            organization_id=organization_id,
            region=region,
            mcp_enabled=mcp_enabled,
            read_operations_only=read_operations_only,
        )

    def require_auth(self) -> None:
        if not self.project_id:
            raise GcpCloudConfigError(
                "Missing GCP config: set GCP_PROJECT (or GOOGLE_CLOUD_PROJECT) in the environment"
            )
        if not self.credentials_path and not os.getenv("GCP_SERVICE_ACCOUNT_EMAIL", "").strip():
            raise GcpCloudConfigError(
                "Missing GCP auth config: set GOOGLE_APPLICATION_CREDENTIALS or GCP_SERVICE_ACCOUNT_EMAIL"
            )

    def require_mcp_enabled(self) -> None:
        if not self.mcp_enabled:
            raise GcpCloudConfigError(
                "GCP MCP config is disabled. Rename mcp/gcp.json.disabled to mcp/gcp.json "
                "and set enabled=true before collecting cloud evidence."
            )
