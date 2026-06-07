"""Exploitability risk scoring and framework mapping."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from spa.paths import SKILLS_DIR
from spa.scanners.models import RawFinding

_RISK_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

_ASVS_MAP_PATH = SKILLS_DIR / "repo-security-review" / "checks" / "asvs-map.yaml"


def _load_asvs_map() -> dict[str, Any]:
    if not _ASVS_MAP_PATH.exists():
        return {"mappings": {}, "default": {}}
    return yaml.safe_load(_ASVS_MAP_PATH.read_text(encoding="utf-8")) or {}


def _lookup_mapping(category: str) -> dict[str, Any]:
    catalog = _load_asvs_map()
    mappings = catalog.get("mappings") or {}
    for key, value in mappings.items():
        if key.startswith(category.split()[0]):
            return value
    return catalog.get("default") or {}


def bump_risk(current: str, delta: int = 1) -> str:
    order = ["info", "low", "medium", "high", "critical"]
    idx = order.index(current) if current in order else 0
    return order[min(idx + delta, len(order) - 1)]


def finalize_finding(raw: RawFinding) -> dict[str, Any]:
    mapping = _lookup_mapping(raw.category)
    risk = raw.default_risk
    if raw.source == "secrets":
        risk = "critical"
    elif raw.source == "dependency_cve":
        risk = raw.default_risk

    return {
        "risk": risk,
        "category": raw.category,
        "title": raw.title,
        "location": raw.location,
        "owasp": raw.owasp,
        "asvs": mapping.get("asvs", "V1.1.1"),
        "attack": mapping.get("attack", "T1190"),
        "exploitability": raw.exploitability,
        "control_tags": list(mapping.get("control_tags") or ["CSF:ID.RA-01"]),
    }


def sort_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(findings, key=lambda f: (_RISK_ORDER.get(f.get("risk", "info"), 99), f.get("location", "")))


def aggregate_control_tags(findings: list[dict[str, Any]]) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()
    for finding in findings:
        for tag in finding.get("control_tags") or []:
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return tags or ["CSF:ID.RA-01", "SOC2:CC7.1", "800-53:SA-11"]
