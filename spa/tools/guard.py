"""Tool-layer enforcement of autonomy-policy.yaml — A3+ requires CPO + approval."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from spa.governance.approval_queue import ApprovalQueue
from spa.governance.policy import AutonomyPolicy
from spa.audit.logger import AuditLogger


class ToolBlockedError(Exception):
    def __init__(self, message: str, *, cpo_id: str | None = None) -> None:
        super().__init__(message)
        self.cpo_id = cpo_id


@dataclass
class ToolContext:
    tool_name: str
    action_class: str | None = None
    cpo_id: str | None = None
    run_id: str | None = None


class ToolGuard:
    """Wrap tool execution with policy checks and audit emission."""

    def __init__(
        self,
        policy: AutonomyPolicy | None = None,
        queue: ApprovalQueue | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self.policy = policy or AutonomyPolicy.load()
        self.audit = audit or AuditLogger()
        self.queue = queue or ApprovalQueue(audit=self.audit)

    def classify(self, tool_name: str) -> str:
        return self.policy.classify_tool(tool_name)

    def check_allowed(
        self,
        tool_name: str,
        *,
        cpo_id: str | None = None,
        create_cpo: Callable[[], dict[str, Any]] | None = None,
    ) -> ToolContext:
        action_class = self.classify(tool_name)
        ctx = ToolContext(tool_name=tool_name, action_class=action_class, run_id=self.audit.run_id)

        if self.policy.is_blocked(action_class):
            self.audit.emit(
                "tool_blocked",
                task_class="tool",
                risk_class=action_class,
                tools_called=[tool_name],
                approval_required=True,
                outputs={"reason": "A5 blocked by policy"},
            )
            raise ToolBlockedError(f"Tool '{tool_name}' blocked (class {action_class})")

        if self.policy.requires_approval(action_class) or self.policy.block_without_cpo(action_class):
            if not cpo_id:
                if create_cpo is None:
                    raise ToolBlockedError(
                        f"Tool '{tool_name}' requires approved CPO (class {action_class})",
                    )
                cpo = create_cpo()
                cpo_id = cpo["id"]
                raise ToolBlockedError(
                    f"Tool '{tool_name}' blocked pending approval. CPO created: {cpo_id}",
                    cpo_id=cpo_id,
                )
            if not self.queue.is_approved(cpo_id):
                raise ToolBlockedError(
                    f"Tool '{tool_name}' blocked — CPO {cpo_id} not approved",
                    cpo_id=cpo_id,
                )
            ctx.cpo_id = cpo_id

        return ctx

    def execute(
        self,
        tool_name: str,
        fn: Callable[[], Any],
        *,
        cpo_id: str | None = None,
        create_cpo: Callable[[], dict[str, Any]] | None = None,
        preview: str | None = None,
        task_class: str = "tool",
    ) -> Any:
        ctx = self.check_allowed(tool_name, cpo_id=cpo_id, create_cpo=create_cpo)
        action_class = ctx.action_class or "A0"
        self.audit.emit(
            "tool_preview" if preview else "tool_start",
            task_class=task_class,
            risk_class=action_class,
            tools_called=[tool_name],
            approval_required=self.policy.requires_approval(action_class),
            cpo_id=ctx.cpo_id,
            preview=preview,
        )
        result = fn()
        self.audit.emit(
            "tool_complete",
            task_class=task_class,
            risk_class=action_class,
            tools_called=[tool_name],
            cpo_id=ctx.cpo_id,
            outputs=result if isinstance(result, (dict, list, str)) else str(result),
        )
        return result
