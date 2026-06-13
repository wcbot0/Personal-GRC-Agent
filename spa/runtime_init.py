"""Per-runtime glue generation for spa init --runtime."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from spa.audit.logger import AuditLogger
from spa.paths import ROOT
from spa.tools.guard import ToolGuard

VALID_RUNTIMES = ("cursor", "claude", "chatgpt", "hermes", "openclaw")

MANAGED_MARKER = "# pga-init-managed"


@dataclass
class InitResult:
    runtime: str
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    dry_run: bool = False


def _spa_mcp_command(root: Path) -> list[str]:
    spa = root / ".venv" / "bin" / "spa"
    if spa.is_file():
        return [str(spa), "mcp", "serve"]
    return ["spa", "mcp", "serve"]


def _mcp_servers_block(root: Path, *, claude: bool = False) -> dict[str, Any]:
    cmd, *args = _spa_mcp_command(root)
    if claude:
        cmd = "${CLAUDE_PROJECT_DIR:-.}/.venv/bin/spa"
        if not (root / ".venv" / "bin" / "spa").is_file():
            cmd = "spa"
    server: dict[str, Any] = {
        "type": "stdio",
        "command": cmd,
        "args": args or ["mcp", "serve"],
    }
    return {
        "pga-governed": server,
    }


def _claude_md(root: Path) -> str:
    return f"""{MANAGED_MARKER}

# CLAUDE.md — Personal GRC Agent

Guidance for Claude Code sessions in this repo. **Canonical agent navigation lives in `AGENTS.md`** — read it first.

Also read at session start:
- `agent/charter.md` — persona and draft surfaces
- `agent/autonomy-policy.yaml` — action-risk gates (A0–A5)

Skills under `skills/` are auto-discovered via `SKILL.md` frontmatter. For governed ingest, skills, proposals, and audit, use the **`pga-governed`** MCP server (`spa mcp serve`) or the `spa` CLI — not direct artifact writes when verifiers matter.

```bash
source .venv/bin/activate
spa ingest inbox/<file>.md
spa run-skill meeting-synth --input evals/fixtures/meeting_sample.md
spa proposals list
spa audit verify
```
"""


def _cursor_runtime_mdc() -> str:
    return f"""---
description: PGA runtime init — governed MCP and AGENTS.md authority
alwaysApply: true
---

{MANAGED_MARKER}

# Personal GRC Agent — runtime (Cursor)

Read `AGENTS.md` at session start, then `agent/charter.md` and `agent/autonomy-policy.yaml`.

Use **`pga-governed`** MCP (`spa mcp serve`) for ingest, skills, proposals, and audit. Prefer `spa` CLI in the terminal for verifiable skill runs.
"""


def _chatgpt_runtime_md(root: Path) -> str:
    rel_spa = ".venv/bin/spa"
    return f"""{MANAGED_MARKER}

# ChatGPT / Codex runtime — Personal GRC Agent

Codex CLI reads **`AGENTS.md`** at the repo root natively — no extra agent file required.

## Governed MCP (ChatGPT Desktop)

Register the governed PGA server (stdio):

```json
{json.dumps({"mcpServers": _mcp_servers_block(root)}, indent=2)}
```

Command resolves to `{rel_spa} mcp serve` from the repo root after `./bootstrap.sh`.

## CLI fallback

```bash
source .venv/bin/activate
spa ingest inbox/<file>.md
spa run-skill meeting-synth --input evals/fixtures/meeting_sample.md
```

