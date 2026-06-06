"""Purge memory by id or tag across episodic + semantic stores."""
from __future__ import annotations

from spa.audit.logger import AuditLogger
from spa.memory.episodic import EpisodicMemory
from spa.memory.semantic import SemanticMemory


def forget_by_id(memory_id: str, audit: AuditLogger | None = None) -> dict[str, bool]:
    audit = audit or AuditLogger()
    episodic = EpisodicMemory()
    semantic = SemanticMemory()
    result = {
        "episodic": episodic.forget_by_id(memory_id),
        "semantic": semantic.forget_by_id(memory_id),
    }
    audit.emit(
        "memory_forget",
        task_class="memory",
        risk_class="A1",
        outputs={"memory_id": memory_id, **result},
    )
    return result


def forget_by_tag(tag: str, audit: AuditLogger | None = None) -> dict[str, int]:
    audit = audit or AuditLogger()
    episodic = EpisodicMemory()
    semantic = SemanticMemory()
    result = {
        "episodic": episodic.forget_by_tag(tag),
        "semantic": semantic.forget_by_tag(tag),
    }
    audit.emit(
        "memory_forget_tag",
        task_class="memory",
        risk_class="A1",
        outputs={"tag": tag, **result},
    )
    return result
