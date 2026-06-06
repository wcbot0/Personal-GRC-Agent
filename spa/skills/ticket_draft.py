"""ticket-draft: AI-Proposed unassigned ticket object."""
from __future__ import annotations

import json
import re
from typing import Any

from spa.paths import resolve_output_dir


def create_proposal(ticket: dict[str, Any]) -> dict[str, Any]:
    """Persist an AI-proposed ticket via the configured ticket provider (file-only in MVP)."""
    from connectors.registry import get_ticket_provider

    record = dict(ticket)
    record.setdefault("status", "ai_proposed")
    record.setdefault("assignee", "unassigned")
    owner = record.get("suggested_owner", "security-team")
    rationale = record.get("rationale", "Draft ticket generated locally; assignee remains unassigned.")
    record.setdefault(
        "description",
        f"{record.get('title', 'AI-Proposed security task')}\n\n"
        f"Suggested owner: {owner}\n\n{rationale}",
    )
    record.setdefault("control_tags", ["CSF:PR.IP", "SOC2:CC8.1", "800-53:CM-3"])
    return get_ticket_provider().create_draft(record)


def run(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    out_dir = resolve_output_dir(context)
    out_dir.mkdir(parents=True, exist_ok=True)

    title_match = re.search(r"(?im)^#\s+(.+)$", content)
    title = title_match.group(1).strip() if title_match else "AI-Proposed security task"
    body_lines = [ln.strip() for ln in content.splitlines() if ln.strip() and not ln.startswith("#")]
    description = "\n".join(body_lines[:20]) or "Draft ticket from SPA input."

    ticket = {
        "id": "AI-PROPOSED-001",
        "title": title,
        "description": description,
        "status": "ai_proposed",
        "assignee": "unassigned",
        "suggested_owner": "grc-engineer",
        "priority": "medium",
        "rationale": "Draft ticket generated locally; assignee remains unassigned per MVP policy.",
        "control_tags": ["CSF:PR.IP", "SOC2:CC8.1", "800-53:CM-3"],
    }
    record = dict(ticket)
    record.setdefault("status", "ai_proposed")
    record.setdefault("assignee", "unassigned")
    owner = record.get("suggested_owner", "security-team")
    rationale = record.get("rationale", "Draft ticket generated locally; assignee remains unassigned.")
    record.setdefault(
        "description",
        f"{record.get('title', 'AI-Proposed security task')}\n\n"
        f"Suggested owner: {owner}\n\n{rationale}",
    )
    record.setdefault("control_tags", ["CSF:PR.IP", "SOC2:CC8.1", "800-53:CM-3"])

    ticket_id = record.get("id", "ai-proposed").replace("/", "-")
    path = out_dir / f"ticket-proposal-{ticket_id}.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")

    return {
        "skill": "ticket-draft",
        "ticket": record,
        "artifact_file": path.name,
        "control_tags": record["control_tags"],
    }
