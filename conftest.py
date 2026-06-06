"""Pytest configuration — isolate writable state from the repo tree."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_state_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    audit_dir = tmp_path / "audit"
    monkeypatch.setenv("SPA_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SPA_AUDIT_DIR", str(audit_dir))
