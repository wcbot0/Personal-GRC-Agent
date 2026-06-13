"""Tests for spa init --runtime."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from spa.audit.logger import AuditLogger
from spa.paths import ROOT
from spa.runtime_init import VALID_RUNTIMES, init_runtime, planned_files
from spa.tools.guard import ToolGuard


@pytest.fixture
def mini_repo(tmp_path):
    """Minimal PGA-like repo root for init tests."""
    for name in ("AGENTS.md", "agent/charter.md", "agent/autonomy-policy.yaml"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name == "AGENTS.md":
            path.write_text("# AGENTS\n", encoding="utf-8")
        else:
            shutil.copy(ROOT / name, path)

    venv_spa = tmp_path / ".venv" / "bin" / "spa"
    venv_spa.parent.mkdir(parents=True, exist_ok=True)
    venv_spa.write_text("#!/bin/sh\necho spa\n", encoding="utf-8")
    venv_spa.chmod(0o755)

    setup = tmp_path / "scripts" / "setup-hermes.sh"
    setup.parent.mkdir(parents=True, exist_ok=True)
    setup.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    setup.chmod(0o755)
    return tmp_path


@pytest.fixture
def init_guard(tmp_path, monkeypatch):
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    monkeypatch.setenv("SPA_AUDIT_DIR", str(audit_dir))
    return ToolGuard(audit=AuditLogger(log_dir=audit_dir))


@pytest.mark.parametrize("runtime", VALID_RUNTIMES)
def test_each_profile_generates_expected_files(mini_repo, init_guard, runtime):
    if runtime == "hermes":
        with patch("spa.runtime_init.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            result = init_runtime(runtime, root=mini_repo, guard=init_guard)
    else:
        result = init_runtime(runtime, root=mini_repo, guard=init_guard)

    planned = planned_files(runtime, mini_repo)
    for rel in planned:
        assert (mini_repo / rel).is_file(), f"missing {rel} for {runtime}"
    assert not result.errors or runtime == "hermes"


@pytest.mark.parametrize("runtime", ["cursor", "claude", "chatgpt", "openclaw"])
def test_idempotent_second_run_no_diff(mini_repo, init_guard, runtime):
    init_runtime(runtime, root=mini_repo, guard=init_guard)
    before = {rel: (mini_repo / rel).read_text(encoding="utf-8") for rel in planned_files(runtime, mini_repo)}
    result = init_runtime(runtime, root=mini_repo, guard=init_guard)
    after = {rel: (mini_repo / rel).read_text(encoding="utf-8") for rel in planned_files(runtime, mini_repo)}
    assert before == after
    assert not result.written


def test_check_detects_drift(mini_repo, init_guard):
    init_runtime("cursor", root=mini_repo, guard=init_guard)
    mcp = mini_repo / ".cursor" / "mcp.json"
    mcp.write_text("{}", encoding="utf-8")
    result = init_runtime("cursor", root=mini_repo, guard=init_guard, check=True)
    assert result.errors


def test_check_passes_when_fresh(mini_repo, init_guard):
    init_runtime("claude", root=mini_repo, guard=init_guard)
    result = init_runtime("claude", root=mini_repo, guard=init_guard, check=True)
    assert not result.errors


def test_dry_run_does_not_write(mini_repo, init_guard):
    result = init_runtime("cursor", root=mini_repo, guard=init_guard, dry_run=True)
    assert result.written
    assert not (mini_repo / ".cursor" / "mcp.json").exists()


def test_unknown_runtime_raises():
    with pytest.raises(ValueError, match="Unknown runtime"):
        init_runtime("vscode")


def test_generated_mcp_references_spa_mcp_serve(mini_repo, init_guard):
    init_runtime("cursor", root=mini_repo, guard=init_guard)
    payload = json.loads((mini_repo / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
    server = payload["mcpServers"]["pga-governed"]
    assert server["args"] == ["mcp", "serve"]
    assert "spa" in server["command"]
