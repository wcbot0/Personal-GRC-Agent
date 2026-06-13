"""Questionnaire skill tests."""
from __future__ import annotations

import json

import jsonschema
import pytest

from spa.paths import SKILLS_DIR
from spa.skills.questionnaire import run
from spa.skills.runner import run_skill
from spa.skills.verifiers import run_verifiers


def _validate_schema(output: dict) -> None:
    schema = json.loads((SKILLS_DIR / "questionnaire" / "output.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(output, schema)


def test_questionnaire_deterministic_cites_brain_and_flags_unsupported(tmp_path):
    content = (SKILLS_DIR.parent / "evals" / "fixtures" / "questionnaire_input.md").read_text(encoding="utf-8")
    output = run(content, context={"output_dir": tmp_path})

    _validate_schema(output)
    assert len(output["answers"]) == 3
    cited = [a for a in output["answers"] if a["citations"]]
    needs_human = [a for a in output["answers"] if a["needs_human"]]
    assert len(cited) >= 1
    assert len(needs_human) >= 1
    assert all("brain/" in c for a in cited for c in a["citations"])

    serialized = json.dumps(output, indent=2)
    _, verifications = run_verifiers("questionnaire", output, serialized, retry_fn=lambda _: output)
    assert all(v["passed"] for v in verifications)


def test_questionnaire_run_skill_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setenv("SPA_NO_LLM", "1")
    fixture = SKILLS_DIR.parent / "evals" / "fixtures" / "questionnaire_input.md"
    result = run_skill("questionnaire", fixture, output_dir=tmp_path)
    assert result["skill"] == "questionnaire"
    assert all(v["passed"] for v in result["verifications"])
