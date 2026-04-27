"""Tests for atomic_dag.fsm - the FSM engine."""

from __future__ import annotations

from atomic_dag.fsm import (
    TERMINAL_STATES,
    TRANSITIONS,
    VALID_STATES,
    valid_actions_from,
    validate_transition,
)


def test_canonical_states_present() -> None:
    """All nine canonical SOC V4 states must be declared."""
    expected = {
        "pending",
        "contracted",
        "in-progress",
        "checked",
        "verified",
        "returned",
        "completed",
        "closed",
        "attention",
    }
    assert set(VALID_STATES) == expected


def test_closed_is_terminal() -> None:
    """'closed' must be the terminal state (no outgoing transitions)."""
    assert "closed" in TERMINAL_STATES
    assert not [key for key in TRANSITIONS if key[0] == "closed"]


def test_happy_path_pending_to_closed() -> None:
    """Walk the full happy path: pending -> in-progress -> checked -> ... -> closed."""
    state = "pending"

    # pending -> in-progress via 'do'
    valid, state = validate_transition(state, "do")
    assert valid and state == "in-progress"

    # in-progress -> checked via 'check'
    valid, state = validate_transition(state, "check")
    assert valid and state == "checked"

    # 'checked' is transient: in the orchestrator it auto-resolves to either
    # 'verified' or 'returned' depending on the gate. In the pure FSM we
    # simulate a successful gate by directly going verified here - the
    # gate logic will live in gate.py, not fsm.py.
    # For now we check that the happy path continues from 'verified'.
    state = "verified"

    valid, state = validate_transition(state, "next")
    assert valid and state == "completed"

    valid, state = validate_transition(state, "last")
    assert valid and state == "closed"


def test_invalid_transition_returns_false_and_unchanged_state() -> None:
    """An invalid (state, action) pair must not change the state."""
    valid, new_state = validate_transition("pending", "kaizen")
    assert not valid
    assert new_state == "pending"


def test_kaizen_from_returned() -> None:
    """'kaizen' is the action that restarts work on a returned atom."""
    valid, state = validate_transition("returned", "kaizen")
    assert valid and state == "in-progress"


def test_warning_available_from_most_states() -> None:
    """Any non-terminal working state must accept 'warning' -> attention."""
    for state in ("pending", "contracted", "in-progress", "verified", "returned"):
        valid, new_state = validate_transition(state, "warning")
        assert valid, f"warning should be valid from {state}"
        assert new_state == "attention"


def test_valid_actions_from_returns_sorted_list() -> None:
    """Actions from a state must be returned sorted for deterministic output."""
    actions = valid_actions_from("pending")
    assert actions == sorted(actions)
    assert "do" in actions
    assert "contract" in actions
    assert "warning" in actions


def test_valid_actions_from_closed_is_empty() -> None:
    """Terminal state has no legal actions."""
    assert valid_actions_from("closed") == []
