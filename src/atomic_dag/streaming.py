"""atomic_dag.streaming — streaming tick with mandatory cursor advancement.

Closes FM-10 (RPN=162): tick_streaming GUARANTEES a call to advance_cursor,
so the on-disk cursor never lags a processed event. Falsifiable [Popper, 1934:
testable / refutable — virtue, not fraudability; see ADR-007 §0] by
tests/test_fm10_regression.py — remove the advance_cursor call and the test
refutes the FM-10-closed claim. See ADR-007 §0 and §D7.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atomic_dag import wal, writer


class StreamCursorMismatchError(Exception):
    """Raised when event.expected_cursor_from != state.cursor."""


@dataclass(frozen=True)
class StreamEvent:
    event_id: str
    ts: str
    payload: dict[str, Any]
    expected_cursor_from: str


@dataclass(frozen=True)
class TickResult:
    event_id: str
    advanced_cursor_from: str
    advanced_cursor_to: str
    wal_event_logged: bool
    idempotent_replay: bool

    def __bool__(self) -> bool:
        return not self.idempotent_replay or self.advanced_cursor_to != ""


def _state_path(project: Path) -> Path:
    # Errata 0.5a: cursor store at project root; .atomic-dag/ holds only the WAL.
    return project / "state.json"


def _wal_path(project: Path) -> Path:
    return project / ".atomic-dag" / "wal.jsonl"


def _next_cursor(current: str) -> str:
    """Lexicographic increment. 'C-042' -> 'C-043'. '<start>' -> 'C-001'.

    Prefix-N split on last '-'; numeric tail incremented preserving width.
    Fallback: append '-001' for non-conforming inputs (no numeric tail).
    """
    if current == "<start>":
        return "C-001"
    if "-" in current:
        prefix, _, tail = current.rpartition("-")
        if tail.isdigit():
            width = len(tail)
            return f"{prefix}-{int(tail) + 1:0{width}d}"
    return f"{current}-001"


def advance_cursor(state_path: Path, new_cursor: str) -> None:
    """Atomic mutation of the cursor field. I3: uses writer.write_atomic."""
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["cursor"] = new_cursor
    writer.write_atomic(state_path, json.dumps(state, indent=2))


def _already_applied(wal_path: Path, event_id: str) -> bool:
    if not wal_path.exists():
        return False
    for ev in wal.read_events(wal_path):
        if ev.get("tipo") == "streaming_tick" and ev.get("event_id") == event_id:
            return True
    return False


def tick_streaming(project: Path, event: StreamEvent) -> TickResult:
    """Process one stream event, guaranteeing cursor advancement (FM-10 fix).

    Order (ADR-007 D1/D11): idempotency check -> cursor guard ->
    advance_cursor + write_atomic(state.json) -> wal.log_event.
    Disk leads, WAL confirms. The only tolerated SIGKILL outcome is
    disk-ahead-of-WAL; WAL-ahead-of-disk is forbidden (D7).

    Post-condition (FM-10 fix, ADR-007 D7):
        state.json["cursor"] == result.advanced_cursor_to
    """
    state_path = _state_path(project)
    wal_path = _wal_path(project)

    state = json.loads(state_path.read_text(encoding="utf-8"))
    current_cursor = state["cursor"]

    # D3 idempotency BEFORE FSM/mutation
    if _already_applied(wal_path, event.event_id):
        return TickResult(
            event_id=event.event_id,
            advanced_cursor_from=current_cursor,
            advanced_cursor_to=current_cursor,
            wal_event_logged=False,
            idempotent_replay=True,
        )

    # cursor guard
    if event.expected_cursor_from != current_cursor:
        raise StreamCursorMismatchError(
            f"expected {event.expected_cursor_from!r}, found {current_cursor!r}"
        )

    new_cursor = _next_cursor(current_cursor)

    # ── THE FM-10 FIX (ADR-007 D7) — advance_cursor BEFORE wal (D11) ──
    advance_cursor(state_path, new_cursor)

    # WAL dir created lazily (wal.log_event requires the parent dir to exist).
    wal_path.parent.mkdir(parents=True, exist_ok=True)
    wal.log_event(
        wal_path,
        {
            "tipo": "streaming_tick",
            "event_id": event.event_id,
            "cursor_from": current_cursor,
            "cursor_to": new_cursor,
            "event_payload": event.payload,
        },
    )

    return TickResult(
        event_id=event.event_id,
        advanced_cursor_from=current_cursor,
        advanced_cursor_to=new_cursor,
        wal_event_logged=True,
        idempotent_replay=False,
    )
