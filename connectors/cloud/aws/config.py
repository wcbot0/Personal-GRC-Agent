"""AWS cloud connector configuration (MCP + auth from env)."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from connectors.interfaces.cloud import CloudConfigError
from spa.paths import ROOT


class AwsCloudConfigError(CloudConfigError):
    pass


_REGION_RE = re.compile(r"^[a-z]{2,6}(?:-[a-z]+)+-[0-9]+$")


@dataclass(frozen=True)
class AwsCloudConfig:
    profile: str | None
    role_arn: str | None
    region: str
    mcp_enabled: bool

    @classmethod
    def load(cls, *, mcp_path: Path | None = None) -> AwsCloudConfig:
        path = mcp_path or (ROOT / "mcp" / "aws.json")
        mcp_enabled = False
        region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")).strip()

        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            mcp_enabled = bool(data.get("enabled", False))
            env_cfg = data.get("env") or {}
            read_only = str(env_cfg.get("READ_OPERATIONS_ONLY", "true")).strip().lower()
            if read_only != "true":
                raise AwsCloudConfigError("AWS MCP config must keep READ_OPERATIONS_ONLY=true")
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
        )

    def require_auth(self) -> None:
        if not _REGION_RE.fullmatch(self.region):
            raise AwsCloudConfigError("Invalid AWS region: set AWS_REGION to a canonical region name")
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
