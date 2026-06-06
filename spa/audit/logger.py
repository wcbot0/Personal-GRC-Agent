"""Append-only JSONL audit logger with schema validation and redaction."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from spa.audit.chain import GENESIS_HASH, compute_event_hash, load_chain_head
from spa.governance.policy import AutonomyPolicy
from spa.memory.redaction import redact_obj
from spa.paths import AUDIT_EVENT_SCHEMA, ensure_private_dir, ensure_private_file, get_audit_logs_dir


class AuditLogger:
    def __init__(self, run_id: str | None = None, log_dir: Path | None = None) -> None:
        self.run_id = run_id or str(uuid.uuid4())
        self.log_dir = log_dir or get_audit_logs_dir()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        ensure_private_dir(self.log_dir)
        self._schema = json.loads(AUDIT_EVENT_SCHEMA.read_text())

    def _log_path(self) -> Path:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.log_dir / f"audit-{day}.jsonl"

    def _provenance_defaults(self) -> dict[str, Any]:
        try:
            policy_version = AutonomyPolicy.load().version
        except Exception:  # noqa: BLE001
            policy_version = None
        return {
            "policy_version": policy_version,
            "model_id": os.environ.get("LLM_MODEL", "stub"),
            "runtime": os.environ.get("SPA_RUNTIME", "local"),
        }

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
        input_sha256: str | None = None,
        artifact_refs: list[str] | None = None,
    ) -> dict[str, Any]:
        provenance = self._provenance_defaults()
        prev_head = load_chain_head(self.log_dir)
        prev_event_hash = prev_head if prev_head else GENESIS_HASH

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
            "prev_event_hash": prev_event_hash,
            "policy_version": provenance["policy_version"],
            "model_id": provenance["model_id"],
            "runtime": provenance["runtime"],
            "input_sha256": input_sha256,
            "artifact_refs": artifact_refs or [],
        }
        event = redact_obj(event)
        event["event_hash"] = compute_event_hash(event)
        jsonschema.validate(event, self._schema)
        log_path = self._log_path()
        if not log_path.exists():
            log_path.touch(mode=0o600)
        ensure_private_file(log_path)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event
