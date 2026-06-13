"""SPA CLI — proposals, ingest, skills."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from spa.audit.chain import verify_chain
from spa.evidence.export import export_evidence, parse_export_dates
from spa.governance.approval_queue import ApprovalQueue, ApprovalQueueError
from spa.ingest import ingest_file
from spa.paths import get_audit_logs_dir
from spa.runtime_init import VALID_RUNTIMES


@click.group()
def main() -> None:
    """Security Personal Assistant CLI."""


@main.command("ingest")
@click.argument("file_path")
def ingest_cmd(file_path: str) -> None:
    """Ingest a file into episodic + semantic memory."""
    result = ingest_file(file_path)
    click.echo(json.dumps(result, indent=2))


@main.group("audit")
def audit_group() -> None:
    """Audit log integrity commands."""


@audit_group.command("verify")
@click.option("--dir", "audit_dir", default=None, type=click.Path(exists=True, file_okay=False))
@click.option("--from", "from_date", default=None, help="Start date YYYY-MM-DD")
@click.option("--to", "to_date", default=None, help="End date YYYY-MM-DD")
@click.option("--require-full-chain", is_flag=True, help="Fail if legacy events without hashes exist")
def audit_verify(
    audit_dir: str | None,
    from_date: str | None,
    to_date: str | None,
    require_full_chain: bool,
) -> None:
    """Verify hash chain integrity of audit JSONL logs."""
    log_dir = Path(audit_dir) if audit_dir else get_audit_logs_dir()
    start, end = parse_export_dates(from_date, to_date)
    result = verify_chain(log_dir, start=start, end=end, require_full_chain=require_full_chain)
    payload = {
        "valid": result.valid,
        "event_count": result.event_count,
        "legacy_count": result.legacy_count,
        "chain_starts": result.chain_starts,
        "breaks": [{"event_id": b.event_id, "line": b.line_number, "reason": b.reason} for b in result.breaks],
        "warnings": result.warnings,
    }
    click.echo(json.dumps(payload, indent=2))
    if not result.valid:
        sys.exit(1)


@main.group("evidence")
def evidence_group() -> None:
    """Evidence export commands."""


@evidence_group.command("export")
@click.option("--from", "from_date", default=None, help="Start date YYYY-MM-DD")
@click.option("--to", "to_date", default=None, help="End date YYYY-MM-DD")
@click.option("--output", required=True, type=click.Path(dir_okay=False))
@click.option("--force", is_flag=True, help="Export even if chain verification fails")
def evidence_export(from_date: str | None, to_date: str | None, output: str, force: bool) -> None:
    """Export auditor-ready evidence bundle."""
    start, end = parse_export_dates(from_date, to_date)
    try:
        manifest = export_evidence(output=Path(output), start=start, end=end, force=force)
    except RuntimeError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    click.echo(json.dumps(manifest, indent=2))


@main.group("proposals")
def proposals_group() -> None:
    """Manage change proposal objects (CPOs)."""


@proposals_group.command("list")
@click.option("--status", default="pending", help="Filter by status (pending|approved|rejected|all)")
def proposals_list(status: str) -> None:
    queue = ApprovalQueue()
    filter_status = None if status == "all" else status
    items = queue.list_proposals(status=filter_status)
    if not items:
        click.echo("No proposals found.")
        return
    for cpo in items:
        row = ApprovalQueue.summary_row(cpo)
        click.echo(f"{row['id']}  {row['type']}  {row['risk']}  {row['summary']}")


@proposals_group.command("show")
@click.argument("cpo_id")
def proposals_show(cpo_id: str) -> None:
    queue = ApprovalQueue()
    try:
        detail = queue.get_detail(cpo_id)
    except ApprovalQueueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    click.echo(json.dumps(detail, indent=2))


@proposals_group.command("approve")
@click.argument("cpo_id", required=False)
@click.option("--batch", is_flag=True, help="Batch-approve pending CPOs matching filters")
@click.option("--type", "action_type", default=None, help="Filter by action_type (batch mode)")
@click.option("--max-risk", default="A3", help="Max action class to approve (A3|A4)")
@click.option("--by", "approved_by", default="human-reviewer")
def proposals_approve(
    cpo_id: str | None,
    batch: bool,
    action_type: str | None,
    max_risk: str,
    approved_by: str,
) -> None:
    queue = ApprovalQueue()
    if batch:
        if cpo_id:
            click.echo("Provide either cpo_id or --batch, not both.", err=True)
            sys.exit(1)
        try:
            results = queue.batch_approve(
                action_type=action_type,
                max_risk=max_risk,
                approved_by=approved_by,
            )
        except ApprovalQueueError as exc:
            click.echo(str(exc), err=True)
            sys.exit(1)
        for item in results:
            click.echo(f"Approved {item['cpo']['id']}")
        click.echo(f"Batch approved {len(results)} proposal(s)")
        return

    if not cpo_id:
        click.echo("Missing CPO id. Use 'spa proposals approve <id>' or '--batch'.", err=True)
        sys.exit(1)

    try:
        result = queue.approve_and_execute(cpo_id, approved_by=approved_by)
    except ApprovalQueueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    click.echo(f"Approved {result['cpo']['id']}")
    click.echo(json.dumps(result["execution_result"], indent=2, default=str))


@proposals_group.command("reject")
@click.argument("cpo_id")
@click.option("--reason", required=True, help="Rejection reason (required)")
@click.option("--by", "rejected_by", default="human-reviewer")
def proposals_reject(cpo_id: str, reason: str, rejected_by: str) -> None:
    queue = ApprovalQueue()
    try:
        cpo = queue.reject(cpo_id, reason=reason, rejected_by=rejected_by)
    except ApprovalQueueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    click.echo(f"Rejected {cpo['id']}: {reason}")


@main.group("cloud")
def cloud_group() -> None:
    """Cloud findings commands."""


@cloud_group.command("scan")
@click.option("--provider", default=None, help="Cloud provider (aws|gcp); default: CLOUD_PROVIDER env")
@click.option("--period", default=None, help="Evidence period label (e.g. 2026-Q2)")
@click.option("--output-dir", default=None, type=click.Path(file_okay=False), help="Findings output directory")
def cloud_scan(provider: str | None, period: str | None, output_dir: str | None) -> None:
    """Run read-only cloud checks → findings JSON, ticket proposals, evidence indexes."""
    from spa.audit.logger import AuditLogger
    from spa.cloud_scan import run_cloud_scan
    from spa.tools.guard import ToolGuard

    audit = AuditLogger()
    guard = ToolGuard(audit=audit)
    out = Path(output_dir) if output_dir else None
    result = run_cloud_scan(provider=provider, period=period, guard=guard, output_dir=out)
    click.echo(json.dumps(result, indent=2))


@main.group("tickets")
def tickets_group() -> None:
    """Ticket proposal commands."""


@tickets_group.command("publish")
@click.option("--path", "proposal_path", default=None, type=click.Path(exists=True, dir_okay=False))
@click.option("--id", "ticket_id", default=None, help="Ticket proposal id (e.g. AI-PROPOSED-001)")
@click.option("--skill", default="ticket-draft", help="Originating skill for provenance")
def tickets_publish(proposal_path: str | None, ticket_id: str | None, skill: str) -> None:
    """Propose publishing an AI-Proposed ticket draft to an external system (CPO-gated)."""
    from spa.audit.logger import AuditLogger
    from spa.tools.guard import ToolGuard
    from spa.workflows.ticket_publish import propose_ai_proposed_ticket_cpo

    if not proposal_path and not ticket_id:
        click.echo("Provide --path or --id.", err=True)
        sys.exit(1)

    audit = AuditLogger()
    guard = ToolGuard(audit=audit)
    try:
        cpo_id = propose_ai_proposed_ticket_cpo(
            guard=guard,
            queue=guard.queue,
            path=proposal_path,
            ticket_id=ticket_id,
            skill=skill,
        )
    except FileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    click.echo(json.dumps({"cpo_id": cpo_id, "status": "pending"}, indent=2))


@main.group("mcp")
def mcp_group() -> None:
    """MCP server commands."""


@mcp_group.command("serve")
def mcp_serve() -> None:
    """Start the governed MCP server (stdio transport)."""
    from spa.mcp_server import serve_stdio

    serve_stdio()


@main.command("run-skill")
@click.argument("skill_name")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--output-dir", default=None, type=click.Path())
def run_skill(skill_name: str, input_path: str, output_dir: str | None) -> None:
    """Run a drafting skill."""
    from spa.skills.runner import run_skill as _run

    result = _run(skill_name, input_path, output_dir=output_dir)
    click.echo(json.dumps(result, indent=2, default=str))


@main.command("init")
@click.option(
    "--runtime",
    required=True,
    type=click.Choice(list(VALID_RUNTIMES)),
    help="Runtime profile: cursor, claude, chatgpt, hermes, openclaw",
)
@click.option("--dry-run", is_flag=True, help="Print planned changes without writing")
@click.option("--check", is_flag=True, help="Exit nonzero if glue is missing or stale")
@click.option("--force", is_flag=True, help="Overwrite user-modified managed files")
def init_cmd(runtime: str, dry_run: bool, check: bool, force: bool) -> None:
    """Generate or validate per-runtime glue (MCP registration, agent docs)."""
    from spa.runtime_init import init_runtime

    try:
        result = init_runtime(runtime, dry_run=dry_run, check=check, force=force)
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    if dry_run:
        for path in result.written:
            click.echo(f"would write: {path}")
        for path in result.skipped:
            click.echo(f"would skip (user-modified): {path}")
        for path in result.checked:
            click.echo(f"ok: {path}")
    else:
        for path in result.written:
            click.echo(f"written: {path}")
        for path in result.skipped:
            click.echo(f"skipped: {path}")
        for path in result.checked:
            click.echo(f"ok: {path}")

    for err in result.errors:
        click.echo(err, err=True)

    if result.errors and check:
        sys.exit(1)
    if result.errors and not dry_run and runtime != "hermes":
        sys.exit(1)


if __name__ == "__main__":
    main()
