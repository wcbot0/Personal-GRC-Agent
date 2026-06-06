"""End-to-end ingest workflow tests (T4)."""
from __future__ import annotations

import json
from pathlib import Path

from spa.ingest import ingest_file
from spa.paths import ROOT, get_drafts_dir, get_proposals_dir


def test_ingest_meeting_sample_produces_draft_artifacts():
    fixture = ROOT / "evals/fixtures/meeting_sample.md"
    result = ingest_file(fixture)

    assert result["meeting_synth"] is not None
    assert result["meeting_synth"]["control_tags"]
    assert len(result["ticket_proposals"]) == 3

    tickets_dir = get_proposals_dir() / "tickets"
    for proposal in result["ticket_proposals"]:
        ticket = proposal["ticket"]
        assert ticket["assignee"] == "unassigned"
        assert ticket["status"] == "ai_proposed"
        assert ticket.get("suggested_owner")
        assert ticket.get("rationale")
        assert ticket.get("control_tags")
        path = Path(proposal["path"])
        assert path.exists()
        assert path.parent == tickets_dir
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        assert on_disk["assignee"] == "unassigned"

    policy = result["policy_redline"]
    assert policy is not None
    assert policy["control_tags"]
    proposals_dir = get_proposals_dir()
    redline_path = proposals_dir / "03-policies" / "proposals" / "access-control-policy-redline.md"
    pr_body_path = proposals_dir / "draft-pr-body-access-control-policy.md"
    assert redline_path.exists()
    assert pr_body_path.exists()

    meeting_out = get_drafts_dir() / "meeting-synth"
    assert meeting_out.exists()
    assert list(meeting_out.glob("meeting-synth-*.json"))
