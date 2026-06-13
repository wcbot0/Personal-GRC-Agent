"""Secret detection for arbitrary repository roots."""
from __future__ import annotations

from pathlib import Path

from spa.lint.secrets import PATTERNS, scan_text_for_secrets
from spa.scanners.models import RawFinding
from spa.scanners.repo import walk_files


def scan_secrets(repo_root: Path) -> list[RawFinding]:
    findings: list[RawFinding] = []
    for path in walk_files(repo_root):
        rel = path.relative_to(repo_root)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "example" in str(rel).lower():
            continue
        for label, line_no in scan_text_for_secrets(text):
            findings.append(
                RawFinding(
                    check_id="secret",
                    category="A02 Cryptographic Failures",
                    owasp="A02:2021",
                    default_risk="critical",
                    title=f"Likely secret: {label}",
                    location=f"{rel}:{line_no}",
                    exploitability="Credential exposure in source; trivial to exploit if repo is accessible.",
                    source="secrets",
                )
            )
    return findings
