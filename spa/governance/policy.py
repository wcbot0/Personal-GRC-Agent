"""Load and enforce autonomy-policy.yaml action-risk gates."""
from __future__ import annotations

from typing import Any

import yaml

from spa.paths import AUTONOMY_POLICY


class PolicyError(Exception):
    pass


_UNKNOWN_CLASS_CONFIG: dict[str, Any] = {"approval": "blocked", "block_without_cpo": True}


class AutonomyPolicy:
    _cached_mtime: float | None = None
    _cached_policy: AutonomyPolicy | None = None

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.defaults: dict[str, Any] = data.get("defaults", {})
        self.tool_mappings: dict[str, str] = data.get("tool_mappings", {})
        self.action_classes: dict[str, dict[str, Any]] = data.get("action_classes", {})
        self.connectors: dict[str, Any] = data.get("connectors", {})
        self._validate_references()

    @classmethod
    def load(cls) -> AutonomyPolicy:
        if not AUTONOMY_POLICY.exists():
            raise PolicyError(f"Missing autonomy policy: {AUTONOMY_POLICY}")
        mtime = AUTONOMY_POLICY.stat().st_mtime
        if cls._cached_policy is not None and cls._cached_mtime == mtime:
            return cls._cached_policy
        data = yaml.safe_load(AUTONOMY_POLICY.read_text())
        policy = cls(data)
        cls._cached_policy = policy
        cls._cached_mtime = mtime
        return policy

    @classmethod
    def clear_cache(cls) -> None:
        cls._cached_policy = None
        cls._cached_mtime = None

    @staticmethod
    def _normalize_action_class(action_class: str) -> str:
        return action_class.strip().upper()

    def _class_config(self, action_class: str) -> dict[str, Any]:
        normalized = self._normalize_action_class(action_class)
        if normalized in self.action_classes:
            return self.action_classes[normalized]
        return _UNKNOWN_CLASS_CONFIG

    def _validate_references(self) -> None:
        known = set(self.action_classes.keys())
        unknown = self._normalize_action_class(str(self.defaults.get("unknown_tool_class", "A5")))
        if unknown not in known:
            raise PolicyError(f"unknown_tool_class {unknown!r} not defined in action_classes")
        if not self.is_blocked(unknown):
            raise PolicyError(f"unknown_tool_class {unknown!r} must have approval: blocked")
        for tool, action_class in self.tool_mappings.items():
            normalized = self._normalize_action_class(str(action_class))
            if normalized not in known:
                raise PolicyError(
                    f"tool_mappings[{tool!r}] references undefined class {action_class!r}"
                )

    @property
    def version(self) -> str:
        return str(self.data.get("version", "0.0"))

    def classify_tool(self, tool_name: str) -> str:
        if tool_name in self.tool_mappings:
            return self._normalize_action_class(self.tool_mappings[tool_name])
        return self._normalize_action_class(str(self.defaults.get("unknown_tool_class", "A5")))

    def requires_approval(self, action_class: str) -> bool:
        normalized = self._normalize_action_class(action_class)
        if normalized not in self.action_classes:
            return True
        return self.action_classes[normalized].get("approval") == "required"

    def is_blocked(self, action_class: str) -> bool:
        normalized = self._normalize_action_class(action_class)
        if normalized not in self.action_classes:
            return True
        return self.action_classes[normalized].get("approval") == "blocked"

    def block_without_cpo(self, action_class: str) -> bool:
        normalized = self._normalize_action_class(action_class)
        if normalized not in self.action_classes:
            return True
        return bool(self.action_classes[normalized].get("block_without_cpo"))

    def approval_mode(self, action_class: str) -> str:
        return self._class_config(action_class).get("approval", "blocked")

    def live_writes_enabled(self, connector_type: str) -> bool:
        cfg = self.connectors.get(connector_type, {})
        return bool(cfg.get("live_write_enabled", False))
