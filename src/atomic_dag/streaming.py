"""Sprint 3 — FM-10 closure (TD-003).

3.C.1: skeleton + happy path. SEM advance_cursor (gera SHA X-1 RED).
3.C.2: adiciona advance_cursor (gera SHA X GREEN).

Spec: docs/architecture/adrs/ADR-007-sprint-3-fm10-streaming.md
API:  docs/api/streaming.md
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atomic_dag import wal as _wal
from atomic_dag import writer as _writer


class StreamCursorMismatchError(Exception):
    """Cursor no state.json diverge do esperado pelo evento."""


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


def tick_streaming(project: Path, event: StreamEvent) -> TickResult:
    """Processa um evento de stream.

    FM-10 BUG (3.C.1 deliberado): advance_cursor NÃO é chamado aqui.
    Isso garante que test_fm10_regression falhe neste SHA (SHA X-1 RED).
    O fix é adicionado em 3.C.2 (SHA X GREEN).

    Post-condition (violada aqui, fixada em 3.C.2):
        state.cursor == result.advanced_cursor_to
    """
    state_path = project / "state.json"
    wal_path = project / ".atomic-dag" / "wal.jsonl"

    # 1. Parse state atual
    state = json.loads(state_path.read_text())
    current_cursor = state.get("cursor", "")

    # 2. Validate cursor
    if event.expected_cursor_from != current_cursor:
        raise StreamCursorMismatchError(
            f"Expected cursor {event.expected_cursor_from!r}, "
            f"got {current_cursor!r}"
        )

    # 3. Check idempotência via WAL
    if wal_path.exists():
        for line in wal_path.read_text().splitlines():
            try:
                entry = json.loads(line)
                if entry.get("event_id") == event.event_id:
                    return TickResult(
                        event_id=event.event_id,
                        advanced_cursor_from=current_cursor,
                        advanced_cursor_to=current_cursor,
                        wal_event_logged=False,
                        idempotent_replay=True,
                    )
            except json.JSONDecodeError:
                continue

    # 4. Compute new_cursor
    new_cursor = _next_cursor(current_cursor)

    # 5. FM-10 BUG: advance_cursor NÃO chamado aqui (SHA X-1)
    # Fix em 3.C.2: advance_cursor(state_path, new_cursor)

    # 6. WAL log (em 3.C.2 será APÓS advance_cursor — D11: disk leads, WAL confirms)
    wal_entry = {
        "ts": event.ts,
        "tipo": "streaming_tick",
        "event_id": event.event_id,
        "cursor_from": current_cursor,
        "cursor_to": new_cursor,
        "event_payload": event.payload,
    }
    _wal.log_event(wal_path, wal_entry)

    return TickResult(
        event_id=event.event_id,
        advanced_cursor_from=current_cursor,
        advanced_cursor_to=new_cursor,
        wal_event_logged=True,
        idempotent_replay=False,
    )


def advance_cursor(state_path: Path, new_cursor: str) -> None:
    """Mutação atômica do campo cursor em state.json.

    Usa writer.write_atomic (I3: não modifica writer.py).
    """
    state = json.loads(state_path.read_text())
    state["cursor"] = new_cursor
    _writer.write_atomic(state_path, json.dumps(state, indent=2))


def _next_cursor(cursor: str) -> str:
    """Incremento lexicográfico: C-042 -> C-043.

    Fallback: prefixo-N -> prefixo-(N+1). Sem prefixo: int+1.
    """
    if "-" in cursor:
        prefix, _, num_str = cursor.rpartition("-")
        try:
            n = int(num_str)
            width = len(num_str)
            return f"{prefix}-{str(n + 1).zfill(width)}"
        except ValueError:
            pass
    try:
        return str(int(cursor) + 1)
    except ValueError:
        return cursor + "_next"
