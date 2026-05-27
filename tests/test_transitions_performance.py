"""Performance budget for execute_transition (RF-2.6).

RF-2.6 verbatim from PLANO_ENGENHARIA_SOFTWARE_V1.md §3.3:
    "A operação completa termina em menos de 100ms para projetos com
    até 100 átomos em hardware de referência (Pop OS, Python 3.13,
    SSD). Critério de falseabilidade: teste test_transition_performance
    mede latência em 50 execuções e exige p99 menor que 100ms."

This test runs 100 sequential happy-path transitions on distinct atoms
in tmp_path and asserts p99 < 100.0 ms. The hardware reference is
local: CI runners may exhibit different latencies (registered as
dívida D5 alongside the missing `-m "not slow"` filter in ci.yml).

Marked @pytest.mark.slow: intended to run locally or via
workflow_dispatch. Once dívida D5 closes (ci.yml gains `-m "not slow"`),
this test is excluded from normal CI by design.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
import yaml

from atomic_dag.transitions import execute_transition


def _write_atom(path: Path, atomic_id: str, state: str) -> None:
    meta: dict[str, Any] = {"atomic_id": atomic_id, "state": state}
    fm = yaml.safe_dump(meta, sort_keys=False).strip()
    content = f"---\n{fm}\n---\n\nAtom body.\n"
    path.write_text(content, encoding="utf-8")


@pytest.mark.slow
def test_transition_performance_p99_under_100ms(tmp_path: Path) -> None:
    """100 happy-path transitions on distinct atoms; p99 latency < 100ms.

    Each atom is fresh (pending → in-progress via 'do'); the WAL is
    shared across all 100 calls (worst case for read_events as the
    file grows). Timing is wall-clock around the full execute_transition
    call, including the existence check, parse, gate, FSM, write, and
    log_event.
    """
    durations_ms: list[float] = []
    for i in range(100):
        path = tmp_path / f"atom-{i:03d}.md"
        _write_atom(path, f"atom-{i:03d}", "pending")
        t0 = time.perf_counter()
        result = execute_transition(path, "do", project_root=tmp_path)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert result.success, f"transition {i} failed unexpectedly"
        durations_ms.append(elapsed_ms)

    # p99 of 100 samples is the 99th value when sorted (index 98).
    sorted_dur = sorted(durations_ms)
    p99 = sorted_dur[98]
    median = sorted_dur[49]
    p95 = sorted_dur[94]
    max_dur = sorted_dur[99]

    # Print the distribution for human inspection regardless of pass/fail.
    print(
        f"\n=== execute_transition latency over 100 calls ===\n"
        f"  median: {median:.2f} ms\n"
        f"  p95:    {p95:.2f} ms\n"
        f"  p99:    {p99:.2f} ms\n"
        f"  max:    {max_dur:.2f} ms\n"
        f"  RF-2.6 threshold: p99 < 100.00 ms\n"
    )

    assert p99 < 100.0, (
        f"RF-2.6 violation: p99={p99:.2f}ms exceeds 100ms threshold "
        f"(median={median:.2f}, p95={p95:.2f}, max={max_dur:.2f})"
    )
