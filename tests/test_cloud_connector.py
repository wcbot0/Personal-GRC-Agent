"""Cloud evidence connector tests (mocked MCP/AWS — no real network)."""
from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from connectors.cloud.aws.client import AwsMcpClient
from connectors.cloud.aws.config import AwsCloudConfig, AwsCloudConfigError
from connectors.cloud.aws.provider import AwsCloudProvider
from connectors.cloud.gcp.provider import GcpCloudProvider
from connectors.cloud.none.provider import NoneCloudProvider
from connectors.interfaces.cloud import CloudCapabilities, CloudConnector
from connectors.registry import LiveWriteDisabledError, get_cloud_provider
from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import ApprovalQueue
from spa.governance.policy import AutonomyPolicy
from spa.memory.redaction import redact_obj
from spa.tools.guard import ToolGuard


def _read_audit_events(audit_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(audit_dir.glob("audit-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


def _policy_with_live_cloud_writes() -> AutonomyPolicy:
    policy = AutonomyPolicy.load()
    data = copy.deepcopy(policy.data)
    data["connectors"]["cloud"]["live_write_enabled"] = True
    return AutonomyPolicy(data)


@pytest.fixture
def guard_setup(tmp_path: Path):
    queue_dir = tmp_path / "approval-queue"
    audit_dir = tmp_path / "audit"
    audit = AuditLogger(log_dir=audit_dir)
    queue = ApprovalQueue(queue_dir=queue_dir, audit=audit)
    guard = ToolGuard(queue=queue, audit=audit)
    return guard, queue, audit_dir


@pytest.fixture
def live_cloud_policy(monkeypatch):
    AutonomyPolicy.clear_cache()
    policy = _policy_with_live_cloud_writes()
    monkeypatch.setattr("spa.governance.policy.AutonomyPolicy.load", lambda: policy)
    yield policy


@pytest.fixture
def enabled_aws_config() -> AwsCloudConfig:
    return AwsCloudConfig(
        profile="audit-readonly",
        role_arn=None,
        region="us-east-1",
        mcp_enabled=True,
        read_operations_only=True,
    )


def _trail_response(account_id: str = "123456789012") -> dict[str, Any]:
    return {
        "output": {
            "trailList": [
                {
                    "Name": "org-trail",
                    "TrailARN": f"arn:aws:cloudtrail:us-east-1:{account_id}:trail/org-trail",
                    "HomeRegion": "us-east-1",
                }
            ]
        }
    }


def test_none_cloud_provider_is_default_safe(monkeypatch):
    monkeypatch.delenv("CLOUD_PROVIDER", raising=False)
    provider = get_cloud_provider()
    assert provider.__class__ is NoneCloudProvider
    assert provider.enabled is True
    assert provider.provider == "none"


def test_none_cloud_provider_collect_raises_clear_message():
    provider = NoneCloudProvider()
    with pytest.raises(RuntimeError, match="No cloud provider configured"):
        provider.collect("iam_account_summary")


def test_none_cloud_provider_no_network():
    provider = NoneCloudProvider()
    assert provider.list_capabilities() == []


def test_aws_provider_blocked_by_registry_by_default(monkeypatch):
    monkeypatch.setenv("CLOUD_PROVIDER", "aws")
    with pytest.raises(LiveWriteDisabledError):
        get_cloud_provider()


def test_gcp_provider_blocked_by_registry_by_default(monkeypatch):
    monkeypatch.setenv("CLOUD_PROVIDER", "gcp")
    with pytest.raises(LiveWriteDisabledError):
        get_cloud_provider()


def test_gcp_provider_raises_deferred_message():
    provider = GcpCloudProvider()
    assert provider.enabled is False
    with pytest.raises(RuntimeError, match="deferred to H9"):
        provider.collect("any-check")
    with pytest.raises(RuntimeError, match="deferred to H9"):
        provider.list_capabilities()


def test_cloud_connector_exposes_no_write_or_mutate_methods():
    forbidden = ("write", "create", "mutate", "delete", "update", "assign", "publish")
    for name, member in inspect.getmembers(CloudConnector):
        if name.startswith("_"):
            continue
        lowered = name.lower()
        assert not any(token in lowered for token in forbidden), f"Unexpected method: {name}"

    caps = CloudCapabilities(read=True, collect=True)
    cap_keys = set(caps.__dict__.keys())
    assert cap_keys == {"read", "collect"}
    assert "write" not in cap_keys
    assert "create" not in cap_keys
    assert "mutate" not in cap_keys


def test_cloud_connector_contract_has_no_write_capabilities():
    provider = NoneCloudProvider()
    contract = provider.contract()
    assert set(contract["capabilities"].keys()) == {"read", "collect"}
    assert "gated_capabilities" not in contract


def test_missing_aws_auth_config_raises_clear_error(enabled_aws_config):
    cfg = AwsCloudConfig(
        profile=None,
        role_arn=None,
        region="us-east-1",
        mcp_enabled=True,
    )
    provider = AwsCloudProvider(config=cfg, client=AwsMcpClient(cfg, invoke=lambda *_: {}))
    with pytest.raises(AwsCloudConfigError, match="Missing AWS auth config"):
        provider.collect("iam_account_summary")


def test_aws_collect_emits_audit_event_and_redacts_findings(
    guard_setup,
    enabled_aws_config,
):
    guard, _, audit_dir = guard_setup
    account_id = "123456789012"

    def invoke(tool: str, params: dict[str, Any]) -> dict[str, Any]:
        assert tool == "call_aws"
        assert "cloudtrail describe-trails" in params["cli_command"]
        return _trail_response(account_id)

    client = AwsMcpClient(enabled_aws_config, invoke=invoke)
    provider = AwsCloudProvider(guard=guard, config=enabled_aws_config, client=client)
    findings = provider.collect("cloudtrail_trails")

    assert findings
    serialized = json.dumps(findings)
    assert account_id not in serialized
    assert "arn:aws:cloudtrail" not in serialized
    assert "[REDACTED" in serialized

    events = _read_audit_events(audit_dir)
    collect_events = [e for e in events if e.get("event_type") == "cloud_collect"]
    assert len(collect_events) == 1
    assert collect_events[0]["outputs"]["check"] == "cloudtrail_trails"
    assert collect_events[0]["outputs"]["finding_count"] == len(findings)
    assert account_id not in json.dumps(collect_events[0])


def test_redaction_runs_before_persistence_on_cloud_findings():
    raw = [
        {
            "check": "cloudtrail_trails",
            "resource": "arn:aws:cloudtrail:us-east-1:123456789012:trail/org-trail",
            "detail": {"OwnerId": "123456789012", "SourceIp": "10.0.0.1"},
        }
    ]
    redacted = redact_obj(raw)
    text = json.dumps(redacted)
    assert "123456789012" not in text
    assert "arn:aws:cloudtrail" not in text
    assert "10.0.0.1" not in text


def test_aws_collect_normalized_findings(guard_setup, enabled_aws_config):
    guard, _, _ = guard_setup

    def invoke(_tool: str, _params: dict[str, Any]) -> dict[str, Any]:
        return {
            "output": {
                "Summary": {
                    "Users": 12,
                    "Groups": 3,
                }
            }
        }

    client = AwsMcpClient(enabled_aws_config, invoke=invoke)
    provider = AwsCloudProvider(guard=guard, config=enabled_aws_config, client=client)
    findings = provider.collect("iam_account_summary")

    assert len(findings) == 2
    assert all(item["check"] == "iam_account_summary" for item in findings)
    assert {item["metric"] for item in findings} == {"Users", "Groups"}


def test_aws_provider_disabled_when_mcp_config_not_enabled(monkeypatch, live_cloud_policy):
    monkeypatch.setenv("CLOUD_PROVIDER", "aws")
    monkeypatch.setenv("AWS_PROFILE", "audit-readonly")
    provider = get_cloud_provider()
    assert provider.enabled is False
    with pytest.raises(AwsCloudConfigError, match="AWS MCP config is disabled"):
        provider.collect("iam_account_summary")


def test_aws_selected_with_live_policy_and_mock(
    monkeypatch,
    live_cloud_policy,
    guard_setup,
    enabled_aws_config,
):
    monkeypatch.setenv("CLOUD_PROVIDER", "aws")
    guard, _, audit_dir = guard_setup

    def invoke(_tool: str, _params: dict[str, Any]) -> dict[str, Any]:
        return _trail_response()

    client = AwsMcpClient(enabled_aws_config, invoke=invoke)
    provider = AwsCloudProvider(guard=guard, config=enabled_aws_config, client=client)
    findings = provider.collect("cloudtrail_trails")
    assert findings
    assert any(e.get("event_type") == "cloud_collect" for e in _read_audit_events(audit_dir))
