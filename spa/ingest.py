"""Ingest inbox/brain files into memory and run downstream drafting skills."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from spa.audit.logger import AuditLogger
from spa.memory.episodic import EpisodicMemory
from spa.memory.redaction import redact_text
from spa.memory.semantic import SemanticMemory
from spa.paths import ROOT, WORKSPACE_DIR
from spa.skills.runner import run_skill
from spa.skills.ticket_draft import create_proposal

MEETING_SIGNALS = (
    "decisions",
    "action items",
    "action item",
    "risks",
    "transcript",
    "meeting",
    "attendees",
)
POLICY_SIGNALS = ("policy", "redline", "mfa")


def _is_meeting_content(content: str) -> bool:
    lower = content.lower()
    return sum(1 for signal in MEETING_SIGNALS if signal in lower) >= 2


def _policy_change_text(content: str, action_items: list[str]) -> str | None:
    policy_actions = [
        item for item in action_items if any(signal in item.lower() for signal in POLICY_SIGNALS)
    ]
    if policy_actions:
        return "Policy: access-control-policy\n\n" + "\n".join(policy_actions)
    lower = content.lower()
    if "policy" in lower and any(signal in lower for signal in ("redline", "update", "mfa")):
        return content
    return None


def _assert_verifiers_passed(skill: str, verifications: list[dict[str, Any]]) -> None:
    failed = [v for v in verifications if not v.get("passed")]
    if failed:
        details = ", ".join(f"{v['name']}: {v.get('detail', '')}" for v in failed)
        raise RuntimeError(f"{skill} verifiers failed: {details}")


def ingest_file(path: str | Path, audit: AuditLogger | None = None) -> dict:
    audit = audit or AuditLogger()
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = ROOT / file_path
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    os.environ.setdefault("TICKET_PROVIDER", "none")
    os.environ.setdefault("GRC_PROVIDER", "none")

    content = file_path.read_text(encoding="utf-8", errors="replace")
    redacted = redact_text(content)
    source = str(file_path.relative_to(ROOT)) if file_path.is_relative_to(ROOT) else str(file_path)

    episodic = EpisodicMemory()
    semantic = SemanticMemory()

    episodic_record = episodic.write(
        {
            "source": source,
            "content": redacted,
            "type": "episodic",
            "sensitivity": "internal",
            "tags": ["ingested"],
        }
    )
    semantic_id = semantic.upsert_document(
        doc_id=source,
        content=redacted,
        metadata={"source": source, "type": "ingested", "tags": ["ingested"]},
    )

    audit.emit(
        "ingest_complete",
        task_class="ingest",
        risk_class="A0",
        tools_called=["ingest_file"],
        retrieved_memory_ids=[episodic_record["id"], semantic_id],
        outputs={"source": source, "episodic_id": episodic_record["id"], "semantic_id": semantic_id},
        preview=redacted[:500],
    )

    result: dict[str, Any] = {
        "source": source,
        "episodic_id": episodic_record["id"],
        "semantic_id": semantic_id,
        "content_preview": redacted[:200],
        "meeting_synth": None,
        "ticket_proposals": [],
        "policy_redline": None,
        "verifications": [],
    }

    if not _is_meeting_content(redacted):
        return result

    meeting_out = WORKSPACE_DIR / "drafts" / "meeting-synth"
    meeting_result = run_skill(
        "meeting-synth",
        file_path,
        output_dir=meeting_out,
        audit=audit,
    )
    _assert_verifiers_passed("meeting-synth", meeting_result["verifications"])
    result["meeting_synth"] = meeting_result["output"]
    result["verifications"].extend(meeting_result["verifications"])

    for ticket in meeting_result["output"].get("proposed_tickets", []):
        proposal = create_proposal(ticket)
        result["ticket_proposals"].append(proposal)
        audit.emit(
            "ticket_draft_created",
            task_class="ingest",
            risk_class="A2",
            tools_called=["ticket_provider.create_draft"],
            outputs={"path": proposal["path"], "ticket_id": proposal["ticket"]["id"]},
            preview=proposal["ticket"].get("description", "")[:500],
        )

    policy_text = _policy_change_text(redacted, meeting_result["output"].get("action_items", []))
    if policy_text:
        policy_input = meeting_out / "policy-change-input.md"
        policy_input.write_text(policy_text, encoding="utf-8")
        policy_result = run_skill(
            "policy-redline",
            policy_input,
            output_dir=WORKSPACE_DIR / "proposals",
            audit=audit,
        )
        _assert_verifiers_passed("policy-redline", policy_result["verifications"])
        result["policy_redline"] = policy_result["output"]
        result["verifications"].extend(policy_result["verifications"])

    return result
