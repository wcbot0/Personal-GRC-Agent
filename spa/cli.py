"""SPA CLI — proposals, ingest, skills."""
from __future__ import annotations

import json
import sys

import click

from spa.governance.approval_queue import ApprovalQueue, ApprovalQueueError
from spa.ingest import ingest_file


@click.group()
def main() -> None:
    """Security Personal Assistant CLI."""


@main.command("ingest")
@click.argument("file_path")
def ingest_cmd(file_path: str) -> None:
    """Ingest a file into episodic + semantic memory."""
    result = ingest_file(file_path)
    click.echo(json.dumps(result, indent=2))


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
        click.echo(f"{cpo['id']}  [{cpo['status']}]  {cpo['title']}  ({cpo['action_class']})")


@proposals_group.command("show")
@click.argument("cpo_id")
def proposals_show(cpo_id: str) -> None:
    queue = ApprovalQueue()
    try:
        cpo = queue.get(cpo_id)
    except ApprovalQueueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    click.echo(json.dumps(cpo, indent=2))


@proposals_group.command("approve")
@click.argument("cpo_id")
@click.option("--by", "approved_by", default="human-reviewer")
def proposals_approve(cpo_id: str, approved_by: str) -> None:
    queue = ApprovalQueue()
    try:
        cpo = queue.approve(cpo_id, approved_by=approved_by)
    except ApprovalQueueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    click.echo(f"Approved {cpo['id']}")


@proposals_group.command("batch-approve")
@click.option("--type", "action_type", default=None, help="Filter by action_type")
@click.option("--max-risk", default="A3", help="Max action class to approve (A3|A4)")
@click.option("--by", "approved_by", default="human-reviewer")
def proposals_batch_approve(action_type: str | None, max_risk: str, approved_by: str) -> None:
    """Batch-approve pending CPOs matching type and max risk."""
    queue = ApprovalQueue()
    risk_order = ["A3", "A4", "A5"]
    if max_risk not in risk_order:
        click.echo("max-risk must be A3 or A4", err=True)
        raise SystemExit(1)
    allowed = set(risk_order[: risk_order.index(max_risk) + 1])
    count = 0
    for cpo in queue.list_proposals(status="pending"):
        if cpo["action_class"] not in allowed:
            continue
        if action_type and cpo.get("action_type") != action_type:
            continue
        queue.approve(cpo["id"], approved_by=approved_by)
        click.echo(f"Approved {cpo['id']}")
        count += 1
    click.echo(f"Batch approved {count} proposal(s)")


@proposals_group.command("reject")
@click.argument("cpo_id")
@click.option("--reason", required=True)
@click.option("--by", "rejected_by", default="human-reviewer")
def proposals_reject(cpo_id: str, reason: str, rejected_by: str) -> None:
    queue = ApprovalQueue()
    try:
        cpo = queue.reject(cpo_id, reason=reason, rejected_by=rejected_by)
    except ApprovalQueueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    click.echo(f"Rejected {cpo['id']}: {reason}")


@main.command("run-skill")
@click.argument("skill_name")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
@click.option("--output-dir", default=None, type=click.Path())
def run_skill(skill_name: str, input_path: str, output_dir: str | None) -> None:
    """Run a drafting skill."""
    from spa.skills.runner import run_skill as _run

    result = _run(skill_name, input_path, output_dir=output_dir)
    click.echo(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
