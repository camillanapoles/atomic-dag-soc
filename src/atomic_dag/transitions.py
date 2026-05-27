"""
execute_transition: composition of parser, gate, fsm, writer, wal.

Sprint 2 Phase 2.C.2 — first operation in the system with a persistent
side effect. Implements the observable contract specified in
docs/api/transitions.md and the design decisions of ADR-006.

Operation ordering (D1, ADR-003 §Lesson 3, transitions.md §3 + §5):

    parse_atom
      → gate.validate_gate          # ALWAYS, before FSM (D4 / RF-2.5)
      → idempotency pre-check       # §5: BEFORE any side effect AND before
                                    #   FSM, so replay (prior to_state ==
                                    #   current disk state) short-circuits
                                    #   to success without engaging FSM
                                    #   (FSM has no self-loops; replays
                                    #   always look FSM-invalid).
      → fsm.validate_transition     # invalid -> raise ALWAYS (no replay
                                    #   branch — replay already handled
                                    #   above; §3+§6 literal)
      → route resolution            # action=="check" routes via gate
      → re-read raw .md content     # Atom does not retain raw text
      → parser.replace_state_in_frontmatter
      → writer.write_atomic         # local POSIX atomicity (FM-02 closed)
      → wal.log_event               # SINGLE event, AFTER the write

D11 — disk never lags the WAL: the WAL is always emitted after the
atomic write, never before. SIGKILL between write and log_event leaves
a disk-ahead-of-WAL gap that is recoverable by the Sprint 5 `reconcile`.
The reverse (WAL-ahead-of-disk) is forbidden and structurally impossible
under this ordering.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atomic_dag import fsm, gate, parser, wal, writer


class AtomNotFoundError(FileNotFoundError):
    """Raised when the atom file path does not exist on disk.

    Maps to CLI exit 2 (structural) per D6.
    """


class InvalidTransitionError(ValueError):
    """Raised when (state, action) is invalid under the FSM (D6).

    Covers both undefined transitions and any action attempted from a
    terminal state. The message names atom_id, action, current state,
    and a textual reason verbatim (RF-2.3).

    Maps to CLI exit 1 (operational).
    """


@dataclass(frozen=True)
class TransitionResult:
    """Immutable result of execute_transition (D5).

    Mirrors the GateResult precedent from gate.py: `__bool__` returns
    `success`. The frozen dataclass guarantees no field can be mutated
    after construction.
    """

    atom_id: str
    from_state: str
    to_state: str
    action: str
    gate_passed: bool
    idempotent: bool
    duration_ms: int
    success: bool

    def __bool__(self) -> bool:
        return self.success


def _serialise_gate_result(g: gate.GateResult) -> dict[str, Any]:
    """Convert GateResult dataclass to a JSON-serialisable dict (D4).

    Required because `wal.log_event` uses `json.dumps`, which does not
    accept arbitrary dataclasses; passing a `GateResult` directly would
    raise `TypeError`. The output mirrors the public fields of
    `GateResult` exactly: passed, gold_score, pqms_score, vvv_score,
    reasons (as list).
    """
    return {
        "passed": g.passed,
        "gold_score": g.gold_score,
        "pqms_score": g.pqms_score,
        "vvv_score": g.vvv_score,
        "reasons": list(g.reasons),
    }


def _find_idempotent_prior_event(
    wal_path: Path,
    atom_id: str,
    action: str,
    current_state: str,
) -> dict[str, Any] | None:
    """Find a prior 'transition' event whose action matches and whose
    to_state equals the current on-disk state. Returns the event dict
    or None.

    This is the D2 / RF-2.4 / transitions.md §5 replay criterion: the
    disk is already in the state that a prior application of this
    action produced; the second call is a no-op. The match is
    structural — atom_id, action, and to_state of the WAL event must
    match the current call's atom_id, action, and current disk state.

    Called as a pre-check BEFORE fsm.validate_transition. §5 specifies
    "Before any side effect, execute_transition calls wal.read_events";
    in a strict reading, raising InvalidTransitionError is a flow-end
    that precludes the idempotency path, so the check must precede
    FSM. This also keeps §3 (FSM-invalid always raises) and §6 (the
    exit-code table) literal — neither has a "replay exception" clause.

    On match: caller returns immediately with idempotent=True. The
    returned TransitionResult reports from_state/to_state from the
    prior event (historical truth), not from the current read.
    """
    if not wal_path.exists():
        return None
    for e in wal.read_events(wal_path):
        if (
            e.get("event_type") == "transition"
            and e.get("atom_id") == atom_id
            and e.get("action") == action
            and e.get("to_state") == current_state
        ):
            return e
    return None


def execute_transition(
    filepath: str | Path,
    action: str,
    *,
    project_root: str | Path,
    wal_path: str | Path | None = None,
) -> TransitionResult:
    """Execute a state transition on an atom.

    Composes parser + gate + fsm + writer + wal in the exact order
    mandated by ADR-003 §Lesson 3 and re-stated in transitions.md §3.
    The WAL event is emitted as a single record after the atomic disk
    write; this preserves D11 (disk never lags WAL).

    Parameters
    ----------
    filepath : str or Path
        Path to the atom `.md` file to transition.
    action : str
        FSM action requested (e.g. "do", "check", "next", "warning").
    project_root : str or Path, keyword-only
        Project root directory. The WAL is stored at
        `<project_root>/.atomic-dag/wal.jsonl` unless `wal_path` overrides.
        The `.atomic-dag/` directory is created lazily on first transition.
    wal_path : str or Path or None, keyword-only
        Explicit WAL file path; if None, derived from `project_root`.

    Returns
    -------
    TransitionResult
        Immutable record of the outcome. `success=True` iff the
        transition completed normally (or was an idempotent replay).

    Raises
    ------
    AtomNotFoundError
        The `filepath` does not exist on disk (maps to CLI exit 2).
    InvalidTransitionError
        The `(state, action)` pair is undefined in the FSM, or any
        action was attempted from a terminal state (maps to CLI exit 1).
        Message names `atom_id`, `action`, current state, and reason.
    AtomParseError
        The file exists but its frontmatter is malformed. Propagates
        from `parser.parse_atom` unchanged; the CLI layer (Phase 2.E)
        maps this to a separate exit code.
    """
    t0 = time.perf_counter()
    filepath = Path(filepath)
    if wal_path is None:
        wal_path = Path(project_root) / ".atomic-dag" / "wal.jsonl"
    else:
        wal_path = Path(wal_path)

    # 1. Existence check. parser.parse_atom wraps OSError as
    # AtomParseError, so a pre-check is the only clean way to map
    # missing-file to AtomNotFoundError (D6 / CLI exit 2) without
    # inspecting an OS-dependent error string.
    if not filepath.exists():
        raise AtomNotFoundError(f"atom file not found: {filepath}")

    # 2. Parse.
    atom = parser.parse_atom(filepath)
    atom_id = atom.atomic_id
    from_state = atom.state

    # 3. Gate ALWAYS, before FSM (D4 / RF-2.5 / ADR-003 §Lesson 3).
    # Pure function over atom.meta — no I/O. Even FSM-invalid transitions
    # invoke this, satisfying the "always called" guarantee of D4. The
    # result is only consumed below if FSM accepts the transition.
    gate_result = gate.validate_gate(atom.meta)

    # 4. Idempotency pre-check (D2 / RF-2.4 / transitions.md §5).
    # BEFORE FSM, BEFORE any side effect. §5 reads "Before any side
    # effect, execute_transition calls wal.read_events"; a strict
    # reading places this before FSM-invalid raises, since the raise
    # is a flow-end with no replay branch (§3 + §6 literal). Match
    # criterion: prior 'transition' event with same atom_id, same
    # action, AND to_state equal to current disk state (the FSM
    # matrix has no self-loops, so a successful prior application
    # leaves the disk in a state from which the same action is
    # FSM-invalid — the signature of a replay).
    prior = _find_idempotent_prior_event(
        wal_path, atom_id, action, from_state
    )
    if prior is not None:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        return TransitionResult(
            atom_id=atom_id,
            from_state=str(prior["from_state"]),
            to_state=str(prior["to_state"]),
            action=action,
            gate_passed=gate_result.passed,
            idempotent=True,
            duration_ms=duration_ms,
            success=True,
        )

    # 5. FSM check. Hard stop on invalid — ALWAYS raises (no replay
    # branch; replay is handled exclusively in step 4 above). §3 and
    # §6 are now literal: FSM-invalid pair / terminal state →
    # InvalidTransitionError, ZERO disk, ZERO WAL.
    valid, fsm_new_state = fsm.validate_transition(from_state, action)
    if not valid:
        if from_state in fsm.TERMINAL_STATES:
            reason = "terminal"
        else:
            reason = f"no transition for action {action!r}"
        raise InvalidTransitionError(
            f"atom={atom_id} action={action!r}: "
            f"invalid from state {from_state!r} ({reason})"
        )

    # 6. Route resolution. The action "check" routes via gate
    # (pass→verified, fail→returned, both exit 0); all other actions
    # take the FSM-supplied new_state directly. "checked" is never
    # persisted as a stable state (DA-3).
    if action == "check":
        to_state = "verified" if gate_result.passed else "returned"
    else:
        to_state = fsm_new_state

    # 7. Re-read raw content. Atom dataclass holds only meta+body+filepath,
    # not the verbatim .md text, so a single re-read is required to feed
    # replace_state_in_frontmatter (which preserves bytes outside the
    # state scalar — surgical, not round-trip).
    raw_content = filepath.read_text(encoding="utf-8")
    new_content = parser.replace_state_in_frontmatter(raw_content, to_state)

    # 8. Atomic disk write (writer.write_atomic, FM-02 closed by tmp+fsync+rename).
    writer.write_atomic(filepath, new_content)

    # 9. WAL emit — SINGLE event, AFTER the write (D1 / ADR-003 §Lesson 3 / D11).
    # Lazy mkdir of .atomic-dag/ preserves wal.log_event's contract
    # ("parent dir must exist") without modifying wal.py.
    wal_path.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    wal.log_event(
        wal_path,
        {
            "event_type": "transition",
            "atom_id": atom_id,
            "from_state": from_state,
            "to_state": to_state,
            "action": action,
            "gate_result": _serialise_gate_result(gate_result),
            "duration_ms": duration_ms,
        },
    )

    return TransitionResult(
        atom_id=atom_id,
        from_state=from_state,
        to_state=to_state,
        action=action,
        gate_passed=gate_result.passed,
        idempotent=False,
        duration_ms=duration_ms,
        success=True,
    )
