"""test_streaming — cobertura unitária do módulo streaming."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atomic_dag.streaming import (
    StreamCursorMismatchError,
    StreamEvent,
    TickResult,
    _next_cursor,
    advance_cursor,
    tick_streaming,
)


def _make_project(tmp_path: Path, cursor: str = "C-001") -> Path:
    (tmp_path / ".atomic-dag").mkdir()
    (tmp_path / ".atomic-dag" / "wal.jsonl").touch()
    (tmp_path / "state.json").write_text(json.dumps({"cursor": cursor}))
    return tmp_path


class TestTickStreamingHappyPath:
    def test_returns_tick_result(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, "C-001")
        event = StreamEvent("e1", "2026-01-01T00:00:00Z", {"x": 1}, "C-001")

        result = tick_streaming(project, event)

        assert isinstance(result, TickResult)
        assert result.event_id == "e1"
        assert result.advanced_cursor_from == "C-001"
        assert result.advanced_cursor_to == "C-002"
        assert result.wal_event_logged is True
        assert result.idempotent_replay is False

    def test_writes_wal_entry(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, "C-010")
        event = StreamEvent("e2", "2026-01-01T00:00:00Z", {"k": "v"}, "C-010")

        tick_streaming(project, event)

        wal_lines = (project / ".atomic-dag" / "wal.jsonl").read_text().splitlines()
        assert len(wal_lines) == 1
        entry = json.loads(wal_lines[0])
        assert entry["tipo"] == "streaming_tick"
        assert entry["event_id"] == "e2"
        assert entry["cursor_from"] == "C-010"
        assert entry["cursor_to"] == "C-011"
        assert entry["event_payload"] == {"k": "v"}


class TestCursorMismatch:
    def test_raises_on_mismatch(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, "C-001")
        event = StreamEvent("e1", "2026-01-01T00:00:00Z", {}, "C-ERRADO")

        with pytest.raises(StreamCursorMismatchError) as exc:
            tick_streaming(project, event)

        assert "C-ERRADO" in str(exc.value)
        assert "C-001" in str(exc.value)

    def test_state_unchanged_on_mismatch(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, "C-001")
        state_before = (project / "state.json").read_text()
        wal_before = (project / ".atomic-dag" / "wal.jsonl").read_text()

        with pytest.raises(StreamCursorMismatchError):
            tick_streaming(
                project,
                StreamEvent("e1", "2026-01-01T00:00:00Z", {}, "C-ERRADO"),
            )

        assert (project / "state.json").read_text() == state_before
        assert (project / ".atomic-dag" / "wal.jsonl").read_text() == wal_before


class TestIdempotency:
    def test_replay_same_event_id(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, "C-001")
        event = StreamEvent("e-idem", "2026-01-01T00:00:00Z", {}, "C-001")

        r1 = tick_streaming(project, event)
        assert r1.idempotent_replay is False

        r2 = tick_streaming(project, event)
        assert r2.idempotent_replay is True
        assert r2.wal_event_logged is False
        assert r2.advanced_cursor_from == r2.advanced_cursor_to

    def test_replay_does_not_grow_wal(self, tmp_path: Path) -> None:
        project = _make_project(tmp_path, "C-001")
        event = StreamEvent("e-idem", "2026-01-01T00:00:00Z", {}, "C-001")

        tick_streaming(project, event)
        wal_after_first = (project / ".atomic-dag" / "wal.jsonl").read_text()

        tick_streaming(project, event)
        wal_after_replay = (project / ".atomic-dag" / "wal.jsonl").read_text()

        assert wal_after_first == wal_after_replay

    def test_malformed_wal_line_is_skipped(self, tmp_path: Path) -> None:
        """WAL com linha JSON malformada não quebra idempotency check."""
        project = _make_project(tmp_path, "C-001")
        wal_path = project / ".atomic-dag" / "wal.jsonl"
        wal_path.write_text("not-valid-json\n")

        event = StreamEvent("e-new", "2026-01-01T00:00:00Z", {}, "C-001")
        result = tick_streaming(project, event)

        assert result.idempotent_replay is False
        assert result.advanced_cursor_to == "C-002"

    def test_no_wal_file_yet(self, tmp_path: Path) -> None:
        """WAL inexistente: pula idempotency check, processa normalmente."""
        (tmp_path / "state.json").write_text(json.dumps({"cursor": "C-001"}))
        (tmp_path / ".atomic-dag").mkdir()
        # NÃO cria wal.jsonl — wal.log_event criará

        event = StreamEvent("e1", "2026-01-01T00:00:00Z", {}, "C-001")
        result = tick_streaming(tmp_path, event)

        assert result.advanced_cursor_to == "C-002"
        assert (tmp_path / ".atomic-dag" / "wal.jsonl").exists()


class TestAdvanceCursor:
    def test_updates_cursor_field(self, tmp_path: Path) -> None:
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"cursor": "X-001", "other": "kept"}))

        advance_cursor(state_path, "X-002")

        state = json.loads(state_path.read_text())
        assert state["cursor"] == "X-002"
        assert state["other"] == "kept", "advance_cursor deve preservar outros campos"

    def test_atomic_repeated(self, tmp_path: Path) -> None:
        state_path = tmp_path / "state.json"
        state_path.write_text(json.dumps({"cursor": "A-000"}))

        for i in range(1, 11):
            advance_cursor(state_path, f"A-{i:03d}")
            parsed = json.loads(state_path.read_text())
            assert parsed["cursor"] == f"A-{i:03d}"


class TestNextCursor:
    def test_prefix_dash_numeric(self) -> None:
        assert _next_cursor("C-042") == "C-043"

    def test_preserves_width(self) -> None:
        assert _next_cursor("X-0009") == "X-0010"
        assert _next_cursor("Y-001") == "Y-002"

    def test_multi_dash_prefix(self) -> None:
        # rpartition usa ÚLTIMO "-"
        assert _next_cursor("foo-bar-7") == "foo-bar-8"

    def test_dash_non_numeric_suffix_falls_back(self) -> None:
        # rpartition("a-bc") → ("a", "-", "bc"); int("bc") falha;
        # int("a-bc") falha; retorna "a-bc_next"
        assert _next_cursor("a-bc") == "a-bc_next"

    def test_pure_integer(self) -> None:
        assert _next_cursor("42") == "43"

    def test_non_numeric_no_dash(self) -> None:
        assert _next_cursor("foo") == "foo_next"
