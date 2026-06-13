"""Repo scanner SSRF and branch validation tests."""
from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

import pytest

from spa.scanners.repo import RepoScanError, resolve_repo, validate_git_url_host


def _mock_resolver(*addresses: str):
    def resolver(host: str, port: int | None) -> list[tuple]:
        families = {4: socket.AF_INET, 6: socket.AF_INET6}
        out = []
        for addr in addresses:
            family = families[6] if ":" in addr else families[4]
            out.append((family, socket.SOCK_STREAM, 6, "", (addr, 0)))
        return out

    return resolver


def test_validate_git_url_blocks_loopback_literal():
    with pytest.raises(RepoScanError, match="Blocked address"):
        validate_git_url_host("https://127.0.0.1/repo.git")


def test_validate_git_url_blocks_private_literal():
    with pytest.raises(RepoScanError, match="Blocked address"):
        validate_git_url_host("https://192.168.1.1/repo.git")


def test_validate_git_url_blocks_resolved_private_host():
    resolver = _mock_resolver("10.0.0.5")
    with pytest.raises(RepoScanError, match="Blocked address"):
        validate_git_url_host("https://internal.example/repo.git", resolver=resolver)


def test_validate_git_url_allows_public_host():
    resolver = _mock_resolver("93.184.216.34")
    assert validate_git_url_host("https://github.com/org/repo.git", resolver=resolver)


def test_validate_git_url_returns_validated_addresses():
    resolver = _mock_resolver("93.184.216.34")
    addrs = validate_git_url_host("https://github.com/org/repo.git", resolver=resolver)
    assert [str(a) for a in addrs] == ["93.184.216.34"]


def test_validate_git_url_internal_override_allows_loopback(monkeypatch):
    monkeypatch.setenv("REPO_SCAN_ALLOW_INTERNAL", "true")
    assert validate_git_url_host("https://127.0.0.1/repo.git")


def test_validate_git_url_internal_override_allows_rfc1918(monkeypatch):
    monkeypatch.setenv("REPO_SCAN_ALLOW_INTERNAL", "true")
    resolver = _mock_resolver("10.0.0.5")
    assert validate_git_url_host("https://git.internal/repo.git", resolver=resolver)


def test_metadata_ip_blocked_even_with_internal_override_literal(monkeypatch):
    monkeypatch.setenv("REPO_SCAN_ALLOW_INTERNAL", "true")
    with pytest.raises(RepoScanError, match="Blocked address"):
        validate_git_url_host("https://169.254.169.254/latest/meta-data/")


def test_metadata_ip_blocked_even_with_internal_override_resolved(monkeypatch):
    monkeypatch.setenv("REPO_SCAN_ALLOW_INTERNAL", "true")
    resolver = _mock_resolver("169.254.169.254")
    with pytest.raises(RepoScanError, match="Blocked address"):
        validate_git_url_host("https://rebind.example/repo.git", resolver=resolver)


def test_ipv6_link_local_blocked_with_internal_override(monkeypatch):
    monkeypatch.setenv("REPO_SCAN_ALLOW_INTERNAL", "true")
    with pytest.raises(RepoScanError, match="Blocked address"):
        validate_git_url_host("https://[fe80::1]/repo.git")


def test_resolve_repo_rejects_invalid_branch(tmp_path):
    with pytest.raises(RepoScanError, match="Invalid branch"):
        resolve_repo("https://github.com/org/repo.git", branch="main;--upload-pack=evil")


def test_resolve_repo_rejects_internal_url(tmp_path, monkeypatch):
    monkeypatch.delenv("REPO_SCAN_ALLOW_INTERNAL", raising=False)
    with pytest.raises(RepoScanError, match="Blocked address"):
        resolve_repo("https://169.254.169.254/meta", branch="main")


def test_resolve_repo_metadata_blocked_with_override(tmp_path, monkeypatch):
    monkeypatch.setenv("REPO_SCAN_ALLOW_INTERNAL", "true")
    with pytest.raises(RepoScanError, match="Blocked address"):
        resolve_repo("https://169.254.169.254/meta", branch="main")


def test_resolve_repo_git_clone_with_mocked_validation(tmp_path):
    mock_repo = MagicMock()
    with patch("spa.scanners.repo.Repo.clone_from", mock_repo) as clone:
        with patch("spa.scanners.repo.get_data_dir", return_value=tmp_path):
            with patch("spa.scanners.repo.validate_git_url_host") as validate:
                dest = tmp_path / "org-demo"
                dest.mkdir()
                ctx = resolve_repo("https://github.com/org/demo-app", branch="main")
    validate.assert_called_once()
    clone.assert_called_once()
    assert ctx.is_temp is True
    assert ctx.branch == "main"


def test_clone_applies_redirect_and_protocol_hardening(tmp_path):
    mock_repo = MagicMock()
    with patch("spa.scanners.repo.Repo.clone_from", mock_repo) as clone:
        with patch("spa.scanners.repo.get_data_dir", return_value=tmp_path):
            with patch("spa.scanners.repo.validate_git_url_host"):
                (tmp_path / "org-demo").mkdir()
                resolve_repo("https://github.com/org/demo-app", branch="main")
    _, kwargs = clone.call_args
    multi_options = kwargs["multi_options"]
    assert any("http.followRedirects=false" in opt for opt in multi_options)
    assert kwargs["env"]["GIT_ALLOW_PROTOCOL"] == "https"
