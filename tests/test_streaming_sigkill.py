"""SIGKILL fuzzer for tick_streaming — alpha.3 deterministic (Phase 3.D).

Strategy alpha.3 (adapted from test_transitions_sigkill.py):
the child process monkey-patches `atomic_dag.wal.log_event` to SIGSTOP
itself BEFORE performing the append. The parent uses `waitpid(WUNTRACED)`
to block until the child enters the stopped state — by construction this
is the moment immediately after `advance_cursor` completed (state.json
written atomically via writer.write_atomic) and before any WAL line is
appended. The parent then sends SIGKILL: the kill lands deterministically
inside the advance_cursor→log_event critical window.

Post-mortem:
  - read state.json → disk_cursor
  - read WAL events → streaming_tick events
  - D7/D11 falsification: for every streaming_tick in WAL,
    cursor_to ≤ disk_cursor (WAL-ahead-of-disk is forbidden;
    disk-ahead-of-WAL is the only tolerated SIGKILL outcome)

Per-trial assertion: category == "in_critical_window". Any deviation
means the monkey-patch did not fire as expected and the test fails.

Marked @pytest.mark.slow.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import pytest

from atomic_dag.wal import read_events

_CHILD_SCRIPT = textwrap.dedent(
    """
    import os
    import signal
    import sys

    import atomic_dag.wal as _wal
    _real_log = _wal.log_event

    def _pause_then_log(wal_path, event):
        os.kill(os.getpid(), signal.SIGSTOP)
        _real_log(wal_path, event)

    _wal.log_event = _pause_then_log

    from pathlib import Path
    from atomic_dag.streaming import StreamEvent, tick_streaming

    project = Path(sys.argv[1])
    cursor = sys.argv[2]
    tick_streaming(project, StreamEvent("evt-sigkill", "t", {}, cursor))
    """
).strip()


def _mk_project(tmp_path: Path, cursor: str = "C-001") -> Path:
    """Project layout per errata 0.5a: state.json at root, WAL in .atomic-dag/."""
    (tmp_path / "state.json").write_text(
        json.dumps({"cursor": cursor, "updated_at": "t"})
    )
    (tmp_path / ".atomic-dag").mkdir(parents=True)
    (tmp_path / ".atomic-dag" / "wal.jsonl").write_text("")
    return tmp_path


_DISTRIBUTION_REPORT_PATH = Path(
    "/tmp/atomic-dag-streaming-sigkill-distribution.txt"
)


@pytest.fixture(scope="session")
def streaming_sigkill_category_log(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[Path]:
    """Session-scoped log of categories across all 50 parametrized trials.

    On teardown, writes the distribution to a deterministic external
    file so the operator can inspect it after the pytest run.
    """
    log_dir = tmp_path_factory.mktemp("streaming-sigkill-fuzzer")
    log_file = log_dir / "categories.txt"
    log_file.touch()
    yield log_file
    lines = [line for line in log_file.read_text().split("\n") if line]
    counts = Counter(lines)
    in_window = counts.get("in_critical_window", 0)
    gate_pass = in_window >= 40
    report = (
        "=== SIGKILL fuzzer category distribution"
        " (streaming, alpha.3) ===\n"
        f"  total trials:       {sum(counts.values())}\n"
        f"  pre_write:          {counts.get('pre_write', 0)}\n"
        f"  in_critical_window: {in_window}\n"
        f"  post_log:           {counts.get('post_log', 0)}\n"
        f"  GATE (>=40 in_critical_window): "
        f"{'PASS' if gate_pass else 'FAIL — alpha.3 monkey-patch broken'}\n"
    )
    _DISTRIBUTION_REPORT_PATH.write_text(report, encoding="utf-8")


def _wait_for_stopped(pid: int, timeout_s: float = 5.0) -> int:
    """Poll waitpid(WUNTRACED|WNOHANG) until child enters stopped state."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        result_pid, status = os.waitpid(pid, os.WUNTRACED | os.WNOHANG)
        if result_pid != 0:
            return status
        time.sleep(0.005)
    raise TimeoutError(
        f"child pid={pid} never reached stopped state within {timeout_s}s"
    )


@pytest.mark.slow
@pytest.mark.parametrize("seed", range(50))
def test_streaming_survives_sigkill_in_critical_window(
    tmp_path: Path,
    seed: int,
    streaming_sigkill_category_log: Path,
) -> None:
    """alpha.3: deterministic kill inside advance_cursor→log_event window.

    Per-trial assertions:
      - child entered stopped state (monkey-patch fired)
      - category == 'in_critical_window' (cursor advanced, WAL empty)
      - D7/D11: WAL-ahead-of-disk is forbidden
    """
    del seed

    p = _mk_project(tmp_path, "C-001")
    initial_cursor = "C-001"

    proc = subprocess.Popen(
        [sys.executable, "-c", _CHILD_SCRIPT, str(p), initial_cursor]
    )

    try:
        status = _wait_for_stopped(proc.pid, timeout_s=10.0)
    except TimeoutError:
        proc.kill()
        proc.wait(timeout=2.0)
        pytest.fail(
            "child never reached SIGSTOP — alpha.3 monkey-patch did not fire"
        )

    assert os.WIFSTOPPED(status), (
        f"child did not stop normally: WIFSTOPPED=False, status={status} "
        f"(WIFEXITED={os.WIFEXITED(status)}, "
        f"WIFSIGNALED={os.WIFSIGNALED(status)})"
    )
    assert os.WSTOPSIG(status) == signal.SIGSTOP, (
        f"child stopped by signal {os.WSTOPSIG(status)}, expected SIGSTOP"
    )

    os.kill(proc.pid, signal.SIGKILL)
    _final_pid, final_status = os.waitpid(proc.pid, 0)
    assert os.WIFSIGNALED(final_status), (
        f"child did not terminate by signal: status={final_status}"
    )
    assert os.WTERMSIG(final_status) == signal.SIGKILL, (
        f"child terminated by signal {os.WTERMSIG(final_status)}, "
        f"expected SIGKILL"
    )

    # Post-mortem from observable state alone.
    disk_cursor = json.loads((p / "state.json").read_text())["cursor"]
    wal_path = p / ".atomic-dag" / "wal.jsonl"
    wal_events = read_events(wal_path) if wal_path.exists() else []
    tick_events = [
        e for e in wal_events if e.get("tipo") == "streaming_tick"
    ]

    if tick_events:
        category = "post_log"
    elif disk_cursor != initial_cursor:
        category = "in_critical_window"
    else:
        category = "pre_write"

    with streaming_sigkill_category_log.open("a", encoding="utf-8") as f:
        f.write(category + "\n")

    assert category == "in_critical_window", (
        f"alpha.3 determinism broken: category={category!r} "
        f"(initial_cursor={initial_cursor!r}, "
        f"disk_cursor={disk_cursor!r}, "
        f"tick_events={len(tick_events)})"
    )

    # D7/D11 falsification: WAL-ahead-of-disk is forbidden.
    for ev in tick_events:
        assert ev["cursor_to"] <= disk_cursor, (
            f"D7 VIOLATION — WAL claims cursor_to={ev['cursor_to']!r} "
            f"but disk cursor={disk_cursor!r}. "
            f"WAL-ahead-of-disk is forbidden."
        )
