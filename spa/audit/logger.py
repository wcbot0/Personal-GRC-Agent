"""Append-only JSONL audit logger with schema validation and redaction."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from spa.memory.redaction import redact_obj
from spa.paths import AUDIT_EVENT_SCHEMA, get_audit_logs_dir


class AuditLogger:
    def __init__(self, run_id: str | None = None, log_dir: Path | None = None) -> None:
        self.run_id = run_id or str(uuid.uuid4())
        self.log_dir = log_dir or get_audit_logs_dir()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._schema = json.loads(AUDIT_EVENT_SCHEMA.read_text())

    def _log_path(self) -> Path:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.log_dir / f"audit-{day}.jsonl"

    def emit(
        self,
        event_type: str,
        *,
        task_class: str = "general",
        risk_class: str = "A0",
        user_request: str | None = None,
        retrieved_memory_ids: list[str] | None = None,
        tools_called: list[str] | None = None,
        approval_required: bool = False,
        cpo_id: str | None = None,
        outputs: Any = None,
        verifications: list[dict[str, Any]] | None = None,
        preview: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "user_request": user_request,
            "task_class": task_class,
            "risk_class": risk_class,
            "retrieved_memory_ids": retrieved_memory_ids or [],
            "tools_called": tools_called or [],
            "approval_required": approval_required,
            "cpo_id": cpo_id,
            "outputs": outputs,
            "verifications": verifications or [],
            "preview": preview,
            "metadata": metadata or {},
        }
        event = redact_obj(event)
        jsonschema.validate(event, self._schema)
        with self._log_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event
