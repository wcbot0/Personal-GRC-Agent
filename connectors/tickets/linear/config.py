"""Linear connector configuration (fixed team — no dynamic resolution)."""
from __future__ import annotations

import os
from dataclasses import dataclass


class LinearConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class LinearConfig:
    api_key: str
    team_id: str
    project_id: str | None = None

    @classmethod
    def from_env(cls) -> LinearConfig:
        api_key = os.getenv("LINEAR_API_KEY", "").strip()
        team_id = os.getenv("LINEAR_TEAM_ID", "").strip()
        project_id = os.getenv("LINEAR_PROJECT_ID", "").strip() or None
        missing = [name for name, val in [("LINEAR_API_KEY", api_key), ("LINEAR_TEAM_ID", team_id)] if not val]
        if missing:
            raise LinearConfigError(f"Missing required Linear config: {', '.join(missing)}")
        return cls(api_key=api_key, team_id=team_id, project_id=project_id)
