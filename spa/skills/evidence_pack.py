"""evidence-pack: control id + period -> evidence index file."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spa.paths import BRAIN_DIR, ROOT


def run(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    control_match = re.search(r"(?i)control[:\s]+([A-Za-z0-9.\-]+)", content)
    period_match = re.search(r"(?i)period[:\s]+([^\n]+)", content)
    control_id = control_match.group(1) if control_match else "CC6.1"
    period = period_match.group(1).strip() if period_match else datetime.now(timezone.utc).strftime("%Y-Q%q")

    evidence_dir = BRAIN_DIR / "evidence" / control_id.replace(".", "-")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    index_path = evidence_dir / f"index-{datetime.now(timezone.utc).strftime('%Y%m%d')}.md"
    index_md = f"""# Evidence Index — {control_id}

**Period:** {period}
**Status:** DRAFT — not authoritative until approved

## Artifacts
| Item | Source | Collected |
|------|--------|-----------|
| Access review export | manual | pending |
| Policy excerpt | brain/policies/ | pending |

## Control tags
- SOC2: {control_id}
- CSF: PR.AC
- 800-53: AC-2
"""
    index_path.write_text(index_md, encoding="utf-8")
    return {
        "skill": "evidence-pack",
        "control_id": control_id,
        "period": period,
        "index_file": str(index_path.relative_to(ROOT)),
        "control_tags": [f"SOC2:{control_id}", "CSF:PR.AC", "800-53:AC-2"],
    }
