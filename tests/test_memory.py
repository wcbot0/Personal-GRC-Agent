"""Memory + redaction tests."""
from __future__ import annotations

import tempfile
from pathlib import Path

from spa.ingest import ingest_file
from spa.memory.episodic import EpisodicMemory
from spa.memory.redaction import redact_text


def test_redaction_strips_secrets():
    text = "contact: user@corp.com api_key=SUPER_SECRET_TOKEN_abcdef123456"
    redacted = redact_text(text)
    assert "user@corp.com" not in redacted
    assert "SUPER_SECRET_TOKEN" not in redacted


def test_ingest_redacts_before_persist(tmp_path):
    fixture = tmp_path / "secret.md"
    fixture.write_text("api_key=SUPER_SECRET_TOKEN_SHOULD_REDACT\nnotes")
    result = ingest_file(fixture)
    episodic = EpisodicMemory()
    record = episodic.get(result["episodic_id"])
    assert record is not None
    assert "SUPER_SECRET_TOKEN" not in record["content"]
