"""Connector registry — provider selection via environment/config."""
from __future__ import annotations

import os

from connectors.grc.drata.provider import DrataGrcProvider
from connectors.grc.none.provider import NoneGrcProvider
from connectors.grc.secureframe.provider import SecureframeGrcProvider
from connectors.grc.vanta.provider import VantaGrcProvider
from connectors.notes.filesystem.provider import FilesystemNotesProvider
from connectors.tickets.jira.provider import JiraTicketProvider
from connectors.tickets.linear.provider import LinearTicketProvider
from connectors.tickets.none.provider import NoneTicketProvider


def get_ticket_provider():
    name = os.getenv("TICKET_PROVIDER", "none").lower()
    providers = {
        "none": NoneTicketProvider,
        "linear": LinearTicketProvider,
        "jira": JiraTicketProvider,
    }
    cls = providers.get(name, NoneTicketProvider)
    return cls()


def get_grc_provider():
    name = os.getenv("GRC_PROVIDER", "none").lower()
    providers = {
        "none": NoneGrcProvider,
        "vanta": VantaGrcProvider,
        "drata": DrataGrcProvider,
        "secureframe": SecureframeGrcProvider,
    }
    cls = providers.get(name, NoneGrcProvider)
    return cls()


def get_notes_provider():
    return FilesystemNotesProvider()
