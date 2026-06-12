"""OWASP Top 10 heuristic pattern scanner."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from spa.paths import SKILLS_DIR
from spa.scanners.models import RawFinding
from spa.scanners.repo import walk_files

_HEURISTICS_PATH = SKILLS_DIR / "repo-security-review" / "checks" / "owasp-heuristics.yaml"

FOCUS_CHECKS = {
    "secrets": [],
    "dependencies": [],
    "injection": {
        "A03 Injection",
        "A08 Software and Data Integrity Failures",
        "A10 Server-Side Request Forgery",
    },
    "auth": {"A01 Broken Access Control", "A07 Identification and Authentication Failures"},
    "config": {"A05 Security Misconfiguration", "A02 Cryptographic Failures"},
    "all": None,
}


def _load_heuristics() -> list[dict]:
    if not _HEURISTICS_PATH.exists():
        return []
    data = yaml.safe_load(_HEURISTICS_PATH.read_text(encoding="utf-8")) or {}
    return list(data.get("checks") or [])


def _matches_focus(category: str, focus: str) -> bool:
    allowed = FOCUS_CHECKS.get(focus)
    if allowed is None:
        return True
    return category in allowed


def scan_owasp(repo_root: Path, focus: str = "all") -> list[RawFinding]:
    checks = _load_heuristics()
    findings: list[RawFinding] = []
    compiled: list[tuple[dict, list[re.Pattern[str]]]] = []
    for check in checks:
        if not _matches_focus(check.get("category", ""), focus):
            continue
        patterns = [re.compile(p) for p in check.get("patterns") or []]
        compiled.append((check, patterns))

    for path in walk_files(repo_root):
        rel = path.relative_to(repo_root)
        if rel.name == ".env":
            findings.append(
                RawFinding(
                    check_id="committed_env",
                    category="A05 Security Misconfiguration",
                    owasp="A05:2021",
                    default_risk="high",
                    title="Environment file committed to repository",
                    location=str(rel),
                    exploitability="Env files often contain secrets and config overrides.",
                    source="heuristic",
                )
            )
        ext = path.suffix.lower()
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for check, patterns in compiled:
            extensions = check.get("extensions") or []
            if extensions and ext not in extensions:
                continue
            for line_no, line in enumerate(lines, start=1):
                for pattern in patterns:
                    if pattern.search(line):
                        findings.append(
                            RawFinding(
                                check_id=check.get("id", "owasp"),
                                category=check.get("category", "Unknown"),
                                owasp=check.get("owasp", "A00:2021"),
                                default_risk=check.get("default_risk", "medium"),
                                title=check.get("title", "Security heuristic match"),
                                location=f"{rel}:{line_no}",
                                exploitability="Pattern match indicates likely exploitable weakness.",
                                source="heuristic",
                            )
                        )
                        break
    return findings
