"""Dependency manifest checks and optional audit CLI integration."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from spa.scanners.models import RawFinding

REQUIREMENTS_LINE = re.compile(r"^([a-zA-Z0-9_\-\.]+)\s*(.*)$")

AUDIT_TIMEOUT = 30


def _flag_unpinned_requirements(path: Path, repo_root: Path) -> list[RawFinding]:
    findings: list[RawFinding] = []
    rel = path.relative_to(repo_root)
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        match = REQUIREMENTS_LINE.match(stripped)
        if not match:
            continue
        pkg, spec = match.group(1), match.group(2).strip()
        pinned = spec and ("==" in spec or "~=" in spec) and spec not in {"*", "latest"}
        if not pinned:
            findings.append(
                RawFinding(
                    check_id="unpinned_dep",
                    category="A06 Vulnerable Components",
                    owasp="A06:2021",
                    default_risk="medium",
                    title=f"Unpinned dependency: {pkg}",
                    location=f"{rel}:{line_no}",
                    exploitability="Floating version may pull vulnerable releases on install.",
                    source="dependency",
                )
            )
    return findings


def _run_pip_audit(requirements_path: Path) -> tuple[list[RawFinding], str]:
    if not shutil.which("pip-audit"):
        return [], "not_installed"
    try:
        proc = subprocess.run(
            ["pip-audit", "-r", str(requirements_path), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=AUDIT_TIMEOUT,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return [], "timeout"
    if proc.returncode not in (0, 1) or not proc.stdout.strip():
        return [], "error"
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [], "parse_error"

    findings: list[RawFinding] = []
    deps = data if isinstance(data, list) else data.get("dependencies") or []
    for item in deps:
        name = item.get("name", "unknown")
        for vuln in item.get("vulns") or []:
            severity = (vuln.get("severity") or "medium").lower()
            risk = "critical" if severity == "critical" else "high" if severity == "high" else "medium"
            findings.append(
                RawFinding(
                    check_id="pip_audit_cve",
                    category="A06 Vulnerable Components",
                    owasp="A06:2021",
                    default_risk=risk,
                    title=f"Known CVE in {name}: {vuln.get('id', 'CVE')}",
                    location=str(requirements_path.name),
                    exploitability=f"Published vulnerability ({vuln.get('id', 'CVE')}) with {severity} severity.",
                    source="dependency_cve",
                )
            )
    return findings, "ran"


def _run_npm_audit(package_dir: Path) -> tuple[list[RawFinding], str]:
    if not shutil.which("npm"):
        return [], "not_installed"
    lock = package_dir / "package-lock.json"
    if not lock.exists():
        return [], "skipped"
    try:
        proc = subprocess.run(
            ["npm", "audit", "--json"],
            cwd=str(package_dir),
            capture_output=True,
            text=True,
            timeout=AUDIT_TIMEOUT,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return [], "timeout"
    if not proc.stdout.strip():
        return [], "error"
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [], "parse_error"

    findings: list[RawFinding] = []
    advisories: dict[str, Any] = {}
    if "vulnerabilities" in data:
        for name, info in (data.get("vulnerabilities") or {}).items():
            severity = (info.get("severity") or "moderate").lower()
            risk = "critical" if severity == "critical" else "high" if severity == "high" else "medium"
            findings.append(
                RawFinding(
                    check_id="npm_audit_cve",
                    category="A06 Vulnerable Components",
                    owasp="A06:2021",
                    default_risk=risk,
                    title=f"npm advisory: {name}",
                    location="package-lock.json",
                    exploitability=f"npm audit reported {severity} severity for {name}.",
                    source="dependency_cve",
                )
            )
    elif "advisories" in data:
        advisories = data.get("advisories") or {}
        for adv in advisories.values():
            severity = (adv.get("severity") or "moderate").lower()
            risk = "critical" if severity == "critical" else "high" if severity == "high" else "medium"
            findings.append(
                RawFinding(
                    check_id="npm_audit_cve",
                    category="A06 Vulnerable Components",
                    owasp="A06:2021",
                    default_risk=risk,
                    title=f"npm advisory: {adv.get('module_name', 'package')}",
                    location="package-lock.json",
                    exploitability=f"npm audit reported {severity} severity.",
                    source="dependency_cve",
                )
            )
    return findings, "ran"


def scan_dependencies(repo_root: Path) -> tuple[list[RawFinding], dict[str, str]]:
    findings: list[RawFinding] = []
    tools: dict[str, str] = {"pip_audit": "skipped", "npm_audit": "skipped"}

    req = repo_root / "requirements.txt"
    if req.exists():
        findings.extend(_flag_unpinned_requirements(req, repo_root))
        cve_findings, status = _run_pip_audit(req)
        findings.extend(cve_findings)
        tools["pip_audit"] = status

    if (repo_root / "package.json").exists():
        cve_findings, status = _run_npm_audit(repo_root)
        findings.extend(cve_findings)
        tools["npm_audit"] = status

    for pyproject in repo_root.glob("pyproject.toml"):
        findings.append(
            RawFinding(
                check_id="manifest",
                category="A06 Vulnerable Components",
                owasp="A06:2021",
                default_risk="info",
                title="Python project uses pyproject.toml — verify lock/pin strategy",
                location=str(pyproject.relative_to(repo_root)),
                exploitability="Manifest present; manual review recommended for dependency pinning.",
                source="dependency",
            )
        )

    if (repo_root / "go.mod").exists():
        findings.append(
            RawFinding(
                check_id="manifest",
                category="A06 Vulnerable Components",
                owasp="A06:2021",
                default_risk="info",
                title="Go module detected — run govulncheck separately",
                location="go.mod",
                exploitability="Go dependencies require govulncheck for CVE coverage (not run in this scan).",
                source="dependency",
            )
        )

    return findings, tools
