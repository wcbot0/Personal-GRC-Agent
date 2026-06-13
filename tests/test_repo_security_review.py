"""repo-security-review skill tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import jsonschema
import pytest

from spa.paths import ROOT, SKILLS_DIR
from spa.scanners.dependencies import scan_dependencies
from spa.scanners.repo import resolve_repo
from spa.scanners.runner import run_scan
from spa.scanners.secrets import scan_secrets
from spa.skills.repo_security_review import run
from spa.skills.runner import run_skill

FIXTURE_REPO = ROOT / "evals" / "fixtures" / "sample-vuln-repo"
FIXTURE_INPUT = ROOT / "evals" / "fixtures" / "repo_security_review_input.md"


def _validate_output_schema(output: dict) -> None:
    schema_path = SKILLS_DIR / "repo-security-review" / "output.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(output, schema)


def test_scan_secrets_finds_hardcoded_secret():
    findings = scan_secrets(FIXTURE_REPO)
    assert any("secret" in f.title.lower() or "Hardcoded" in f.title for f in findings)


def test_scan_dependencies_flags_unpinned():
    findings, tools = scan_dependencies(FIXTURE_REPO)
    assert any("Unpinned" in f.title for f in findings)
    assert "pip_audit" in tools


def test_run_scan_finds_multiple_issues():
    result = run_scan(FIXTURE_REPO, focus="all")
    assert result.files_scanned >= 2
    assert len(result.findings) >= 3
    risks = {f["risk"] for f in result.findings}
    assert "critical" in risks or "high" in risks


def test_run_skill_integration(tmp_path: Path):
    content = f"Repo: {FIXTURE_REPO}\nFocus: all\n"
    output = run(content, context={"output_dir": tmp_path})
    _validate_output_schema(output)
    assert output["skill"] == "repo-security-review"
    assert len(output["findings"]) >= 3
    assert "repo-security-review" in output["report_file"]
    report = Path(output["report_file"])
    assert report.exists()


def test_run_skill_via_runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SPA_AUDIT_DIR", str(tmp_path / "audit"))
    input_file = tmp_path / "input.md"
    input_file.write_text(f"Repo: {FIXTURE_REPO}\nFocus: all\n", encoding="utf-8")
    result = run_skill("repo-security-review", input_file, output_dir=tmp_path / "drafts")
    _validate_output_schema(result["output"])
    assert all(v["passed"] for v in result["verifications"])


def test_resolve_repo_local_path():
    ctx = resolve_repo(str(FIXTURE_REPO))
    assert ctx.path.exists()
    assert ctx.is_temp is False


def test_resolve_repo_git_clone(tmp_path: Path):
    mock_repo = MagicMock()
    with patch("spa.scanners.repo.Repo.clone_from", mock_repo) as clone:
        with patch("spa.scanners.repo.get_data_dir", return_value=tmp_path):
            with patch("spa.scanners.repo.validate_git_url_host"):
                dest = tmp_path / "org-demo"
                dest.mkdir()
                ctx = resolve_repo("https://github.com/org/demo-app", branch="main")
    clone.assert_called_once()
    assert ctx.is_temp is True
    assert ctx.branch == "main"


def test_pip_audit_mock(tmp_path: Path):
    req = tmp_path / "requirements.txt"
    req.write_text("badpkg==1.0.0\n", encoding="utf-8")
    audit_json = json.dumps(
        [{"name": "badpkg", "vulns": [{"id": "CVE-2024-0001", "severity": "critical"}]}]
    )
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stdout = audit_json
    with patch("spa.scanners.dependencies.shutil.which", return_value="/usr/bin/pip-audit"):
        with patch("spa.scanners.dependencies.subprocess.run", return_value=mock_proc):
            findings, status = scan_dependencies(tmp_path)
    assert status["pip_audit"] == "ran"
    assert any("CVE" in f.title for f in findings)


def test_missing_repo_raises():
    with pytest.raises(FileNotFoundError):
        resolve_repo("/nonexistent/path/to/repo")


def test_fixture_input_file_exists():
    assert FIXTURE_INPUT.exists()
    content = FIXTURE_INPUT.read_text(encoding="utf-8")
    assert "Repo:" in content
