"""Redaction rule and engine tests."""
from __future__ import annotations

import re

import pytest
import yaml

from spa.memory import redaction as redaction_module
from spa.memory.redaction import _load_rules, redact_text
from spa.paths import REDACTION_RULES


def test_redaction_rules_yaml_compiles():
    rules = yaml.safe_load(REDACTION_RULES.read_text())
    for entry in rules["regex_patterns"]:
        re.compile(entry["pattern"])


def test_redact_short_password():
    redacted = redact_text("password: hunter2")
    assert "hunter2" not in redacted
    assert "[REDACTED_SECRET]" in redacted


def test_redact_github_gitlab_slack_jwt_tokens():
    samples = {
        "ghp_abcdefghijklmnopqrstuvwxyz1234567890AB": "[REDACTED_GITHUB_TOKEN]",
        "glpat-abcdefghijklmnopqrst": "[REDACTED_GITLAB_TOKEN]",
        "xoxb-1234567890-abcdefghij": "[REDACTED_SLACK_TOKEN]",
        "xapp-1-A0123456789-abcdefghij": "[REDACTED_SLACK_TOKEN]",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U": "[REDACTED_JWT]",
    }
    for sample, placeholder in samples.items():
        redacted = redact_text(sample)
        assert sample not in redacted
        assert placeholder in redacted


def test_redact_db_and_url_embedded_credentials():
    redacted = redact_text("postgresql://dbuser:dbpass@localhost/app")
    assert "dbuser:dbpass" not in redacted
    assert "postgresql://[REDACTED_CREDS]@" in redacted

    redacted = redact_text("http://admin:secret@internal-host/app")
    assert "admin:secret" not in redacted
    assert "http://[REDACTED_CREDENTIALS]@" in redacted


def test_denylist_replace_is_case_insensitive():
    redacted = redact_text("prefix super_secret_token suffix")
    assert "super_secret_token" not in redacted.lower()
    assert "[REDACTED_DENYLIST]" in redacted


def test_load_rules_cached_by_mtime(monkeypatch):
    redaction_module._rules_cache = None
    redaction_module._rules_cache_mtime = None

    first = _load_rules()
    second = _load_rules()
    assert first is second


def test_load_rules_missing_file_raises(tmp_path, monkeypatch):
    redaction_module._rules_cache = None
    redaction_module._rules_cache_mtime = None
    missing = tmp_path / "missing-redaction-rules.yaml"
    monkeypatch.setattr(redaction_module, "REDACTION_RULES", missing)
    with pytest.raises(FileNotFoundError):
        _load_rules()
