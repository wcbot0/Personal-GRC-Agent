"""Dedicated csf-crosswalk scenario eval tests."""
from __future__ import annotations

import pytest

from evals.crosswalk_eval import (
    load_scenarios,
    run_all_crosswalk_evals,
    run_scenario,
    score_crosswalk_output,
)


@pytest.fixture(autouse=True)
def heuristic_mode(monkeypatch):
    monkeypatch.setenv("SPA_NO_LLM", "1")


@pytest.mark.parametrize("scenario", load_scenarios(), ids=lambda s: s["id"])
def test_crosswalk_scenario_passes(scenario):
    output, verifications, errors = run_scenario(scenario)
    assert not errors, "\n".join(errors)
    assert output.get("skill") == "csf-crosswalk"
    assert all(v["passed"] for v in verifications)


def test_all_crosswalk_scenarios_pass():
    errors, records = run_all_crosswalk_evals(use_runner=False)
    assert not errors, "\n".join(errors)
    assert len(records) == len(load_scenarios())
    assert all(r["passed"] for r in records)


def test_cloud_scenario_requires_iso27018_not_iso42001():
    scenario = next(s for s in load_scenarios() if s["id"] == "cloud-saas-vendor")
    output, verifications, _ = run_scenario(scenario)
    tags = output.get("control_tags", [])
    assert any(t.startswith("ISO27018:") for t in tags)
    assert not any(t.startswith("ISO42001:") for t in tags)
    mappings = output.get("control_mappings", [])
    assert any(m.get("iso27018") for m in mappings)
    assert all(not m.get("iso42001") for m in mappings)


def test_ai_scenario_requires_iso42001_not_iso27018():
    scenario = next(s for s in load_scenarios() if s["id"] == "ai-governance-vendor")
    output, _, _ = run_scenario(scenario)
    tags = output.get("control_tags", [])
    assert any(t.startswith("ISO42001:") for t in tags)
    assert not any(t.startswith("ISO27018:") for t in tags)
    mappings = output.get("control_mappings", [])
    assert any(m.get("iso42001") for m in mappings)
    assert all(not m.get("iso27018") for m in mappings)


def test_combined_scenario_requires_both_iso_extensions():
    scenario = next(s for s in load_scenarios() if s["id"] == "combined-ai-cloud")
    output, _, _ = run_scenario(scenario)
    tags = output.get("control_tags", [])
    assert any(t.startswith("ISO27018:") for t in tags)
    assert any(t.startswith("ISO42001:") for t in tags)
    mappings = output.get("control_mappings", [])
    assert any(m.get("iso27018") for m in mappings)
    assert any(m.get("iso42001") for m in mappings)


def test_score_crosswalk_output_catches_missing_prefix():
    golden = {
        "required_fields": ["control_mappings"],
        "control_tags_include_prefixes": ["ISO42001:"],
    }
    output = {"control_mappings": [{}], "control_tags": ["ISO27001:A.5.15"]}
    errors = score_crosswalk_output(output, golden, [], scenario_id="test")
    assert any("ISO42001:" in e for e in errors)


def test_scenario_manifest_lists_three_scenarios():
    ids = [s["id"] for s in load_scenarios()]
    assert ids == ["cloud-saas-vendor", "ai-governance-vendor", "combined-ai-cloud"]