All writes pass ToolGuard, verifiers, and the hash-chained audit trail.
"""


def _openclaw_config(root: Path) -> dict[str, Any]:
    cmd, *args = _spa_mcp_command(root)
    return {
        "skills": {
            "load": {
                "extraDirs": [str(root / "skills")],
                "watch": True,
            },
        },
        "mcpServers": {
            "pga-governed": {
                "command": cmd,
                "args": args or ["mcp", "serve"],
                "cwd": str(root),
                "enabled": True,
            },
        },
    }


def planned_files(runtime: str, root: Path | None = None) -> dict[str, str]:
    """Return relative path → file content for a runtime profile."""
    root = root or ROOT
    rel_root = root
    files: dict[str, str] = {}

    if runtime == "cursor":
        files[".cursor/mcp.json"] = json.dumps(
            {"mcpServers": _mcp_servers_block(root)},
            indent=2,
        ) + "\n"
        files[".cursor/rules/pga-runtime.mdc"] = _cursor_runtime_mdc()
    elif runtime == "claude":
        files["CLAUDE.md"] = _claude_md(root)
        files[".mcp.json"] = json.dumps(
            {"mcpServers": _mcp_servers_block(root, claude=True)},
            indent=2,
        ) + "\n"
    elif runtime == "chatgpt":
        files["docs/runtimes/chatgpt.md"] = _chatgpt_runtime_md(root)
    elif runtime == "openclaw":
        files[".openclaw/openclaw.json"] = json.dumps(
            _openclaw_config(root),
            indent=2,
        ) + "\n"
        files["docs/runtimes/openclaw.md"] = (
            f"{MANAGED_MARKER}\n\n"
            "# OpenClaw runtime — Personal GRC Agent\n\n"
            "Workspace skills load from `skills/` (SKILL.md). Governed tools use "
            "the `pga-governed` MCP server configured in `.openclaw/openclaw.json`.\n"
        )
    elif runtime == "hermes":
        files["docs/runtimes/hermes.md"] = (
            f"{MANAGED_MARKER}\n\n"
            "# Hermes runtime — Personal GRC Agent\n\n"
            "Run `./scripts/setup-hermes.sh` to register `pga-governed` in "
            "`~/.hermes/config.yaml`. Start sessions from the repo root: `hermes chat`.\n"
        )
    else:
        raise ValueError(f"Unknown runtime {runtime!r}; choose from: {', '.join(VALID_RUNTIMES)}")

    if runtime != "chatgpt" and runtime != "hermes" and runtime != "openclaw":
        pass  # AGENTS.md is verified, not generated

    _ = rel_root  # reserved for future path-relative templates
    return files


def _is_managed(content: str) -> bool:
    return MANAGED_MARKER in content.splitlines()[0:3]


def _write_file(
    guard: ToolGuard,
    path: Path,
    content: str,
    *,
    force: bool,
    dry_run: bool,
) -> tuple[str, bool]:
    """Return (status, changed). status: written|skipped|ok|stale"""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            return "ok", False
        if not force and not _is_managed(existing):
            return "skipped", False
    if dry_run:
        return "planned", True

    path.parent.mkdir(parents=True, exist_ok=True)

    def _do_write() -> dict[str, str]:
        path.write_text(content, encoding="utf-8")
        return {"path": str(path)}

    guard.execute("runtime_init", _do_write, task_class="cli")
    return "written", True


def _verify_agents_md(root: Path) -> str | None:
    agents = root / "AGENTS.md"
    if not agents.is_file():
        return "missing AGENTS.md at repo root"
    return None


def init_runtime(
    runtime: str,
    *,
    root: Path | None = None,
    dry_run: bool = False,
    check: bool = False,
    force: bool = False,
    guard: ToolGuard | None = None,
) -> InitResult:
    if runtime not in VALID_RUNTIMES:
        raise ValueError(f"Unknown runtime {runtime!r}; choose from: {', '.join(VALID_RUNTIMES)}")

    root = (root or ROOT).resolve()
    guard = guard or ToolGuard(audit=AuditLogger())
    result = InitResult(runtime=runtime, dry_run=dry_run)

    agents_err = _verify_agents_md(root)
    if agents_err:
        result.errors.append(agents_err)
        if check:
            return result

    planned = planned_files(runtime, root)
    stale: list[str] = []

    for rel, content in sorted(planned.items()):
        path = root / rel
        if check:
            if not path.is_file():
                stale.append(rel)
                result.errors.append(f"missing {rel}")
            elif path.read_text(encoding="utf-8") != content:
                stale.append(rel)
                result.errors.append(f"stale {rel}")
            else:
                result.checked.append(rel)
            continue

        status, changed = _write_file(guard, path, content, force=force, dry_run=dry_run)
        if status == "written" or status == "planned":
            result.written.append(rel)
        elif status == "skipped":
            result.skipped.append(rel)
        elif status == "ok" and not changed:
            result.checked.append(rel)

    if runtime in {"cursor", "claude"} and not check and not dry_run:
        agents = root / "AGENTS.md"
        if agents.is_file():
            result.checked.append("AGENTS.md")

    if runtime == "hermes" and not check:
        script = root / "scripts" / "setup-hermes.sh"
        if not script.is_file():
            result.errors.append("missing scripts/setup-hermes.sh")
        elif dry_run:
            result.written.append("~/.hermes/config.yaml (via setup-hermes.sh)")
        else:
            try:
                proc = subprocess.run(
                    [str(script)],
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if proc.returncode != 0:
                    result.errors.append(
                        f"setup-hermes.sh exited {proc.returncode}: {proc.stderr.strip() or proc.stdout.strip()}"
                    )
                else:
                    result.written.append("~/.hermes/config.yaml (via setup-hermes.sh)")
            except OSError as exc:
                result.errors.append(f"setup-hermes.sh failed: {exc}")

    if check and stale:
        result.errors.extend([f"drift detected: {s}" for s in stale])

    return result
