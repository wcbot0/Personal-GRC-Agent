"""evidence-pack skill tests — mocked cloud connector, no live cloud."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from connectors.interfaces.cloud import CloudCapabilities, CloudConnector
from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import ApprovalQueue
from spa.memory.redaction import redact_obj
from spa.paths import SKILLS_DIR
from spa.skills.evidence_pack import run
from spa.skills.runner import run_skill
from spa.tools.guard import ToolGuard


class MockCloudProvider(CloudConnector):
    def __init__(self, findings_by_check: dict[str, list[dict[str, Any]]] | None = None) -> None:
        super().__init__(
            provider="aws",
            enabled=True,
            capabilities=CloudCapabilities(read=True, collect=True),
        )
        self._findings_by_check = findings_by_check or {}

    def collect(self, check: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return redact_obj(list(self._findings_by_check.get(check, [])))

    def list_capabilities(self) -> list[str]:
        return sorted(self._findings_by_check.keys())


def _read_audit_events(audit_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(audit_dir.glob("audit-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


def _validate_output_schema(output: dict[str, Any]) -> None:
    schema_path = SKILLS_DIR / "evidence-pack" / "output.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(output, schema)


@pytest.fixture
def guard_setup(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    queue_dir = tmp_path / "approval-queue"
    audit = AuditLogger(log_dir=audit_dir)
    queue = ApprovalQueue(queue_dir=queue_dir, audit=audit)
    guard = ToolGuard(queue=queue, audit=audit)
    return guard, audit_dir, tmp_path / "out"


def test_evidence_pack_none_provider_manual_only(monkeypatch, guard_setup):
    monkeypatch.setenv("CLOUD_PROVIDER", "none")
    guard, audit_dir, out_dir = guard_setup
    content = "Control: CC6.1\nPeriod: 2026-Q2\n"

    output = run(content, context={"output_dir": out_dir, "guard": guard})

    _validate_output_schema(output)
    assert output["provider"] == "none"
    assert output["checks"] == ["iam_account_summary", "iam_password_policy", "cloudtrail_trails"]
    assert output["findings"] == []

    index_path = out_dir / "brain" / "evidence" / "CC6-1" / Path(output["index_file"]).name
    index_text = index_path.read_text(encoding="utf-8")
    assert "manual-evidence-only" in index_text
    assert "no cloud provider configured" in index_text

    collect_events = [e for e in _read_audit_events(audit_dir) if e.get("event_type") == "evidence_pack_collect"]
    assert len(collect_events) == 1
    assert collect_events[0]["outputs"]["finding_count"] == 0


def test_evidence_pack_mocked_aws_includes_findings(monkeypatch, guard_setup):
    monkeypatch.setenv("CLOUD_PROVIDER", "aws")
    guard, _, out_dir = guard_setup
    account_id = "123456789012"
    mock_provider = MockCloudProvider(
        {
            "iam_account_summary": [
                {"check": "iam_account_summary", "metric": "Users", "value": 5, "status": "collected"},
            ],
            "iam_password_policy": [],
            "cloudtrail_trails": [
                {
                    "check": "cloudtrail_trails",
                    "status": "collected",
                    "resource": f"arn:aws:cloudtrail:us-east-1:{account_id}:trail/org-trail",
                },
            ],
        }
    )

    def _mock_get_cloud_provider(guard=None):  # noqa: ARG001
        return mock_provider

    monkeypatch.setattr("spa.skills.evidence_pack.get_cloud_provider", _mock_get_cloud_provider)

    content = "Control: CC6.1\nPeriod: 2026-Q2\nProvider: aws\n"
    output = run(content, context={"output_dir": out_dir, "guard": guard})

    _validate_output_schema(output)
    assert output["provider"] == "aws"
    assert len(output["findings"]) >= 1
    assert any(tag.startswith("SOC2:") for tag in output["control_tags"])

    serialized = json.dumps(output["findings"])
    assert account_id not in serialized
    assert "arn:aws:cloudtrail" not in serialized

    findings_files = list((out_dir / "brain" / "evidence" / "CC6-1").glob("findings-*.json"))
    assert findings_files
    persisted = findings_files[0].read_text(encoding="utf-8")
    assert account_id not in persisted
    assert "arn:aws:cloudtrail" not in persisted


def test_evidence_pack_unmapped_control_manual_only(monkeypatch, guard_setup):
    monkeypatch.setenv("CLOUD_PROVIDER", "none")
    guard, _, out_dir = guard_setup
    content = "Control: CC9.9\nPeriod: 2026-Q2\n"

    output = run(content, context={"output_dir": out_dir, "guard": guard})

    _validate_output_schema(output)
    assert output["checks"] == []
    assert output["findings"] == []

    index_path = out_dir / "brain" / "evidence" / "CC9-9" / Path(output["index_file"]).name
    index_text = index_path.read_text(encoding="utf-8")
    assert "manual-evidence-only" in index_text
    assert "no cloud checks mapped" in index_text


def test_evidence_pack_emits_audit_event_via_runner(monkeypatch, tmp_path):
    monkeypatch.setenv("CLOUD_PROVIDER", "none")
    audit_dir = tmp_path / "audit"
    out_dir = tmp_path / "out"
    input_file = tmp_path / "input.md"
    input_file.write_text("Control: CC6.1\nPeriod: 2026-Q2\n", encoding="utf-8")

    run_skill(
        "evidence-pack",
        input_file,
        output_dir=out_dir,
        audit=AuditLogger(log_dir=audit_dir),
    )

    events = _read_audit_events(audit_dir)
    event_types = {e.get("event_type") for e in events}
    assert "evidence_pack_collect" in event_types
    assert "skill_complete" in event_types


def test_evidence_pack_persisted_findings_redacted(monkeypatch, guard_setup):
    monkeypatch.setenv("CLOUD_PROVIDER", "aws")
    guard, _, out_dir = guard_setup
    sensitive_arn = "arn:aws:cloudtrail:us-east-1:123456789012:trail/secret-trail"
    mock_provider = MockCloudProvider(
        {
            "cloudtrail_trails": [
                {
                    "check": "cloudtrail_trails",
                    "status": "collected",
                    "resource": sensitive_arn,
                    "detail": {"OwnerId": "123456789012", "SourceIp": "10.0.0.1"},
                },
            ],
        }
    )
    monkeypatch.setattr("spa.skills.evidence_pack.get_cloud_provider", lambda guard=None: mock_provider)

    content = "Control: CC7.2\nPeriod: 2026-Q2\nProvider: aws\n"
    run(content, context={"output_dir": out_dir, "guard": guard})

    findings_files = list((out_dir / "brain" / "evidence" / "CC7-2").glob("findings-*.json"))
    assert findings_files
    text = findings_files[0].read_text(encoding="utf-8")
    assert "123456789012" not in text
    assert "arn:aws:cloudtrail" not in text
    assert "10.0.0.1" not in text
