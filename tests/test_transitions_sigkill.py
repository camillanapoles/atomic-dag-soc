"""SIGKILL fuzzer for execute_transition — alpha.3 deterministic (Phase 2.D).

Strategy alpha.3 (operator-authorized after D4 evidence-driven failure):
the child process monkey-patches `atomic_dag.wal.log_event` to SIGSTOP
itself BEFORE performing the append. The parent uses `waitpid(WUNTRACED)`
to block until the child enters the stopped state — by construction this
is the moment immediately after `writer.write_atomic` completed and
before any WAL line is written. The parent then sends SIGKILL: the kill
lands deterministically inside the write→log critical window.

Why this replaces D4 (uniform random sleep): D4 produced 1/50 hits in
the critical window because the window is microsecond-scale (a couple
of dict + json.dumps + file append calls) while the sleep range was
50ms. alpha.3 makes the kill timing deterministic by gating it on the
child's signal-emitted readiness, eliminating the timing race entirely.

Post-mortem (unchanged from D4):
  - parse atom from disk -> disk_state
  - read WAL events -> transition_events
  - assert disk_state == event["to_state"] for every transition event
    (D11 falsification — WAL-ahead-of-disk is forbidden; the structural
    impossibility under the ordering write_atomic→log_event is now
    *tested* with deterministic kill in the actual critical window)

Per-trial assertion: category == "in_critical_window". Any deviation
(pre_write or post_log) means the monkey-patch did not fire as
expected and the test fails — operator stop condition §5.

Marked @pytest.mark.slow.
"""

from __future__ import annotations

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
import yaml

from atomic_dag.parser import parse_atom
from atomic_dag.wal import read_events

# Child script: monkey-patch wal.log_event BEFORE importing transitions,
# then run execute_transition. The SIGSTOP fires when the orchestrator
# reaches log_event — i.e. after write_atomic has completed. Parent
# uses waitpid(WUNTRACED) to detect this and SIGKILL the stopped child.
_CHILD_SCRIPT = textwrap.dedent(
    """
    import os
    import signal
    import sys

    # Monkey-patch must happen BEFORE atomic_dag.transitions imports wal.
    import atomic_dag.wal as _wal
    _real_log = _wal.log_event

    def _pause_then_log(wal_path, event):
        # Pause this process; parent collects the stop via waitpid(WUNTRACED)
        # and SIGKILLs us before _real_log ever runs. If parent does not kill
        # (impossible under alpha.3 design), _real_log would proceed normally.
        os.kill(os.getpid(), signal.SIGSTOP)
        _real_log(wal_path, event)

    _wal.log_event = _pause_then_log

    # Now safe to import; transitions binds to the patched log_event.
    from atomic_dag.transitions import execute_transition

    filepath, action, project_root, wal_path = sys.argv[1:5]
    execute_transition(
        filepath,
        action,
        project_root=project_root,
        wal_path=wal_path,
    )
    """
).strip()


def _write_atom(path: Path, atomic_id: str, state: str) -> None:
    """Build a minimal atom .md inline. No fixtures exist in the repo."""
    meta = {"atomic_id": atomic_id, "state": state}
    fm = yaml.safe_dump(meta, sort_keys=False).strip()
    content = f"---\n{fm}\n---\n\nAtom body.\n"
    path.write_text(content, encoding="utf-8")


_DISTRIBUTION_REPORT_PATH = Path("/tmp/atomic-dag-sigkill-distribution.txt")


