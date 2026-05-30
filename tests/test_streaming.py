"""Unit coverage for atomic_dag.streaming (Sprint 3, fase 3.C)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atomic_dag import wal
from atomic_dag.streaming import (
    StreamCursorMismatchError,
    StreamEvent,
    _next_cursor,
    advance_cursor,
    tick_streaming,
)


def _mk_project(tmp_path: Path, cursor: str = "C-001") -> Path:
    """Project layout per errata 0.5a: state.json at root, WAL in .atomic-dag/."""
    (tmp_path / "state.json").write_text(
        json.dumps({"cursor": cursor, "updated_at": "2026-05-30T00:00:00Z"})
    )
    (tmp_path / ".atomic-dag").mkdir(parents=True)
    (tmp_path / ".atomic-dag" / "wal.jsonl").write_text("")
    return tmp_path


def test_tick_advances_cursor_and_logs(tmp_path: Path) -> None:
    p = _mk_project(tmp_path, "C-001")
    ev = StreamEvent("evt-1", "2026-05-30T00:00:00Z", {"k": "v"}, "C-001")
    r = tick_streaming(p, ev)
    assert r.advanced_cursor_from == "C-001"
    assert r.advanced_cursor_to == "C-002"
    assert r.wal_event_logged is True
    assert r.idempotent_replay is False
    assert json.loads((p / "state.json").read_text())["cursor"] == "C-002"
    evs = wal.read_events(p / ".atomic-dag" / "wal.jsonl")
    assert len([e for e in evs if e.get("tipo") == "streaming_tick"]) == 1


def test_tick_preserves_other_state_fields(tmp_path: Path) -> None:
    p = _mk_project(tmp_path, "C-010")
    tick_streaming(p, StreamEvent("e", "t", {}, "C-010"))
    state = json.loads((p / "state.json").read_text())
    assert state["cursor"] == "C-011"
    assert state["updated_at"] == "2026-05-30T00:00:00Z"


def test_wal_entry_payload_verbatim(tmp_path: Path) -> None:
    p = _mk_project(tmp_path, "C-001")
    tick_streaming(p, StreamEvent("evt-p", "t", {"a": 1, "b": [2, 3]}, "C-001"))
    evs = wal.read_events(p / ".atomic-dag" / "wal.jsonl")
    tick = next(e for e in evs if e.get("tipo") == "streaming_tick")
    assert tick["event_payload"] == {"a": 1, "b": [2, 3]}
    assert tick["cursor_from"] == "C-001"
    assert tick["cursor_to"] == "C-002"
    assert tick["event_id"] == "evt-p"


def test_idempotent_replay(tmp_path: Path) -> None:
    p = _mk_project(tmp_path, "C-001")
    tick_streaming(p, StreamEvent("evt-1", "t", {}, "C-001"))
    # replay SAME event_id; cursor already moved — idempotency checks WAL first
    r = tick_streaming(p, StreamEvent("evt-1", "t", {}, "C-002"))
    assert r.idempotent_replay is True
    assert r.wal_event_logged is False
    assert r.advanced_cursor_from == r.advanced_cursor_to == "C-002"
    evs = wal.read_events(p / ".atomic-dag" / "wal.jsonl")
    assert len([e for e in evs if e.get("tipo") == "streaming_tick"]) == 1  # not 2


def test_idempotent_replay_no_wal_file(tmp_path: Path) -> None:
    """WAL absent: _already_applied returns False, normal processing."""
    (tmp_path / "state.json").write_text(json.dumps({"cursor": "C-001"}))
    # no .atomic-dag/ yet — log_event creates it lazily
    r = tick_streaming(tmp_path, StreamEvent("e1", "t", {}, "C-001"))
    assert r.idempotent_replay is False
    assert r.advanced_cursor_to == "C-002"
    assert (tmp_path / ".atomic-dag" / "wal.jsonl").exists()


def test_cursor_mismatch_raises_no_write(tmp_path: Path) -> None:
    p = _mk_project(tmp_path, "C-001")
    with pytest.raises(StreamCursorMismatchError) as exc:
        tick_streaming(p, StreamEvent("evt-x", "t", {}, "C-999"))
    assert "C-999" in str(exc.value)
    assert "C-001" in str(exc.value)
    assert json.loads((p / "state.json").read_text())["cursor"] == "C-001"
    evs = wal.read_events(p / ".atomic-dag" / "wal.jsonl")
    assert [e for e in evs if e.get("tipo") == "streaming_tick"] == []


def test_advance_cursor_isolated(tmp_path: Path) -> None:
    p = _mk_project(tmp_path, "C-005")
    sp = p / "state.json"
    advance_cursor(sp, "C-006")
    state = json.loads(sp.read_text())
    assert state["cursor"] == "C-006"
    assert state["updated_at"] == "2026-05-30T00:00:00Z"  # preserved


def test_truthiness_success(tmp_path: Path) -> None:
    p = _mk_project(tmp_path, "C-001")
    r = tick_streaming(p, StreamEvent("e", "t", {}, "C-001"))
    assert bool(r) is True


def test_truthiness_idempotent(tmp_path: Path) -> None:
    p = _mk_project(tmp_path, "C-001")
    tick_streaming(p, StreamEvent("e", "t", {}, "C-001"))
    r = tick_streaming(p, StreamEvent("e", "t", {}, "C-002"))
    # idempotent replay with non-empty cursor is still truthy
    assert bool(r) is True


@pytest.mark.parametrize(
    "cur,nxt",
    [
        ("C-042", "C-043"),
        ("<start>", "C-001"),
        ("A-099", "A-100"),
        ("X-001", "X-002"),
        ("foo-bar-7", "foo-bar-8"),
        ("noformat", "noformat-001"),
        ("a-bc", "a-bc-001"),
    ],
)
def test_next_cursor(cur: str, nxt: str) -> None:
    assert _next_cursor(cur) == nxt
