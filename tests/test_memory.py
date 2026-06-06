"""Memory + redaction tests."""
from __future__ import annotations

from spa.ingest import ingest_file
from spa.memory.episodic import EpisodicMemory
from spa.memory.redaction import redact_text


def test_redaction_strips_secrets():
    text = "contact: user@corp.com api_key=SUPER_SECRET_TOKEN_abcdef123456"
    redacted = redact_text(text)
    assert "user@corp.com" not in redacted
    assert "SUPER_SECRET_TOKEN" not in redacted


def test_ingest_redacts_before_persist(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SPA_DATA_DIR", str(data_dir))

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
