"""Autonomy policy fail-closed and reload tests."""
from __future__ import annotations

import time
from pathlib import Path

import pytest
import yaml

from spa.governance.policy import AutonomyPolicy, PolicyError
from spa.paths import AUTONOMY_POLICY


@pytest.fixture(autouse=True)
def _clear_policy_cache():
    AutonomyPolicy.clear_cache()
    yield
    AutonomyPolicy.clear_cache()


def test_unknown_action_class_is_blocked_and_requires_approval():
    policy = AutonomyPolicy.load()
    assert not policy.is_blocked("a3")
    assert policy.is_blocked(" A3X ")
    assert policy.is_blocked("bogus")
    assert policy.requires_approval("bogus")
    assert policy.block_without_cpo(" A3X ")


def test_classify_tool_unknown_defaults_to_a5():
    policy = AutonomyPolicy.load()
    assert policy.classify_tool("totally_unknown_tool_xyz") == "A5"


def test_invalid_tool_mapping_raises_policy_error(tmp_path: Path, monkeypatch):
    data = yaml.safe_load(AUTONOMY_POLICY.read_text())
    data["tool_mappings"]["bad_tool"] = "A9"
    bad_policy = tmp_path / "autonomy-policy.yaml"
    bad_policy.write_text(yaml.dump(data), encoding="utf-8")
    monkeypatch.setattr("spa.governance.policy.AUTONOMY_POLICY", bad_policy)

    with pytest.raises(PolicyError, match="undefined class"):
        AutonomyPolicy.load()


def test_non_blocked_unknown_tool_class_raises_policy_error(tmp_path: Path, monkeypatch):
    data = yaml.safe_load(AUTONOMY_POLICY.read_text())
    data["defaults"]["unknown_tool_class"] = "A1"
    bad_policy = tmp_path / "autonomy-policy.yaml"
    bad_policy.write_text(yaml.dump(data), encoding="utf-8")
    monkeypatch.setattr("spa.governance.policy.AUTONOMY_POLICY", bad_policy)

    with pytest.raises(PolicyError, match="must have approval: blocked"):
        AutonomyPolicy.load()


def test_policy_reloads_when_mtime_changes(tmp_path: Path, monkeypatch):
    copy = tmp_path / "autonomy-policy.yaml"
    copy.write_text(AUTONOMY_POLICY.read_text(), encoding="utf-8")
    monkeypatch.setattr("spa.governance.policy.AUTONOMY_POLICY", copy)

    first = AutonomyPolicy.load()
    assert first.version == "1.0"

    time.sleep(0.05)
    data = yaml.safe_load(copy.read_text())
    data["version"] = "1.1"
    copy.write_text(yaml.dump(data), encoding="utf-8")

    second = AutonomyPolicy.load()
    assert second.version == "1.1"
    assert second is not first
