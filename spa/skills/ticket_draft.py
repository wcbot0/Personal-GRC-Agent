"""ticket-draft: AI-Proposed unassigned ticket object."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from connectors.registry import get_ticket_provider


def create_proposal(ticket: dict[str, Any]) -> dict[str, Any]:
    """Persist an AI-proposed ticket via the configured ticket provider (file-only in MVP)."""
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
    ctx = context or {}
    out_dir: Path = ctx.get("output_dir", Path("."))
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
    result = create_proposal(ticket)
    path = Path(result["path"])
    if path.parent != out_dir:
        artifact = out_dir / path.name
        artifact.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        result["path"] = str(artifact)
    return {
        "skill": "ticket-draft",
        "ticket": result["ticket"],
        "artifact_file": Path(result["path"]).name,
        "control_tags": result["ticket"]["control_tags"],
    }