@pytest.fixture(scope="session")
def sigkill_category_log(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[Path]:
    """Session-scoped log of categories across all 50 parametrized trials.

    On teardown, writes the distribution to a deterministic external
    file (/tmp/atomic-dag-sigkill-distribution.txt) so the operator
    can inspect it after the pytest run (pytest captures stdout/stderr
    in teardown hooks by default; a deterministic file path is the
    only reliable way to surface the distribution in the triad output).

    Under alpha.3, every trial is expected to land in 'in_critical_window'
    by construction; any deviation triggers a per-trial assertion
    failure inside the test, not just a fixture-level gate report.
    """
    log_dir = tmp_path_factory.mktemp("sigkill-fuzzer")
    log_file = log_dir / "categories.txt"
    log_file.touch()
    yield log_file
    lines = [line for line in log_file.read_text().split("\n") if line]
    counts = Counter(lines)
    in_window = counts.get("in_critical_window", 0)
    gate_pass = in_window >= 40
    report = (
        "=== SIGKILL fuzzer category distribution (alpha.3 deterministic) ===\n"
        f"  total trials:       {sum(counts.values())}\n"
        f"  pre_write:          {counts.get('pre_write', 0)}\n"
        f"  in_critical_window: {in_window}\n"
        f"  post_log:           {counts.get('post_log', 0)}\n"
        f"  GATE (>=40 in_critical_window): "
        f"{'PASS' if gate_pass else 'FAIL — alpha.3 monkey-patch broken'}\n"
    )
    _DISTRIBUTION_REPORT_PATH.write_text(report, encoding="utf-8")


def _wait_for_stopped(pid: int, timeout_s: float = 5.0) -> int:
    """Poll waitpid(WUNTRACED|WNOHANG) until child enters stopped state.

    Returns the status code. Raises TimeoutError if timeout elapses
    without the child stopping (or exiting).
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        result_pid, status = os.waitpid(pid, os.WUNTRACED | os.WNOHANG)
        if result_pid != 0:
            return status
        time.sleep(0.005)
    raise TimeoutError(f"child pid={pid} never reached stopped state within {timeout_s}s")


@pytest.mark.slow
@pytest.mark.parametrize("seed", range(50))
def test_transition_survives_sigkill_in_critical_window(
    tmp_path: Path,
    seed: int,
    sigkill_category_log: Path,
) -> None:
    """alpha.3: deterministic kill inside the write→log critical window.

    Child Python subprocess monkey-patches wal.log_event to SIGSTOP
    before the real append. Parent waits for the stop via
    waitpid(WUNTRACED), then SIGKILLs the stopped child. By construction
    the kill lands AFTER write_atomic completed and BEFORE any WAL line
    was appended.

    Per-trial assertions:
      - child entered stopped state (monkey-patch fired)
      - category == 'in_critical_window' (atom mtime advanced, WAL empty)
      - D11 trivially preserved (WAL has no events; no false claims possible)

    The `seed` parameter is unused under alpha.3 (kill is deterministic) but
    kept for the 50x falsification budget the operator's gate requires.
    """
    del seed  # alpha.3 is deterministic; seed kept only for parametrize budget

    path = tmp_path / "atom-sk.md"
    _write_atom(path, "atom-sk", "pending")
    initial_mtime_ns = path.stat().st_mtime_ns
    wal_path = tmp_path / ".atomic-dag" / "wal.jsonl"

    # Spawn child as a separate Python invocation. clean module state,
    # no shared coverage/pytest plumbing — fork-related test pollution
    # is avoided by construction.
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _CHILD_SCRIPT,
            str(path),
            "do",
            str(tmp_path),
            str(wal_path),
        ]
    )

    try:
        status = _wait_for_stopped(proc.pid, timeout_s=10.0)
    except TimeoutError:
        # Child never paused — monkey-patch broken or transition raised.
        proc.kill()
        proc.wait(timeout=2.0)
        pytest.fail(
            "child never reached SIGSTOP — alpha.3 monkey-patch did not fire "
            "(broken patch, or execute_transition raised before reaching log_event)"
        )

    assert os.WIFSTOPPED(status), (
        f"child did not stop normally: WIFSTOPPED=False, status={status} "
        f"(WIFEXITED={os.WIFEXITED(status)}, WIFSIGNALED={os.WIFSIGNALED(status)})"
    )
    assert os.WSTOPSIG(status) == signal.SIGSTOP, (
        f"child stopped by signal {os.WSTOPSIG(status)}, expected SIGSTOP"
    )

    # Deterministic kill in the critical window.
    os.kill(proc.pid, signal.SIGKILL)
    # Reap zombie. Stopped children require a second waitpid to complete.
    _final_pid, final_status = os.waitpid(proc.pid, 0)
    assert os.WIFSIGNALED(final_status), (
        f"child did not terminate by signal: status={final_status}"
    )
    assert os.WTERMSIG(final_status) == signal.SIGKILL, (
        f"child terminated by signal {os.WTERMSIG(final_status)}, expected SIGKILL"
    )

    # Post-mortem from observable state alone.
    current_mtime_ns = path.stat().st_mtime_ns
    wal_events = read_events(wal_path) if wal_path.exists() else []
    transition_events = [
        e for e in wal_events if e.get("event_type") == "transition"
    ]

    if transition_events:
        category = "post_log"
    elif current_mtime_ns > initial_mtime_ns:
        category = "in_critical_window"
    else:
        category = "pre_write"

    with sigkill_category_log.open("a", encoding="utf-8") as f:
        f.write(category + "\n")

    # alpha.3 per-trial determinism: every kill MUST land in the critical
    # window. Any deviation indicates the monkey-patch did not fire as
    # designed and the falsification budget is wasted.
    assert category == "in_critical_window", (
        f"alpha.3 determinism broken: category={category!r} "
        f"(initial_mtime={initial_mtime_ns}, current_mtime={current_mtime_ns}, "
        f"transition_events={len(transition_events)})"
    )

    # D11 falsification: with alpha.3 the WAL is guaranteed empty (we killed
    # before log_event), so the per-event invariant is vacuously true.
    # The defensive loop remains as a sanity guard against future drift
    # (if some refactor makes the WAL non-empty here, the assertion
    # would actually fire on a false-positive claim).
    if transition_events:
        if not path.exists():
            pytest.fail("WAL has transition event but atom file is missing")
        disk_state = parse_atom(path).state
        for event in transition_events:
            assert disk_state == event["to_state"], (
                f"D11 VIOLATION — WAL claims to_state={event['to_state']!r} "
                f"but disk is {disk_state!r}. WAL-ahead-of-disk is forbidden."
            )
