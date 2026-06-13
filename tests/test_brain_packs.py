"""Brain pack install tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from spa.brain_packs import BrainPackError, check_packs, install_pack, list_available_packs


@pytest.fixture
def pack_env(tmp_path: Path, monkeypatch):
    brain = tmp_path / "brain"
    packs = brain / "packs" / "iso-42001"
    packs.mkdir(parents=True)
    (packs / "pack.yaml").write_text(
        yaml.dump({"name": "iso-42001", "version": "2023", "source": "ISO test"}),
        encoding="utf-8",
    )
    (packs / "overview.md").write_text("# ISO overview\n", encoding="utf-8")
    standards = brain / "04-standards"
    standards.mkdir(parents=True)
    monkeypatch.setattr("spa.brain_packs.BRAIN_DIR", brain)
    monkeypatch.setattr("spa.brain_packs.PACKS_SOURCE_DIR", brain / "packs")
    monkeypatch.setattr("spa.brain_packs.STANDARDS_DIR", standards)
    return brain, standards


def test_list_available_packs(pack_env):
    assert "iso-42001" in list_available_packs()


def test_install_pack_idempotent(pack_env):
    _, standards = pack_env
    with patch("scripts.seed_brain.seed_brain", return_value=3):
        first = install_pack("iso-42001", reindex=True)
        second = install_pack("iso-42001", reindex=True)
    assert first["version"] == "2023"
    assert (standards / "iso-42001" / "overview.md").exists()
    assert second["path"] == first["path"]
    assert second["reindexed"] is True


def test_check_reports_installed_version(pack_env):
    with patch("scripts.seed_brain.seed_brain", return_value=1):
        install_pack("iso-42001", reindex=False)
    report = check_packs()
    assert "iso-42001" in report["installed"]
    assert report["missing"] == []


def test_unknown_pack_raises(pack_env):
    with pytest.raises(BrainPackError, match="Unknown pack"):
        install_pack("does-not-exist")


def test_invalid_pack_name_rejected(pack_env):
    with pytest.raises(BrainPackError, match="Invalid pack name"):
        install_pack("../escape")


def test_path_traversal_pack_name_rejected(pack_env, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "marker.txt").write_text("gone", encoding="utf-8")
    with pytest.raises(BrainPackError, match="Invalid pack name"):
        install_pack("../../outside")
