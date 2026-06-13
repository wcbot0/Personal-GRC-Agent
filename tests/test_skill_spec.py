"""SKILL.md loader compatibility tests."""
from __future__ import annotations

import re

import yaml

from spa.llm.skill_engine import _load_skill_contract, _parse_skill_md
from spa.paths import SKILLS_DIR

SKILL_NAMES = [
    "meeting-synth",
    "ticket-draft",
    "policy-redline",
    "csf-crosswalk",
    "daily-brief",
    "evidence-pack",
    "risk-analyst",
    "repo-security-review",
]

WHEN_CLAUSE = re.compile(r"\buse when\b", re.IGNORECASE)


def test_every_skill_dir_has_skill_md():
    for name in SKILL_NAMES:
        skill_path = SKILLS_DIR / name / "SKILL.md"
        assert skill_path.is_file(), f"missing {skill_path}"


def test_frontmatter_parses_for_all_skills():
    for name in SKILL_NAMES:
        raw = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
        meta, body = _parse_skill_md(raw)
        assert meta.get("name") == name, f"{name}: name mismatch"
        description = meta.get("description", "")
        assert description.strip(), f"{name}: empty description"
        assert WHEN_CLAUSE.search(description), f"{name}: description missing when-to-use clause"
        assert body.strip(), f"{name}: empty body below frontmatter"


def test_load_skill_contract_returns_body_and_schema():
    for name in SKILL_NAMES:
        body, schema = _load_skill_contract(name)
        assert body.strip()
        assert schema.get("type") == "object" or "properties" in schema or "required" in schema
        raw = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
        _, expected_body = _parse_skill_md(raw)
        assert body == expected_body


def test_frontmatter_is_valid_yaml():
    for name in SKILL_NAMES:
        raw = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
        assert raw.startswith("---")
        end = raw.find("\n---", 3)
        meta = yaml.safe_load(raw[3:end])
        assert isinstance(meta, dict)
        assert "name" in meta and "description" in meta
