"""meeting-synth: transcript/notes -> decisions, risks, action items, proposed tickets."""
from __future__ import annotations

import re
from typing import Any

from spa.paths import resolve_output_dir


_SECTION_HEADERS = frozenset(
    {"decisions", "risks", "action items", "action item", "notes", "attendees"}
)


def _extract_bullets(text: str, keywords: list[str]) -> list[str]:
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lower = stripped.lower()
        if any(k in lower for k in keywords):
            cleaned = re.sub(r"^[-*#\d.\s]+", "", stripped).strip()
            if not cleaned or cleaned.lower() in _SECTION_HEADERS:
                continue
            items.append(cleaned)
    return items[:10]


def run(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    resolve_output_dir(context)

    decisions = _extract_bullets(content, ["decided", "decision", "agreed", "approved"])
    risks = _extract_bullets(content, ["risk", "concern", "blocker", "gap"])
    actions = _extract_bullets(content, ["action", "todo", "follow-up", "follow up", "next step"])

    if not decisions:
        decisions = ["Review meeting notes and confirm decisions with stakeholders"]
    if not risks:
        risks = ["No explicit risks captured — validate during daily brief"]
    if not actions:
        actions = ["Schedule follow-up review of open control gaps"]

    tickets = []
    for i, action in enumerate(actions[:5], start=1):
        ticket = {
            "id": f"AI-PROPOSED-{i:03d}",
            "title": action[:120],
            "status": "ai_proposed",
            "assignee": "unassigned",
            "suggested_owner": "security-team",
            "rationale": f"Derived from meeting action item: {action}",
            "description": (
                f"{action[:120]}\n\n"
                f"Suggested owner: security-team\n\n"
                f"Derived from meeting action item: {action}"
            ),
            "control_tags": ["CSF:ID.AM", "SOC2:CC3.2", "SOC2:CC6.1"],
        }
        tickets.append(ticket)

    return {
        "skill": "meeting-synth",
        "decisions": decisions,
        "risks": risks,
        "action_items": actions,
        "proposed_tickets": tickets,
        "control_tags": ["CSF:ID.AM", "CSF:DE.AE", "SOC2:CC3.2", "SOC2:CC6.1", "800-53:RA-5"],
        "ticket_files": [],
    }
