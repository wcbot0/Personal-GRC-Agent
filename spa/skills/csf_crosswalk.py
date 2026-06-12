"""csf-crosswalk: artifact/policy -> control mapping + gap list."""
from __future__ import annotations

from typing import Any


def run(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    from spa.llm.skill_engine import maybe_run_llm

    return maybe_run_llm("csf-crosswalk", content, context, _run_heuristic)


def _run_heuristic(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    artifact = content.strip().splitlines()[0][:120] if content.strip() else "unspecified artifact"

    mappings = [
        {
            "artifact_excerpt": artifact,
            "csf_2": "PR.IP-12",
            "soc2_cc": "CC8.1",
            "nist_800_53": "CM-3",
            "coverage": "partial",
            "notes": "Change management referenced; evidence linkage incomplete",
        },
        {
            "artifact_excerpt": artifact,
            "csf_2": "DE.AE-2",
            "soc2_cc": "CC7.2",
            "nist_800_53": "AU-6",
            "coverage": "full",
            "notes": "Event analysis / monitoring alignment",
        },
    ]
    gaps = [
        "Missing explicit SOC2 CC6.1 logical access review cadence",
        "800-53 AC-2 account management procedures not mapped",
    ]
    return {
        "skill": "csf-crosswalk",
        "artifact": artifact,
        "control_mappings": mappings,
        "gaps": gaps,
        "control_tags": ["CSF:PR.IP-12", "CSF:DE.AE-2", "SOC2:CC8.1", "SOC2:CC7.2", "800-53:CM-3"],
    }
