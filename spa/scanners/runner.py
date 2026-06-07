"""Orchestrate repository security scans."""
from __future__ import annotations

from pathlib import Path

from spa.scanners.dependencies import scan_dependencies
from spa.scanners.models import RawFinding, ScanResult
from spa.scanners.owasp import scan_owasp
from spa.scanners.repo import walk_files
from spa.scanners.risk import aggregate_control_tags, finalize_finding, sort_findings
from spa.scanners.secrets import scan_secrets

FOCUS_MODULES = {
    "all": {"secrets", "dependencies", "owasp"},
    "secrets": {"secrets"},
    "dependencies": {"dependencies"},
    "injection": {"owasp"},
    "auth": {"owasp"},
    "config": {"owasp", "secrets"},
}


def run_scan(repo_root: Path, focus: str = "all") -> ScanResult:
    modules = FOCUS_MODULES.get(focus, FOCUS_MODULES["all"])
    raw_findings = []
    checks_run: list[str] = []
    dependency_tools: dict[str, str] = {}

    if "secrets" in modules:
        checks_run.append("secrets")
        raw_findings.extend(scan_secrets(repo_root))

    if "dependencies" in modules:
        checks_run.append("dependencies")
        dep_findings, dependency_tools = scan_dependencies(repo_root)
        raw_findings.extend(dep_findings)

    if "owasp" in modules:
        checks_run.append("owasp_heuristics")
        raw_findings.extend(scan_owasp(repo_root, focus=focus))

    findings = sort_findings([finalize_finding(raw) for raw in raw_findings])

    if not findings:
        empty = finalize_finding(
            RawFinding(
                check_id="none",
                category="Scan complete",
                owasp="N/A",
                default_risk="info",
                title="No issues detected in scope",
                location=str(repo_root.name),
                exploitability="Heuristic scan completed without matches for selected focus.",
                source="heuristic",
            )
        )
        empty["owasp"] = "N/A"
        empty["asvs"] = "N/A"
        empty["attack"] = "N/A"
        findings = [empty]

    return ScanResult(
        findings=findings,
        files_scanned=len(walk_files(repo_root)),
        checks_run=checks_run,
        dependency_tools=dependency_tools,
    )
