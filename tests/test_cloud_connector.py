"""Cloud evidence connector tests (mocked MCP/AWS/GCP — no real network)."""
from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from connectors.cloud.aws.client import AwsMcpClient
from connectors.cloud.aws.config import AwsCloudConfig, AwsCloudConfigError
from connectors.cloud.aws.provider import AwsCloudProvider
from connectors.cloud.gcp.client import GcpMcpClient
from connectors.cloud.gcp.config import GcpCloudConfig, GcpCloudConfigError
from connectors.cloud.gcp.provider import READ_ONLY_CHECKS, GcpCloudProvider
from connectors.cloud.none.provider import NoneCloudProvider
from connectors.interfaces.cloud import CloudCapabilities, CloudConnector, apply_command_params
from connectors.registry import LiveWriteDisabledError, get_cloud_provider
from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import ApprovalQueue
from spa.governance.policy import AutonomyPolicy
from spa.memory.redaction import redact_obj
from spa.paths import ROOT
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


def test_gcp_provider_disabled_by_default():
    provider = GcpCloudProvider()
    assert provider.enabled is False
    assert provider.provider == "gcp"
    assert provider.capabilities.read is True
    assert provider.capabilities.collect is True


@pytest.fixture
def enabled_gcp_config() -> GcpCloudConfig:
    return GcpCloudConfig(
        project_id="audit-project",
        credentials_path="/fake/creds.json",
        organization_id=None,
        region="us-central1",
        mcp_enabled=True,
    )


def _gcp_sink_response(project_number: str = "123456789012") -> dict[str, Any]:
    return {
        "output": {
            "sinks": [
                {
                    "name": "audit-logs-sink",
                    "destination": f"storage.googleapis.com/audit-bucket-{project_number}",
                    "filter": "logName:cloudaudit",
                }
            ]
        }
    }


def test_missing_gcp_auth_config_raises_clear_error(enabled_gcp_config):
    cfg = GcpCloudConfig(
        project_id=None,
        credentials_path=None,
        organization_id=None,
        region="us-central1",
        mcp_enabled=True,
    )
    provider = GcpCloudProvider(config=cfg, client=GcpMcpClient(cfg, invoke=lambda *_: {}))
    with pytest.raises(GcpCloudConfigError, match="Missing GCP config"):
        provider.collect("log_sink_configured")


def test_gcp_collect_emits_audit_event_and_redacts_findings(
    guard_setup,
    enabled_gcp_config,
):
    guard, _, audit_dir = guard_setup
    project_number = "123456789012"

    def invoke(tool: str, params: dict[str, Any]) -> dict[str, Any]:
        assert tool == "run_gcloud"
        assert "logging sinks list" in params["cli_command"]
        return _gcp_sink_response(project_number)

    client = GcpMcpClient(enabled_gcp_config, invoke=invoke)
    provider = GcpCloudProvider(guard=guard, config=enabled_gcp_config, client=client)
    findings = provider.collect("log_sink_configured")

    assert findings
    serialized = json.dumps(findings)
    assert project_number not in serialized
    assert "[REDACTED" in serialized

    events = _read_audit_events(audit_dir)
    collect_events = [e for e in events if e.get("event_type") == "cloud_collect"]
    assert len(collect_events) == 1
    assert collect_events[0]["outputs"]["check"] == "log_sink_configured"
    assert collect_events[0]["outputs"]["finding_count"] == len(findings)
    assert project_number not in json.dumps(collect_events[0])


def test_gcp_collect_normalized_findings(guard_setup, enabled_gcp_config):
    guard, _, _ = guard_setup

    def invoke(_tool: str, _params: dict[str, Any]) -> dict[str, Any]:
        return {
            "output": {
                "bindings": [
                    {"role": "roles/owner", "members": ["user:admin@example.com"]},
                    {"role": "roles/viewer", "members": ["serviceAccount:audit@audit-project.iam.gserviceaccount.com"]},
                ]
            }
        }

    client = GcpMcpClient(enabled_gcp_config, invoke=invoke)
    provider = GcpCloudProvider(guard=guard, config=enabled_gcp_config, client=client)
    findings = provider.collect("super_admin_inventory")

    assert len(findings) == 2
    assert all(item["check"] == "super_admin_inventory" for item in findings)
    assert {item["resource"] for item in findings} == {"roles/owner", "roles/viewer"}


