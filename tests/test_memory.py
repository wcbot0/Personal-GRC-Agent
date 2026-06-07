"""Memory + redaction tests."""
from __future__ import annotations

import json
import builtins

from spa.ingest import ingest_file
from spa.memory.episodic import EpisodicMemory
from spa.memory.redaction import redact_text
from spa.memory.semantic import SemanticMemory


def test_redaction_strips_secrets():
    text = "contact: user@corp.com api_key=SUPER_SECRET_TOKEN_abcdef123456"
    redacted = redact_text(text)
    assert "user@corp.com" not in redacted
    assert "SUPER_SECRET_TOKEN" not in redacted


def test_redaction_preserves_cpo_ids_with_numeric_uuid_segments():
    cpo_id = "cpo-70c53b98-de1c-4ac6-890b-123456789012"
    arn = "arn:aws:cloudtrail:us-east-1:123456789012:trail/org-trail"
    redacted = redact_text(f"{cpo_id} account=123456789012 arn={arn}")

    assert cpo_id in redacted
    assert "account=[REDACTED_ACCOUNT_ID]" in redacted
    assert arn not in redacted


def test_ingest_redacts_before_persist(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SPA_DATA_DIR", str(data_dir))

    # Force offline fallback by mocking Qdrant import failure
    import builtins
    original_import = builtins.__import__

    def fail_qdrant_import(name, *args, **kwargs):
        if name.startswith("qdrant_client"):
            raise ImportError("force offline fallback")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_qdrant_import)

    aws_key = "AKIAIOSFODNN7EXAMPLE"
    bearer_secret = "sk-live-abcdefghijklmnopqrstuvwxyz"
    denylist_secret = "SUPER_SECRET_TOKEN_SHOULD_REDACT"

    fixture = tmp_path / "secret.md"
    fixture.write_text(
        f"aws={aws_key}\n"
        f"auth=Bearer {bearer_secret}\n"
        f"api_key={denylist_secret}\n"
        "notes"
    )

    result = ingest_file(fixture)
    episodic = EpisodicMemory()
    record = episodic.get(result["episodic_id"])
    assert record is not None

    for secret in (aws_key, denylist_secret, bearer_secret, "SUPER_SECRET_TOKEN"):
        assert secret not in record["content"]

    db_bytes = episodic.db_path.read_bytes()
    for secret in (aws_key, denylist_secret, bearer_secret, "SUPER_SECRET_TOKEN"):
        assert secret.encode("utf-8") not in db_bytes

    semantic_path = data_dir / "semantic_fallback.jsonl"
    assert semantic_path.exists(), "semantic store should persist offline fallback"
    semantic_raw = semantic_path.read_text(encoding="utf-8")
    for secret in (aws_key, denylist_secret, bearer_secret, "SUPER_SECRET_TOKEN"):
        assert secret not in semantic_raw


def test_ingest_audit_preview_omits_document_content(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    audit_dir = tmp_path / "audit"
    monkeypatch.setenv("SPA_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SPA_AUDIT_DIR", str(audit_dir))

    # Force offline fallback by mocking Qdrant import failure
    import builtins
    original_import = builtins.__import__

    def fail_qdrant_import(name, *args, **kwargs):
        if name.startswith("qdrant_client"):
            raise ImportError("force offline fallback")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_qdrant_import)

    fixture = tmp_path / "internal.md"
    fixture.write_text("Confidential IAM cleanup notes", encoding="utf-8")

    ingest_file(fixture)

    audit_file = next(audit_dir.glob("audit-*.jsonl"))
    events = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines()]
    ingest_events = [event for event in events if event["event_type"] in {"ingest_start", "ingest_complete"}]

    assert ingest_events
    assert audit_file.stat().st_mode & 0o777 == 0o600
    assert (data_dir / "episodic.db").stat().st_mode & 0o777 == 0o600
    assert (data_dir / "semantic_fallback.jsonl").stat().st_mode & 0o777 == 0o600
    for event in ingest_events:
        assert event["preview"].startswith("content omitted; chars=")
        assert "Confidential IAM cleanup notes" not in event["preview"]


def test_ingest_ticket_audit_preview_omits_ticket_description(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    audit_dir = tmp_path / "audit"
    monkeypatch.setenv("SPA_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SPA_AUDIT_DIR", str(audit_dir))

    sensitive_phrase = "Action: rotate production IAM role"
    fixture = tmp_path / "meeting.md"
    fixture.write_text(
        "# Meeting\n\n"
        "## Decisions\n- Approved access review cadence\n\n"
        "## Risks\n- Risk: stale privileged account\n\n"
        f"## Action items\n- {sensitive_phrase}\n",
        encoding="utf-8",
    )

    ingest_file(fixture)

    audit_file = next(audit_dir.glob("audit-*.jsonl"))
    events = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines()]
    ticket_events = [event for event in events if event["event_type"] == "ticket_draft_created"]

    assert ticket_events
    for event in ticket_events:
        assert event["preview"].startswith("ticket_id=")
        assert sensitive_phrase not in event["preview"]


def test_semantic_offline_fallback_upserts_by_doc_id(tmp_path):
    memory = SemanticMemory()
    memory._offline_mode = True
    memory._local_index_path = tmp_path / "semantic_fallback.jsonl"

    first_id = memory.upsert_document("doc-1", "first version", {"tags": ["ingested"]})
    second_id = memory.upsert_document("doc-1", "second version", {"tags": ["ingested"]})

    assert second_id == first_id
    entries = [
        json.loads(line)
        for line in memory._local_index_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(entries) == 1
    assert entries[0]["content"] == "second version"
    assert memory._local_index_path.stat().st_mode & 0o777 == 0o600


def test_semantic_fallback_existing_file_is_made_private(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    fallback = data_dir / "semantic_fallback.jsonl"
    fallback.write_text("", encoding="utf-8")
    fallback.chmod(0o644)
    monkeypatch.setenv("SPA_DATA_DIR", str(data_dir))

    original_import = builtins.__import__

    def fail_qdrant_import(name, *args, **kwargs):
        if name.startswith("qdrant_client"):
            raise ImportError("force offline fallback")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_qdrant_import)

    SemanticMemory()._get_client()

    assert fallback.stat().st_mode & 0o777 == 0o600
