"""Central guarded write entry point for filesystem and connector mutations."""
from __future__ import annotations

from typing import Any, Callable

from spa.tools.guard import ToolGuard


def guarded_write(
    guard: ToolGuard,
    tool_name: str,
    fn: Callable[[], Any],
    *,
    preview: str | None = None,
    cpo_id: str | None = None,
    create_cpo: Callable[[], dict[str, Any]] | None = None,
    audit_outputs: Callable[[Any], Any] | None = None,
) -> Any:
    return guard.execute(
        tool_name,
        fn,
        preview=preview,
        task_class="write",
        cpo_id=cpo_id,
        create_cpo=create_cpo,
        audit_outputs=audit_outputs,
    )
