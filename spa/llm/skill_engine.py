"""LLM-backed skill generation with brain context and strict JSON parsing."""
from __future__ import annotations

import json
import re
from typing import Any

import yaml

from spa.llm.client import LLMClient, llm_enabled
from spa.memory.semantic import SemanticMemory
from spa.paths import SKILLS_DIR


def _brain_snippets(query: str, limit: int = 3) -> list[str]:
    try:
        hits = SemanticMemory().query(query[:500], limit=limit)
    except Exception:
        return []
    snippets: list[str] = []
    for hit in hits:
        content = hit.get("content") or ""
        if content:
            snippets.append(content[:600])
    return snippets


def _parse_skill_md(text: str) -> tuple[dict[str, Any], str]:
    """Return frontmatter dict and markdown body from SKILL.md."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta = yaml.safe_load(text[3:end]) or {}
    body = text[end + 4 :].lstrip("\n")
    return meta, body


def _load_skill_contract(skill_name: str) -> tuple[str, dict[str, Any]]:
    skill_dir = SKILLS_DIR / skill_name
    raw = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    _, skill_md = _parse_skill_md(raw)
    schema = json.loads((skill_dir / "output.schema.json").read_text(encoding="utf-8"))
    return skill_md, schema


def _format_verifier_feedback(feedback: list[dict[str, Any]] | None) -> str:
    if not feedback:
        return ""
    failed = [item for item in feedback if not item.get("passed")]
    if not failed:
        return ""
    lines = [f"- {item['name']}: {item.get('detail', '')}" for item in failed]
    return "Previous output failed verifiers:\n" + "\n".join(lines)


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def parse_skill_json(text: str) -> dict[str, Any]:
    return json.loads(_strip_json_fence(text))


def build_messages(
    skill_name: str,
    input_content: str,
    *,
    verifier_feedback: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    skill_md, schema = _load_skill_contract(skill_name)
    snippets = _brain_snippets(input_content)
    brain_block = ""
    if snippets:
        brain_block = "\n\nRelevant brain snippets:\n" + "\n---\n".join(snippets)

    feedback_block = _format_verifier_feedback(verifier_feedback)
    if feedback_block:
        feedback_block = f"\n\n{feedback_block}\nFix all verifier failures."

    system = (
        f"You are a GRC drafting assistant running skill `{skill_name}`.\n\n"
        f"Skill contract:\n{skill_md}\n\n"
        f"Respond with a single JSON object matching this schema:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Include control_tags using CSF:, SOC2:, and 800-53: prefixes. "
        "Output JSON only — no markdown fences or commentary."
    )
    user = f"Input:\n{input_content}{brain_block}{feedback_block}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _invalid_output(skill_name: str, error: str) -> dict[str, Any]:
    if skill_name == "csf-crosswalk":
        return {
            "skill": "csf-crosswalk",
            "control_mappings": [],
            "gaps": [],
            "control_tags": [],
            "_parse_error": error,
        }
    return {
        "skill": skill_name,
        "decisions": [],
        "risks": [],
        "action_items": [],
        "proposed_tickets": [],
        "control_tags": [],
        "_parse_error": error,
    }


def run_llm_skill(skill_name: str, input_content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    audit = context.get("audit")
    client = LLMClient(audit=audit)
    feedback = context.get("verifier_feedback")
    messages = build_messages(skill_name, input_content, verifier_feedback=feedback)
    raw = client.complete(messages, json_mode=True)
    try:
        return parse_skill_json(raw)
    except json.JSONDecodeError as exc:
        return _invalid_output(skill_name, str(exc))


def maybe_run_llm(skill_name: str, input_content: str, context: dict[str, Any] | None, heuristic_fn) -> dict[str, Any]:
    if llm_enabled():
        return run_llm_skill(skill_name, input_content, context)
    return heuristic_fn(input_content, context)
