"""Repository resolution and file walking."""
from __future__ import annotations

import ipaddress
import os
import re
import shutil
import socket
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from git import Repo

from spa.paths import get_data_dir

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
    ".tox",
    "vendor",
}

BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".woff", ".woff2", ".pyc", ".so", ".dylib", ".exe", ".zip", ".tar", ".gz"}

_BRANCH_RE = re.compile(r"[A-Za-z0-9._/-]+")
AddrInfoResolver = Callable[[str, int | None], list[tuple[int, int, int, int, tuple]]]
IpAddress = ipaddress.IPv4Address | ipaddress.IPv6Address

# Defense-in-depth hardening for the clone subprocess:
# - GIT_ALLOW_PROTOCOL=https blocks redirect/submodule pivots to file/ext/ssh.
# - http.followRedirects=false stops HTTP redirect-based pivots to a new host
#   (which would otherwise bypass the validated-host check below).
_GIT_CLONE_ENV = {"GIT_ALLOW_PROTOCOL": "https"}
_GIT_CLONE_MULTI_OPTIONS = ["-c http.followRedirects=false"]


@dataclass
class RepoContext:
    source: str
    path: Path
    branch: str
    is_temp: bool = False


class RepoScanError(ValueError):
    pass


def _is_git_url(repo: str) -> bool:
    parsed = urlparse(repo.strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def _allow_internal_hosts() -> bool:
    return os.getenv("REPO_SCAN_ALLOW_INTERNAL", "").lower() in ("1", "true", "yes")


def _validate_branch(branch: str) -> None:
    if not _BRANCH_RE.fullmatch(branch):
        raise RepoScanError(f"Invalid branch name: {branch!r}")


def _resolve_host_addresses(
    host: str,
    *,
    resolver: AddrInfoResolver = socket.getaddrinfo,
) -> list[IpAddress]:
    addresses: list[IpAddress] = []
    for family, _, _, _, sockaddr in resolver(host, None):
        if family in (socket.AF_INET, socket.AF_INET6):
            addresses.append(ipaddress.ip_address(sockaddr[0]))
    return addresses


def _is_blocked_address(addr: IpAddress, *, allow_internal: bool) -> bool:
    # Link-local (IPv4 169.254.0.0/16, IPv6 fe80::/10) is ALWAYS blocked because
    # it covers cloud metadata endpoints (e.g. 169.254.169.254) — the highest-impact
    # SSRF target. REPO_SCAN_ALLOW_INTERNAL never loosens this.
    if addr.is_link_local:
        return True
    if addr.is_global:
        return False
    # Non-global: only RFC1918 private ranges and loopback may be loosened for
    # legitimate internal git servers. Multicast/reserved/etc. stay blocked.
    if allow_internal and (addr.is_private or addr.is_loopback):
        return False
    return True


def validate_git_url_host(
    url: str,
    *,
    resolver: AddrInfoResolver = socket.getaddrinfo,
) -> list[IpAddress]:
    """Resolve and validate the host once, returning the approved addresses.

    The returned addresses are the set we approved at validation time; callers
    should treat them as the trusted resolution and avoid re-resolving the host
    through an unguarded path.
    """
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise RepoScanError("Git URLs must use https with a hostname")

    host = parsed.hostname
    if not host:
        raise RepoScanError("Git URL missing hostname")

    allow_internal = _allow_internal_hosts()

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        if _is_blocked_address(literal, allow_internal=allow_internal):
            raise RepoScanError(f"Blocked address: {host}")
        return [literal]

    try:
        addresses = _resolve_host_addresses(host, resolver=resolver)
    except socket.gaierror as exc:
        raise RepoScanError(f"Cannot resolve host: {host}") from exc

    if not addresses:
        raise RepoScanError(f"No addresses resolved for host: {host}")

    for addr in addresses:
        if _is_blocked_address(addr, allow_internal=allow_internal):
            raise RepoScanError(f"Blocked address for host {host}: {addr}")
    return addresses


def resolve_repo(repo: str, branch: str = "main") -> RepoContext:
    repo = repo.strip()
    _validate_branch(branch)
    if _is_git_url(repo):
        # Validate (and resolve) the host once here. Residual TOCTOU: git performs
        # its OWN DNS lookup at clone time, so a DNS-rebinding attacker could still
        # swap to a blocked IP between this check and the clone. We shrink the
        # window by forbidding redirect/protocol pivots below; the complete fix is
        # running clones behind network isolation or an egress proxy that enforces
        # the allowlist at connect time.
        validate_git_url_host(repo)
        scans_dir = get_data_dir() / "scans"
        scans_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", urlparse(repo).path.strip("/"))[:80] or "repo"
        dest = scans_dir / slug
        if dest.exists():
            shutil.rmtree(dest)
        Repo.clone_from(
            repo,
            dest,
            depth=1,
            branch=branch,
            single_branch=True,
            env=dict(_GIT_CLONE_ENV),
            multi_options=list(_GIT_CLONE_MULTI_OPTIONS),
            allow_unsafe_options=True,
        )
        return RepoContext(source=repo, path=dest.resolve(), branch=branch, is_temp=True)

    path = Path(repo).expanduser()
    if not path.is_absolute():
        path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Repo path does not exist: {repo}")
    if not path.is_dir():
        raise NotADirectoryError(f"Repo path is not a directory: {repo}")
    return RepoContext(source=repo, path=path, branch=branch, is_temp=False)


def should_scan_file(path: Path, repo_root: Path) -> bool:
    if not path.is_file():
        return False
    rel = path.relative_to(repo_root)
    if any(part in SKIP_DIR_NAMES for part in rel.parts):
        return False
    if path.suffix.lower() in BINARY_SUFFIXES:
        return False
    return True


def walk_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo_root.rglob("*"):
        if should_scan_file(path, repo_root):
            files.append(path)
    return files
