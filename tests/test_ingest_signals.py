"""Ingest meeting signal detection tests."""
from __future__ import annotations

from spa.ingest import MEETING_SIGNALS, _is_meeting_content


def test_action_items_alone_does_not_trigger_meeting_pipeline():
    content = "## Action items\n- Update MFA policy\n- Review access logs\n"
    assert _is_meeting_content(content) is False


def test_two_distinct_signals_trigger_meeting_pipeline():
    content = "## Meeting notes\nAttendees: Alice, Bob\n## Action items\n- Update MFA\n"
    assert _is_meeting_content(content) is True


def test_meeting_signals_have_no_redundant_substrings():
    lowered = [signal.lower() for signal in MEETING_SIGNALS]
    for signal in lowered:
        for other in lowered:
            if other != signal and signal in other:
                raise AssertionError(f"Redundant signal {signal!r} contained in {other!r}")
