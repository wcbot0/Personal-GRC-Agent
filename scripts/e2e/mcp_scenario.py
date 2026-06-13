#!/usr/bin/env python3
"""Shared E2E scenario: inbox → governed skill → CPO → approve → audit verify."""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from spa.audit.chain import verify_chain
from spa.audit.logger import AuditLogger
from spa.governance.approval_queue import ApprovalQueue
from spa.paths import ROOT
from spa.tools.guard import ToolBlockedError, ToolGuard


def _prepare_env(work_root: Path) -> dict[str, str]:
    data = work_root / "data"
    audit = work_root / "audit"
    queue = work_root / "queue"
    inbox = work_root / "inbox"
    for path in (data, audit, queue, inbox):
        path.mkdir(parents=True, exist_ok=True)
    fixture = ROOT / "evals/fixtures/meeting_sample.md"
    inbox_file = inbox / "meeting_sample.md"
    shutil.copy(fixture, inbox_file)
    return {
        "SPA_DATA_DIR": str(data),
        "SPA_AUDIT_DIR": str(audit),
        "SPA_APPROVAL_QUEUE_DIR": str(queue),
        "SPA_NO_LLM": "1",
        "inbox_file": str(inbox_file),
        "data_dir": str(data),
        "audit_dir": str(audit),
        "queue_dir": str(queue),
    }


def _seed_cpo(queue_dir: str, audit_dir: str) -> str:
    audit = AuditLogger(log_dir=Path(audit_dir))
    queue = ApprovalQueue(queue_dir=Path(queue_dir), audit=audit)
    guard = ToolGuard(queue=queue, audit=audit)

    def _create() -> dict:
        return queue.create(
            action_class="A3",
            action_type="assign_human",
            title="E2E test — assign ticket for human review",
            description="Governed E2E scenario CPO",
            risk_rationale="Assignee would change from unassigned",
            proposed_change={"ticket_id": "AI-PROPOSED-E2E", "assignee": "security-lead"},
        )

    try:
        guard.check_allowed("assign_human", create_cpo=_create)
    except ToolBlockedError as exc:
        if exc.cpo_id:
            return exc.cpo_id
    pending = queue.list_proposals(status="pending")
    if not pending:
        raise RuntimeError("expected pending CPO after assign_human gate")
    return pending[0]["id"]


async def _mcp_flow(env: dict[str, str]) -> str:
    out_dir = Path(env["data_dir"]) / "drafts" / "meeting-synth"
    out_dir.mkdir(parents=True, exist_ok=True)
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "spa.mcp_server"],
        env={
            "SPA_DATA_DIR": env["SPA_DATA_DIR"],
            "SPA_AUDIT_DIR": env["SPA_AUDIT_DIR"],
            "SPA_APPROVAL_QUEUE_DIR": env["SPA_APPROVAL_QUEUE_DIR"],
            "SPA_NO_LLM": "1",
        },
        cwd=str(ROOT),
    )

    cpo_id = _seed_cpo(env["queue_dir"], env["audit_dir"])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            ingest = await session.call_tool("pga_ingest", arguments={"path": env["inbox_file"]})
            if ingest.isError:
                raise RuntimeError(f"pga_ingest failed: {ingest.content}")
            assert "meeting_synth" in ingest.content[0].text

            skill = await session.call_tool(
                "pga_run_skill",
                arguments={
                    "skill": "meeting-synth",
                    "input_path": env["inbox_file"],
                    "output_dir": str(out_dir),
                },
            )
            if skill.isError:
                raise RuntimeError(f"pga_run_skill failed: {skill.content}")
            skill_payload = json.loads(skill.content[0].text)
            assert skill_payload.get("skill") == "meeting-synth"

            proposals = await session.call_tool("pga_proposals_list", arguments={"status": "pending"})
            pending = json.loads(proposals.content[0].text)
            if not any(p["id"] == cpo_id for p in pending):
                raise RuntimeError(f"CPO {cpo_id} not in pending list")

            approve = await session.call_tool(
                "pga_proposals_approve",
                arguments={"id": cpo_id, "confirm": True},
            )
            if approve.isError:
                raise RuntimeError(f"pga_proposals_approve failed: {approve.content}")

            verify = await session.call_tool("pga_audit_verify", arguments={})
            verify_payload = json.loads(verify.content[0].text)
            if not verify_payload.get("valid"):
                raise RuntimeError(f"audit verify failed: {verify_payload}")

    chain = verify_chain(Path(env["audit_dir"]))
    if not chain.valid:
        raise RuntimeError(f"local audit verify failed: {chain.breaks}")
    return cpo_id


def main() -> int:
    parser = argparse.ArgumentParser(description="PGA governed MCP E2E scenario")
    parser.add_argument("--runtime", default="cli", help="Runtime label for logging")
    parser.add_argument("--work-dir", default=None, help="Temp work directory")
    args = parser.parse_args()

    work_root = Path(args.work_dir) if args.work_dir else ROOT / "workspace/.data/e2e" / args.runtime
    work_root.mkdir(parents=True, exist_ok=True)
    env = _prepare_env(work_root)

    try:
        cpo_id = asyncio.run(_mcp_flow(env))
    except Exception as exc:
        print(f"E2E FAILED ({args.runtime}): {exc}", file=sys.stderr)
        return 1

    print(f"E2E OK ({args.runtime}): ingest + meeting-synth + CPO {cpo_id} approved + audit valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
