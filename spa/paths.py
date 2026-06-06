"""Canonical repository paths."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

AGENT_DIR = ROOT / "agent"
BRAIN_DIR = ROOT / "brain"
GOVERNANCE_DIR = ROOT / "governance"
SKILLS_DIR = ROOT / "skills"
MEMORY_SCHEMAS_DIR = ROOT / "memory" / "schemas"
CONNECTORS_DIR = ROOT / "connectors"
EVALS_DIR = ROOT / "evals"
WORKSPACE_DIR = ROOT / "workspace"
INBOX_DIR = ROOT / "inbox"

AUTONOMY_POLICY = AGENT_DIR / "autonomy-policy.yaml"
REDACTION_RULES = GOVERNANCE_DIR / "redaction-rules.yaml"
APPROVAL_QUEUE_DIR = GOVERNANCE_DIR / "approval-queue"

CPO_SCHEMA = MEMORY_SCHEMAS_DIR / "cpo.schema.json"
MEMORY_OBJECT_SCHEMA = MEMORY_SCHEMAS_DIR / "memory-object.schema.json"
AUDIT_EVENT_SCHEMA = MEMORY_SCHEMAS_DIR / "audit-event.schema.json"


def get_data_dir() -> Path:
    override = os.environ.get("SPA_DATA_DIR")
    if override:
        return Path(override)
    return WORKSPACE_DIR / ".data"


def get_audit_logs_dir() -> Path:
    override = os.environ.get("SPA_AUDIT_DIR")
    if override:
        return Path(override)
    return GOVERNANCE_DIR / "audit-logs"


def get_proposals_dir() -> Path:
    override = os.environ.get("SPA_DATA_DIR")
    if override:
        return Path(override) / "proposals"
    return WORKSPACE_DIR / "proposals"


def resolve_output_dir(context: dict | None) -> Path:
    """Skill write root: harness output_dir, else env-configurable proposals dir."""
    if context and context.get("output_dir"):
        return Path(context["output_dir"])
    return get_proposals_dir()


def rel_to_repo(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)