@pytest.mark.parametrize(
    "project_id",
    [
        "audit-project;rm",
        "audit--project",
        "abcde",
        "1audit-project",
        "audit-project-12345678901234567",
    ],
)
def test_gcp_rejects_unsafe_project_id_before_mcp_call(enabled_gcp_config, project_id):
    cfg = GcpCloudConfig(
        project_id=project_id,
        credentials_path=enabled_gcp_config.credentials_path,
        organization_id=None,
        region=enabled_gcp_config.region,
        mcp_enabled=True,
    )

    def invoke(_tool: str, _params: dict[str, Any]) -> dict[str, Any]:
        pytest.fail("unsafe config should be rejected before MCP invocation")

    provider = GcpCloudProvider(config=cfg, client=GcpMcpClient(cfg, invoke=invoke))
    with pytest.raises(GcpCloudConfigError, match="Invalid GCP project id"):
        provider.collect("log_sink_configured")


def test_gcp_rejects_unsafe_organization_id_before_mcp_call(enabled_gcp_config):
    cfg = GcpCloudConfig(
        project_id=enabled_gcp_config.project_id,
        credentials_path=enabled_gcp_config.credentials_path,
        organization_id="12345 --format=json",
        region=enabled_gcp_config.region,
        mcp_enabled=True,
    )

    def invoke(_tool: str, _params: dict[str, Any]) -> dict[str, Any]:
        pytest.fail("unsafe config should be rejected before MCP invocation")

    provider = GcpCloudProvider(config=cfg, client=GcpMcpClient(cfg, invoke=invoke))
    with pytest.raises(GcpCloudConfigError, match="Invalid GCP organization id"):
        provider.collect("security_command_center_detectors")


def test_gcp_accepts_valid_organization_id(enabled_gcp_config):
    cfg = GcpCloudConfig(
        project_id=enabled_gcp_config.project_id,
        credentials_path=enabled_gcp_config.credentials_path,
        organization_id="123456789012",
        region=enabled_gcp_config.region,
        mcp_enabled=True,
    )

    def invoke(_tool: str, params: dict[str, Any]) -> dict[str, Any]:
        assert "--organization 123456789012" in params["cli_command"]
        return {"output": {"sources": [{"name": "scc-source"}]}}

    provider = GcpCloudProvider(config=cfg, client=GcpMcpClient(cfg, invoke=invoke))
    assert provider.collect("security_command_center_detectors")[0]["resource"] == "scc-source"


def test_gcp_rejects_unsafe_service_account_email_before_mcp_call():
    cfg = GcpCloudConfig(
        project_id="audit-project",
        credentials_path=None,
        organization_id=None,
        service_account_email="auditor@example.com;rm",
        region="us-central1",
        mcp_enabled=True,
    )

    def invoke(_tool: str, _params: dict[str, Any]) -> dict[str, Any]:
        pytest.fail("unsafe config should be rejected before MCP invocation")

    provider = GcpCloudProvider(config=cfg, client=GcpMcpClient(cfg, invoke=invoke))
    with pytest.raises(GcpCloudConfigError, match="Invalid GCP service account email"):
        provider.collect("log_sink_configured")


def test_gcp_accepts_valid_service_account_email_without_credentials():
    cfg = GcpCloudConfig(
        project_id="audit-project",
        credentials_path=None,
        organization_id=None,
        service_account_email="auditor@audit-project.iam.gserviceaccount.com",
        region="us-central1",
        mcp_enabled=True,
    )
    called = False

    def invoke(_tool: str, _params: dict[str, Any]) -> dict[str, Any]:
        nonlocal called
        called = True
        return {"output": {"sinks": []}}

    provider = GcpCloudProvider(config=cfg, client=GcpMcpClient(cfg, invoke=invoke))
    assert provider.collect("log_sink_configured") == []
    assert called


