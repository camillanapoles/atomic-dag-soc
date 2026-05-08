"""Tests for atomic_dag.dag — 16 scenarios."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from atomic_dag.dag import (
    CYCLE_LEVEL,
    DAGCycleError,
    compute_dag_levels,
    compute_dag_levels_strict,
    find_next_actionable,
    state_summary,
)
from atomic_dag.parser import Atom


def _atom(aid: str, state: str = "pending", deps: list[str] | None = None) -> Atom:
    meta: dict[str, Any] = {"atomic_id": aid, "state": state}
    if deps:
        meta["deps"] = deps
    return Atom(meta=meta, body="", filepath=Path(f"{aid}.md"))


# ── Scenario 1: Linear chain A→B→C ──────────────────────────────────


def test_linear_chain() -> None:
    atoms = {
        "a": _atom("a"),
        "b": _atom("b", deps=["a"]),
        "c": _atom("c", deps=["b"]),
    }
    levels = compute_dag_levels(atoms)
    assert levels == {0: ["a"], 1: ["b"], 2: ["c"]}
    # Strict mode produces identical result for acyclic graph
    assert compute_dag_levels_strict(atoms) == levels


# ── Scenario 2: Diamond A→B,C→D ──────────────────────────────────────


def test_diamond() -> None:
    atoms = {
        "a": _atom("a"),
        "b": _atom("b", deps=["a"]),
        "c": _atom("c", deps=["a"]),
        "d": _atom("d", deps=["b", "c"]),
    }
    levels = compute_dag_levels(atoms)
    assert levels[0] == ["a"]
    assert sorted(levels[1]) == ["b", "c"]
    assert levels[2] == ["d"]


# ── Scenario 3: Single root (no deps) ────────────────────────────────


def test_single_root() -> None:
    atoms = {"a": _atom("a")}
    assert compute_dag_levels(atoms) == {0: ["a"]}


# ── Scenario 4: External dep treated as satisfied ────────────────────


def test_external_dep() -> None:
    atoms = {"a": _atom("a", deps=["external"])}
    assert compute_dag_levels(atoms) == {0: ["a"]}


# ── Scenario 5: Cycle A→B→A lenient ──────────────────────────────────


def test_cycle_lenient() -> None:
    atoms = {
        "a": _atom("a", deps=["b"]),
        "b": _atom("b", deps=["a"]),
    }
    levels = compute_dag_levels(atoms)
    assert levels == {CYCLE_LEVEL: ["a", "b"]}


# ── Scenario 6: Cycle A→B→A strict ───────────────────────────────────


def test_cycle_strict() -> None:
    atoms = {
        "a": _atom("a", deps=["b"]),
        "b": _atom("b", deps=["a"]),
    }
    with pytest.raises(DAGCycleError, match="cycle detected"):
        compute_dag_levels_strict(atoms)


# ── Scenario 7: Cycle of 3 lenient ───────────────────────────────────


def test_cycle_of_three() -> None:
    atoms = {
        "a": _atom("a", deps=["c"]),
        "b": _atom("b", deps=["a"]),
        "c": _atom("c", deps=["b"]),
    }
    levels = compute_dag_levels(atoms)
    assert levels == {CYCLE_LEVEL: ["a", "b", "c"]}


# ── Scenario 8: Partial cycle with acyclic atoms ─────────────────────


def test_partial_cycle() -> None:
    atoms = {
        "a": _atom("a"),
        "b": _atom("b", deps=["c"]),
        "c": _atom("c", deps=["b"]),
        "d": _atom("d", deps=["a"]),
    }
    levels = compute_dag_levels(atoms)
    assert levels[0] == ["a"]
    assert levels[1] == ["d"]
    assert levels[CYCLE_LEVEL] == ["b", "c"]


# ── Scenario 9: Empty atoms dict ─────────────────────────────────────


def test_empty_atoms() -> None:
    assert compute_dag_levels({}) == {}


# ── Scenario 10: Single atom no deps (explicit) ──────────────────────


def test_single_atom_no_deps() -> None:
    atoms = {"x": _atom("x")}
    assert compute_dag_levels(atoms) == {0: ["x"]}


# ── Scenario 11: find_next_actionable root atom ──────────────────────


def test_find_next_root() -> None:
    atoms = {
        "a": _atom("a", state="pending"),
        "b": _atom("b", state="verified"),
    }
    assert find_next_actionable(atoms) == "a"


# ── Scenario 12: find_next_actionable dep not satisfied ──────────────


def test_find_next_dep_unsatisfied() -> None:
    atoms = {
        "a": _atom("a", state="active"),
        "b": _atom("b", state="pending", deps=["a"]),
    }
    assert find_next_actionable(atoms) is None


# ── Scenario 13: find_next_actionable tie-breaking ───────────────────


def test_find_next_tiebreaking() -> None:
    atoms = {
        "b": _atom("b", state="pending"),
        "a": _atom("a", state="pending"),
    }
    assert find_next_actionable(atoms) == "a"


# ── Scenario 14: find_next_actionable nothing actionable ─────────────


def test_find_next_nothing() -> None:
    atoms = {"a": _atom("a", state="verified")}
    assert find_next_actionable(atoms) is None


# ── Scenario 15: state_summary ───────────────────────────────────────


def test_state_summary() -> None:
    atoms = {
        "a": _atom("a", state="pending"),
        "b": _atom("b", state="pending"),
        "c": _atom("c", state="verified"),
    }
    assert state_summary(atoms) == {"pending": 2, "verified": 1}


# ── Scenario 16: Alphabetical ordering within level ──────────────────


def test_level_alphabetical_ordering() -> None:
    atoms = {
        "c": _atom("c"),
        "a": _atom("a"),
        "b": _atom("b"),
    }
    levels = compute_dag_levels(atoms)
    assert levels[0] == ["a", "b", "c"]
