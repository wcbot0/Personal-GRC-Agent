"""Connector interface contract tests."""
from __future__ import annotations

import os

from connectors.grc.drata.provider import DrataGrcProvider
from connectors.grc.none.provider import NoneGrcProvider
from connectors.grc.vanta.provider import VantaGrcProvider
from connectors.registry import get_grc_provider, get_ticket_provider
from connectors.tickets.linear.provider import LinearTicketProvider
from connectors.tickets.none.provider import NoneTicketProvider


def test_none_ticket_provider_file_draft():
    provider = NoneTicketProvider()
    result = provider.create_draft({"id": "TEST-1", "title": "Test"})
    assert result["provider"] == "none"
    assert result["ticket"]["assignee"] == "unassigned"


def test_disabled_providers_not_enabled():
    for cls in (LinearTicketProvider, VantaGrcProvider, DrataGrcProvider):
        p = cls()
        assert p.enabled is False


def test_registry_defaults_to_none():
    os.environ["TICKET_PROVIDER"] = "none"
    os.environ["GRC_PROVIDER"] = "none"
    assert get_ticket_provider().provider == "none"
    assert get_grc_provider().provider == "none"


def test_provider_swap_is_config_only():
    os.environ["TICKET_PROVIDER"] = "linear"
    linear = get_ticket_provider()
    assert linear.provider == "linear"
    assert linear.enabled is False
    os.environ["TICKET_PROVIDER"] = "none"
    none = get_ticket_provider()
    assert none.__class__ is NoneTicketProvider
