"""Granola adapter stub — DISABLED in MVP (meeting notes ingestion deferred)."""
from __future__ import annotations

from connectors.interfaces.notes import NotesConnector
from connectors.messages import disabled_post_mvp_message

_DISABLED = disabled_post_mvp_message("granola", "NOTES_PROVIDER")


class GranolaNotesProvider(NotesConnector):
    def __init__(self) -> None:
        super().__init__(provider="granola", enabled=False)

    def read(self, path: str) -> str:
        raise RuntimeError(_DISABLED)

    def list_sources(self) -> list[str]:
        raise RuntimeError(_DISABLED)
