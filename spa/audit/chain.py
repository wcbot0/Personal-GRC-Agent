"""Hash-chained audit log integrity utilities."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


GENESIS_HASH = "0" * 64
CHAIN_HEAD_FILENAME = ".chain-head.json"


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
class ChainHeadState:
    event_hash: str | None
    event_count: int
    last_sequence: int


@dataclass
class _SegmentResult:
    breaks: list[ChainBreak]
    legacy_count: int
    chain_starts: int
    last_hash: str | None
    hashed_event_count: int
    last_sequence: int | None


def canonical_payload(event: dict[str, Any]) -> bytes:
    payload = {k: v for k, v in event.items() if k != "event_hash"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_event_hash(event: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_payload(event)).hexdigest()


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _read_raw_lines(log_dir: Path) -> list[tuple[Path, int, str]]:
    raw: list[tuple[Path, int, str]] = []
    for path in sorted(log_dir.glob("audit-*.jsonl")):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if line.strip():
                raw.append((path, line_no, line))
    return raw


def _parse_log_records(log_dir: Path) -> tuple[list[tuple[Path, int, dict[str, Any]]], list[ChainBreak]]:
    records: list[tuple[Path, int, dict[str, Any]]] = []
    breaks: list[ChainBreak] = []
    for path, line_no, line in _read_raw_lines(log_dir):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            breaks.append(
                ChainBreak(None, line_no, f"invalid JSON in {path.name}: {exc.msg}")
            )
            continue
        if not isinstance(event, dict):
            breaks.append(ChainBreak(None, line_no, f"event is not a JSON object in {path.name}"))
            continue
        timestamp = event.get("timestamp")
        if not timestamp:
            breaks.append(
                ChainBreak(event.get("event_id"), line_no, f"missing timestamp in {path.name}")
            )
            continue
        if not event.get("event_id"):
            breaks.append(ChainBreak(None, line_no, f"missing event_id in {path.name}"))
            continue
        try:
            _parse_timestamp(str(timestamp))
        except (ValueError, TypeError):
            breaks.append(
                ChainBreak(
                    event.get("event_id"),
                    line_no,
                    f"invalid timestamp in {path.name}: {timestamp!r}",
                )
            )
            continue
        records.append((path, line_no, event))
    records.sort(key=lambda item: _parse_timestamp(item[2]["timestamp"]))
    return records, breaks


def iter_log_events(log_dir: Path) -> list[tuple[Path, int, dict[str, Any]]]:
    records, _ = _parse_log_records(log_dir)
    return records


def compute_log_tail(log_dir: Path) -> ChainHeadState:
    """Derive the chain tail from the JSONL log itself.

    The log is the authoritative record; this scans the actual events rather
    than trusting the sidecar pointer, so callers can reconcile a stale or
    truncated ``.chain-head.json`` against reality.
    """
    records = iter_log_events(log_dir)
    event_hash: str | None = None
    hashed_count = 0
    last_sequence: int | None = None
    for _, _, event in records:
        if event.get("event_hash"):
            event_hash = str(event["event_hash"])
            hashed_count += 1
            seq = event.get("sequence_number")
            if isinstance(seq, int):
                last_sequence = seq
    return ChainHeadState(
        event_hash=event_hash,
        event_count=hashed_count,
        last_sequence=last_sequence or 0,
    )


def load_chain_head_state(log_dir: Path) -> ChainHeadState:
    head_path = log_dir / CHAIN_HEAD_FILENAME
    if head_path.exists():
        try:
            data = json.loads(head_path.read_text(encoding="utf-8"))
            return ChainHeadState(
                event_hash=data.get("event_hash"),
                event_count=int(data.get("event_count", 0)),
                last_sequence=int(data.get("last_sequence", 0)),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    return compute_log_tail(log_dir)


def load_chain_head(log_dir: Path) -> str | None:
    return load_chain_head_state(log_dir).event_hash


def write_chain_head(
    log_dir: Path,
    *,
    event_hash: str,
    event_count: int,
    last_sequence: int,
) -> None:
    head_path = log_dir / CHAIN_HEAD_FILENAME
    tmp_path = head_path.with_suffix(".json.tmp")
    payload = {
        "event_hash": event_hash,
        "event_count": event_count,
        "last_sequence": last_sequence,
    }
    tmp_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp_path, head_path)


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
    require_full_chain: bool = True,
) -> _SegmentResult:
    breaks: list[ChainBreak] = []
    legacy_count = 0
    chain_starts = 0
    expected_prev = initial_expected_prev
    hashed_event_count = 0
    last_sequence: int | None = None

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

        hashed_event_count += 1
        seq = event.get("sequence_number")
        if isinstance(seq, int):
            if last_sequence is not None and seq != last_sequence + 1:
                breaks.append(
                    ChainBreak(
                        event_id=event.get("event_id"),
                        line_number=line_no,
                        reason=f"sequence_number gap (expected {last_sequence + 1}, got {seq})",
                    )
                )
            elif last_sequence is None and seq != 1:
                breaks.append(
                    ChainBreak(
                        event_id=event.get("event_id"),
                        line_number=line_no,
                        reason=f"sequence_number must start at 1, got {seq}",
                    )
                )
            last_sequence = seq

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
        hashed_event_count=hashed_event_count,
        last_sequence=last_sequence,
    )


def _verify_chain_head(
    log_dir: Path,
    *,
    last_hash: str | None,
    hashed_event_count: int,
    last_sequence: int | None,
) -> tuple[list[ChainBreak], list[str]]:
    breaks: list[ChainBreak] = []
    warnings: list[str] = []
    head_path = log_dir / CHAIN_HEAD_FILENAME
    if not head_path.exists():
        if hashed_event_count:
            warnings.append("chain head pointer missing; tail truncation cannot be detected")
        return breaks, warnings

    head = load_chain_head_state(log_dir)
    if last_hash != head.event_hash:
        breaks.append(
            ChainBreak(
                None,
                0,
                f"chain tail hash does not match head pointer (log={last_hash}, head={head.event_hash})",
            )
        )
    if hashed_event_count != head.event_count:
        breaks.append(
            ChainBreak(
                None,
                0,
                f"hashed event count mismatch (log={hashed_event_count}, head={head.event_count})",
            )
        )
    if last_sequence is not None and head.last_sequence and last_sequence != head.last_sequence:
        breaks.append(
            ChainBreak(
                None,
                0,
                f"sequence_number mismatch (log={last_sequence}, head={head.last_sequence})",
            )
        )
    return breaks, warnings


def verify_chain(
    log_dir: Path,
    *,
    start: date | None = None,
    end: date | None = None,
    require_full_chain: bool = True,
) -> VerifyResult:
    all_records, parse_breaks = _parse_log_records(log_dir)
    breaks: list[ChainBreak] = list(parse_breaks)
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

    if not start and not end:
        head_breaks, head_warnings = _verify_chain_head(
            log_dir,
            last_hash=segment.last_hash,
            hashed_event_count=segment.hashed_event_count,
            last_sequence=segment.last_sequence,
        )
        breaks.extend(head_breaks)
        warnings.extend(head_warnings)

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
