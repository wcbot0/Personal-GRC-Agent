"""Execute drafting skills with verifiers and audit emission."""
from __future__ import annotations

import hashlib
import importlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spa.audit.logger import AuditLogger
from spa.paths import ROOT, get_drafts_dir
from spa.skills.verifiers import run_verifiers
from spa.tools.guard import ToolGuard
from spa.tools.write import guarded_write


class VerifierFailedError(Exception):
    def __init__(self, message: str, *, cpo_id: str | None = None, verifications: list | None = None) -> None:
        super().__init__(message)
        self.cpo_id = cpo_id
        self.verifications = verifications or []


SKILL_MODULES = {
    "meeting-synth": "spa.skills.meeting_synth",
    "ticket-draft": "spa.skills.ticket_draft",
    "policy-redline": "spa.skills.policy_redline",
    "csf-crosswalk": "spa.skills.csf_crosswalk",
    "daily-brief": "spa.skills.daily_brief",
    "evidence-pack": "spa.skills.evidence_pack",
    "risk-analyst": "spa.skills.risk_analyst",
    "repo-security-review": "spa.skills.repo_security_review",
}


def _load_skill_fn(skill_name: str):
    module_path = SKILL_MODULES.get(skill_name)
    if not module_path:
        raise ValueError(f"Unknown skill: {skill_name}")
    mod = importlib.import_module(module_path)
    return mod.run


def _input_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_skill(
    skill_name: str,
    input_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    audit: AuditLogger | None = None,
    guard: ToolGuard | None = None,
) -> dict[str, Any]:
    audit = audit or AuditLogger()
    guard = guard or ToolGuard(audit=audit)
    input_path = Path(input_path)
    out_dir = Path(output_dir) if output_dir else get_drafts_dir() / skill_name
    out_dir.mkdir(parents=True, exist_ok=True)
    input_hash = _input_sha256(input_path)

    guard.execute(
        "write_draft_file",
        lambda: None,
        preview=f"skill={skill_name} input={input_path.name}",
        task_class="skill",
    )

    skill_fn = _load_skill_fn(skill_name)
    context: dict[str, Any] = {"output_dir": out_dir, "guard": guard, "audit": audit}
    output = skill_fn(input_path.read_text(encoding="utf-8"), context=context)

    serialized = json.dumps(output, indent=2, default=str)
    audit.emit(
        "skill_preview",
        task_class="skill",
        risk_class="A1",
        tools_called=[f"skill:{skill_name}"],
        preview=f"skill={skill_name} chars={len(serialized)}",
        input_sha256=input_hash,
    )

    final_output, verifications = run_verifiers(
        skill_name,
        output,
        serialized,
        retry_fn=lambda failed: skill_fn(
            input_path.read_text(encoding="utf-8"),
            context={**context, "retry": True, "verifier_feedback": failed},
        ),
    )

    cpo_id: str | None = None
    if not all(v["passed"] for v in verifications):
        cpo = guard.queue.create(
            action_class="A3",
            action_type="skill_verifier_escalation",
            title=f"Verifier failure: {skill_name}",
            description="Skill output failed verifiers after retry",
            risk_rationale="Draft quality gate not met",
            proposed_change={"skill": skill_name, "verifications": verifications},
            control_tags=final_output.get("control_tags", []),
        )
        cpo_id = cpo["id"]
        audit.emit(
            "skill_failed",
            task_class="skill",
            risk_class="A3",
            approval_required=True,
            cpo_id=cpo_id,
            verifications=verifications,
            input_sha256=input_hash,
        )
        audit.emit(
            "skill_escalated",
            task_class="skill",
            risk_class="A3",
            approval_required=True,
            cpo_id=cpo_id,
            verifications=verifications,
        )
        raise VerifierFailedError(
            f"{skill_name} verifiers failed after retry",
            cpo_id=cpo_id,
            verifications=verifications,
        )

    artifact_path = out_dir / f"{skill_name}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"

    def _write_artifact() -> None:
        artifact_path.write_text(json.dumps(final_output, indent=2), encoding="utf-8")

    guarded_write(
        guard,
        "write_local_markdown",
        _write_artifact,
        preview=artifact_path.name,
    )

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
        artifact_refs=[artifact_ref],
        input_sha256=input_hash,
    )
    return {
        "skill": skill_name,
        "artifact": str(artifact_path),
        "output": final_output,
        "verifications": verifications,
    }
