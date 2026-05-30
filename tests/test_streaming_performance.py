"""Performance budget for tick_streaming (Sprint 3, Phase 3.D).

Adapted from test_transitions_performance.py (RF-2.6). 100 sequential
ticks on a single project, cursor advancing from C-001 to C-101.
Asserts p99 < 100ms. The WAL grows with each tick (worst case for the
_already_applied idempotency scan as the file grows).

Marked @pytest.mark.slow: intended to run locally or via
workflow_dispatch. Excluded from normal CI by -m "not slow" (D5).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from atomic_dag.streaming import StreamEvent, tick_streaming


def _mk_project(tmp_path: Path, cursor: str = "C-001") -> Path:
    """Project layout per errata 0.5a: state.json at root, WAL in .atomic-dag/."""
    (tmp_path / "state.json").write_text(
        json.dumps({"cursor": cursor, "updated_at": "t"})
    )
    (tmp_path / ".atomic-dag").mkdir(parents=True)
    (tmp_path / ".atomic-dag" / "wal.jsonl").write_text("")
    return tmp_path


@pytest.mark.slow
def test_streaming_performance_p99_under_100ms(tmp_path: Path) -> None:
    """100 sequential ticks; p99 latency < 100ms.

    Each tick advances the cursor by 1 (C-001 -> C-002 -> ... -> C-101).
    Timing is wall-clock around the full tick_streaming call including
    state read, idempotency check, cursor computation, advance_cursor
    (writer.write_atomic), and wal.log_event.
    """
    p = _mk_project(tmp_path, "C-001")
    durations_ms: list[float] = []

    for i in range(100):
        cursor = f"C-{i + 1:03d}"
        ev = StreamEvent(f"evt-{i}", "t", {}, cursor)
        t0 = time.perf_counter()
        result = tick_streaming(p, ev)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert result.wal_event_logged, f"tick {i} did not log WAL event"
        durations_ms.append(elapsed_ms)

    sorted_dur = sorted(durations_ms)
    p99 = sorted_dur[98]
    median = sorted_dur[49]
    p95 = sorted_dur[94]
    max_dur = sorted_dur[99]

    print(
        f"\n=== tick_streaming latency over 100 calls ===\n"
        f"  median: {median:.2f} ms\n"
        f"  p95:    {p95:.2f} ms\n"
        f"  p99:    {p99:.2f} ms\n"
        f"  max:    {max_dur:.2f} ms\n"
        f"  threshold: p99 < 100.00 ms\n"
    )

    assert p99 < 100.0, (
        f"p99={p99:.2f}ms exceeds 100ms threshold "
        f"(median={median:.2f}, p95={p95:.2f}, max={max_dur:.2f})"
    )
