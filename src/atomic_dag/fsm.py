"""
FSM Engine: the finite-state machine that governs atom lifecycle.

The states and transitions below are the canonical specification from
SOC_V4_UAT_FRAMEWORK.md section 2. They are transcribed here as the
authoritative source for the Python implementation.

This module is functional from Sprint 0 because the FSM itself has no
external dependencies - it's pure data plus a lookup function. Sprint 1
will add guard conditions (dependency checks, body validation, gate
evaluation) on top.
"""

from __future__ import annotations

from typing import Final

# The nine canonical states of a SOC V4 atom.
VALID_STATES: Final[tuple[str, ...]] = (
    "pending",
    "contracted",
    "in-progress",
    "checked",
    "verified",
    "returned",
    "completed",
    "closed",
    "attention",
)

# Terminal states: once entered, no further transitions are allowed.
TERMINAL_STATES: Final[frozenset[str]] = frozenset({"closed"})

# The transition matrix: a mapping from (current_state, action) to new_state.
# Any (state, action) pair not in this map is an invalid transition.
TRANSITIONS: Final[dict[tuple[str, str], str]] = {
    ("pending", "do"): "in-progress",
    ("pending", "contract"): "contracted",
    ("pending", "warning"): "attention",
    ("contracted", "do"): "in-progress",
    ("contracted", "warning"): "attention",
    ("in-progress", "check"): "checked",
    ("in-progress", "warning"): "attention",
    ("verified", "next"): "completed",
    ("verified", "warning"): "attention",
    ("returned", "do"): "in-progress",
    ("returned", "kaizen"): "in-progress",
    ("returned", "warning"): "attention",
    ("completed", "last"): "closed",
    ("attention", "do"): "in-progress",
    ("attention", "kaizen"): "in-progress",
}


def validate_transition(current_state: str, action: str) -> tuple[bool, str]:
    """
    Check whether a transition is valid under the FSM.

    Parameters
    ----------
    current_state : str
        The atom's current state. Must be one of VALID_STATES.
    action : str
        The action requested by the caller.

    Returns
    -------
    (valid, new_state) : tuple[bool, str]
        ``valid`` is True if the (state, action) pair is in TRANSITIONS,
        False otherwise. ``new_state`` is the resulting state if valid,
        or ``current_state`` unchanged if invalid.
    """
    key = (current_state, action)
    if key in TRANSITIONS:
        return True, TRANSITIONS[key]
    return False, current_state


def valid_actions_from(state: str) -> list[str]:
    """Return the list of actions that are legal from the given state."""
    return sorted(action for (s, action) in TRANSITIONS if s == state)
