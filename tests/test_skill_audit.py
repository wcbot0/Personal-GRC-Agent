"""Skill audit logging tests."""
from __future__ import annotations

import json

from spa.audit.logger import AuditLogger
from spa.skills.runner import run_skill


def test_skill_preview_omits_serialized_output(tmp_path):
    audit_dir = tmp_path / "audit"
    input_file = tmp_path / "ticket.md"
    sensitive_phrase = "Sensitive control decision: rotate production IAM role"
    input_file.write_text(f"# Ticket\n\n{sensitive_phrase}", encoding="utf-8")

    run_skill(
        "ticket-draft",
        input_file,
        output_dir=tmp_path / "drafts",
        audit=AuditLogger(log_dir=audit_dir),
    )

    audit_file = next(audit_dir.glob("audit-*.jsonl"))
    events = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines()]
    skill_preview = next(event for event in events if event["event_type"] == "skill_preview")

    assert skill_preview["preview"].startswith("skill=ticket-draft chars=")
    assert sensitive_phrase not in skill_preview["preview"]
