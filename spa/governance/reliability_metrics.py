"""Reliability metrics M1/M2/M3 from audit and eval history."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spa.paths import GOVERNANCE_DIR, get_audit_logs_dir

EVAL_HISTORY_DIR = GOVERNANCE_DIR / "eval-history"
FINDING_EVENTS = {
    "ticket_draft_created",
    "cloud_scan_complete",
    "skill_failed",
}
CPO_EVENT = "cpo_created"


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_audit_events(audit_dir: Path | None = None) -> list[dict[str, Any]]:
    audit_dir = audit_dir or get_audit_logs_dir()
    events: list[dict[str, Any]] = []
    if not audit_dir.exists():
        return events
    for path in sorted(audit_dir.glob("audit-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    events.sort(key=lambda e: e.get("timestamp", ""))
    return events


def compute_m1_first_pass_acceptance(events: list[dict[str, Any]]) -> dict[str, Any]:
    """M1: skill drafts accepted on first verifier pass (proxy for first-pass acceptance)."""
    complete = [e for e in events if e.get("event_type") == "skill_complete"]
    failed = [e for e in events if e.get("event_type") == "skill_failed"]
    total = len(complete) + len(failed)
    rate = len(complete) / total if total else None
    return {
        "metric": "M1",
        "label": "first_pass_acceptance",
        "accepted": len(complete),
        "rejected_or_escalated": len(failed),
        "total": total,
        "rate": round(rate, 4) if rate is not None else None,
        "rate_pct": f"{rate:.0%}" if rate is not None else "n/a",
    }


def compute_m2_time_to_detect(events: list[dict[str, Any]]) -> dict[str, Any]:
    """M2: mean hours from finding/risk signal to CPO creation."""
    finding_times: list[datetime] = []
    cpo_times: list[datetime] = []
    deltas_hours: list[float] = []

    for event in events:
        ts = _parse_ts(event.get("timestamp"))
        if not ts:
            continue
        if event.get("event_type") in FINDING_EVENTS:
            finding_times.append(ts)
        if event.get("event_type") == CPO_EVENT:
            cpo_times.append(ts)

    for f_ts in finding_times:
        later_cpos = [c for c in cpo_times if c >= f_ts]
        if later_cpos:
            delta = (later_cpos[0] - f_ts).total_seconds() / 3600
            deltas_hours.append(delta)

    mean_hours = sum(deltas_hours) / len(deltas_hours) if deltas_hours else None
    return {
        "metric": "M2",
        "label": "time_to_detect_hours",
        "samples": len(deltas_hours),
        "mean_hours": round(mean_hours, 2) if mean_hours is not None else None,
        "finding_events": len(finding_times),
        "cpo_events": len(cpo_times),
    }


def load_m3_verifier_pass_rate(history_dir: Path | None = None) -> dict[str, Any]:
    """M3: latest verifier first-pass rate from eval-history."""
    history_dir = history_dir or EVAL_HISTORY_DIR
    reports = sorted(history_dir.glob("m3-*.json"), reverse=True)
    if not reports:
        return {
            "metric": "M3",
            "label": "verifier_first_pass_rate",
            "rate": None,
            "rate_pct": "n/a",
            "source": None,
        }
    latest_path = reports[0]
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    rate = latest.get("first_pass_rate")
    try:
        source = str(latest_path.relative_to(GOVERNANCE_DIR.parent))
    except ValueError:
        source = str(latest_path)
    return {
        "metric": "M3",
        "label": "verifier_first_pass_rate",
        "rate": rate,
        "rate_pct": f"{rate:.0%}" if isinstance(rate, (int, float)) else "n/a",
        "source": source,
        "first_pass_count": latest.get("first_pass_count"),
        "total_skills": latest.get("total_skills"),
    }


def compute_all_metrics(
    *,
    audit_dir: Path | None = None,
    history_dir: Path | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    events = _load_audit_events(audit_dir)
    m1 = compute_m1_first_pass_acceptance(events)
    m2 = compute_m2_time_to_detect(events)
    m3 = load_m3_verifier_pass_rate(history_dir)
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {"M1": m1, "M2": m2, "M3": m3},
    }
    if persist:
        history_dir = history_dir or EVAL_HISTORY_DIR
        history_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = history_dir / f"m1-m2-{stamp}.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        try:
            report["persisted_to"] = str(out.relative_to(GOVERNANCE_DIR.parent))
        except ValueError:
            report["persisted_to"] = str(out)
    return report
