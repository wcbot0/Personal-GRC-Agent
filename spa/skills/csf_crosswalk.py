"""csf-crosswalk: artifact/policy -> control mapping + gap list."""
from __future__ import annotations

import re
from typing import Any

_CLOUD_PII = re.compile(r"\b(saas|cloud|pii|privacy|customer metadata|sub-processor)\b", re.I)
_AI_SCOPE = re.compile(
    r"\b(ai|ml|llm|machine learning|model|gpt|foundation model|prompt|inference)\b",
    re.I,
)


def run(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    from spa.llm.skill_engine import maybe_run_llm

    return maybe_run_llm("csf-crosswalk", content, context, _run_heuristic)


def _run_heuristic(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    artifact = content.strip().splitlines()[0][:120] if content.strip() else "unspecified artifact"
    cloud_pii = bool(_CLOUD_PII.search(content))
    ai_scope = bool(_AI_SCOPE.search(content))

    mappings: list[dict[str, Any]] = [
        {
            "artifact_excerpt": artifact,
            "csf_2": "PR.AA-05",
            "soc2_cc": "CC6.1",
            "iso27001": "A.5.15",
            "iso27018": "A.9.2.1" if cloud_pii else "",
            "iso42001": "",
            "nist_800_53": "AC-2",
            "coverage": "partial",
            "notes": "Logical access / customer agreement for PII processing",
        },
        {
            "artifact_excerpt": artifact,
            "csf_2": "DE.AE-2",
            "soc2_cc": "CC7.2",
            "iso27001": "A.8.16",
            "iso27018": "A.10.1" if cloud_pii else "",
            "iso42001": "A.6.2.6" if ai_scope else "",
            "nist_800_53": "AU-6",
            "coverage": "full",
            "notes": "Monitoring and event analysis alignment",
        },
    ]
    gaps = [
        "Missing explicit SOC2 CC6.1 logical access review cadence",
        "ISO27001 A.5.18 access rights not mapped to vendor SSO claims",
        "800-53 AC-2 account management procedures not mapped",
    ]
    if cloud_pii:
        gaps.append("ISO27018 A.18.1.4 PII return/deletion at contract termination not evidenced")
    if ai_scope:
        gaps.append("ISO42001 A.5.2 AI impact assessment not documented for in-scope models")

    control_tags = [
        "CSF:PR.AA-05",
        "CSF:DE.AE-2",
        "SOC2:CC6.1",
        "SOC2:CC7.2",
        "ISO27001:A.5.15",
        "ISO27001:A.8.16",
        "800-53:AC-2",
        "800-53:AU-6",
    ]
    if cloud_pii:
        control_tags.extend(["ISO27018:A.9.2.1", "ISO27018:A.10.1"])
    if ai_scope:
        control_tags.append("ISO42001:A.6.2.6")

    return {
        "skill": "csf-crosswalk",
        "artifact": artifact,
        "control_mappings": mappings,
        "gaps": gaps,
        "control_tags": control_tags,
    }
