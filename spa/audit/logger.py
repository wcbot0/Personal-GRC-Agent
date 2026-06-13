"""Append-only JSONL audit logger with schema validation and redaction."""
from __future__ import annotations

import fcntl
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema

from spa.audit.chain import (
    CHAIN_HEAD_FILENAME,
    GENESIS_HASH,
    compute_event_hash,
    compute_log_tail,
    write_chain_head,
)
from spa.governance.policy import AutonomyPolicy
from spa.memory.redaction import redact_obj
from spa.paths import AUDIT_EVENT_SCHEMA, ensure_private_dir, ensure_private_file, get_audit_logs_dir


class AuditLogger:
    _registry_lock = threading.Lock()
    _dir_thread_locks: dict[str, threading.Lock] = {}

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

    def _dir_thread_lock(self) -> threading.Lock:
        key = str(self.log_dir.resolve())
        with self._registry_lock:
            if key not in self._dir_thread_locks:
                self._dir_thread_locks[key] = threading.Lock()
            return self._dir_thread_locks[key]

    def _acquire_dir_lock(self) -> Any:
        lock_path = self.log_dir / ".emit.lock"
        if not lock_path.exists():
            lock_path.touch(mode=0o600)
        ensure_private_file(lock_path)
        fh = lock_path.open("r+", encoding="utf-8")
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        return fh

    def _release_dir_lock(self, fh: Any) -> None:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()

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
        with self._dir_thread_lock():
            lock_fh = self._acquire_dir_lock()
            try:
                tail_state = compute_log_tail(self.log_dir)
                prev_event_hash = tail_state.event_hash if tail_state.event_hash else GENESIS_HASH
                sequence_number = tail_state.last_sequence + 1

                provenance = self._provenance_defaults()
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
                    "sequence_number": sequence_number,
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
                    fh.flush()
                    os.fsync(fh.fileno())
                write_chain_head(
                    self.log_dir,
                    event_hash=event["event_hash"],
                    event_count=tail_state.event_count + 1,
                    last_sequence=sequence_number,
                )
                head_path = self.log_dir / CHAIN_HEAD_FILENAME
                ensure_private_file(head_path)
                return event
            finally:
                self._release_dir_lock(lock_fh)
