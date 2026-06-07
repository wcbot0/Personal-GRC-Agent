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
from spa.paths import CPO_SCHEMA, get_approval_queue_dir, get_proposals_dir


class ApprovalQueueError(Exception):
    pass


RISK_ORDER = ["A3", "A4", "A5"]


def _allowed_risk_classes(max_risk: str) -> set[str]:
    if max_risk not in RISK_ORDER:
        raise ApprovalQueueError(f"max-risk must be one of {', '.join(RISK_ORDER[:-1])}")
    return set(RISK_ORDER[: RISK_ORDER.index(max_risk) + 1])


class ApprovalQueue:
    def __init__(self, queue_dir: Path | None = None, audit: AuditLogger | None = None) -> None:
        self.queue_dir = queue_dir or get_approval_queue_dir()
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
        audit_event = self.audit.emit(
            "cpo_created",
            task_class="governance",
            risk_class=action_class,
            approval_required=True,
            cpo_id=cpo["id"],
            outputs={"cpo_id": cpo["id"], "title": title},
        )
        cpo["created_audit_event_id"] = audit_event["event_id"]
        cpo["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._validate(cpo)
        self._path_for(cpo["id"]).write_text(json.dumps(cpo, indent=2), encoding="utf-8")
        return cpo

    def list_proposals(self, status: str | None = "pending") -> list[dict[str, Any]]:
        proposals = []
        for path in sorted(self.queue_dir.glob("cpo-*.json")):
            cpo = json.loads(path.read_text(encoding="utf-8"))
            if status is None or cpo.get("status") == status:
                proposals.append(cpo)
        return proposals

    @staticmethod
    def summary_row(cpo: dict[str, Any]) -> dict[str, str]:
        return {
            "id": cpo["id"],
            "type": cpo["action_type"],
            "risk": cpo["action_class"],
            "summary": cpo["title"],
        }

    def get(self, cpo_id: str) -> dict[str, Any]:
        path = self._path_for(cpo_id)
        if not path.exists():
            raise ApprovalQueueError(f"CPO not found: {cpo_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def build_preview(self, cpo: dict[str, Any]) -> str:
        change = cpo.get("proposed_change") or {}
        lines = [
            f"Action: {cpo['action_type']} ({cpo['action_class']})",
            f"Summary: {cpo['title']}",
            "",
            cpo.get("description", ""),
            "",
            "Proposed change:",
            json.dumps(change, indent=2),
        ]
        if cpo["action_type"] == "assign_human":
            ticket_preview = self._assign_human_diff(change)
            if ticket_preview:
                lines.extend(["", "Diff:", ticket_preview])
        return "\n".join(lines).strip()

    def get_detail(self, cpo_id: str) -> dict[str, Any]:
        cpo = self.get(cpo_id)
        return {**cpo, "preview": self.build_preview(cpo)}

    def _assign_human_diff(self, change: dict[str, Any]) -> str | None:
        assignee = change.get("assignee")
        if not assignee:
            return None
        ticket_path = self._resolve_ticket_path(change)
        if ticket_path is None or not ticket_path.exists():
            return f"assignee: unassigned -> {assignee}"
        ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
        before = ticket.get("assignee", "unassigned")
        return f"assignee: {before} -> {assignee}"

    def _resolve_ticket_path(self, change: dict[str, Any]) -> Path | None:
        if change.get("path"):
            return Path(change["path"])
        ticket_id = change.get("ticket_id")
        if not ticket_id:
            return None
        tickets_dir = get_proposals_dir() / "tickets"
        safe_id = str(ticket_id).replace("/", "-")
        matches = sorted(tickets_dir.glob(f"*{safe_id}*.json"))
        if matches:
            return matches[0]
        return tickets_dir / f"ticket-proposal-{safe_id}.json"

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
        if not reason or not reason.strip():
            raise ApprovalQueueError("Rejection reason is required")
        cpo = self.get(cpo_id)
        if cpo["status"] != "pending":
            raise ApprovalQueueError(f"CPO {cpo_id} is not pending (status={cpo['status']})")
        now = datetime.now(timezone.utc).isoformat()
        cpo.update(
            {
                "status": "rejected",
                "rejected_by": rejected_by,
                "rejected_at": now,
                "rejection_reason": reason.strip(),
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
            outputs={"rejected_by": rejected_by, "reason": reason.strip()},
        )
        return cpo

    def execute(self, cpo_id: str) -> Any:
        from spa.tools.guard import ToolGuard

        cpo = self.get(cpo_id)
        if cpo["status"] != "approved":
            raise ApprovalQueueError(f"CPO {cpo_id} must be approved before execution (status={cpo['status']})")

        guard = ToolGuard(queue=self, audit=self.audit)
        action_type = cpo["action_type"]
        change = cpo.get("proposed_change") or {}

        if action_type == "assign_human":
            result = self._apply_assign_human(change, cpo_id=cpo_id)
        elif action_type == "skill_verifier_escalation":
            result = {"status": "escalation_acknowledged", **change}
            self.audit.emit(
                "cpo_executed",
                task_class="governance",
                risk_class=cpo["action_class"],
                approval_required=False,
                cpo_id=cpo_id,
                outputs=result if isinstance(result, dict) else {"result": result},
                preview=self.build_preview(cpo),
            )
            return result
        elif action_type == "memory_forget":
            from spa.memory.forget import forget_by_id

            target = change.get("target")
            if not target:
                raise ApprovalQueueError("memory_forget CPO missing target in proposed_change")
            result = forget_by_id(target, guard=guard, cpo_id=cpo_id, audit=self.audit)
        elif action_type == "memory_forget_tag":
            from spa.memory.forget import forget_by_tag

            target = change.get("target")
            if not target:
                raise ApprovalQueueError("memory_forget_tag CPO missing target in proposed_change")
            result = forget_by_tag(target, guard=guard, cpo_id=cpo_id, audit=self.audit)
        else:
            tool_name = action_type
            result = guard.execute(
                tool_name,
                lambda: change,
                cpo_id=cpo_id,
            )

        self.audit.emit(
            "cpo_executed",
            task_class="governance",
            risk_class=cpo["action_class"],
            approval_required=False,
            cpo_id=cpo_id,
            outputs=result if isinstance(result, (dict, list, str)) else str(result),
        )
        return result

    def _apply_assign_human(self, change: dict[str, Any], *, cpo_id: str) -> dict[str, Any]:
        from connectors.registry import get_ticket_provider
        from spa.tools.guard import ToolGuard

        assignee = change.get("assignee")
        if not assignee:
            raise ApprovalQueueError("assign_human CPO missing assignee in proposed_change")

        ticket_id = change.get("ticket_id")
        if not ticket_id:
            raise ApprovalQueueError("assign_human CPO missing ticket_id in proposed_change")

        guard = ToolGuard(queue=self, audit=self.audit)
        provider = get_ticket_provider(guard=guard)
        return provider.assign(
            ticket_id,
            assignee,
            cpo_id=cpo_id,
            cpo_approved=True,
            path=change.get("path"),
            status=change.get("status", "assigned"),
        )

    def approve_and_execute(
        self,
        cpo_id: str,
        approved_by: str = "human-reviewer",
    ) -> dict[str, Any]:
        cpo = self.approve(cpo_id, approved_by=approved_by)
        result = self.execute(cpo_id)
        return {"cpo": cpo, "execution_result": result}

    def batch_approve(
        self,
        *,
        action_type: str | None = None,
        max_risk: str = "A3",
        approved_by: str = "human-reviewer",
        execute: bool = True,
    ) -> list[dict[str, Any]]:
        allowed = _allowed_risk_classes(max_risk)
        approved: list[dict[str, Any]] = []
        for cpo in self.list_proposals(status="pending"):
            if cpo["action_class"] not in allowed:
                continue
            if action_type and cpo.get("action_type") != action_type:
                continue
            if execute:
                approved.append(self.approve_and_execute(cpo["id"], approved_by=approved_by))
            else:
                approved.append({"cpo": self.approve(cpo["id"], approved_by=approved_by)})
        return approved

    def is_approved(self, cpo_id: str) -> bool:
        try:
            return self.get(cpo_id)["status"] == "approved"
        except ApprovalQueueError:
            return False