def test_gcp_rejects_uppercase_service_account_email_before_mcp_call():
    cfg = GcpCloudConfig(
        project_id="audit-project",
        credentials_path=None,
        organization_id=None,
        service_account_email="Auditor@audit-project.iam.gserviceaccount.com",
        region="us-central1",
        mcp_enabled=True,
    )

    def invoke(_tool: str, _params: dict[str, Any]) -> dict[str, Any]:
        pytest.fail("unsafe config should be rejected before MCP invocation")

    provider = GcpCloudProvider(config=cfg, client=GcpMcpClient(cfg, invoke=invoke))
    with pytest.raises(GcpCloudConfigError, match="Invalid GCP service account email"):
        provider.collect("log_sink_configured")


def test_gcp_collect_rejects_unsupported_params(enabled_gcp_config):
    provider = GcpCloudProvider(
        config=enabled_gcp_config,
        client=GcpMcpClient(enabled_gcp_config, invoke=lambda *_: {"output": {}}),
    )
    with pytest.raises(ValueError, match="Unsupported cloud check parameter"):
        provider.collect("log_sink_configured", params={"project": "audit-project"})


def test_aws_collect_rejects_unsupported_params(enabled_aws_config):
    provider = AwsCloudProvider(
        config=enabled_aws_config,
        client=AwsMcpClient(enabled_aws_config, invoke=lambda *_: {"output": {}}),
    )
    with pytest.raises(ValueError, match="Unsupported cloud check parameter"):
        provider.collect("cloudtrail_trails", params={"profile": "audit-readonly"})


@pytest.mark.parametrize("value", ["", "--format=json", "../creds.json", "{nested}", "a" * 257])
def test_cloud_command_params_reject_unsafe_values(value):
    with pytest.raises(ValueError, match="Unsafe cloud check parameter value"):
        apply_command_params("service list --filter={filter}", {"filter": value})


def test_cloud_command_params_reject_invalid_names():
    with pytest.raises(ValueError, match="Invalid cloud check parameter name"):
        apply_command_params("service list --filter={filter}", {"bad-name": "enabled"})


def test_cloud_command_params_accept_256_char_values():
    value = "a" * 256
    assert apply_command_params("service list --filter={filter}", {"filter": value}).endswith(value)


def test_cloud_command_params_allows_placeholder_free_commands_without_params():
    command = "service list --enabled"
    assert apply_command_params(command, {}) == command


def test_cloud_command_params_accept_filter_style_values():
    assert (
        apply_command_params("service list --filter={filter}", {"filter": "name:foo=bar"})
        == "service list --filter=name:foo=bar"
    )


def test_cloud_command_params_reject_unresolved_placeholders():
    with pytest.raises(ValueError, match="Missing required cloud check parameter"):
        apply_command_params("service list --filter={filter} --region={region}", {"filter": "enabled"})


def test_cloud_command_params_reject_unresolved_placeholders_with_empty_params():
    with pytest.raises(ValueError, match="Missing required cloud check parameter"):
        apply_command_params("service list --filter={filter}", {})


def test_gcp_asset_inventory_uses_service_enablement_check():
    assert (
        READ_ONLY_CHECKS["asset_inventory_enabled"]
        == "services list --enabled --filter=name:cloudasset.googleapis.com"
    )


def test_gcp_mcp_config_requires_read_only(tmp_path):
    mcp_config = tmp_path / "gcp.json"
    mcp_config.write_text(
        json.dumps({"enabled": True, "env": {"READ_OPERATIONS_ONLY": "false"}}),
        encoding="utf-8",
    )
    with pytest.raises(GcpCloudConfigError, match="READ_OPERATIONS_ONLY=true"):
        GcpCloudConfig.load(mcp_path=mcp_config)


