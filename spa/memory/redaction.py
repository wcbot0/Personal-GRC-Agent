"""Redaction-at-write: deterministic secret/PII scrubbing before persistence."""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

import yaml

from spa.paths import REDACTION_RULES


def _load_rules() -> dict[str, Any]:
    if not REDACTION_RULES.exists():
        return {"denylist_terms": [], "regex_patterns": []}
    return yaml.safe_load(REDACTION_RULES.read_text()) or {}


def redact_text(text: str) -> str:
    rules = _load_rules()
    result = text
    for term in rules.get("denylist_terms", []):
        if term:
            result = result.replace(term, "[REDACTED_DENYLIST]")
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
