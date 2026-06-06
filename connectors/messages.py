"""Shared connector messages (avoids registry ↔ provider import cycles)."""
from __future__ import annotations

POST_MVP_ENABLE_MSG = (
    "Provider '{name}' is selected but disabled in MVP. "
    "Set {env_var}=none for file-only mode, or select and enable the live adapter post-MVP."
)


def disabled_post_mvp_message(provider_name: str, env_var: str) -> str:
    return POST_MVP_ENABLE_MSG.format(name=provider_name, env_var=env_var)
