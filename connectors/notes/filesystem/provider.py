"""Filesystem notes provider — reads brain/ and inbox/."""
from __future__ import annotations

from pathlib import Path

from connectors.interfaces.notes import NotesConnector
from spa.paths import BRAIN_DIR, INBOX_DIR, ROOT


class FilesystemNotesProvider(NotesConnector):
    _READ_ROOTS = (BRAIN_DIR, INBOX_DIR)

    def __init__(self) -> None:
        super().__init__(provider="filesystem", enabled=True)

    def read(self, path: str) -> str:
        p = Path(path)
        if not p.is_absolute():
            p = ROOT / p
        resolved = p.resolve()
        roots = tuple(r.resolve() for r in self._READ_ROOTS)
        if not any(resolved.is_relative_to(r) for r in roots):
            allowed = ", ".join(str(r.relative_to(ROOT)) for r in roots)
            raise ValueError(f"path must be under one of: {allowed}")
        return resolved.read_text(encoding="utf-8", errors="replace")

    def list_sources(self) -> list[str]:
        sources = []
        for base in (BRAIN_DIR, INBOX_DIR):
            if base.exists():
                for f in base.rglob("*.md"):
                    sources.append(str(f.relative_to(ROOT)))
        return sorted(sources)
