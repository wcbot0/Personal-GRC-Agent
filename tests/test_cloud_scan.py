"""Cloud scan pipeline tests — fixture responses, no live cloud."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from connectors.interfaces.cloud import CloudCapabilities, CloudConnector
from spa.audit.logger import AuditLogger
from spa.cloud_scan import run_cloud_scan
from spa.governance.approval_queue import ApprovalQueue
from spa.memory.redaction import redact_obj
from spa.tools.guard import ToolGuard


class MockCloudProvider(CloudConnector):
    def __init__(
        self,
        findings_by_check: dict[str, list[dict[str, Any]]] | None = None,
        *,
        provider: str = "gcp",
        capabilities: list[str] | None = None,
    ) -> None:
        super().__init__(
            provider=provider,
            enabled=True,
            capabilities=CloudCapabilities(read=True, collect=True),
        )
        self._findings_by_check = findings_by_check or {}
        self._capabilities = capabilities or sorted(self._findings_by_check.keys())

    def collect(self, check: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return redact_obj(list(self._findings_by_check.get(check, [])))

    def list_capabilities(self) -> list[str]:
        return list(self._capabilities)


def _read_audit_events(audit_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(audit_dir.glob("audit-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


@pytest.fixture
def guard_setup(tmp_path: Path, monkeypatch):
    audit_dir = tmp_path / "audit"
    queue_dir = tmp_path / "approval-queue"
    proposals_dir = tmp_path / "proposals" / "tickets"
    proposals_dir.mkdir(parents=True)
    findings_dir = tmp_path / "findings"
    evidence_root = tmp_path / "brain" / "evidence"
    evidence_root.mkdir(parents=True)

    audit = AuditLogger(log_dir=audit_dir)
    queue = ApprovalQueue(queue_dir=queue_dir, audit=audit)
    guard = ToolGuard(queue=queue, audit=audit)

    monkeypatch.setattr("spa.cloud_scan.get_data_dir", lambda: tmp_path)
    proposals_root = tmp_path / "proposals"
    monkeypatch.setattr("spa.cloud_scan.get_proposals_dir", lambda: proposals_root)
    monkeypatch.setattr("spa.paths.get_proposals_dir", lambda: proposals_root)
    monkeypatch.setattr("connectors.tickets.none.provider.get_proposals_dir", lambda: proposals_root)
    monkeypatch.setattr("spa.cloud_scan.BRAIN_DIR", tmp_path / "brain")
    none_mod = __import__("connectors.tickets.none.provider", fromlist=["NoneTicketProvider"])
    monkeypatch.setattr(
        "connectors.registry.get_ticket_provider",
        lambda guard=None, require_live_writes=True: none_mod.NoneTicketProvider(guard=guard),
    )

    return guard, audit_dir, findings_dir, evidence_root


def test_cloud_scan_gcp_fixtures_produces_findings_proposals_and_evidence(
    monkeypatch, guard_setup, tmp_path: Path
):
    guard, audit_dir, findings_dir, evidence_root = guard_setup
    monkeypatch.setenv("CLOUD_PROVIDER", "gcp")

    mock_provider = MockCloudProvider(
        {
            "iam_mfa_enforced": [{"check": "iam_mfa_enforced", "status": "collected", "detail": "ok"}],
            "service_account_key_inventory": [],
            "super_admin_inventory": [],
            "cloud_storage_public_access": [],
            "firewall_open_ingress": [],
            "cloud_storage_encryption_default": [{"check": "cloud_storage_encryption_default", "status": "collected"}],
            "compute_disk_encryption_default": [],
            "security_command_center_detectors": [],
            "security_command_center_enabled": [],
            "asset_inventory_enabled": [],
            "cloud_audit_logging_enabled": [],
            "log_sink_configured": [],
        },
        provider="gcp",
        capabilities=[
            "iam_mfa_enforced",
            "service_account_key_inventory",
            "super_admin_inventory",
            "cloud_storage_public_access",
            "firewall_open_ingress",
            "cloud_storage_encryption_default",
            "compute_disk_encryption_default",
            "security_command_center_detectors",
            "security_command_center_enabled",
            "asset_inventory_enabled",
            "cloud_audit_logging_enabled",
            "log_sink_configured",
        ],
    )
    monkeypatch.setattr("spa.cloud_scan.get_cloud_provider", lambda guard=None: mock_provider)

    result = run_cloud_scan(provider="gcp", period="2026-Q2", guard=guard, output_dir=findings_dir)

    assert result["provider"] == "gcp"
    assert result["period"] == "2026-Q2"
    assert result["summary"]["total_checks"] == 12
    assert result["summary"]["pass"] >= 1
    assert result["summary"]["gaps"] >= 1
    assert len(result["ticket_proposals"]) == result["summary"]["gaps"] + result["summary"]["errors"]

    findings_files = list(findings_dir.glob("gcp-*.json"))
    assert len(findings_files) == 1
    saved = json.loads(findings_files[0].read_text(encoding="utf-8"))
    assert any(any(tag.startswith("SOC2:") for tag in f["control_tags"]) for f in saved["findings"])

    ticket_files = list((tmp_path / "proposals" / "tickets").glob("ticket-proposal-AI-PROPOSED-CLOUD-*.json"))
    assert len(ticket_files) == len(result["ticket_proposals"])

    index_path = evidence_root / "CC6-1" / "index-2026-Q2.md"
    assert index_path.exists()
    index_text = index_path.read_text(encoding="utf-8")
    assert "Cloud scan" in index_text
    assert "iam_mfa_enforced" in index_text

    events = _read_audit_events(audit_dir)
    assert any(e["event_type"] == "cloud_scan_complete" for e in events)
    assert any(e["event_type"] == "cloud_collect" for e in events) is False  # mock bypasses provider audit


def test_cloud_scan_write_disabled_provider_none_zero_network(monkeypatch, guard_setup):
    guard, audit_dir, findings_dir, _ = guard_setup
    monkeypatch.setenv("CLOUD_PROVIDER", "none")

    result = run_cloud_scan(provider="gcp", period="2026-Q2", guard=guard, output_dir=findings_dir)

    assert result["cloud_status"] == "manual-evidence-only"
    assert result["summary"]["unimplemented"] == result["summary"]["total_checks"]
    assert result["ticket_proposals"] == []
    assert list(findings_dir.glob("gcp-*.json"))

    events = _read_audit_events(audit_dir)
    assert any(e["event_type"] == "cloud_scan_complete" for e in events)
