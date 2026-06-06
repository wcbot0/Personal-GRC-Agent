"""Purge memory by id or tag across episodic + semantic stores."""
from __future__ import annotations

from typing import Any, Callable

from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import ApprovalQueue
from spa.memory.episodic import EpisodicMemory
from spa.memory.semantic import SemanticMemory
from spa.tools.guard import ToolGuard
from spa.tools.write import guarded_write


def _forget_cpo_factory(queue: ApprovalQueue, action_type: str, target: str) -> Callable[[], dict[str, Any]]:
    def _create() -> dict[str, Any]:
        return queue.create(
            action_class="A4",
            action_type=action_type,
            title=f"Memory forget: {target}",
            description=f"Authorized deletion of memory target {target}",
            risk_rationale="Memory deletion is an authoritative record change",
            proposed_change={"target": target, "action_type": action_type},
        )

    return _create


def forget_by_id(
    memory_id: str,
    *,
    guard: ToolGuard | None = None,
    cpo_id: str | None = None,
    audit: AuditLogger | None = None,
) -> dict[str, bool]:
    audit = audit or AuditLogger()
    guard = guard or ToolGuard(audit=audit)

    def _forget() -> dict[str, bool]:
        episodic = EpisodicMemory()
        semantic = SemanticMemory()
        result = {
            "episodic": episodic.forget_by_id(memory_id),
            "semantic": semantic.forget_by_id(memory_id),
        }
        guard.audit.emit(
            "memory_forget",
            task_class="memory",
            risk_class="A4",
            cpo_id=cpo_id,
            outputs={"memory_id": memory_id, **result},
        )
        return result

    return guarded_write(
        guard,
        "memory_forget",
        _forget,
        cpo_id=cpo_id,
        create_cpo=_forget_cpo_factory(guard.queue, "memory_forget", memory_id) if not cpo_id else None,
    )


def forget_by_tag(
    tag: str,
    *,
    guard: ToolGuard | None = None,
    cpo_id: str | None = None,
    audit: AuditLogger | None = None,
) -> dict[str, int]:
    audit = audit or AuditLogger()
    guard = guard or ToolGuard(audit=audit)

    def _forget() -> dict[str, int]:
        episodic = EpisodicMemory()
        semantic = SemanticMemory()
        result = {
            "episodic": episodic.forget_by_tag(tag),
            "semantic": semantic.forget_by_tag(tag),
        }
        guard.audit.emit(
            "memory_forget_tag",
            task_class="memory",
            risk_class="A4",
            cpo_id=cpo_id,
            outputs={"tag": tag, **result},
        )
        return result

    return guarded_write(
        guard,
        "memory_forget_tag",
        _forget,
        cpo_id=cpo_id,
        create_cpo=_forget_cpo_factory(guard.queue, "memory_forget_tag", tag) if not cpo_id else None,
    )
