"""Shared scanner data models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawFinding:
    check_id: str
    category: str
    owasp: str
    default_risk: str
    title: str
    location: str
    exploitability: str
    source: str = "heuristic"


@dataclass
class ScanResult:
    findings: list[dict[str, Any]] = field(default_factory=list)
    files_scanned: int = 0
    checks_run: list[str] = field(default_factory=list)
    dependency_tools: dict[str, str] = field(default_factory=dict)
