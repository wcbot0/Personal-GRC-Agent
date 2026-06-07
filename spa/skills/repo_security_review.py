"""repo-security-review: lightweight OWASP/ASVS repo scan with dependency checks."""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from spa.memory.redaction import redact_text
from spa.paths import rel_to_repo, resolve_output_dir
from spa.scanners.repo import resolve_repo
from spa.scanners.risk import aggregate_control_tags
from spa.scanners.runner import run_scan
from spa.skills.io import write_text_file


def _parse_field(content: str, name: str, default: str | None = None) -> str | None:
    match = re.search(rf"(?i){name}[:\s]+([^\n]+)", content)
    return match.group(1).strip() if match else default


def _repo_display(source: str) -> str:
    if source.startswith("https://"):
        parts = source.rstrip("/").split("/")
        if len(parts) >= 2:
            return "/".join(parts[-2:])
    return source


def _build_summary(findings: list[dict[str, Any]], dependency_tools: dict[str, str]) -> str:
    counts = Counter(f.get("risk", "info") for f in findings)
    parts = []
    for risk in ("critical", "high", "medium", "low", "info"):
        if counts.get(risk):
            parts.append(f"{counts[risk]} {risk}")
    summary = f"Findings: {', '.join(parts) or 'none'}."
    tool_bits = [f"{k}={v}" for k, v in sorted(dependency_tools.items())]
    if tool_bits:
        summary += f" Dependency tools: {', '.join(tool_bits)}."
    return summary


def _build_report_md(
    *,
    repo_display: str,
    scope: str,
    branch: str,
    files_scanned: int,
    summary: str,
    findings: list[dict[str, Any]],
    checks_run: list[str],
) -> str:
    lines = [
        f"# Repo Security Review — {repo_display}",
        "",
        f"**Scope:** {scope} | **Files scanned:** {files_scanned} | **Branch:** {branch}",
        f"**Checks:** {', '.join(checks_run) or 'none'}",
        "",
        "## Summary",
        summary,
        "",
        "## Findings",
        "| Risk | Category | Location | Title | ATT&CK |",
        "|------|----------|----------|-------|--------|",
    ]
    for f in findings:
        attack = f.get("attack", "—")
        lines.append(
            f"| {f.get('risk', 'info')} | {f.get('category', '—')} | "
            f"{f.get('location', '—')} | {f.get('title', '—')} | {attack} |"
        )
    lines.append("")
    lines.append("## Threat model notes")
    lines.append(
        "_Findings map to MITRE ATT&CK techniques where applicable; "
        "use with ASVS controls for remediation prioritization._"
    )
    return "\n".join(lines) + "\n"


def run(content: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    repo_source = _parse_field(content, "repo")
    if not repo_source:
        raise ValueError("Input must include Repo: <path or https URL>")

    branch = _parse_field(content, "branch", "main") or "main"
    scope = (_parse_field(content, "focus", "all") or "all").lower()

    repo_ctx = resolve_repo(repo_source, branch=branch)
    scan = run_scan(repo_ctx.path, focus=scope)

    summary = _build_summary(scan.findings, scan.dependency_tools)
    report_md = redact_text(
        _build_report_md(
            repo_display=_repo_display(repo_source),
            scope=scope,
            branch=branch,
            files_scanned=scan.files_scanned,
            summary=summary,
            findings=scan.findings,
            checks_run=scan.checks_run,
        )
    )

    out_dir = resolve_output_dir(context)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"repo-security-review-{datetime.now(timezone.utc).strftime('%Y%m%d')}.md"
    write_text_file(context, "write_local_markdown", report_path, report_md)

    control_tags = aggregate_control_tags(scan.findings)

    return {
        "skill": "repo-security-review",
        "repo": repo_source,
        "repo_path": str(repo_ctx.path),
        "scope": scope,
        "branch": branch,
        "summary": summary,
        "findings": scan.findings,
        "report_file": rel_to_repo(report_path),
        "scan_coverage": {
            "files_scanned": scan.files_scanned,
            "checks_run": scan.checks_run,
            "dependency_tools": scan.dependency_tools,
        },
        "control_tags": control_tags,
    }