def test_aws_mcp_config_requires_read_only(tmp_path):
    mcp_config = tmp_path / "aws.json"
    mcp_config.write_text(
        json.dumps({"enabled": True, "env": {"READ_OPERATIONS_ONLY": "false"}}),
        encoding="utf-8",
    )
    with pytest.raises(AwsCloudConfigError, match="READ_OPERATIONS_ONLY=true"):
        AwsCloudConfig.load(mcp_path=mcp_config)


def test_gitignore_blocks_live_mcp_configs():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "mcp/*.json" in gitignore
    assert "mcp/**/*.json" in gitignore
    assert "!mcp/filesystem.json" in gitignore


def test_gcp_normalization_extracts_nested_resource_and_relevant_field():
    sink_findings = GcpCloudProvider._normalize_findings(
        "log_sink_configured",
        {"output": {"sinks": [{"config": {"name": "audit-sink"}}]}},
    )
    assert sink_findings[0]["resource"] == "audit-sink"

    bucket_findings = GcpCloudProvider._normalize_findings(
        "cloud_storage_public_access",
        {
            "output": [
                {
                    "name": "evidence-bucket",
                    "iamConfiguration": {"publicAccessPrevention": "enforced"},
                }
            ]
        },
    )
    assert bucket_findings[0]["evidence_field"] == "iamConfiguration.publicAccessPrevention"
    assert bucket_findings[0]["evidence_value"] == "enforced"

    missing_field_findings = GcpCloudProvider._normalize_findings(
        "cloud_storage_encryption_default",
        {"output": [{"name": "default-encrypted-bucket"}]},
    )
    assert missing_field_findings[0]["evidence_field"] == "encryption.defaultKmsKeyName"
    assert missing_field_findings[0]["evidence_value"] is None

    non_dict_nested_findings = GcpCloudProvider._normalize_findings(
        "compute_disk_encryption_default",
        {"output": [{"name": "disk-1", "diskEncryptionKey": "google-managed"}]},
    )
    assert non_dict_nested_findings[0]["evidence_field"] == "diskEncryptionKey.kmsKeyName"
    assert non_dict_nested_findings[0]["evidence_value"] is None

    policy_findings = GcpCloudProvider._normalize_findings(
        "security_command_center_enabled",
        {"output": {"services": [{"config": {"name": "securitycenter.googleapis.com"}}]}},
    )
    assert policy_findings[0]["resource"] == "securitycenter.googleapis.com"

    firewall_findings = GcpCloudProvider._normalize_findings(
        "firewall_open_ingress",
        {"output": {"firewallRules": [{"name": "allow-http", "direction": "INGRESS"}]}},
    )
    assert firewall_findings[0]["resource"] == "allow-http"
    assert firewall_findings[0]["check"] == "firewall_open_ingress"

    list_payload_firewall_findings = GcpCloudProvider._normalize_findings(
        "firewall_open_ingress",
        {"output": [{"name": "allow-ssh", "direction": "INGRESS"}]},
    )
    assert list_payload_firewall_findings[0]["resource"] == "allow-ssh"


def test_gcp_provider_disabled_when_mcp_config_not_enabled(monkeypatch, live_cloud_policy):
    monkeypatch.setenv("CLOUD_PROVIDER", "gcp")
    monkeypatch.setenv("GCP_PROJECT", "audit-project")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/fake/creds.json")
    provider = get_cloud_provider()
    assert provider.enabled is False
    with pytest.raises(GcpCloudConfigError, match="GCP MCP config is disabled"):
        provider.collect("log_sink_configured")


def test_gcp_selected_with_live_policy_and_mock(
    monkeypatch,
    live_cloud_policy,
    guard_setup,
    enabled_gcp_config,
):
    monkeypatch.setenv("CLOUD_PROVIDER", "gcp")
    guard, _, audit_dir = guard_setup

    def invoke(_tool: str, _params: dict[str, Any]) -> dict[str, Any]:
        return _gcp_sink_response()

    client = GcpMcpClient(enabled_gcp_config, invoke=invoke)
    provider = GcpCloudProvider(guard=guard, config=enabled_gcp_config, client=client)
    findings = provider.collect("log_sink_configured")
    assert findings
    assert any(e.get("event_type") == "cloud_collect" for e in _read_audit_events(audit_dir))


