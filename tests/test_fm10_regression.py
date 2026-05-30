"""test_fm10_regression — Critério Popperiano-mestre (ADR-007 D7).

Estes testes falsificam a afirmação "FM-10 está fechada" se advance_cursor
for removido de tick_streaming. Par red→green observável no histórico:
- SHA X-1 (1049649): tick_streaming SEM advance_cursor → este teste FALHA
- SHA X   (64c3f5e): advance_cursor invocado → este teste PASSA
"""

from __future__ import annotations

import json
from pathlib import Path

from atomic_dag.streaming import StreamEvent, tick_streaming


def _make_project(tmp_path: Path, cursor: str = "C-001") -> Path:
    (tmp_path / ".atomic-dag").mkdir()
    (tmp_path / ".atomic-dag" / "wal.jsonl").touch()
    (tmp_path / "state.json").write_text(json.dumps({"cursor": cursor}))
    return tmp_path


def test_tick_streaming_advances_cursor_on_disk(tmp_path: Path) -> None:
    """D7: state.json cursor deve avançar após tick bem-sucedido.

    Este é o teste que falsifica "FM-10 fechada" se advance_cursor sumir.
    Verbatim do critério Popperiano-mestre ADR-007 §Decision D7.
    """
    project = _make_project(tmp_path, "C-042")
    event = StreamEvent(
        event_id="e-001",
        ts="2026-05-30T00:00:00Z",
        payload={},
        expected_cursor_from="C-042",
    )

    result = tick_streaming(project, event)

    state_after = json.loads((project / "state.json").read_text())
    assert state_after["cursor"] == result.advanced_cursor_to, (
        f"FM-10 PRESENTE: state.cursor={state_after['cursor']!r} "
        f"!= result.advanced_cursor_to={result.advanced_cursor_to!r}. "
        "advance_cursor não foi chamado em tick_streaming."
    )
    assert state_after["cursor"] != "C-042", "Cursor não avançou"


def test_wal_never_ahead_of_disk(tmp_path: Path) -> None:
    """D7 invariant: para todo streaming_tick no WAL com cursor_to=X,
    state.json cursor == X (ou posterior).

    WAL-ahead-of-disk é o cenário proibido (ADR-007 §Decision D7).
    """
    project = _make_project(tmp_path, "C-100")
    events = [
        StreamEvent(f"e-{i}", "2026-01-01T00:00:00Z", {}, f"C-{100 + i:03d}")
        for i in range(5)
    ]

    for ev in events:
        tick_streaming(project, ev)

    wal_lines = (project / ".atomic-dag" / "wal.jsonl").read_text().splitlines()
    final_cursor = json.loads((project / "state.json").read_text())["cursor"]

    for line in wal_lines:
        entry = json.loads(line)
        if entry.get("tipo") != "streaming_tick":
            continue
        cursor_to = entry["cursor_to"]
        assert cursor_to <= final_cursor, (
            f"D7 VIOLADA: WAL entry cursor_to={cursor_to!r} > "
            f"state.json cursor={final_cursor!r} (WAL ahead of disk)"
        )

    assert final_cursor == "C-105", f"esperado C-105, obtido {final_cursor!r}"
