"""Skill runner staging, verifier gating, and artifact redaction tests."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import ApprovalQueue
from spa.skills.runner import VerifierFailedError, run_skill
from spa.tools.guard import ToolGuard


def test_verifier_failure_discards_staged_skill_side_files(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SPA_DATA_DIR", str(tmp_path / "data"))
    audit_dir = tmp_path / "audit"
    queue_dir = tmp_path / "queue"
    audit = AuditLogger(log_dir=audit_dir)
    queue = ApprovalQueue(queue_dir=queue_dir, audit=audit)
    guard = ToolGuard(queue=queue, audit=audit)
    out_dir = tmp_path / "out"
    input_file = tmp_path / "policy.md"
    input_file.write_text("Policy: staged-policy\nUpdate access review cadence.", encoding="utf-8")

    def fail_verifiers(*args, **kwargs):
        return (
            {"skill": "policy-redline", "control_tags": ["SOC2:CC6.1"]},
            [{"name": "schema", "passed": False, "detail": "test"}],
        )

    with patch("spa.skills.runner.run_verifiers", side_effect=fail_verifiers):
        with pytest.raises(VerifierFailedError):
            run_skill(
                "policy-redline",
                input_file,
                output_dir=out_dir,
                audit=audit,
                guard=guard,
            )

    assert list(out_dir.rglob("*-redline.md")) == []
    assert list(out_dir.rglob("draft-pr-body-*.md")) == []
    assert list(out_dir.glob("policy-redline-*.json")) == []


def test_runner_promotes_staged_files_on_success(tmp_path: Path):
    input_file = tmp_path / "policy.md"
    input_file.write_text("Policy: promoted-policy\nUpdate logging retention.", encoding="utf-8")
    out_dir = tmp_path / "out"

    result = run_skill(
        "policy-redline",
        input_file,
        output_dir=out_dir,
        audit=AuditLogger(log_dir=tmp_path / "audit"),
    )

    slug = result["output"]["policy_name"]
    assert (out_dir / "03-policies" / "proposals" / f"{slug}-redline.md").exists()
    assert (out_dir / f"draft-pr-body-{slug}.md").exists()
    assert Path(result["artifact"]).exists()


def test_runner_artifact_applies_redaction(tmp_path: Path):
    sensitive_account = "123456789012"
    input_file = tmp_path / "ticket.md"
    input_file.write_text(
        f"# Ticket\n\nRotate IAM role arn:aws:iam::{sensitive_account}:role/admin\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"

    result = run_skill(
        "ticket-draft",
        input_file,
        output_dir=out_dir,
        audit=AuditLogger(log_dir=tmp_path / "audit"),
    )

    artifact_text = Path(result["artifact"]).read_text(encoding="utf-8")
    assert sensitive_account not in artifact_text
