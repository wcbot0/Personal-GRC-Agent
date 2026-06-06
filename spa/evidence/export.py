"""Evidence bundle export for auditors."""
from __future__ import annotations

import hashlib
import json
import tarfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from spa.audit.chain import iter_log_events, verify_chain
from spa.governance.policy import AutonomyPolicy
from spa.paths import APPROVAL_QUEUE_DIR, AUTONOMY_POLICY, GOVERNANCE_DIR, REDACTION_RULES, get_audit_logs_dir


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _cpo_in_range(cpo: dict[str, Any], start: date | None, end: date | None) -> bool:
    created = datetime.fromisoformat(cpo["created_at"].replace("Z", "+00:00")).date()
    if start and created < start:
        return False
    if end and created > end:
        return False
    return True


def _latest_m3_report() -> Path | None:
    history = GOVERNANCE_DIR / "eval-history"
    if not history.exists():
        return None
    reports = sorted(history.glob("m3-*.json"))
    return reports[-1] if reports else None


def export_evidence(
    *,
    output: Path,
    audit_dir: Path | None = None,
    queue_dir: Path | None = None,
    start: date | None = None,
    end: date | None = None,
    force: bool = False,
) -> dict[str, Any]:
    audit_dir = audit_dir or get_audit_logs_dir()
    queue_dir = queue_dir or APPROVAL_QUEUE_DIR
    verify = verify_chain(audit_dir)
    if not verify.valid and not force:
        raise RuntimeError(
            f"Audit chain verification failed ({len(verify.breaks)} break(s)); use --force to export anyway"
        )

    staging = output.parent / f".export-staging-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    staging.mkdir(parents=True, exist_ok=True)

    audit_out = staging / "audit"
    audit_out.mkdir(exist_ok=True)
    event_count = 0
    for path, _, event in iter_log_events(audit_dir):
        event_date = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")).date()
        if start and event_date < start:
            continue
        if end and event_date > end:
            continue
        day_file = audit_out / path.name
        with day_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        event_count += 1

    cpo_out = staging / "cpo"
    cpo_out.mkdir(exist_ok=True)
    cpo_count = 0
    if queue_dir.exists():
        for path in sorted(queue_dir.glob("cpo-*.json")):
            cpo = json.loads(path.read_text(encoding="utf-8"))
            if _cpo_in_range(cpo, start, end):
                (cpo_out / path.name).write_text(json.dumps(cpo, indent=2), encoding="utf-8")
                cpo_count += 1

    policy_out = staging / "policy"
    policy_out.mkdir(exist_ok=True)
    for src in (AUTONOMY_POLICY, REDACTION_RULES):
        if src.exists():
            (policy_out / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    evals_out = staging / "evals"
    evals_out.mkdir(exist_ok=True)
    m3 = _latest_m3_report()
    if m3:
        (evals_out / m3.name).write_text(m3.read_text(encoding="utf-8"), encoding="utf-8")

    try:
        policy_version = AutonomyPolicy.load().version
    except Exception:  # noqa: BLE001
        policy_version = None

    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "policy_version": policy_version,
        "date_range": {"from": start.isoformat() if start else None, "to": end.isoformat() if end else None},
        "audit_event_count": event_count,
        "cpo_count": cpo_count,
        "chain_verification": {
            "valid": verify.valid,
            "event_count": verify.event_count,
            "legacy_count": verify.legacy_count,
            "breaks": [break_.reason for break_ in verify.breaks],
            "warnings": verify.warnings,
        },
        "files": [],
    }
    manifest_path = staging / "manifest.json"

    manifest_files: list[dict[str, str]] = []
    for file_path in sorted(staging.rglob("*")):
        if file_path.is_file():
            rel = str(file_path.relative_to(staging))
            manifest_files.append({"path": rel, "sha256": _sha256_file(file_path)})
    manifest["files"] = manifest_files

    manifest_body = json.dumps(manifest, indent=2)
    manifest_self_hash = hashlib.sha256(manifest_body.encode("utf-8")).hexdigest()
    manifest["files"] = manifest_files + [{"path": "manifest.json", "sha256": manifest_self_hash}]
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as tar:
        tar.add(staging, arcname=output.stem)

    for file_path in sorted(staging.rglob("*"), reverse=True):
        if file_path.is_file():
            file_path.unlink()
    for dir_path in sorted([p for p in staging.rglob("*") if p.is_dir()], reverse=True):
        dir_path.rmdir()
    staging.rmdir()

    return manifest


def parse_export_dates(from_date: str | None, to_date: str | None) -> tuple[date | None, date | None]:
    return _parse_date(from_date), _parse_date(to_date)
