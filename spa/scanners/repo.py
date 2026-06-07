"""Repository resolution and file walking."""
from __future__ import annotations

import re
import shutil
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


@dataclass
class RepoContext:
    source: str
    path: Path
    branch: str
    is_temp: bool = False


def _is_git_url(repo: str) -> bool:
    parsed = urlparse(repo.strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def resolve_repo(repo: str, branch: str = "main") -> RepoContext:
    repo = repo.strip()
    if _is_git_url(repo):
        scans_dir = get_data_dir() / "scans"
        scans_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", urlparse(repo).path.strip("/"))[:80] or "repo"
        dest = scans_dir / slug
        if dest.exists():
            shutil.rmtree(dest)
        Repo.clone_from(repo, dest, depth=1, branch=branch, single_branch=True)
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
