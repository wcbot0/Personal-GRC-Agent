"""Redaction-at-write: deterministic secret/PII scrubbing before persistence."""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

import yaml

from spa.paths import REDACTION_RULES

_rules_cache: dict[str, Any] | None = None
_rules_cache_mtime: float | None = None


def _load_rules() -> dict[str, Any]:
    global _rules_cache, _rules_cache_mtime

    if not REDACTION_RULES.exists():
        raise FileNotFoundError(f"Redaction rules file missing: {REDACTION_RULES}")

    mtime = REDACTION_RULES.stat().st_mtime
    if _rules_cache is not None and _rules_cache_mtime == mtime:
        return _rules_cache

    try:
        raw = REDACTION_RULES.read_text()
    except OSError as exc:
        raise RuntimeError(f"Cannot read redaction rules: {REDACTION_RULES}") from exc

    rules = yaml.safe_load(raw)
    if not isinstance(rules, dict) or not rules:
        raise ValueError(f"Redaction rules empty or invalid: {REDACTION_RULES}")

    _rules_cache = rules
    _rules_cache_mtime = mtime
    return rules


def redact_text(text: str) -> str:
    rules = _load_rules()
    result = text
    for term in rules.get("denylist_terms", []):
        if term:
            result = re.sub(
                re.escape(term),
                "[REDACTED_DENYLIST]",
                result,
                flags=re.IGNORECASE,
            )
    for pattern in rules.get("regex_patterns", []):
        regex = pattern.get("pattern")
        replacement = pattern.get("replacement", "[REDACTED]")
        if regex:
            result = re.sub(regex, replacement, result, flags=re.MULTILINE)
    return result


def redact_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return redact_text(obj)
    if isinstance(obj, list):
        return [redact_obj(item) for item in obj]
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    return obj
