"""Audit hash chain and evidence export tests."""
from __future__ import annotations

import hashlib
import json
import tarfile
import threading
from datetime import date
from pathlib import Path

import pytest

from spa.audit.chain import GENESIS_HASH, compute_event_hash, verify_chain
from spa.audit.logger import AuditLogger
from spa.evidence.export import export_evidence


def test_emit_three_events_verifies_chain(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    logger = AuditLogger(log_dir=audit_dir)
    for idx in range(3):
        logger.emit("test_event", task_class="test", risk_class="A0", preview=f"event-{idx}")

    result = verify_chain(audit_dir)
    assert result.valid
    assert result.event_count == 3
    assert result.chain_starts == 1


def test_tampered_event_breaks_chain(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    logger = AuditLogger(log_dir=audit_dir)
    logger.emit("one", task_class="test", risk_class="A0")
    logger.emit("two", task_class="test", risk_class="A0")

    log_file = next(audit_dir.glob("audit-*.jsonl"))
    lines = log_file.read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[1])
    event["preview"] = "tampered"
    lines[1] = json.dumps(event)
    log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = verify_chain(audit_dir)
    assert not result.valid
    assert result.breaks
    assert "event_hash" in result.breaks[0].reason


def test_legacy_events_fail_by_default(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    log_file = audit_dir / "audit-2026-06-05.jsonl"
    audit_dir.mkdir(parents=True)
    legacy = {
        "event_id": "legacy-1",
        "run_id": "r1",
        "timestamp": "2026-06-05T10:00:00+00:00",
        "event_type": "old",
        "task_class": "test",
        "risk_class": "A0",
    }
    log_file.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

    logger = AuditLogger(log_dir=audit_dir)
    logger.emit("new", task_class="test", risk_class="A0")

    result = verify_chain(audit_dir)
    assert not result.valid
    assert result.legacy_count == 1
    assert any("legacy event without hash" in b.reason for b in result.breaks)


def test_legacy_events_warn_but_allow_new_chain(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    log_file = audit_dir / "audit-2026-06-05.jsonl"
    audit_dir.mkdir(parents=True)
    legacy = {"event_id": "legacy-1", "run_id": "r1", "timestamp": "2026-06-05T10:00:00+00:00",
              "event_type": "old", "task_class": "test", "risk_class": "A0"}
    log_file.write_text(json.dumps(legacy) + "\n", encoding="utf-8")

    logger = AuditLogger(log_dir=audit_dir)
    logger.emit("new", task_class="test", risk_class="A0")

    result = verify_chain(audit_dir, require_full_chain=False)
    assert result.valid
    assert result.legacy_count == 1
    assert result.chain_starts == 1
    assert result.warnings


def test_date_filtered_verify_uses_prior_chain_head(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir(parents=True)

    event1 = {
        "event_id": "evt-1",
        "run_id": "run-1",
        "timestamp": "2026-06-05T12:00:00+00:00",
        "event_type": "day_one",
        "task_class": "test",
        "risk_class": "A0",
        "retrieved_memory_ids": [],
        "tools_called": [],
        "approval_required": False,
        "cpo_id": None,
        "outputs": None,
        "verifications": [],
        "preview": None,
        "metadata": {},
        "prev_event_hash": GENESIS_HASH,
        "policy_version": "1.0",
        "model_id": "stub",
        "runtime": "local",
        "input_sha256": None,
        "artifact_refs": [],
    }
    event1["event_hash"] = compute_event_hash(event1)
    (audit_dir / "audit-2026-06-05.jsonl").write_text(json.dumps(event1) + "\n", encoding="utf-8")

    event2 = {
        "event_id": "evt-2",
        "run_id": "run-2",
        "timestamp": "2026-06-06T12:00:00+00:00",
        "event_type": "day_two",
        "task_class": "test",
        "risk_class": "A0",
        "retrieved_memory_ids": [],
        "tools_called": [],
        "approval_required": False,
        "cpo_id": None,
        "outputs": None,
        "verifications": [],
        "preview": None,
        "metadata": {},
        "prev_event_hash": event1["event_hash"],
        "policy_version": "1.0",
        "model_id": "stub",
        "runtime": "local",
        "input_sha256": None,
        "artifact_refs": [],
    }
    event2["event_hash"] = compute_event_hash(event2)
    (audit_dir / "audit-2026-06-06.jsonl").write_text(json.dumps(event2) + "\n", encoding="utf-8")

    result = verify_chain(audit_dir, start=date(2026, 6, 6), end=date(2026, 6, 6))
    assert result.valid
    assert result.event_count == 1

    manifest = export_evidence(
        output=tmp_path / "bundle-day2.tar.gz",
        audit_dir=audit_dir,
        queue_dir=tmp_path / "queue",
        start=date(2026, 6, 6),
        end=date(2026, 6, 6),
    )
    assert manifest["chain_verification"]["valid"]
    assert any(entry["path"] == "manifest.json" for entry in manifest["files"])


def test_date_filtered_verify_rejects_tampered_pre_window_anchor(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir(parents=True)

    event1 = {
        "event_id": "evt-1",
        "run_id": "run-1",
        "timestamp": "2026-06-05T12:00:00+00:00",
        "event_type": "day_one",
        "task_class": "test",
        "risk_class": "A0",
        "retrieved_memory_ids": [],
        "tools_called": [],
        "approval_required": False,
        "cpo_id": None,
        "outputs": None,
        "verifications": [],
        "preview": "tampered",
        "metadata": {},
        "prev_event_hash": GENESIS_HASH,
        "policy_version": "1.0",
        "model_id": "stub",
        "runtime": "local",
        "input_sha256": None,
        "artifact_refs": [],
        "event_hash": "deadbeef",
    }
    (audit_dir / "audit-2026-06-05.jsonl").write_text(json.dumps(event1) + "\n", encoding="utf-8")

    event2 = {
        "event_id": "evt-2",
        "run_id": "run-2",
        "timestamp": "2026-06-06T12:00:00+00:00",
        "event_type": "day_two",
        "task_class": "test",
        "risk_class": "A0",
        "retrieved_memory_ids": [],
        "tools_called": [],
        "approval_required": False,
        "cpo_id": None,
        "outputs": None,
        "verifications": [],
        "preview": None,
        "metadata": {},
        "prev_event_hash": "deadbeef",
        "policy_version": "1.0",
        "model_id": "stub",
        "runtime": "local",
        "input_sha256": None,
        "artifact_refs": [],
    }
    event2["event_hash"] = compute_event_hash(event2)
    (audit_dir / "audit-2026-06-06.jsonl").write_text(json.dumps(event2) + "\n", encoding="utf-8")

    result = verify_chain(audit_dir, start=date(2026, 6, 6), end=date(2026, 6, 6))
    assert not result.valid
    assert result.breaks


def test_evidence_export_bundle_manifest(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir(parents=True)
    logger = AuditLogger(log_dir=audit_dir)
    logger.emit("skill_complete", task_class="skill", risk_class="A1")

    bundle = tmp_path / "bundle.tar.gz"
    manifest = export_evidence(
        output=bundle,
        audit_dir=audit_dir,
        queue_dir=queue_dir,
        start=date(2026, 1, 1),
        end=date(2099, 12, 31),
    )
    assert bundle.exists()
    assert manifest["audit_event_count"] >= 1
    assert manifest["chain_verification"]["valid"]
    assert any(entry["path"] == "manifest.json" for entry in manifest["files"])

    with tarfile.open(bundle, "r:gz") as tar:
        names = tar.getnames()
    assert any(name.endswith("manifest.json") for name in names)


def test_evidence_manifest_self_hash_matches_on_disk(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    logger = AuditLogger(log_dir=audit_dir)
    logger.emit("skill_complete", task_class="skill", risk_class="A1")

    bundle = tmp_path / "bundle.tar.gz"
    manifest = export_evidence(
        output=bundle,
        audit_dir=audit_dir,
        queue_dir=tmp_path / "queue",
    )

    manifest_entry = next(entry for entry in manifest["files"] if entry["path"] == "manifest.json")
    manifest_without_self = {**manifest, "files": [f for f in manifest["files"] if f["path"] != "manifest.json"]}
    expected_self_hash = hashlib.sha256(json.dumps(manifest_without_self, indent=2).encode("utf-8")).hexdigest()
    assert manifest_entry["sha256"] == expected_self_hash


def test_tail_truncation_breaks_chain(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    logger = AuditLogger(log_dir=audit_dir)
    for idx in range(3):
        logger.emit("test_event", task_class="test", risk_class="A0", preview=f"event-{idx}")

    log_file = next(audit_dir.glob("audit-*.jsonl"))
    lines = log_file.read_text(encoding="utf-8").splitlines()
    log_file.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

    result = verify_chain(audit_dir)
    assert not result.valid
    assert any("count mismatch" in b.reason for b in result.breaks)


def test_malformed_line_recorded_as_break(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir(parents=True)
    log_file = audit_dir / "audit-2026-06-07.jsonl"
    log_file.write_text("not-json\n", encoding="utf-8")

    result = verify_chain(audit_dir)
    assert not result.valid
    assert any("invalid JSON" in b.reason for b in result.breaks)


def test_emit_reconciles_stale_head_against_log_tail(tmp_path: Path):
    from spa.audit.chain import CHAIN_HEAD_FILENAME, compute_log_tail

    audit_dir = tmp_path / "audit"
    logger = AuditLogger(log_dir=audit_dir)
    logger.emit("one", task_class="test", risk_class="A0")
    logger.emit("two", task_class="test", risk_class="A0")
    logger.emit("three", task_class="test", risk_class="A0")

    real_tail = compute_log_tail(audit_dir)

    head_path = audit_dir / CHAIN_HEAD_FILENAME
    stale = json.loads(head_path.read_text(encoding="utf-8"))
    stale["event_hash"] = "stale" + "0" * 59
    stale["event_count"] = stale["event_count"] - 1
    stale["last_sequence"] = stale["last_sequence"] - 1
    head_path.write_text(json.dumps(stale, sort_keys=True) + "\n", encoding="utf-8")

    new_event = logger.emit("four", task_class="test", risk_class="A0")

    assert new_event["prev_event_hash"] == real_tail.event_hash
    assert new_event["sequence_number"] == real_tail.last_sequence + 1

    result = verify_chain(audit_dir)
    assert result.valid
    assert result.event_count == 4
    assert result.chain_starts == 1


def test_emit_reconciles_head_after_log_only_write(tmp_path: Path):
    from spa.audit.chain import CHAIN_HEAD_FILENAME, compute_log_tail

    audit_dir = tmp_path / "audit"
    logger = AuditLogger(log_dir=audit_dir)
    first = logger.emit("one", task_class="test", risk_class="A0")

    log_file = next(audit_dir.glob("audit-*.jsonl"))
    second = dict(first)
    second["event_id"] = "evt-crashed"
    second["prev_event_hash"] = first["event_hash"]
    second["sequence_number"] = first["sequence_number"] + 1
    second.pop("event_hash")
    second["event_hash"] = compute_event_hash(second)
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(second) + "\n")

    real_tail = compute_log_tail(audit_dir)
    assert real_tail.event_hash == second["event_hash"]

    third = logger.emit("three", task_class="test", risk_class="A0")
    assert third["prev_event_hash"] == second["event_hash"]
    assert third["sequence_number"] == second["sequence_number"] + 1

    head = json.loads((audit_dir / CHAIN_HEAD_FILENAME).read_text(encoding="utf-8"))
    assert head["event_hash"] == third["event_hash"]
    assert head["event_count"] == 3

    result = verify_chain(audit_dir)
    assert result.valid
    assert result.event_count == 3


def test_concurrent_emit_maintains_chain(tmp_path: Path):
    audit_dir = tmp_path / "audit"
    logger = AuditLogger(log_dir=audit_dir)
    errors: list[Exception] = []

    def emit_many() -> None:
        try:
            for idx in range(10):
                logger.emit("concurrent", task_class="test", risk_class="A0", preview=f"evt-{idx}")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=emit_many) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    result = verify_chain(audit_dir)
    assert result.valid
    assert result.event_count == 20
