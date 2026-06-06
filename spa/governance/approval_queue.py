"""Change Proposal Object (CPO) approval queue."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from spa.audit.logger import AuditLogger
from spa.memory.redaction import redact_obj
from spa.paths import APPROVAL_QUEUE_DIR, CPO_SCHEMA


class ApprovalQueueError(Exception):
    pass


class ApprovalQueue:
    def __init__(self, queue_dir: Path | None = None, audit: AuditLogger | None = None) -> None:
        self.queue_dir = queue_dir or APPROVAL_QUEUE_DIR
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.audit = audit or AuditLogger()
        self._schema = json.loads(CPO_SCHEMA.read_text())

    def _path_for(self, cpo_id: str) -> Path:
        return self.queue_dir / f"{cpo_id}.json"

    def _validate(self, cpo: dict[str, Any]) -> None:
        jsonschema.validate(cpo, self._schema)

    def create(
        self,
        *,
        action_class: str,
        action_type: str,
        title: str,
        description: str,
        risk_rationale: str,
        proposed_change: dict[str, Any],
        control_tags: list[str] | None = None,
        requested_by: str = "spa-agent",
        run_id: str | None = None,
    ) -> dict[str, Any]:
        if action_class not in {"A3", "A4", "A5"}:
            raise ApprovalQueueError(f"CPO requires A3+ action class, got {action_class}")

        now = datetime.now(timezone.utc).isoformat()
        cpo: dict[str, Any] = {
            "id": f"cpo-{uuid.uuid4()}",
            "created_at": now,
            "updated_at": now,
            "status": "pending",
            "action_class": action_class,
            "action_type": action_type,
            "title": title,
            "description": description,
            "risk_rationale": risk_rationale,
            "proposed_change": proposed_change,
            "control_tags": control_tags or [],
            "requested_by": requested_by,
            "approved_by": None,
            "approved_at": None,
            "rejected_by": None,
            "rejected_at": None,
            "rejection_reason": None,
            "run_id": run_id or self.audit.run_id,
        }
        cpo = redact_obj(cpo)
        self._validate(cpo)
        self._path_for(cpo["id"]).write_text(json.dumps(cpo, indent=2), encoding="utf-8")
        self.audit.emit(
            "cpo_created",
            task_class="governance",
            risk_class=action_class,
            approval_required=True,
            cpo_id=cpo["id"],
            outputs={"cpo_id": cpo["id"], "title": title},
        )
        return cpo

    def list_proposals(self, status: str | None = "pending") -> list[dict[str, Any]]:
        proposals = []
        for path in sorted(self.queue_dir.glob("cpo-*.json")):
            cpo = json.loads(path.read_text(encoding="utf-8"))
            if status is None or cpo.get("status") == status:
                proposals.append(cpo)
        return proposals

    def get(self, cpo_id: str) -> dict[str, Any]:
        path = self._path_for(cpo_id)
        if not path.exists():
            raise ApprovalQueueError(f"CPO not found: {cpo_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def approve(self, cpo_id: str, approved_by: str = "human-reviewer") -> dict[str, Any]:
        cpo = self.get(cpo_id)
        if cpo["status"] != "pending":
            raise ApprovalQueueError(f"CPO {cpo_id} is not pending (status={cpo['status']})")
        now = datetime.now(timezone.utc).isoformat()
        cpo.update(
            {
                "status": "approved",
                "approved_by": approved_by,
                "approved_at": now,
                "updated_at": now,
            }
        )
        self._validate(cpo)
        self._path_for(cpo_id).write_text(json.dumps(cpo, indent=2), encoding="utf-8")
        self.audit.emit(
            "cpo_approved",
            task_class="governance",
            risk_class=cpo["action_class"],
            approval_required=False,
            cpo_id=cpo_id,
            outputs={"approved_by": approved_by},
        )
        return cpo

    def reject(self, cpo_id: str, reason: str, rejected_by: str = "human-reviewer") -> dict[str, Any]:
        cpo = self.get(cpo_id)
        if cpo["status"] != "pending":
            raise ApprovalQueueError(f"CPO {cpo_id} is not pending (status={cpo['status']})")
        now = datetime.now(timezone.utc).isoformat()
        cpo.update(
            {
                "status": "rejected",
                "rejected_by": rejected_by,
                "rejected_at": now,
                "rejection_reason": reason,
                "updated_at": now,
            }
        )
        self._validate(cpo)
        self._path_for(cpo_id).write_text(json.dumps(cpo, indent=2), encoding="utf-8")
        self.audit.emit(
            "cpo_rejected",
            task_class="governance",
            risk_class=cpo["action_class"],
            approval_required=False,
            cpo_id=cpo_id,
            outputs={"rejected_by": rejected_by, "reason": reason},
        )
        return cpo

    def is_approved(self, cpo_id: str) -> bool:
        try:
            return self.get(cpo_id)["status"] == "approved"
        except ApprovalQueueError:
            return False
