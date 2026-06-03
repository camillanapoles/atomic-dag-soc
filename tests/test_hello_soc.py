"""End-to-end test for the Hello SOC example.

Uses `RecordedProvider` exclusively — ZERO real LLM calls (ADR-009 D-bridge-5).
Validates that the example runs end-to-end and that all 3 atoms reach the
`closed` terminal state through the FSM.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

from atomic_dag.gate import validate_gate
from atomic_dag.parser import parse_atom_directory

EXAMPLE_DIR = Path(__file__).parent.parent / "examples" / "hello-soc"


def _load_run_module() -> ModuleType:
    """Load examples/hello-soc/run_hello_soc.py without polluting sys.path."""
    spec = importlib.util.spec_from_file_location(
        "hello_soc_run", EXAMPLE_DIR / "run_hello_soc.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["hello_soc_run"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hello_project(tmp_path: Path) -> Path:
    """Copy the example into tmp_path so the in-repo files stay clean."""
    dst = tmp_path / "hello-soc"
    shutil.copytree(EXAMPLE_DIR, dst)
    (dst / ".atomic-dag").mkdir(exist_ok=True)
    return dst


def test_hello_soc_end_to_end(hello_project: Path) -> None:
    """All 3 atoms walk pending → ... → closed via the recorded provider."""
    run_mod = _load_run_module()
    provider = run_mod.load_recorded_provider(hello_project / "recorded")

    finals = run_mod.run(hello_project, provider)

    assert len(finals) == 3
    assert all(r.to_state == "closed" for r in finals), (
        f"expected all closed, got {[r.to_state for r in finals]}"
    )

    wal = hello_project / ".atomic-dag" / "wal.jsonl"
    assert wal.exists(), "WAL should have been created lazily by execute_transition"
    wal_lines = [ln for ln in wal.read_text(encoding="utf-8").splitlines() if ln.strip()]
    # 3 atoms x 4 transitions (do via bridge_transition + check + next + last) = 12 WAL events
    # (bridge_transition internally calls execute_transition, which logs to the WAL)
    assert len(wal_lines) == 12, (
        f"expected 12 transition events in WAL, got {len(wal_lines)}"
    )


def test_hello_soc_atoms_are_real(hello_project: Path) -> None:
    """The atoms are real: parser accepts them and the gate passes."""
    atoms = parse_atom_directory(hello_project / "atoms")
    assert set(atoms.keys()) == {"HELLO-001", "HELLO-002", "HELLO-003"}
    for atom in atoms.values():
        result = validate_gate(atom.meta)
        assert result.passed, f"{atom.atomic_id} gate failed: {result.reasons}"


def test_hello_soc_main_with_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    """`main([])` runs end-to-end via RecordedProvider and returns 0.

    `main` copies the example to a fresh tmp dir by default, so the in-repo
    source files are never mutated. Confirms the entry point and the
    `--real`-gating logic (no key → recorded path) both work.
    """
    run_mod = _load_run_module()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert run_mod.main([]) == 0


def test_hello_soc_main_real_flag_without_key_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--real` without ANTHROPIC_API_KEY still uses RecordedProvider (safe)."""
    run_mod = _load_run_module()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert run_mod.main(["--real"]) == 0  # falls back to recorded


def test_recorded_provider_exhausted_raises(tmp_path: Path) -> None:
    """RecordedProvider raises a helpful error when out of recordings."""
    run_mod = _load_run_module()
    provider = run_mod.RecordedProvider(["only one"])
    assert provider.complete("first call") == "only one"
    with pytest.raises(RuntimeError, match="exhausted"):
        provider.complete("second call should fail")
