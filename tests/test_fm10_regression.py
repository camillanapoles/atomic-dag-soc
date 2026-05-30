"""FM-10 regression — the Popperian artifact (ADR-007 §0, §D7).

Refutes the claim "FM-10 is closed" if tick_streaming ever stops advancing the
on-disk cursor. Two complementary assertions: behavioural (cursor on disk) and
structural (advance_cursor is invoked). RED was observed locally at 1049649
(pre-coupling); GREEN at 64c3f5e (coupling added). See ADR-007 §D7.

"Falsifiable" here is Popperian (1934): testable / open to empirical refutation
— an epistemic virtue, not "fraudability". See ADR-007 §0.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from atomic_dag import streaming, wal
from atomic_dag.streaming import StreamEvent, tick_streaming


def _mk_project(tmp_path: Path, cursor: str = "C-001") -> Path:
    """Project layout per errata 0.5a: state.json at root, WAL in .atomic-dag/."""
    (tmp_path / "state.json").write_text(
        json.dumps({"cursor": cursor, "updated_at": "t"})
    )
    (tmp_path / ".atomic-dag").mkdir(parents=True)
    (tmp_path / ".atomic-dag" / "wal.jsonl").write_text("")
    return tmp_path


class TestFM10Regression:
    def test_cursor_advances_after_tick(self, tmp_path: Path) -> None:
        """Behavioural: after a successful tick, state.json cursor on disk
        equals result.advanced_cursor_to.

        This is the assertion that refutes "FM-10 closed" if advance_cursor
        is removed from tick_streaming.
        """
        p = _mk_project(tmp_path, "C-042")
        r = tick_streaming(p, StreamEvent("e1", "t", {}, "C-042"))
        on_disk = json.loads((p / "state.json").read_text())["cursor"]
        assert on_disk == r.advanced_cursor_to == "C-043"

    def test_tick_invokes_advance_cursor(self, tmp_path: Path) -> None:
        """Structural: tick_streaming MUST call advance_cursor.

        The spy refutes a future decoupling even if behaviour were masked.
        """
        p = _mk_project(tmp_path, "C-001")
        with patch.object(
            streaming, "advance_cursor", wraps=streaming.advance_cursor
        ) as spy:
            tick_streaming(p, StreamEvent("e2", "t", {}, "C-001"))
        assert spy.called, (
            "FM-10 REGRESSION: tick_streaming did not call advance_cursor"
        )
        # invoked with the next cursor, against the root state.json
        (called_path, called_cursor), _ = spy.call_args
        assert called_path == p / "state.json"
        assert called_cursor == "C-002"

    def test_wal_never_ahead_of_disk(self, tmp_path: Path) -> None:
        """D7 invariant: every streaming_tick in the WAL with cursor_to=X has
        on-disk state.json cursor == X (or lexicographically later).

        WAL-ahead-of-disk is forbidden (ADR-007 §D7).
        """
        p = _mk_project(tmp_path, "C-001")
        # several sequential ticks
        for expected in ("C-001", "C-002", "C-003"):
            tick_streaming(p, StreamEvent(f"e-{expected}", "t", {}, expected))
        disk = json.loads((p / "state.json").read_text())["cursor"]
        for ev in wal.read_events(p / ".atomic-dag" / "wal.jsonl"):
            if ev.get("tipo") == "streaming_tick":
                assert ev["cursor_to"] <= disk, (
                    f"WAL ahead of disk: WAL cursor_to={ev['cursor_to']!r} "
                    f"> disk cursor={disk!r} — FM-10 violation"
                )
        assert disk == "C-004"
