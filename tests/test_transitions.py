"""Tests for atomic_dag.transitions — Phase 2.C.2 (skeleton + happy path)."""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

from atomic_dag import wal as wal_mod
from atomic_dag.parser import parse_atom
from atomic_dag.transitions import (
    AtomNotFoundError,
    InvalidTransitionError,
    execute_transition,
)

# ── Synthetic atom builder ─────────────────────────────────────────────
# No fixtures exist in tests/atoms/ or docs/atoms/ — verified by find.
# Tests build their own atom .md files inline in tmp_path.


def _make_atom(
    tmp_path: Path,
    *,
    state: str = "pending",
    atomic_id: str = "atom-001",
    body: str = "Atom body.",
    extra_meta: dict[str, Any] | None = None,
    filename: str | None = None,
) -> Path:
    """Build a synthetic atom .md with valid YAML frontmatter; returns the filepath."""
    meta: dict[str, Any] = {"atomic_id": atomic_id, "state": state}
    if extra_meta:
        meta.update(extra_meta)
    fm = yaml.safe_dump(meta, sort_keys=False).strip()
    content = f"---\n{fm}\n---\n\n{body}\n"
    path = tmp_path / (filename or f"{atomic_id}.md")
    path.write_text(content, encoding="utf-8")
    return path


def _passing_gate_meta() -> dict[str, Any]:
    """Meta dict that passes gate.validate_gate (gold + pqms + vvv all above thresholds)."""
    return {
        "gold": {c: True for c in "PTDISLGEOX"},
        "pqms": {
            "CE": 9.5, "PI": 9.5, "CC": 9.5, "PRI": 9.5,
            "RA": 9.5, "EIC": 9.5, "OVA": 9.5,
        },
        "vvv": 0.96,
    }


# ── Family 1: Happy path FSM ──────────────────────────────────────────


def test_pending_do_to_in_progress(tmp_path: Path) -> None:
    path = _make_atom(tmp_path, state="pending")
    result = execute_transition(path, "do", project_root=tmp_path)
    assert result.success
    assert result.idempotent is False
    assert result.from_state == "pending"
    assert result.to_state == "in-progress"
    assert result.action == "do"
    assert parse_atom(path).state == "in-progress"


@pytest.mark.parametrize(
    "start_state,action,expected_state",
    [
        ("pending", "do", "in-progress"),
        ("pending", "contract", "contracted"),
        ("pending", "warning", "attention"),
        ("contracted", "do", "in-progress"),
        ("in-progress", "warning", "attention"),
        ("verified", "next", "completed"),
        ("returned", "kaizen", "in-progress"),
        ("completed", "last", "closed"),
        ("attention", "do", "in-progress"),
    ],
)
def test_happy_path_fsm_transitions(
    tmp_path: Path, start_state: str, action: str, expected_state: str
) -> None:
    """Each valid (state, action) pair in fsm.TRANSITIONS transitions correctly."""
    path = _make_atom(tmp_path, state=start_state)
    result = execute_transition(path, action, project_root=tmp_path)
    assert result.success
    assert result.from_state == start_state
    assert result.to_state == expected_state
    assert parse_atom(path).state == expected_state


# ── Family 5: Gate orchestration on action=="check" ───────────────────


def test_check_with_passing_gate_routes_to_verified(tmp_path: Path) -> None:
    path = _make_atom(tmp_path, state="in-progress", extra_meta=_passing_gate_meta())
    result = execute_transition(path, "check", project_root=tmp_path)
    assert result.success
    assert result.gate_passed is True
    assert result.to_state == "verified"  # not "checked" — checked is transient (DA-3)
    assert parse_atom(path).state == "verified"


def test_check_with_failing_gate_routes_to_returned(tmp_path: Path) -> None:
    """No gold/pqms/vvv in meta → gate fails → route to returned (exit 0, not an error)."""
    path = _make_atom(tmp_path, state="in-progress")
    result = execute_transition(path, "check", project_root=tmp_path)
    assert result.success  # gate-fail-on-check is success, not error (D6)
    assert result.gate_passed is False
    assert result.to_state == "returned"
    assert parse_atom(path).state == "returned"


# ── Family 2: FSM rejection ───────────────────────────────────────────


def test_invalid_action_raises_with_message(tmp_path: Path) -> None:
    path = _make_atom(tmp_path, state="pending")
    with pytest.raises(InvalidTransitionError) as exc_info:
        execute_transition(path, "kaizen", project_root=tmp_path)
    msg = str(exc_info.value)
    # RF-2.3: message names atom_id, action, state, and reason
    assert "atom-001" in msg
    assert "'kaizen'" in msg
    assert "'pending'" in msg
    assert "no transition for action" in msg
    # ZERO disk write on FSM-invalid (RF-2.3)
    assert parse_atom(path).state == "pending"


