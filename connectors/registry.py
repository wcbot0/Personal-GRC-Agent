"""Connector registry — provider selection via environment/config."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from connectors.cloud.aws.provider import AwsCloudProvider
from connectors.cloud.gcp.provider import GcpCloudProvider
from connectors.cloud.none.provider import NoneCloudProvider
from connectors.comms.none.provider import NoneCommsProvider
from connectors.comms.slack.provider import SlackCommsProvider
from connectors.grc.drata.provider import DrataGrcProvider
from connectors.grc.none.provider import NoneGrcProvider
from connectors.grc.secureframe.provider import SecureframeGrcProvider
from connectors.grc.vanta.provider import VantaGrcProvider
from connectors.messages import POST_MVP_ENABLE_MSG, disabled_post_mvp_message
from connectors.notes.filesystem.provider import FilesystemNotesProvider
from connectors.notes.granola.provider import GranolaNotesProvider
from connectors.tickets.jira.provider import JiraTicketProvider
from connectors.tickets.linear.provider import LinearTicketProvider
from connectors.tickets.none.provider import NoneTicketProvider
from spa.governance.policy import AutonomyPolicy

if TYPE_CHECKING:
    from spa.tools.guard import ToolGuard

__all__ = [
    "POST_MVP_ENABLE_MSG",
    "disabled_post_mvp_message",
    "get_cloud_provider",
    "get_comms_provider",
    "get_grc_provider",
    "get_notes_provider",
    "get_ticket_provider",
]

_SAFE_PROVIDERS: dict[str, tuple[str, ...]] = {
    "ticket": ("none",),
    "grc": ("none",),
    "notes": ("filesystem",),
    "comms": ("none",),
    "cloud": ("none",),
}


class LiveWriteDisabledError(RuntimeError):
    pass


def _ensure_live_writes(connector_type: str, provider_name: str) -> None:
    if provider_name in _SAFE_PROVIDERS.get(connector_type, ("none",)):
        return
    policy = AutonomyPolicy.load()
    if not policy.live_writes_enabled(connector_type):
        raise LiveWriteDisabledError(
            f"{connector_type.upper()} provider '{provider_name}' is disabled: "
            f"connectors.{connector_type}.live_write_enabled is false in autonomy-policy.yaml. "
            f"{POST_MVP_ENABLE_MSG}"
        )


def get_ticket_provider(guard: "ToolGuard | None" = None, *, require_live_writes: bool = True):
    name = os.getenv("TICKET_PROVIDER", "none").lower()
    if require_live_writes:
        _ensure_live_writes("ticket", name)
    providers = {
        "none": NoneTicketProvider,
        "linear": LinearTicketProvider,
        "jira": JiraTicketProvider,
    }
    cls = providers.get(name, NoneTicketProvider)
    return cls(guard=guard)


def get_grc_provider(guard: "ToolGuard | None" = None):
    name = os.getenv("GRC_PROVIDER", "none").lower()
    _ensure_live_writes("grc", name)
    providers = {
        "none": NoneGrcProvider,
        "vanta": VantaGrcProvider,
        "drata": DrataGrcProvider,
        "secureframe": SecureframeGrcProvider,
    }
    cls = providers.get(name, NoneGrcProvider)
    return cls(guard=guard)


def get_notes_provider():
    name = os.getenv("NOTES_PROVIDER", "filesystem").lower()
    _ensure_live_writes("notes", name)
    providers = {
        "filesystem": FilesystemNotesProvider,
        "granola": GranolaNotesProvider,
    }
    cls = providers.get(name, FilesystemNotesProvider)
    return cls()


def get_comms_provider():
    name = os.getenv("COMMS_PROVIDER", "none").lower()
    _ensure_live_writes("comms", name)
    providers = {
        "none": NoneCommsProvider,
        "slack": SlackCommsProvider,
    }
    cls = providers.get(name, NoneCommsProvider)
    return cls()


def get_cloud_provider(guard: "ToolGuard | None" = None):
    name = os.getenv("CLOUD_PROVIDER", "none").lower()
    _ensure_live_writes("cloud", name)
    providers = {
        "none": NoneCloudProvider,
        "aws": AwsCloudProvider,
        "gcp": GcpCloudProvider,
    }
    cls = providers.get(name, NoneCloudProvider)
    return cls(guard=guard)
