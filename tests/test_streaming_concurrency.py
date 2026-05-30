"""Concurrency posture for tick_streaming (D8 / FM-01, Sprint 3).

4 processes tick 4 distinct projects in parallel. Each project has its
own state.json and WAL (per errata 0.5a layout). Assertions:
  - all 4 ticks succeed
  - each project's state.json cursor advanced to C-002
  - each project's WAL has exactly 1 streaming_tick event
  - D7: for every WAL event, cursor_to <= disk cursor

Not marked @slow — concurrency runs fast (4 short subprocesses) and
SHOULD run in normal CI.
"""

from __future__ import annotations

import json
import multiprocessing as mp
from pathlib import Path

from atomic_dag import wal as wal_mod
from atomic_dag.streaming import StreamEvent, tick_streaming


def _mk_project(project: Path, cursor: str = "C-001") -> Path:
    (project / "state.json").write_text(
        json.dumps({"cursor": cursor, "updated_at": "t"})
    )
    (project / ".atomic-dag").mkdir(parents=True)
    (project / ".atomic-dag" / "wal.jsonl").write_text("")
    return project


def _run_one(args: tuple[str, str]) -> bool:
    """Pool worker. Returns success bool of tick_streaming."""
    project_str, cursor = args
    project = Path(project_str)
    result = tick_streaming(
        project,
        StreamEvent(f"evt-{project.name}", "t", {}, cursor),
    )
    return bool(result)


def test_concurrent_streaming_on_distinct_projects(tmp_path: Path) -> None:
    """4 processes, 4 distinct projects, parallel tick_streaming.

    Asserts:
      - all 4 results report success
      - each project's state.json cursor == C-002
      - each project's WAL has exactly 1 streaming_tick event
      - D7: WAL never ahead of disk
    """
    args_list: list[tuple[str, str]] = []
    for i in range(4):
        project = tmp_path / f"project-{i}"
        project.mkdir()
        _mk_project(project, "C-001")
        args_list.append((str(project), "C-001"))

    with mp.Pool(4) as pool:
        results = pool.map(_run_one, args_list)

    assert all(results), f"some workers reported failure: {results}"
    assert len(results) == 4

    for i in range(4):
        project = tmp_path / f"project-{i}"
        state = json.loads((project / "state.json").read_text())
        assert state["cursor"] == "C-002", (
            f"project-{i} cursor={state['cursor']!r}, expected 'C-002'"
        )
        wal_path = project / ".atomic-dag" / "wal.jsonl"
        events = wal_mod.read_events(wal_path)
        tick_events = [
            e for e in events if e.get("tipo") == "streaming_tick"
        ]
        assert len(tick_events) == 1, (
            f"project-{i}: expected 1 streaming_tick, got {len(tick_events)}"
        )
        for ev in tick_events:
            assert ev["cursor_to"] <= state["cursor"], (
                f"D7 VIOLATION project-{i}: "
                f"WAL cursor_to={ev['cursor_to']!r} "
                f"> disk cursor={state['cursor']!r}"
            )
