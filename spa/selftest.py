"""Self-test suite for bootstrap acceptance and milestone gates."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import ApprovalQueue
from spa.governance.policy import AutonomyPolicy
from spa.memory.redaction import redact_text
from spa.paths import ROOT
from spa.tools.guard import ToolBlockedError, ToolGuard


def test_repo_structure() -> None:
    required = [
        "LICENSE",
        "bootstrap.sh",
        "Makefile",
        "docker-compose.yml",
        "agent/autonomy-policy.yaml",
        "agent/runtime.config.yaml",
        "agent/charter.md",
        "memory/schemas/cpo.schema.json",
        "governance/redaction-rules.yaml",
        "skills/meeting-synth/skill.md",
        "connectors/interfaces/ticket.py",
    ]
    for rel in required:
        assert (ROOT / rel).exists(), f"Missing required path: {rel}"


def test_policy_loads() -> None:
    policy = AutonomyPolicy.load()
    assert policy.classify_tool("read_file") == "A0"
    assert policy.requires_approval("A3")
    assert policy.is_blocked("A5")


def test_redaction() -> None:
    sample = "api_key=SUPER_SECRET_TOKEN_12345 and email user@example.com"
    redacted = redact_text(sample)
    assert "SUPER_SECRET_TOKEN" not in redacted
    assert "user@example.com" not in redacted


def test_cpo_lifecycle() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        audit = AuditLogger()
        queue = ApprovalQueue(queue_dir=Path(tmp), audit=audit)
        cpo = queue.create(
            action_class="A3",
            action_type="assign_human",
            title="Assign ticket to Alice",
            description="Test CPO",
            risk_rationale="Human workflow impact",
            proposed_change={"assignee": "alice"},
        )
        assert cpo["status"] == "pending"
        listed = queue.list_proposals()
        assert any(item["id"] == cpo["id"] for item in listed)
        queue.approve(cpo["id"])
        assert queue.get(cpo["id"])["status"] == "approved"


def test_tool_guard_blocks_a3() -> None:
    audit = AuditLogger()
    with tempfile.TemporaryDirectory() as tmp:
        queue = ApprovalQueue(queue_dir=Path(tmp), audit=audit)
        guard = ToolGuard(queue=queue, audit=audit)
        try:
            guard.check_allowed(
                "assign_human",
                create_cpo=lambda: queue.create(
                    action_class="A3",
                    action_type="assign_human",
                    title="Block test",
                    description="",
                    risk_rationale="test",
                    proposed_change={},
                ),
            )
            raise AssertionError("Expected ToolBlockedError")
        except ToolBlockedError as exc:
            assert exc.cpo_id is not None


def test_audit_schema() -> None:
    audit = AuditLogger()
    event = audit.emit("selftest", task_class="test", risk_class="A0")
    assert "event_id" in event
    assert "run_id" in event


def run_all() -> int:
    tests = [
        test_repo_structure,
        test_policy_loads,
        test_redaction,
        test_cpo_lifecycle,
        test_tool_guard_blocks_a3,
        test_audit_schema,
    ]
    passed = 0
    for test in tests:
        name = test.__name__
        try:
            test()
            print(f"  OK  {name}")
            passed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {name}: {exc}")
    print(f"\nselftest: {passed}/{len(tests)} passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    raise SystemExit(run_all())
