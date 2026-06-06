"""Connector interface contract tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from connectors.grc.drata.provider import DrataGrcProvider
from connectors.grc.none.provider import NoneGrcProvider
from connectors.grc.secureframe.provider import SecureframeGrcProvider
from connectors.grc.vanta.provider import VantaGrcProvider
from connectors.registry import (
    POST_MVP_ENABLE_MSG,
    get_grc_provider,
    get_ticket_provider,
)
from connectors.tickets.jira.provider import JiraTicketProvider
from connectors.tickets.linear.provider import LinearTicketProvider
from connectors.tickets.none.provider import NoneTicketProvider

VENDOR_TICKET_STUBS = (LinearTicketProvider, JiraTicketProvider)
VENDOR_GRC_STUBS = (VantaGrcProvider, DrataGrcProvider, SecureframeGrcProvider)


@pytest.fixture
def isolated_proposals(tmp_path, monkeypatch):
    """Route proposal writes to a temp dir (no repo/workspace pollution)."""
    monkeypatch.setenv("SPA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TICKET_PROVIDER", "none")
    monkeypatch.setenv("GRC_PROVIDER", "none")
    return tmp_path


def test_none_ticket_provider_file_draft(isolated_proposals):
    provider = NoneTicketProvider()
    result = provider.create_draft({"id": "TEST-1", "title": "Test"})
    assert result["provider"] == "none"
    assert result["ticket"]["assignee"] == "unassigned"
    assert Path(result["path"]).exists()


def test_none_providers_full_draft_workflow(isolated_proposals):
    """MVP draft workflow is file-only when both providers are none."""
    ticket = get_ticket_provider().create_draft({"id": "WF-1", "title": "Workflow test"})
    assert ticket["provider"] == "none"
    assert Path(ticket["path"]).exists()

    grc = get_grc_provider().draft_evidence("CC-8.1", {"summary": "evidence draft"})
    assert grc["provider"] == "none"
    assert Path(grc["path"]).exists()


@pytest.mark.parametrize("cls", VENDOR_TICKET_STUBS)
def test_vendor_ticket_stub_declares_disabled(cls):
    provider = cls()
    contract = provider.contract()
    assert provider.enabled is False
    assert contract["enabled"] is False
    assert contract["capabilities"]["create_draft"] is False


@pytest.mark.parametrize("cls", VENDOR_GRC_STUBS)
def test_vendor_grc_stub_declares_disabled(cls):
    provider = cls()
    contract = provider.contract()
    assert provider.enabled is False
    assert contract["enabled"] is False
    assert contract["capabilities"]["write_evidence"] is False


@pytest.mark.parametrize("cls", VENDOR_TICKET_STUBS)
def test_vendor_ticket_stub_raises_on_use(cls):
    provider = cls()
    with pytest.raises(RuntimeError, match="disabled in MVP"):
        provider.create_draft({"id": "X", "title": "blocked"})
    with pytest.raises(RuntimeError, match="post-MVP"):
        provider.read_tickets()


@pytest.mark.parametrize("cls", VENDOR_GRC_STUBS)
def test_vendor_grc_stub_raises_on_use(cls):
    provider = cls()
    with pytest.raises(RuntimeError, match="disabled in MVP"):
        provider.draft_evidence("CC-1", {"note": "blocked"})
    with pytest.raises(RuntimeError, match="post-MVP"):
        provider.read_controls()


def test_registry_defaults_to_none(monkeypatch):
    monkeypatch.delenv("TICKET_PROVIDER", raising=False)
    monkeypatch.delenv("GRC_PROVIDER", raising=False)
    assert get_ticket_provider().__class__ is NoneTicketProvider
    assert get_grc_provider().__class__ is NoneGrcProvider


def test_vendor_stubs_not_selected_by_default(monkeypatch):
    """Vendor adapters stay inert unless env explicitly selects them."""
    monkeypatch.delenv("TICKET_PROVIDER", raising=False)
    monkeypatch.delenv("GRC_PROVIDER", raising=False)
    assert get_ticket_provider().enabled is True
    assert get_grc_provider().enabled is True
    assert get_ticket_provider().provider == "none"
    assert get_grc_provider().provider == "none"


def test_provider_swap_is_config_only(monkeypatch):
    monkeypatch.setenv("TICKET_PROVIDER", "linear")
    linear = get_ticket_provider()
    assert linear.provider == "linear"
    assert linear.enabled is False
    monkeypatch.setenv("TICKET_PROVIDER", "none")
    none = get_ticket_provider()
    assert none.__class__ is NoneTicketProvider


def test_linear_selected_is_no_op_with_post_mvp_message(monkeypatch):
    monkeypatch.setenv("TICKET_PROVIDER", "linear")
    provider = get_ticket_provider()
    assert provider.enabled is False
    with pytest.raises(RuntimeError, match="post-MVP") as exc:
        provider.create_draft({"id": "L-1", "title": "Should not write"})
    assert "TICKET_PROVIDER=none" in str(exc.value)
    assert POST_MVP_ENABLE_MSG.format(name="linear", env_var="TICKET_PROVIDER") in str(exc.value)
