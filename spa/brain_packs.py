"""Installable versioned brain framework packs."""
from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from spa.paths import BRAIN_DIR

PACKS_SOURCE_DIR = BRAIN_DIR / "packs"
STANDARDS_DIR = BRAIN_DIR / "04-standards"

_PACK_NAME_RE = re.compile(r"^[a-z0-9._-]+$")


class BrainPackError(Exception):
    pass


def _validate_pack_name(pack_name: str) -> None:
    if not _PACK_NAME_RE.fullmatch(pack_name):
        raise BrainPackError(f"Invalid pack name: {pack_name!r}")


def _assert_within(parent: Path, child: Path) -> None:
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise BrainPackError(f"Path escapes allowed directory: {child}") from exc


def _pack_source(pack_name: str) -> Path:
    _validate_pack_name(pack_name)
    path = PACKS_SOURCE_DIR / pack_name
    _assert_within(PACKS_SOURCE_DIR, path)
    if not path.is_dir():
        raise BrainPackError(f"Unknown pack: {pack_name}")
    manifest = path / "pack.yaml"
    if not manifest.exists():
        raise BrainPackError(f"Pack missing manifest: {manifest}")
    return path


def _install_target(pack_name: str) -> Path:
    _validate_pack_name(pack_name)
    target = STANDARDS_DIR / pack_name
    _assert_within(STANDARDS_DIR, target)
    return target


def list_available_packs() -> list[str]:
    if not PACKS_SOURCE_DIR.exists():
        return []
    return sorted(
        p.name
        for p in PACKS_SOURCE_DIR.iterdir()
        if p.is_dir() and (p / "pack.yaml").exists()
    )


def list_installed_packs() -> list[dict[str, Any]]:
    installed: list[dict[str, Any]] = []
    if not STANDARDS_DIR.exists():
        return installed
    for path in sorted(STANDARDS_DIR.iterdir()):
        if not path.is_dir():
            continue
        manifest = path / "pack.yaml"
        if not manifest.exists():
            continue
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        installed.append(
            {
                "name": data.get("name", path.name),
                "version": data.get("version", "unknown"),
                "source": data.get("source", ""),
                "path": str(path.relative_to(BRAIN_DIR.parent)),
            }
        )
    return installed


def check_packs() -> dict[str, Any]:
    available = {name: _pack_source(name) for name in list_available_packs()}
    installed = {item["name"]: item for item in list_installed_packs()}
    report = {
        "available": sorted(available.keys()),
        "installed": installed,
        "missing": [name for name in available if name not in installed],
        "stale": [],
    }
    for name, src in available.items():
        if name not in installed:
            continue
        src_manifest = yaml.safe_load((src / "pack.yaml").read_text(encoding="utf-8")) or {}
        inst = installed[name]
        if inst.get("version") != src_manifest.get("version"):
            report["stale"].append(name)
    return report


def install_pack(pack_name: str, *, reindex: bool = True) -> dict[str, Any]:
    source = _pack_source(pack_name)
    target = _install_target(pack_name)
    _assert_within(PACKS_SOURCE_DIR, source)
    _assert_within(STANDARDS_DIR, target)
    manifest = yaml.safe_load((source / "pack.yaml").read_text(encoding="utf-8")) or {}

    if target.exists():
        # Idempotent: refresh content from source pack
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)

    result = {
        "pack": pack_name,
        "version": manifest.get("version", "unknown"),
        "source": manifest.get("source", ""),
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "path": str(target.relative_to(BRAIN_DIR.parent)),
        "reindexed": False,
    }

    if reindex:
        try:
            import sys
            from pathlib import Path

            root = Path(__file__).resolve().parent.parent
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            from scripts.seed_brain import seed_brain

            count = seed_brain()
            result["reindexed"] = count > 0
            result["documents_seeded"] = count
        except Exception as exc:  # noqa: BLE001
            result["reindex_error"] = str(exc)

    return result
