"""daily-brief: synthesize proposals, sessions, pending approvals."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spa.paths import APPROVAL_QUEUE_DIR, get_audit_logs_dir, get_proposals_dir, resolve_output_dir
from spa.skills.io import write_text_file


def _list_pending_cpos(queue_dir: Path) -> list[dict[str, Any]]:
    if not queue_dir.exists():
        return []
    pending: list[dict[str, Any]] = []
    for path in sorted(queue_dir.glob("cpo-*.json")):
        cpo = json.loads(path.read_text(encoding="utf-8"))
        if cpo.get("status") == "pending":
            pending.append(cpo)
    return pending


def run(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    pending = _list_pending_cpos(APPROVAL_QUEUE_DIR)

    proposals_dir = get_proposals_dir()
    proposals = list(proposals_dir.glob("*.md")) if proposals_dir.exists() else []
    audit_dir = get_audit_logs_dir()
    audit_logs = list(audit_dir.glob("audit-*.jsonl")) if audit_dir.exists() else []

    brief_md = f"""# Daily Security Brief — {datetime.now(timezone.utc).date().isoformat()}

## Pending approvals ({len(pending)})
"""
    for cpo in pending[:10]:
        brief_md += f"- **{cpo['title']}** (`{cpo['id']}`) — {cpo['action_class']}\n"

    brief_md += f"""
## Open draft proposals ({len(proposals)})
"""
    for p in proposals[:10]:
        brief_md += f"- {p.name}\n"

    brief_md += f"""
## Recent audit activity
- Audit log files: {len(audit_logs)}
- Context note: {content.strip()[:300] or 'No additional context provided.'}

## Suggested focus
1. Review pending CPOs before assigning work
2. Triage AI-Proposed tickets in workspace/drafts/
3. Run `make eval` if skill outputs drift
"""
    out_dir = resolve_output_dir(context)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"daily-brief-{datetime.now(timezone.utc).strftime('%Y%m%d')}.md"
    write_text_file(context, "write_local_markdown", path, brief_md)

    return {
        "skill": "daily-brief",
        "brief_markdown": brief_md,
        "pending_approvals": len(pending),
        "open_proposals": len(proposals),
        "control_tags": ["CSF:ID.AM", "SOC2:CC4.1"],
    }
