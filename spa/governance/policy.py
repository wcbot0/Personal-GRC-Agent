"""Load and enforce autonomy-policy.yaml action-risk gates."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from spa.paths import AUTONOMY_POLICY


class PolicyError(Exception):
    pass


class AutonomyPolicy:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.tool_mappings: dict[str, str] = data.get("tool_mappings", {})
        self.action_classes: dict[str, dict[str, Any]] = data.get("action_classes", {})

    @classmethod
    @lru_cache(maxsize=1)
    def load(cls) -> "AutonomyPolicy":
        if not AUTONOMY_POLICY.exists():
            raise PolicyError(f"Missing autonomy policy: {AUTONOMY_POLICY}")
        data = yaml.safe_load(AUTONOMY_POLICY.read_text())
        return cls(data)

    def classify_tool(self, tool_name: str) -> str:
        return self.tool_mappings.get(tool_name, "A1")

    def requires_approval(self, action_class: str) -> bool:
        cfg = self.action_classes.get(action_class, {})
        return cfg.get("approval") == "required"

    def is_blocked(self, action_class: str) -> bool:
        cfg = self.action_classes.get(action_class, {})
        return cfg.get("approval") == "blocked"

    def block_without_cpo(self, action_class: str) -> bool:
        cfg = self.action_classes.get(action_class, {})
        return bool(cfg.get("block_without_cpo"))

    def approval_mode(self, action_class: str) -> str:
        return self.action_classes.get(action_class, {}).get("approval", "none")
