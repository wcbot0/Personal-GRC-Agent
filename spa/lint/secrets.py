"""Scan repository for likely secrets (CI secret-scan target)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from spa.paths import ROOT

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "secrets",
}

SKIP_DIR_PREFIXES = (
    "governance/audit-logs",
    "governance/prompt-injection-tests",
    "workspace/.data",
    "tests",
    "evals/fixtures",
)

SKIP_FILES = {
    "scripts/redteam.sh",
    "spa/lint/secrets.py",
    "governance/redaction-rules.yaml",
}

PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"), "Private key block"),
    (
        re.compile(
            r"(?i)\b(api[_-]?key|secret|password)\s*=\s*['\"][^'\"]{12,}['\"]"
        ),
        "Hardcoded secret",
    ),
]


def scan_text_for_secrets(text: str) -> list[tuple[str, int]]:
    """Return (label, line_number) for each pattern match in text."""
    hits: list[tuple[str, int]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern, label in PATTERNS:
            if pattern.search(line):
                hits.append((label, line_no))
                break
    return hits


def scan_repo(root: Path, *, skip_prefixes: tuple[str, ...] = ()) -> list[str]:
    """Scan a repository root and return human-readable finding strings."""
    findings: list[str] = []
    prefixes = SKIP_DIR_PREFIXES + skip_prefixes
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if any(part in SKIP_DIR_NAMES for part in rel.parts):
            continue
        rel_str = str(rel)
        if any(rel_str.startswith(prefix) for prefix in prefixes):
            continue
        if path.suffix in {".png", ".jpg", ".gif", ".woff", ".woff2", ".pyc"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "REDACTED" in text or "example" in rel_str.lower():
            continue
        for label, line_no in scan_text_for_secrets(text):
            findings.append(f"{rel}:{line_no}: {label}")
    return findings


def should_scan(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in SKIP_DIR_NAMES for part in rel.parts):
        return False
    rel_str = str(rel)
    if any(rel_str.startswith(prefix) for prefix in SKIP_DIR_PREFIXES):
        return False
    if path.suffix in {".png", ".jpg", ".gif", ".woff", ".woff2", ".pyc"}:
        return False
    return True


def main() -> int:
    findings = scan_repo(ROOT)
    for rel in SKIP_FILES:
        findings = [f for f in findings if not f.startswith(f"{rel}:")]

    if findings:
        for f in findings:
            print(f"secret-scan FAIL: {f}", file=sys.stderr)
        return 1

    print("secret-scan OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
