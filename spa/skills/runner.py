"""Execute drafting skills with verifiers and audit emission."""
from __future__ import annotations

import importlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import ApprovalQueue
from spa.paths import ROOT, SKILLS_DIR, get_drafts_dir
from spa.skills.verifiers import run_verifiers
from spa.tools.guard import ToolGuard


SKILL_MODULES = {
    "meeting-synth": "spa.skills.meeting_synth",
    "ticket-draft": "spa.skills.ticket_draft",
    "policy-redline": "spa.skills.policy_redline",
    "csf-crosswalk": "spa.skills.csf_crosswalk",
    "daily-brief": "spa.skills.daily_brief",
    "evidence-pack": "spa.skills.evidence_pack",
}


def _load_skill_fn(skill_name: str):
    module_path = SKILL_MODULES.get(skill_name)
    if not module_path:
        raise ValueError(f"Unknown skill: {skill_name}")
    mod = importlib.import_module(module_path)
    return mod.run


def run_skill(
    skill_name: str,
    input_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    audit: AuditLogger | None = None,
) -> dict[str, Any]:
    audit = audit or AuditLogger()
    guard = ToolGuard(audit=audit)
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else get_drafts_dir() / skill_name
    out_dir.mkdir(parents=True, exist_ok=True)

    guard.execute(
        "write_draft_file",
        lambda: None,
        preview=f"skill={skill_name} input={input_path.name}",
        task_class="skill",
    )

    skill_fn = _load_skill_fn(skill_name)
    output = skill_fn(input_path.read_text(encoding="utf-8"), context={"output_dir": out_dir})

    serialized = json.dumps(output, indent=2, default=str)
    audit.emit(
        "skill_preview",
        task_class="skill",
        risk_class="A1",
        tools_called=[f"skill:{skill_name}"],
        preview=f"skill={skill_name} chars={len(serialized)}",
    )

    final_output, verifications = run_verifiers(
        skill_name,
        output,
        serialized,
        retry_fn=lambda: skill_fn(
            input_path.read_text(encoding="utf-8"),
            context={"output_dir": out_dir, "retry": True},
        ),
    )

    if not all(v["passed"] for v in verifications):
        queue = ApprovalQueue(audit=audit)
        cpo = queue.create(
            action_class="A3",
            action_type="skill_verifier_escalation",
            title=f"Verifier failure: {skill_name}",
            description="Skill output failed verifiers after retry",
            risk_rationale="Draft quality gate not met",
            proposed_change={"skill": skill_name, "verifications": verifications},
            control_tags=final_output.get("control_tags", []),
        )
        audit.emit(
            "skill_escalated",
            task_class="skill",
            risk_class="A3",
            approval_required=True,
            cpo_id=cpo["id"],
            verifications=verifications,
        )

    # Write artifacts
    artifact_path = out_dir / f"{skill_name}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    artifact_path.write_text(json.dumps(final_output, indent=2), encoding="utf-8")

    try:
        artifact_ref = str(artifact_path.relative_to(ROOT))
    except ValueError:
        artifact_ref = str(artifact_path)

    audit.emit(
        "skill_complete",
        task_class="skill",
        risk_class="A1",
        tools_called=[f"skill:{skill_name}"],
        outputs={"artifact": artifact_ref},
        verifications=verifications,
    )
    return {
        "skill": skill_name,
        "artifact": str(artifact_path),
        "output": final_output,
        "verifications": verifications,
    }
