"""Hash-chained audit log integrity utilities."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


GENESIS_HASH = "0" * 64


@dataclass
class ChainBreak:
    event_id: str | None
    line_number: int
    reason: str


@dataclass
class VerifyResult:
    valid: bool
    event_count: int
    legacy_count: int
    chain_starts: int
    breaks: list[ChainBreak] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class _SegmentResult:
    breaks: list[ChainBreak]
    legacy_count: int
    chain_starts: int
    last_hash: str | None


def canonical_payload(event: dict[str, Any]) -> bytes:
    payload = {k: v for k, v in event.items() if k != "event_hash"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_event_hash(event: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_payload(event)).hexdigest()


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def iter_log_events(log_dir: Path) -> list[tuple[Path, int, dict[str, Any]]]:
    records: list[tuple[Path, int, dict[str, Any]]] = []
    for path in sorted(log_dir.glob("audit-*.jsonl")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip():
                records.append((path, line_no, json.loads(line)))
    records.sort(key=lambda item: _parse_timestamp(item[2]["timestamp"]))
    return records


def load_chain_head(log_dir: Path) -> str | None:
    records = iter_log_events(log_dir)
    for _, _, event in reversed(records):
        if event.get("event_hash"):
            return str(event["event_hash"])
    return None


def _in_date_range(timestamp: str, start: date | None, end: date | None) -> bool:
    event_date = _parse_timestamp(timestamp).date()
    if start and event_date < start:
        return False
    if end and event_date > end:
        return False
    return True


def _verify_records(
    records: list[tuple[Path, int, dict[str, Any]]],
    *,
    initial_expected_prev: str | None = None,
    require_full_chain: bool = False,
) -> _SegmentResult:
    breaks: list[ChainBreak] = []
    legacy_count = 0
    chain_starts = 0
    expected_prev = initial_expected_prev

    for path, line_no, event in records:
        event_hash = event.get("event_hash")
        prev_hash = event.get("prev_event_hash")

        if not event_hash:
            legacy_count += 1
            if require_full_chain:
                breaks.append(
                    ChainBreak(
                        event_id=event.get("event_id"),
                        line_number=line_no,
                        reason=f"legacy event without hash in {path.name}",
                    )
                )
            continue

        if expected_prev is None:
            if prev_hash != GENESIS_HASH:
                breaks.append(
                    ChainBreak(
                        event_id=event.get("event_id"),
                        line_number=line_no,
                        reason=f"chain segment must start with GENESIS prev hash, got {prev_hash}",
                    )
                )
            chain_starts += 1
        elif prev_hash != expected_prev:
            breaks.append(
                ChainBreak(
                    event_id=event.get("event_id"),
                    line_number=line_no,
                    reason=f"prev_event_hash mismatch (expected {expected_prev}, got {prev_hash})",
                )
            )

        computed = compute_event_hash(event)
        if computed != event_hash:
            breaks.append(
                ChainBreak(
                    event_id=event.get("event_id"),
                    line_number=line_no,
                    reason="event_hash does not match payload",
                )
            )

        expected_prev = event_hash

    return _SegmentResult(
        breaks=breaks,
        legacy_count=legacy_count,
        chain_starts=chain_starts,
        last_hash=expected_prev,
    )


def verify_chain(
    log_dir: Path,
    *,
    start: date | None = None,
    end: date | None = None,
    require_full_chain: bool = False,
) -> VerifyResult:
    all_records = iter_log_events(log_dir)
    breaks: list[ChainBreak] = []
    warnings: list[str] = []
    legacy_count = 0
    chain_starts = 0
    expected_prev: str | None = None

    if start:
        pre_window = [
            record
            for record in all_records
            if _parse_timestamp(record[2]["timestamp"]).date() < start
        ]
        pre_result = _verify_records(pre_window, require_full_chain=require_full_chain)
        breaks.extend(pre_result.breaks)
        legacy_count += pre_result.legacy_count
        chain_starts += pre_result.chain_starts
        expected_prev = pre_result.last_hash

    records = all_records
    if start or end:
        records = [
            record
            for record in all_records
            if _in_date_range(record[2]["timestamp"], start, end)
        ]

    segment = _verify_records(
        records,
        initial_expected_prev=expected_prev,
        require_full_chain=require_full_chain,
    )
    breaks.extend(segment.breaks)
    legacy_count += segment.legacy_count
    chain_starts += segment.chain_starts

    if legacy_count and not require_full_chain:
        warnings.append(f"{legacy_count} legacy event(s) without hash chain fields")

    return VerifyResult(
        valid=len(breaks) == 0,
        event_count=len(records),
        legacy_count=legacy_count,
        chain_starts=chain_starts,
        breaks=breaks,
        warnings=warnings,
    )
