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
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or not should_scan(path):
            continue
        rel = str(path.relative_to(ROOT))
        if rel in SKIP_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern, label in PATTERNS:
            if pattern.search(text):
                # Allow intentional examples in redaction rules / tests
                if "REDACTED" in text or "example" in str(path):
                    continue
                findings.append(f"{path.relative_to(ROOT)}: {label}")

    if findings:
        for f in findings:
            print(f"secret-scan FAIL: {f}", file=sys.stderr)
        return 1

    print("secret-scan OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
