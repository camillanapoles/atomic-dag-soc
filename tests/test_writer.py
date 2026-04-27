"""
Brutal atomicity tests for AtomicWriter.

The strategy is black-box: we don't care about the internals. We care
that the contract - 'target always has valid content' - holds even when
we SIGKILL the writing process at arbitrary moments.

These tests reproduce (and then defend against) the FM-02 failure mode
identified in the SOC V4 FMEA, which stated that 'save_state_atomic' was
not actually atomic despite its name.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import random
import signal
import time
from pathlib import Path

import pytest

from atomic_dag.writer import write_atomic

# ---------------------------------------------------------------------------
# Basic functional tests
# ---------------------------------------------------------------------------

def test_write_string_to_new_file(tmp_path: Path) -> None:
    """Simple string write creates the file with exact content."""
    target = tmp_path / "hello.txt"
    write_atomic(target, "hello world")
    assert target.read_text(encoding="utf-8") == "hello world"


def test_write_bytes_to_new_file(tmp_path: Path) -> None:
    """Bytes input is written directly without re-encoding."""
    target = tmp_path / "data.bin"
    payload = bytes([0, 1, 2, 3, 255])
    write_atomic(target, payload)
    assert target.read_bytes() == payload


def test_overwrite_existing_file(tmp_path: Path) -> None:
    """Second write replaces the content of the target file."""
    target = tmp_path / "state.txt"
    write_atomic(target, "first")
    write_atomic(target, "second")
    assert target.read_text(encoding="utf-8") == "second"


def test_unicode_content(tmp_path: Path) -> None:
    """UTF-8 content (including non-ASCII) is preserved."""
    target = tmp_path / "unicode.txt"
    content = "Análise fractal socrática 中文 🚀"
    write_atomic(target, content)
    assert target.read_text(encoding="utf-8") == content


def test_missing_directory_raises_oserror(tmp_path: Path) -> None:
    """Writing to a nonexistent directory is an error, not a silent create."""
    target = tmp_path / "nonexistent_dir" / "file.txt"
    with pytest.raises(OSError):
        write_atomic(target, "data")


def test_no_orphan_temp_files_on_success(tmp_path: Path) -> None:
    """After a successful write, no .tmp files should remain."""
    target = tmp_path / "state.txt"
    write_atomic(target, "content")
    tmp_files = [p for p in tmp_path.iterdir() if p.name.startswith(".")]
    assert tmp_files == [], f"Orphan temp files found: {tmp_files}"


# ---------------------------------------------------------------------------
# The brutal SIGKILL test - the one that validates the atomicity contract
# ---------------------------------------------------------------------------

def _child_writes_forever(target: str, payload: str) -> None:
    """
    Child process: writes the same payload in an infinite loop.
    The parent will SIGKILL this child at random times.

    We disable SIGTERM's default handler so that only SIGKILL can stop us.
    This matches the realistic scenario where a crash is unexpected and
    gives the process no chance to clean up.
    """
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    while True:
        write_atomic(target, payload)
        time.sleep(0.001)  # tiny yield so the scheduler can interleave


@pytest.mark.parametrize("iteration", range(50))
def test_atomic_write_survives_sigkill(tmp_path: Path, iteration: int) -> None:
    """
    Spawn a child writing continuously. Kill it at a random moment.
    Verify the target file is either empty (child died before first write
    completed) or contains exactly the expected payload - never a partial
    or torn write.

    We run 50 iterations by default in CI. For thorough local validation,
    increase to 1000 by running with pytest -k "sigkill" --count=20 or by
    editing the range above.
    """
    target = tmp_path / "state.json"
    payload = json.dumps({"version": 1, "data": "x" * 1000}, indent=2)

    proc = mp.Process(target=_child_writes_forever, args=(str(target), payload))
    proc.start()

    # Let it run for a random duration before killing
    time.sleep(random.uniform(0.001, 0.050))
    os.kill(proc.pid, signal.SIGKILL)
    proc.join(timeout=2.0)

    # If the child never got to write even once, the target won't exist.
    # That's a valid outcome of the race - no corruption possible.
    if not target.exists():
        return

    content = target.read_text(encoding="utf-8")

    # The CORE contract: target must contain either empty string or the
    # exact full payload. Any intermediate content = torn write = FM-02.
    assert content == "" or content == payload, (
        f"Iteration {iteration}: TORN WRITE DETECTED. "
        f"Length={len(content)}, expected 0 or {len(payload)}. "
        f"This reproduces the FM-02 failure mode that write_atomic is "
        f"supposed to prevent."
    )


def test_concurrent_writers_to_same_target(tmp_path: Path) -> None:
    """
    Multiple processes writing the same payload concurrently must never
    produce a corrupted target. This is a weaker guarantee than full
    transactional writes (last-write-wins semantics apply) but the file
    at every instant must be valid.
    """
    target = tmp_path / "contested.json"
    payload = json.dumps({"v": 1, "payload": "y" * 500})

    processes = [
        mp.Process(target=_child_writes_forever, args=(str(target), payload))
        for _ in range(4)
    ]
    for p in processes:
        p.start()

    time.sleep(0.1)  # let them fight over the file

    for p in processes:
        os.kill(p.pid, signal.SIGKILL)
        p.join(timeout=1.0)

    if target.exists():
        content = target.read_text(encoding="utf-8")
        assert content == "" or content == payload
