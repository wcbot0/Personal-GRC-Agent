"""Skill file write helpers routed through ToolGuard when available."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from spa.tools.write import guarded_write


def write_text_file(
    context: dict[str, Any] | None,
    tool_name: str,
    path: Path,
    content: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    guard = (context or {}).get("guard")
    if guard is None:
        path.write_text(content, encoding="utf-8")
        return

    guarded_write(
        guard,
        tool_name,
        lambda: path.write_text(content, encoding="utf-8"),
        preview=path.name,
    )
