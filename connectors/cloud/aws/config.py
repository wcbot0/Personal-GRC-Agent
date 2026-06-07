"""AWS cloud connector configuration (MCP + auth from env)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from spa.paths import ROOT


class AwsCloudConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class AwsCloudConfig:
    profile: str | None
    role_arn: str | None
    region: str
    mcp_enabled: bool
    read_operations_only: bool = True

    @classmethod
    def load(cls, *, mcp_path: Path | None = None) -> AwsCloudConfig:
        path = mcp_path or (ROOT / "mcp" / "aws.json")
        mcp_enabled = False
        read_operations_only = True
        region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")).strip()

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

        profile = os.getenv("AWS_PROFILE", "").strip() or None
        role_arn = os.getenv("AWS_ROLE_ARN", "").strip() or None
        return cls(
            profile=profile,
            role_arn=role_arn,
            region=region,
            mcp_enabled=mcp_enabled,
            read_operations_only=read_operations_only,
        )

    def require_auth(self) -> None:
        if not self.profile and not self.role_arn:
            raise AwsCloudConfigError(
                "Missing AWS auth config: set AWS_PROFILE or AWS_ROLE_ARN in the environment"
            )

    def require_mcp_enabled(self) -> None:
        if not self.mcp_enabled:
            raise AwsCloudConfigError(
                "AWS MCP config is disabled. Rename mcp/aws.json.disabled to mcp/aws.json "
                "and set enabled=true before collecting cloud evidence."
            )
