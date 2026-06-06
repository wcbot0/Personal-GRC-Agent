#!/usr/bin/env python3
"""Seed brain/ Markdown and YAML into semantic memory (Qdrant)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    brain_dir = ROOT / "brain"
    if not brain_dir.exists():
        print("[seed_brain] brain/ not found; nothing to seed")
        return 0

    try:
        from spa.memory.semantic import SemanticMemory
        from spa.memory.redaction import redact_text

        mem = SemanticMemory()
        count = 0
        for path in sorted(brain_dir.rglob("*")):
            if not path.is_file() or path.suffix not in {".md", ".yaml", ".yml"}:
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            content = redact_text(content)
            mem.upsert_document(
                doc_id=str(path.relative_to(ROOT)),
                content=content,
                metadata={
                    "source": str(path.relative_to(ROOT)),
                    "type": "brain",
                    "sensitivity": "internal",
                },
            )
            count += 1
        print(f"[seed_brain] Seeded {count} brain documents")
        return 0
    except Exception as exc:  # noqa: BLE001 — bootstrap tolerance
        print(f"[seed_brain] Seed deferred: {exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
