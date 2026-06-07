"""evidence-pack: control id + period -> evidence index file with optional cloud collection."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from connectors.registry import LiveWriteDisabledError, get_cloud_provider
from spa.memory.redaction import redact_obj, redact_text
from spa.paths import BRAIN_DIR, rel_to_repo, resolve_output_dir
from spa.skills.io import write_text_file

_CLOUD_CHECKS_PATH = BRAIN_DIR / "02-controls" / "cloud-checks.yaml"

_DEFAULT_CONTROL_TAGS = {
    "CC6.1": ["SOC2:CC6.1", "CSF:PR.AC", "800-53:AC-2"],
}


def _load_cloud_checks() -> dict[str, Any]:
    if not _CLOUD_CHECKS_PATH.exists():
        return {}
    return yaml.safe_load(_CLOUD_CHECKS_PATH.read_text(encoding="utf-8")) or {}


def _parse_provider(content: str) -> str | None:
    match = re.search(r"(?i)provider[:\s]+([A-Za-z0-9_-]+)", content)
    return match.group(1).lower() if match else None


def _resolve_provider(content: str) -> str:
    return _parse_provider(content) or os.environ.get("CLOUD_PROVIDER", "none").lower()


def _resolve_checks(catalog: dict[str, Any], control_id: str, provider: str) -> list[str]:
    controls = catalog.get("controls") or {}
    entry = controls.get(control_id) or {}
    checks_by_provider = entry.get("checks") or {}
    catalog_provider = "aws" if provider == "none" else provider
    raw = checks_by_provider.get(catalog_provider) or []
    return list(raw)


def _control_tags(control_id: str) -> list[str]:
    return _DEFAULT_CONTROL_TAGS.get(
        control_id,
        [f"SOC2:{control_id}", "CSF:PR.AC", "800-53:AC-2"],
    )


def _emit_run_audit(
    context: dict[str, Any] | None,
    *,
    control_id: str,
    period: str,
    provider: str,
    checks: list[str],
    findings: list[dict[str, Any]],
    cloud_status: str,
    index_file: str,
) -> None:
    guard = (context or {}).get("guard")
    if guard is None:
        return
    guard.audit.emit(
        "evidence_pack_collect",
        task_class="skill",
        risk_class="A1",
        tools_called=["skill:evidence-pack", f"cloud:{provider}"],
        outputs=redact_obj(
            {
                "control_id": control_id,
                "period": period,
                "provider": provider,
                "checks": checks,
                "finding_count": len(findings),
                "cloud_status": cloud_status,
                "index_file": index_file,
            }
        ),
    )


def _collect_cloud_findings(
    provider_name: str,
    checks: list[str],
    context: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], str]:
    if not checks:
        return [], "manual-evidence-only (no cloud checks mapped for control)"

    if provider_name == "none":
        return [], "manual-evidence-only (no cloud provider configured)"

    guard = (context or {}).get("guard")
    try:
        connector = get_cloud_provider(guard=guard)
    except LiveWriteDisabledError:
        return [], "manual-evidence-only (no cloud provider configured)"

    if connector.provider == "none":
        return [], "manual-evidence-only (no cloud provider configured)"

    findings: list[dict[str, Any]] = []
    for check in checks:
        try:
            batch = connector.collect(check)
        except RuntimeError:
            return [], "manual-evidence-only (no cloud provider configured)"
        except Exception:  # noqa: BLE001
            continue
        findings.extend(redact_obj(batch))

    if findings:
        return findings, "cloud-evidence-collected"
    return [], "manual-evidence-only (cloud checks returned no findings)"


def _build_index_markdown(
    *,
    control_id: str,
    period: str,
    cloud_status: str,
    provider: str,
    checks: list[str],
    findings: list[dict[str, Any]],
    findings_file: str | None,
) -> str:
    lines = [
        f"# Evidence Index — {control_id}",
        "",
        f"**Period:** {period}",
        "**Status:** DRAFT — not authoritative until approved",
        "",
        "## Cloud collection",
        f"**Provider:** {provider}",
        f"**Status:** {cloud_status}",
    ]
    if checks:
        lines.append(f"**Checks:** {', '.join(checks)}")
    else:
        lines.append("**Checks:** (none mapped)")
    lines.extend(["", "## Cloud findings"])
    if findings:
        lines.extend(
            [
                "| Check | Status | Resource / metric |",
                "|-------|--------|-------------------|",
            ]
        )
        for item in findings:
            resource = item.get("resource") or item.get("metric") or item.get("check") or "—"
            lines.append(
                f"| {item.get('check', '—')} | {item.get('status', 'collected')} | {resource} |"
            )
        if findings_file:
            lines.extend(["", f"Full findings: `{findings_file}`"])
    else:
        lines.append("_No automated cloud findings — manual evidence required._")
    lines.extend(
        [
            "",
            "## Manual artifacts",
            "| Item | Source | Collected |",
            "|------|--------|-----------|",
            "| Access review export | manual | pending |",
            "| Policy excerpt | brain/policies/ | pending |",
            "",
            "## Control tags",
        ]
    )
    for tag in _control_tags(control_id):
        lines.append(f"- {tag.replace(':', ': ')}")
    return "\n".join(lines) + "\n"


def run(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    control_match = re.search(r"(?i)control[:\s]+([A-Za-z0-9.\-]+)", content)
    period_match = re.search(r"(?i)period[:\s]+([^\n]+)", content)
    control_id = control_match.group(1) if control_match else "CC6.1"
    period = period_match.group(1).strip() if period_match else datetime.now(timezone.utc).strftime("%Y-Q%q")

    provider = _resolve_provider(content)
    catalog = _load_cloud_checks()
    checks = _resolve_checks(catalog, control_id, provider)
    findings, cloud_status = _collect_cloud_findings(provider, checks, context)
    findings = redact_obj(findings)

    out_dir = resolve_output_dir(context)
    evidence_dir = out_dir / "brain" / "evidence" / control_id.replace(".", "-")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    date_stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    index_path = evidence_dir / f"index-{date_stamp}.md"

    findings_path: Path | None = None
    findings_rel: str | None = None
    if findings:
        findings_path = evidence_dir / f"findings-{date_stamp}.json"
        write_text_file(
            context,
            "write_local_markdown",
            findings_path,
            json.dumps(findings, indent=2),
        )
        findings_rel = rel_to_repo(findings_path)

    index_md = redact_text(
        _build_index_markdown(
            control_id=control_id,
            period=period,
            cloud_status=cloud_status,
            provider=provider,
            checks=checks,
            findings=findings,
            findings_file=findings_rel,
        )
    )
    write_text_file(context, "write_local_markdown", index_path, index_md)

    index_file = rel_to_repo(index_path)
    _emit_run_audit(
        context,
        control_id=control_id,
        period=period,
        provider=provider,
        checks=checks,
        findings=findings,
        cloud_status=cloud_status,
        index_file=index_file,
    )

    return {
        "skill": "evidence-pack",
        "control_id": control_id,
        "period": period,
        "index_file": index_file,
        "control_tags": _control_tags(control_id),
        "provider": provider,
        "checks": checks,
        "findings": findings,
    }
