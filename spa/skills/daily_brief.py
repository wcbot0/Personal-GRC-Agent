"""daily-brief: synthesize proposals, sessions, pending approvals."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from spa.governance.approval_queue import ApprovalQueue
from spa.paths import GOVERNANCE_DIR, WORKSPACE_DIR


def run(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    queue = ApprovalQueue()
    pending = queue.list_proposals(status="pending")

    proposals = list((WORKSPACE_DIR / "proposals").glob("*.md")) if (WORKSPACE_DIR / "proposals").exists() else []
    audit_logs = list(GOVERNANCE_DIR.joinpath("audit-logs").glob("audit-*.jsonl"))

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
    out_dir = (context or {}).get("output_dir")
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"daily-brief-{datetime.now(timezone.utc).strftime('%Y%m%d')}.md"
        path.write_text(brief_md, encoding="utf-8")

    return {
        "skill": "daily-brief",
        "brief_markdown": brief_md,
        "pending_approvals": len(pending),
        "open_proposals": len(proposals),
        "control_tags": ["CSF:ID.AM", "SOC2:CC4.1"],
    }