def test_gcp_list_capabilities_matches_cloud_checks_yaml():
    checks_path = ROOT / "brain" / "02-controls" / "cloud-checks.yaml"
    catalog = yaml.safe_load(checks_path.read_text(encoding="utf-8"))
    yaml_checks: set[str] = set()
    for entry in (catalog.get("gcp") or {}).values():
        yaml_checks.update(entry.get("checks") or [])

    provider = GcpCloudProvider(
        config=GcpCloudConfig(
            project_id="audit-project",
            credentials_path="/fake/creds.json",
            organization_id=None,
            region="us-central1",
            mcp_enabled=True,
        )
    )
    assert sorted(provider.list_capabilities()) == sorted(yaml_checks)


def test_gcp_collect_error_emits_audit_event(guard_setup, enabled_gcp_config):
    guard, _, audit_dir = guard_setup

    def invoke(_tool: str, _params: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("simulated MCP failure")

    client = GcpMcpClient(enabled_gcp_config, invoke=invoke)
    provider = GcpCloudProvider(guard=guard, config=enabled_gcp_config, client=client)

    with pytest.raises(RuntimeError, match="GCP MCP collect failed"):
        provider.collect("log_sink_configured")

    events = _read_audit_events(audit_dir)
    error_events = [
        e
        for e in events
        if e.get("event_type") == "cloud_collect" and e.get("outputs", {}).get("status") == "error"
    ]
    assert len(error_events) == 1


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


def test_aws_rejects_unsafe_region_before_mcp_call(enabled_aws_config):
    cfg = AwsCloudConfig(
        profile=enabled_aws_config.profile,
        role_arn=None,
        region="us-east-1 --profile evil",
        mcp_enabled=True,
    )

    def invoke(_tool: str, _params: dict[str, Any]) -> dict[str, Any]:
        pytest.fail("unsafe region should be rejected before MCP invocation")

    provider = AwsCloudProvider(config=cfg, client=AwsMcpClient(cfg, invoke=invoke))
    with pytest.raises(AwsCloudConfigError, match="Invalid AWS region"):
        provider.collect("cloudtrail_trails")


def test_aws_rejects_empty_region_before_mcp_call(enabled_aws_config):
    cfg = AwsCloudConfig(
        profile=enabled_aws_config.profile,
        role_arn=None,
        region="",
        mcp_enabled=True,
    )
    provider = AwsCloudProvider(config=cfg, client=AwsMcpClient(cfg, invoke=lambda *_: {}))
    with pytest.raises(AwsCloudConfigError, match="Invalid AWS region"):
        provider.collect("cloudtrail_trails")


@pytest.mark.parametrize("region", ["us-east-1", "ap-southeast-1", "us-gov-west-1", "us-iso-east-1"])
def test_aws_accepts_valid_region_partitions(enabled_aws_config, region):
    cfg = AwsCloudConfig(
        profile=enabled_aws_config.profile,
        role_arn=None,
        region=region,
        mcp_enabled=True,
    )
    cfg.require_auth()


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
            "detail": {
                "OwnerId": "123456789012",
                "SourceIp": "10.0.0.1",
                "AccessToken": "ya29.a0AfH6SMBEXAMPLE",
                "ServiceAccount": "auditor@audit-project.iam.gserviceaccount.com",
                "GcpResource": "//storage.googleapis.com/projects/_/buckets/evidence-bucket",
                "GcpSelfLink": "https://compute.googleapis.com/compute/v1/projects/audit-project/zones/us-central1-a/disks/disk-1",
            },
        }
    ]
    redacted = redact_obj(raw)
    text = json.dumps(redacted)
    assert "123456789012" not in text
    assert "arn:aws:cloudtrail" not in text
    assert "10.0.0.1" not in text
    assert "ya29." not in text
    assert "auditor@audit-project.iam.gserviceaccount.com" not in text
    assert "//storage.googleapis.com" not in text
    assert "https://compute.googleapis.com" not in text


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
