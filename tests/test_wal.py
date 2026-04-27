"""Tests for atomic_dag.wal - the Write-Ahead Log."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from atomic_dag.wal import log_event, read_events


def test_log_and_read_single_event(tmp_path: Path) -> None:
    """Write one event, read it back, verify round-trip integrity."""
    wal = tmp_path / "wal.jsonl"
    log_event(wal, {"atom_id": "soc-c07-schema", "event_type": "transition",
                    "from_state": "pending", "to_state": "in-progress"})

    events = read_events(wal)
    assert len(events) == 1
    assert events[0]["atom_id"] == "soc-c07-schema"
    assert events[0]["event_type"] == "transition"


def test_timestamp_is_added_automatically(tmp_path: Path) -> None:
    """If caller does not provide timestamp, one is added in UTC ISO-8601."""
    wal = tmp_path / "wal.jsonl"
    log_event(wal, {"atom_id": "test", "event_type": "ping"})

    events = read_events(wal)
    timestamp_str = events[0]["timestamp"]

    # Parse it back - must be valid ISO-8601 and must be UTC.
    parsed = datetime.fromisoformat(timestamp_str)
    assert parsed.tzinfo is not None, "timestamp must be timezone-aware"
    assert parsed.utcoffset() == UTC.utcoffset(parsed)


def test_caller_provided_timestamp_is_preserved(tmp_path: Path) -> None:
    """If caller provides a timestamp, it is not overwritten."""
    wal = tmp_path / "wal.jsonl"
    custom_ts = "2026-01-01T00:00:00+00:00"
    log_event(wal, {"timestamp": custom_ts, "atom_id": "test", "event_type": "ping"})

    events = read_events(wal)
    assert events[0]["timestamp"] == custom_ts


def test_events_are_appended_in_order(tmp_path: Path) -> None:
    """Multiple events written sequentially are read back in the same order."""
    wal = tmp_path / "wal.jsonl"
    for i in range(5):
        log_event(wal, {"atom_id": f"atom-{i}", "event_type": "ping", "seq": i})

    events = read_events(wal)
    assert len(events) == 5
    assert [e["seq"] for e in events] == [0, 1, 2, 3, 4]


def test_read_nonexistent_file_returns_empty(tmp_path: Path) -> None:
    """Reading a WAL that does not exist yet returns an empty list."""
    wal = tmp_path / "nonexistent.jsonl"
    assert read_events(wal) == []


def test_each_line_is_valid_json(tmp_path: Path) -> None:
    """The file format guarantee: every non-empty line must parse as JSON."""
    wal = tmp_path / "wal.jsonl"
    log_event(wal, {"atom_id": "a", "event_type": "x"})
    log_event(wal, {"atom_id": "b", "event_type": "y"})

    raw = wal.read_text(encoding="utf-8")
    lines = [line for line in raw.split("\n") if line.strip()]
    assert len(lines) == 2
    for line in lines:
        # Must parse without exception
        json.loads(line)


def test_unicode_content_round_trips(tmp_path: Path) -> None:
    """UTF-8 content (including non-ASCII) must survive the round trip."""
    wal = tmp_path / "wal.jsonl"
    message = "Análise fractal socrática 中文 🚀"
    log_event(wal, {"atom_id": "unicode-test", "event_type": "note", "msg": message})

    events = read_events(wal)
    assert events[0]["msg"] == message


def test_blank_lines_in_wal_are_skipped(tmp_path: Path) -> None:
    """
    Defensive: if the WAL file has been touched by an external tool and
    ended up with blank lines, read_events must skip them gracefully
    rather than failing to parse an empty string as JSON.
    """
    wal = tmp_path / "wal.jsonl"
    # Write a file with valid lines interleaved with blank lines
    wal.write_text(
        '{"atom_id": "a", "event_type": "ping"}\n'
        "\n"
        '{"atom_id": "b", "event_type": "pong"}\n'
        "   \n"
        '{"atom_id": "c", "event_type": "ack"}\n',
        encoding="utf-8",
    )

    events = read_events(wal)
    assert len(events) == 3
    assert [e["atom_id"] for e in events] == ["a", "b", "c"]
