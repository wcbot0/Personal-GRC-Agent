"""File-only GRC provider (MVP default)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from connectors.interfaces.grc import GrcCapabilities, GrcConnector
from spa.paths import get_proposals_dir


class NoneGrcProvider(GrcConnector):
    def __init__(self) -> None:
        super().__init__(
            provider="none",
            enabled=True,
            capabilities=GrcCapabilities(read_controls=False, write_evidence=False),
            gated_capabilities=["write_evidence", "publish_policy"],
        )
        self.out_dir = get_proposals_dir() / "grc"

    def read_controls(self) -> list[dict[str, Any]]:
        return []

    def draft_evidence(self, control_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / f"evidence-draft-{control_id.replace('.', '-')}.json"
        doc = {"control_id": control_id, "status": "draft", **payload}
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return {"provider": "none", "path": str(path), "document": doc}