def test_terminal_state_raises_with_terminal_reason(tmp_path: Path) -> None:
    path = _make_atom(tmp_path, state="closed")
    with pytest.raises(InvalidTransitionError) as exc_info:
        execute_transition(path, "do", project_root=tmp_path)
    msg = str(exc_info.value)
    assert "atom-001" in msg
    assert "'closed'" in msg
    assert "(terminal)" in msg
    assert parse_atom(path).state == "closed"


def test_fsm_invalid_emits_zero_wal_entries(tmp_path: Path) -> None:
    """FSM-invalid path: no disk write, no WAL entry (RF-2.3)."""
    path = _make_atom(tmp_path, state="pending")
    wal_path = tmp_path / ".atomic-dag" / "wal.jsonl"
    with pytest.raises(InvalidTransitionError):
        execute_transition(path, "kaizen", project_root=tmp_path)
    # WAL file may or may not exist, but in either case must have zero events.
    assert wal_mod.read_events(wal_path) == []


# ── AtomNotFoundError ─────────────────────────────────────────────────


def test_missing_filepath_raises_AtomNotFoundError(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.md"
    with pytest.raises(AtomNotFoundError) as exc_info:
        execute_transition(missing, "do", project_root=tmp_path)
    assert "does-not-exist.md" in str(exc_info.value)


# ── Family 3: Idempotency (D2 / RF-2.4) ───────────────────────────────


def test_idempotent_replay_returns_idempotent_true(tmp_path: Path) -> None:
    """Second identical call: idempotent=True, success=True, exit 0."""
    path = _make_atom(tmp_path, state="pending")
    r1 = execute_transition(path, "do", project_root=tmp_path)
    r2 = execute_transition(path, "do", project_root=tmp_path)
    assert r1.idempotent is False
    assert r2.idempotent is True
    assert r2.success is True
    assert r2.from_state == "pending"
    assert r2.to_state == "in-progress"


def test_idempotent_replay_does_not_grow_wal(tmp_path: Path) -> None:
    """RF-2.4 falsifiable: after replay, read_events len == 1, not 2."""
    path = _make_atom(tmp_path, state="pending")
    wal_path = tmp_path / ".atomic-dag" / "wal.jsonl"
    execute_transition(path, "do", project_root=tmp_path)
    assert len(wal_mod.read_events(wal_path)) == 1
    execute_transition(path, "do", project_root=tmp_path)  # replay
    assert len(wal_mod.read_events(wal_path)) == 1  # unchanged


def test_idempotent_replay_file_bytes_unchanged(tmp_path: Path) -> None:
    """Replay performs zero disk writes; file mtime/content unchanged."""
    path = _make_atom(tmp_path, state="pending")
    execute_transition(path, "do", project_root=tmp_path)
    bytes_after_first = path.read_bytes()
    mtime_after_first = path.stat().st_mtime_ns
    execute_transition(path, "do", project_root=tmp_path)  # replay
    assert path.read_bytes() == bytes_after_first
    assert path.stat().st_mtime_ns == mtime_after_first


# ── Family 7: WAL format completeness (D4 / RF-2.5) ───────────────────


def test_wal_event_has_all_mandatory_fields(tmp_path: Path) -> None:
    """RF-2.5: every transition event has timestamp, event_type, atom_id,
    from_state, to_state, action, gate_result, duration_ms — none null."""
    path = _make_atom(tmp_path, state="pending")
    execute_transition(path, "do", project_root=tmp_path)
    events = wal_mod.read_events(tmp_path / ".atomic-dag" / "wal.jsonl")
    assert len(events) == 1
    e = events[0]
    required = {
        "timestamp", "event_type", "atom_id",
        "from_state", "to_state", "action", "gate_result", "duration_ms",
    }
    assert required.issubset(e.keys())
    for field in required:
        assert e[field] is not None, f"field {field!r} is null"
    assert e["event_type"] == "transition"


def test_wal_gate_result_is_json_serialisable_dict(tmp_path: Path) -> None:
    """D4: gate_result is a dict (not a GateResult dataclass), passes json.dumps."""
    path = _make_atom(tmp_path, state="pending")
    execute_transition(path, "do", project_root=tmp_path)
    events = wal_mod.read_events(tmp_path / ".atomic-dag" / "wal.jsonl")
    gr = events[0]["gate_result"]
    assert isinstance(gr, dict)
    # The exact shape from transitions.md §4
    assert set(gr.keys()) == {"passed", "gold_score", "pqms_score", "vvv_score", "reasons"}
    assert isinstance(gr["passed"], bool)
    assert isinstance(gr["reasons"], list)
    # Round-trip via json.dumps must succeed
    json.dumps(gr)


def test_wal_event_timestamp_is_iso_utc(tmp_path: Path) -> None:
    """Timestamp is ISO-8601, parseable, timezone-aware UTC."""
    path = _make_atom(tmp_path, state="pending")
    execute_transition(path, "do", project_root=tmp_path)
    events = wal_mod.read_events(tmp_path / ".atomic-dag" / "wal.jsonl")
    ts = events[0]["timestamp"]
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0  # UTC


def test_wal_duration_ms_is_non_negative_int(tmp_path: Path) -> None:
    path = _make_atom(tmp_path, state="pending")
    result = execute_transition(path, "do", project_root=tmp_path)
    events = wal_mod.read_events(tmp_path / ".atomic-dag" / "wal.jsonl")
    assert isinstance(events[0]["duration_ms"], int)
    assert events[0]["duration_ms"] >= 0
    assert isinstance(result.duration_ms, int)
    assert result.duration_ms >= 0


# ── Lazy .atomic-dag/ directory creation ──────────────────────────────


def test_atomic_dag_directory_created_lazily(tmp_path: Path) -> None:
    """execute_transition creates <project>/.atomic-dag/ on first call."""
    path = _make_atom(tmp_path, state="pending")
    assert not (tmp_path / ".atomic-dag").exists()  # pre-condition
    execute_transition(path, "do", project_root=tmp_path)
    assert (tmp_path / ".atomic-dag").is_dir()
    assert (tmp_path / ".atomic-dag" / "wal.jsonl").is_file()


# ── TransitionResult immutability and truthiness (D5) ─────────────────


def test_transition_result_is_frozen(tmp_path: Path) -> None:
    path = _make_atom(tmp_path, state="pending")
    result = execute_transition(path, "do", project_root=tmp_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.success = False  # type: ignore[misc]


def test_transition_result_bool_returns_success(tmp_path: Path) -> None:
    path = _make_atom(tmp_path, state="pending")
    result = execute_transition(path, "do", project_root=tmp_path)
    assert bool(result) is True
    assert bool(result) == result.success


# ── D1 / D11: disk written BEFORE wal, never after ────────────────────


def test_atom_file_state_matches_wal_to_state_on_success(tmp_path: Path) -> None:
    """D11 (positive): for every transition event in the WAL, the
    on-disk atom is in a state equal to or later than that event's
    to_state. Happy-path test: states are equal."""
    path = _make_atom(tmp_path, state="pending")
    execute_transition(path, "do", project_root=tmp_path)
    events = wal_mod.read_events(tmp_path / ".atomic-dag" / "wal.jsonl")
    assert parse_atom(path).state == events[-1]["to_state"]


# ── Replay-check non-match path: WAL exists but no event matches ─────


def test_fsm_invalid_with_existing_wal_no_replay_match_still_raises(tmp_path: Path) -> None:
    """When the WAL has prior events but none match (atom_id, action,
    to_state=current_state), the replay-check returns None and the
    function raises InvalidTransitionError as on a fresh invalid call.
    Exercises the `return None` branch of _find_idempotent_prior_event."""
    path = _make_atom(tmp_path, state="pending")
    # Build a real WAL by performing one valid transition first.
    execute_transition(path, "do", project_root=tmp_path)  # pending → in-progress
    # Now request an action that is FSM-invalid from in-progress but
    # whose action label does not match the prior event ("do"):
    # in-progress has no "kaizen"; the WAL has no "kaizen" event.
    with pytest.raises(InvalidTransitionError) as exc_info:
        execute_transition(path, "kaizen", project_root=tmp_path)
    msg = str(exc_info.value)
    assert "'kaizen'" in msg
    assert "'in-progress'" in msg
    assert "no transition for action" in msg


# ── Explicit wal_path argument (overrides project_root default) ──────


def test_explicit_wal_path_overrides_project_root(tmp_path: Path) -> None:
    """Passing wal_path= bypasses the <project_root>/.atomic-dag/wal.jsonl
    derivation. Exercises the `else: wal_path = Path(wal_path)` branch."""
    path = _make_atom(tmp_path, state="pending")
    custom_wal = tmp_path / "custom-wal-location" / "events.jsonl"
    result = execute_transition(
        path, "do", project_root=tmp_path, wal_path=custom_wal
    )
    assert result.success
    assert custom_wal.is_file()
    # Default .atomic-dag/ should NOT have been created.
    assert not (tmp_path / ".atomic-dag").exists()
    events = wal_mod.read_events(custom_wal)
    assert len(events) == 1
    assert events[0]["atom_id"] == "atom-001"


# ── D4: gate.validate_gate is called EVEN on FSM-invalid (always called) ──


def test_gate_always_called_serialised_into_wal_on_success(tmp_path: Path) -> None:
    """D4 / RF-2.5: gate_result is present in every successful transition's
    WAL entry, even for actions where it does not determine the route
    (e.g. action='do' uses FSM new_state, not gate)."""
    path = _make_atom(tmp_path, state="pending")
    execute_transition(path, "do", project_root=tmp_path)
    events = wal_mod.read_events(tmp_path / ".atomic-dag" / "wal.jsonl")
    # gate_result present and complete even though "do" did not route via gate
    assert "gate_result" in events[0]
    assert events[0]["gate_result"] is not None
    assert "passed" in events[0]["gate_result"]
