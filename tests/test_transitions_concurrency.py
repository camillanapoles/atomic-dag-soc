"""Concurrency posture (D8 / FM-01).

D8 / ADR-006:
    "Concurrent transitions on distinct atoms are safe and produce one
    valid WAL line each, in arrival order. Concurrent transitions on
    the same atom are outside the Sprint 2 contract."

FM-01 (concurrent WAL writers) is mitigated — not closed — by O_APPEND
semantics plus the guarantee that event payloads stay below PIPE_BUF
(atomic line append on POSIX). This test exercises the mitigation:
4 processes transition 4 distinct atoms in parallel, the WAL receives
4 valid line-delimited JSON events, all 4 atom_ids are distinct.

Not marked @slow — concurrency runs fast (4 short subprocesses) and
SHOULD run in normal CI. Once dívida D5 closes (ci.yml gains the
`-m "not slow"` filter), this test continues to be exercised on
every push.

Same-atom contention is explicitly out of scope for Sprint 2 (lock
deferred to Sprint 5) — not tested here.
"""

from __future__ import annotations

import multiprocessing as mp
from pathlib import Path
from typing import Any

import yaml

from atomic_dag import wal as wal_mod
from atomic_dag.transitions import execute_transition


def _write_atom(path: Path, atomic_id: str, state: str) -> None:
    meta: dict[str, Any] = {"atomic_id": atomic_id, "state": state}
    fm = yaml.safe_dump(meta, sort_keys=False).strip()
    content = f"---\n{fm}\n---\n\nAtom body.\n"
    path.write_text(content, encoding="utf-8")


def _run_one(args: tuple[str, str, str]) -> bool:
    """Pool worker. Returns success bool of execute_transition."""
    filepath, project_root, wal_path = args
    result = execute_transition(
        filepath,
        "do",
        project_root=project_root,
        wal_path=wal_path,
    )
    return bool(result)


def test_concurrent_transitions_on_distinct_atoms(tmp_path: Path) -> None:
    """4 processes, 4 distinct atoms, 1 shared WAL.

    Asserts:
      - all 4 results report success
      - WAL has exactly 4 transition events (no torn writes, no lost events)
      - 4 distinct atom_ids in the WAL (no overwrite, no duplication)
      - each event is JSON-parseable (already validated by wal.read_events)
    """
    wal_path = tmp_path / ".atomic-dag" / "wal.jsonl"
    args_list: list[tuple[str, str, str]] = []
    for i in range(4):
        atom_path = tmp_path / f"atom-conc-{i}.md"
        _write_atom(atom_path, f"atom-conc-{i}", "pending")
        args_list.append((str(atom_path), str(tmp_path), str(wal_path)))

    with mp.Pool(4) as pool:
        results = pool.map(_run_one, args_list)

    assert all(results), f"some workers reported failure: {results}"
    assert len(results) == 4

    events = wal_mod.read_events(wal_path)
    transition_events = [
        e for e in events if e.get("event_type") == "transition"
    ]
    assert len(transition_events) == 4, (
        f"expected 4 transition events, got {len(transition_events)}: {transition_events}"
    )

    atom_ids = {e["atom_id"] for e in transition_events}
    assert atom_ids == {f"atom-conc-{i}" for i in range(4)}, (
        f"unexpected atom_id set: {atom_ids}"
    )
