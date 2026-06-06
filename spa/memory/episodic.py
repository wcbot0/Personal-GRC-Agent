"""SQLite + FTS5 episodic memory store."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from spa.memory.redaction import redact_obj, redact_text
from spa.paths import MEMORY_OBJECT_SCHEMA, get_data_dir


class EpisodicMemory:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or (get_data_dir() / "episodic.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._schema = json.loads(MEMORY_OBJECT_SCHEMA.read_text())
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_objects (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    source TEXT,
                    sensitivity TEXT,
                    ttl TEXT,
                    framework_tags TEXT,
                    related_objects TEXT,
                    confidence REAL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    tags TEXT
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    id UNINDEXED,
                    content,
                    tags,
                    source,
                    tokenize='porter'
                );
                """
            )

    def write(self, obj: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": obj.get("id") or str(uuid.uuid4()),
            "type": obj.get("type", "episodic"),
            "source": obj.get("source", "unknown"),
            "sensitivity": obj.get("sensitivity", "internal"),
            "ttl": obj.get("ttl"),
            "framework_tags": obj.get("framework_tags", []),
            "related_objects": obj.get("related_objects", []),
            "confidence": obj.get("confidence", 1.0),
            "content": redact_text(str(obj.get("content", ""))),
            "created_at": obj.get("created_at", now),
            "tags": obj.get("tags", []),
        }
        record = redact_obj(record)
        jsonschema.validate(record, self._schema)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_objects
                (id, type, source, sensitivity, ttl, framework_tags, related_objects,
                 confidence, content, created_at, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["type"],
                    record["source"],
                    record["sensitivity"],
                    record["ttl"],
                    json.dumps(record["framework_tags"]),
                    json.dumps(record["related_objects"]),
                    record["confidence"],
                    record["content"],
                    record["created_at"],
                    json.dumps(record["tags"]),
                ),
            )
            conn.execute("DELETE FROM memory_fts WHERE id = ?", (record["id"],))
            conn.execute(
                "INSERT INTO memory_fts (id, content, tags, source) VALUES (?, ?, ?, ?)",
                (
                    record["id"],
                    record["content"],
                    " ".join(record["tags"]),
                    record["source"],
                ),
            )
        return record

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT m.* FROM memory_fts f
                JOIN memory_objects m ON m.id = f.id
                WHERE memory_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get(self, memory_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM memory_objects WHERE id = ?", (memory_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def forget_by_id(self, memory_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM memory_objects WHERE id = ?", (memory_id,))
            conn.execute("DELETE FROM memory_fts WHERE id = ?", (memory_id,))
        return cur.rowcount > 0

    def forget_by_tag(self, tag: str) -> int:
        removed = 0
        with self._connect() as conn:
            rows = conn.execute("SELECT id, tags FROM memory_objects").fetchall()
            for row in rows:
                tags = json.loads(row["tags"] or "[]")
                if tag in tags:
                    conn.execute("DELETE FROM memory_objects WHERE id = ?", (row["id"],))
                    conn.execute("DELETE FROM memory_fts WHERE id = ?", (row["id"],))
                    removed += 1
        return removed

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "type": row["type"],
            "source": row["source"],
            "sensitivity": row["sensitivity"],
            "ttl": row["ttl"],
            "framework_tags": json.loads(row["framework_tags"] or "[]"),
            "related_objects": json.loads(row["related_objects"] or "[]"),
            "confidence": row["confidence"],
            "content": row["content"],
            "created_at": row["created_at"],
            "tags": json.loads(row["tags"] or "[]"),
        }
