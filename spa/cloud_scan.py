"""Cloud findings scan — read-only checks → findings JSON, ticket proposals, evidence indexes."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from connectors.interfaces.cloud import CloudConfigError
from connectors.registry import LiveWriteDisabledError, get_cloud_provider
from spa.memory.redaction import redact_obj, redact_text
from spa.paths import BRAIN_DIR, get_data_dir, get_proposals_dir, rel_to_repo
from spa.skills.ticket_draft import create_proposal
from spa.tools.guard import ToolGuard
from spa.tools.write import guarded_write

_CLOUD_CHECKS_PATH = BRAIN_DIR / "02-controls" / "cloud-checks.yaml"

_DEFAULT_CONTROL_TAGS = {
    "CC6.1": ["SOC2:CC6.1", "CSF:PR.AC", "800-53:AC-2"],
    "CC6.6": ["SOC2:CC6.6", "CSF:PR.PT", "800-53:SC-7"],
    "CC6.7": ["SOC2:CC6.7", "CSF:PR.DS", "800-53:SC-28"],
    "CC6.8": ["SOC2:CC6.8", "CSF:DE.CM", "800-53:SI-3"],
    "CC7.1": ["SOC2:CC7.1", "CSF:DE.CM", "800-53:CM-3"],
    "CC7.2": ["SOC2:CC7.2", "CSF:DE.AE", "800-53:AU-2"],
}


def _load_cloud_checks() -> dict[str, Any]:
    if not _CLOUD_CHECKS_PATH.exists():
        return {}
    return yaml.safe_load(_CLOUD_CHECKS_PATH.read_text(encoding="utf-8")) or {}


def _control_tags(control_id: str) -> list[str]:
    return _DEFAULT_CONTROL_TAGS.get(
        control_id,
        [f"SOC2:{control_id}", "CSF:PR.AC", "800-53:AC-2"],
    )


def _default_period() -> str:
    now = datetime.now(timezone.utc)
    quarter = (now.month - 1) // 3 + 1
    return f"{now.year}-Q{quarter}"


def _control_slug(control_id: str) -> str:
    return control_id.replace(".", "-")


def _build_check_index(catalog: dict[str, Any], provider: str) -> dict[str, list[dict[str, str]]]:
    """Map check name → list of {control_id, description}."""
    index: dict[str, list[dict[str, str]]] = {}
    provider_block = catalog.get(provider) or {}
    if not isinstance(provider_block, dict):
        return index
    for control_id, entry in provider_block.items():
        if not isinstance(entry, dict):
            continue
        description = str(entry.get("description") or "")
        for check in entry.get("checks") or []:
            index.setdefault(check, []).append({"control_id": control_id, "description": description})
    return index


def _evaluate_check(
    check: str,
    raw_findings: list[dict[str, Any]] | None,
    *,
    implemented: bool,
    error: str | None = None,
) -> dict[str, Any]:
    if not implemented:
        return {
            "check": check,
            "status": "unimplemented",
            "severity": "info",
            "detail": "Check not implemented in provider READ_ONLY_CHECKS",
        }
    if error:
        return {
            "check": check,
            "status": "error",
            "severity": "medium",
            "detail": error,
        }
    if not raw_findings:
        return {
            "check": check,
            "status": "gap",
            "severity": "medium",
            "detail": "No evidence returned for required check",
        }
    return {
        "check": check,
        "status": "pass",
        "severity": "info",
        "detail": raw_findings[0].get("detail") or raw_findings[0].get("resource") or "evidence collected",
        "raw": raw_findings,
    }


def _should_propose_ticket(finding: dict[str, Any]) -> bool:
    return finding.get("status") in {"gap", "error"}


def _ticket_id_for_finding(provider: str, check: str, seq: int) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", check).strip("-").upper()
    return f"AI-PROPOSED-CLOUD-{provider.upper()}-{slug}-{seq:03d}"


def _append_evidence_index(
    *,
    control_id: str,
    period: str,
    provider: str,
    findings: list[dict[str, Any]],
    scan_timestamp: str,
    guard: ToolGuard,
) -> str:
    evidence_dir = BRAIN_DIR / "evidence" / _control_slug(control_id)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    period_slug = re.sub(r"[^A-Za-z0-9]+", "-", period).strip("-")
    index_path = evidence_dir / f"index-{period_slug}.md"

    section_lines = [
        "",
        f"## Cloud scan — {scan_timestamp}",
        "",
        f"**Provider:** {provider}",
        f"**Period:** {period}",
        "",
        "| Check | Status | Severity | Detail |",
        "|-------|--------|----------|--------|",
    ]
    for item in findings:
        section_lines.append(
            f"| {item.get('check', '—')} | {item.get('status', '—')} | "
            f"{item.get('severity', '—')} | {redact_text(str(item.get('detail', '—')))} |"
        )
    section = "\n".join(section_lines) + "\n"

    def _write() -> str:
        if index_path.exists():
            existing = index_path.read_text(encoding="utf-8").rstrip()
            index_path.write_text(existing + section, encoding="utf-8")
        else:
            header = [
                f"# Evidence Index — {control_id}",
                "",
                f"**Period:** {period}",
                "**Status:** DRAFT — not authoritative until approved",
                "",
                "## Control tags",
            ]
            for tag in _control_tags(control_id):
                header.append(f"- {tag.replace(':', ': ')}")
            index_path.write_text("\n".join(header) + section, encoding="utf-8")
        return rel_to_repo(index_path)

    return guarded_write(
        guard,
        "write_local_markdown",
        _write,
        preview=index_path.name,
        audit_outputs=lambda path: {"index_file": path, "control_id": control_id},
    )


def run_cloud_scan(
    *,
    provider: str | None = None,
    period: str | None = None,
    guard: ToolGuard | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Run all cloud checks for a provider; emit findings, proposals, and evidence indexes."""
    guard = guard or ToolGuard()
    provider_name = (provider or os.environ.get("CLOUD_PROVIDER", "none")).lower()
    period_value = period or _default_period()
    catalog = _load_cloud_checks()
    check_index = _build_check_index(catalog, provider_name)
    all_checks = sorted(check_index.keys())

    capabilities: set[str] = set()
    connector = None
    cloud_status = "manual-evidence-only"
    if provider_name != "none":
        try:
            connector = get_cloud_provider(guard=guard)
            if connector.provider != "none":
                capabilities = set(connector.list_capabilities())
                cloud_status = "cloud-scan-collected"
        except (LiveWriteDisabledError, CloudConfigError):
            cloud_status = "manual-evidence-only"

    scan_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    enriched_findings: list[dict[str, Any]] = []
    controls_touched: dict[str, list[dict[str, Any]]] = {}

    for check in all_checks:
        mappings = check_index[check]
        control_id = mappings[0]["control_id"]
        implemented = check in capabilities
        raw_findings: list[dict[str, Any]] | None = None
        error: str | None = None

        if connector and connector.provider != "none" and implemented:
            try:
                raw_findings = connector.collect(check)
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"

        evaluated = _evaluate_check(check, raw_findings, implemented=implemented, error=error)
        evaluated["control_id"] = control_id
        evaluated["control_tags"] = _control_tags(control_id)
        evaluated["provider"] = provider_name
        enriched_findings.append(redact_obj(evaluated))
        controls_touched.setdefault(control_id, []).append(evaluated)

    ticket_seq = 1
    ticket_proposals: list[dict[str, Any]] = []
    for finding in enriched_findings:
        if not _should_propose_ticket(finding):
            continue
        ticket_id = _ticket_id_for_finding(provider_name, finding["check"], ticket_seq)
        ticket_seq += 1
        proposal = create_proposal(
            {
                "id": ticket_id,
                "title": f"Remediate cloud gap: {finding['check']}",
                "description": (
                    f"Cloud scan ({provider_name}) found a gap for check `{finding['check']}` "
                    f"mapped to {finding['control_id']}.\n\n"
                    f"Detail: {finding.get('detail', 'n/a')}"
                ),
                "status": "ai_proposed",
                "assignee": "unassigned",
                "suggested_owner": "cloud-security",
                "priority": "medium" if finding["status"] == "gap" else "high",
                "rationale": f"Automated cloud scan finding ({finding['status']}) for {finding['control_id']}",
                "control_tags": finding.get("control_tags", []),
            },
            guard=guard,
        )
        ticket_proposals.append(proposal)

    evidence_indexes: list[str] = []
    for control_id, control_findings in controls_touched.items():
        if not control_findings:
            continue
        index_file = _append_evidence_index(
            control_id=control_id,
            period=period_value,
            provider=provider_name,
            findings=control_findings,
            scan_timestamp=scan_ts,
            guard=guard,
        )
        evidence_indexes.append(index_file)

    findings_dir = output_dir or (get_data_dir() / "findings")
    findings_dir.mkdir(parents=True, exist_ok=True)
    findings_path = findings_dir / f"{provider_name}-{scan_ts}.json"

    payload = redact_obj(
        {
            "provider": provider_name,
            "period": period_value,
            "scanned_at": scan_ts,
            "cloud_status": cloud_status,
            "findings": enriched_findings,
            "summary": {
                "total_checks": len(enriched_findings),
                "gaps": sum(1 for f in enriched_findings if f["status"] == "gap"),
                "errors": sum(1 for f in enriched_findings if f["status"] == "error"),
                "unimplemented": sum(1 for f in enriched_findings if f["status"] == "unimplemented"),
                "pass": sum(1 for f in enriched_findings if f["status"] == "pass"),
            },
            "ticket_proposals": [
                {"ticket_id": p["ticket"]["id"], "path": p["path"]} for p in ticket_proposals
            ],
            "evidence_indexes": evidence_indexes,
        }
    )

    def _write_findings() -> str:
        findings_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return rel_to_repo(findings_path)

    findings_file = guarded_write(
        guard,
        "write_workspace_draft",
        _write_findings,
        preview=findings_path.name,
        audit_outputs=lambda path: {"findings_file": path, "finding_count": len(enriched_findings)},
    )
    payload["findings_file"] = findings_file

    guard.audit.emit(
        "cloud_scan_complete",
        task_class="cloud_scan",
        risk_class="A0",
        tools_called=["cloud_scan"],
        outputs=redact_obj(
            {
                "provider": provider_name,
                "period": period_value,
                "findings_file": findings_file,
                "finding_count": len(enriched_findings),
                "ticket_count": len(ticket_proposals),
                "evidence_index_count": len(evidence_indexes),
                "cloud_status": cloud_status,
            }
        ),
    )

    return payload
