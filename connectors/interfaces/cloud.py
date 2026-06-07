"""Cloud evidence connector interface contract (provider-agnostic)."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

_PARAM_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# "=" is allowed for cloud filter expressions, e.g. name:securitycenter.googleapis.com.
_PARAM_VALUE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@+=,-]{0,255}$")
_UNRESOLVED_PARAM_RE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")


class CloudConfigError(RuntimeError):
    """Provider configuration exists but is invalid or incomplete."""


def apply_command_params(command: str, params: dict[str, Any]) -> str:
    """Safely replace allowlisted placeholders in read-only cloud commands."""
    for key, value in params.items():
        placeholder = f"{{{key}}}"
        text_value = str(value)
        if not _PARAM_NAME_RE.fullmatch(key):
            raise ValueError(f"Invalid cloud check parameter name: {key}")
        if placeholder not in command:
            raise ValueError(f"Unsupported cloud check parameter: {key}")
        if not _PARAM_VALUE_RE.fullmatch(text_value):
            raise ValueError(f"Unsafe cloud check parameter value for: {key}")
        command = command.replace(placeholder, text_value)

    if _UNRESOLVED_PARAM_RE.search(command):
        raise ValueError("Missing required cloud check parameter")
    return command


@dataclass
class CloudCapabilities:
    read: bool = False
    collect: bool = False


@dataclass
class CloudConnector(ABC):
    provider: str
    enabled: bool = False
    capabilities: CloudCapabilities = field(default_factory=CloudCapabilities)

    @abstractmethod
    def collect(self, check: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Collect read-only audit findings for a named check."""
        raise NotImplementedError

    @abstractmethod
    def list_capabilities(self) -> list[str]:
        """Return supported check names for this provider."""
        raise NotImplementedError

    def contract(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "enabled": self.enabled,
            "capabilities": self.capabilities.__dict__,
        }
