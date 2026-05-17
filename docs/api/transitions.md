# `atomic_dag.transitions` — Public Protocol

**Status:** Phase 2.B specification (public contract, no production code)
**Authority:** ADR-006 (D1, D2, D4–D8, D11); `PLANO_ENGENHARIA_SOFTWARE_V1.md` §3.3 (RF-2.1–RF-2.6), §6.2
**Constrained by:** ADR-003 §Lesson 1 (Sprint 0/1 modules untouched), §Lesson 3 (operation ordering)

This document specifies the observable contract of the `transitions` module before any implementation exists. `transitions.py` (Phase 2.C) must satisfy every clause here. Where this document and ADR-006 diverge, ADR-006 wins; where ADR-006 and an already-committed authority (ADR-003, §6.2) diverge, the committed authority wins.

## 1. Public surface

The module exposes exactly two public names. Everything else is private.

```python
execute_transition(filepath, action, *, project_root, wal_path=None) -> TransitionResult
TransitionResult  # frozen dataclass
```

No other symbol is part of the contract. Callers must not depend on private helpers.

## 2. `TransitionResult` (D5)

A frozen dataclass mirroring the `GateResult` precedent established in `gate.py` (Sprint 1). Truthiness equals success.

| Field | Type | Meaning |
|---|---|---|
| `atom_id` | `str` | Identifier of the atom transitioned |
| `from_state` | `str` | State before the transition |
| `to_state` | `str` | State after the transition (persisted) |
| `action` | `str` | The action requested by the operator |
| `gate_passed` | `bool` | Result of `gate.validate_gate` (always computed — D4) |
| `idempotent` | `bool` | `True` if this call was a no-op replay (D2) |
| `duration_ms` | `int` | Wall-clock duration, milliseconds, `>= 0` |
| `success` | `bool` | Overall outcome; backs `__bool__` |

**Contract clauses:**

- `__bool__` returns `success`. `if execute_transition(...)` is the idiomatic success check.
- The instance is immutable (`frozen=True`). Mutating any field raises.
- On the FSM-invalid path **no** `TransitionResult` is returned; the function raises a typed error consumed by the CLI layer (see §6). `TransitionResult` is only constructed for outcomes that reached the route-resolution step.

## 3. `execute_transition` — operation ordering (D1)

The function performs these steps in **exactly** this order. The order is the contract, not an implementation detail — it is the ordering mandated by §6.2 and confirmed verbatim by ADR-003 §Lesson 3.

```
1. parse_atom(filepath) -> Atom
2. gate.validate_gate(atom.meta) -> GateResult            # ALWAYS, before FSM (D4)
3. fsm.validate_transition(atom.state, action) -> (valid, new_state)
     not valid -> raise typed error; ZERO disk write; ZERO WAL entry (RF-2.3)
4. route resolution:
     action == "check":  gate.passed -> to_state = "verified"
                         else        -> to_state = "returned"   (both success, exit 0)
     otherwise:          to_state = new_state                   # from FSM
5. content' = parser.replace_state_in_frontmatter(content, to_state)
6. writer.write_atomic(filepath, content')              # local POSIX atomicity (writer.py, FM-02 closed)
7. wal.log_event(wal_path, event)                       # SINGLE event, AFTER the write
```

**Binding consequences of this ordering:**

- **Gate before FSM (D4).** The gate is computed even for transitions the FSM will reject. This makes the "always called" guarantee literally true and is required so `gate_result` can never be absent from a WAL entry (RF-2.5). The cost is trivial: `gate.validate_gate` is a pure function over `atom.meta` with no I/O.
- **Write before WAL (D1, ADR-003 §Lesson 3).** The WAL event is emitted as a single record **after** the atomic disk write. Two-phase emission is rejected (ADR-006 Alternatives item 1).
- **FSM-invalid is a hard stop.** No disk write, no WAL entry, computed `GateResult` discarded with the early return.

## 4. WAL record schema (D4, RF-2.5)

Exactly **one** event of type `transition` is emitted per non-idempotent successful transition. Mandatory fields, all non-null:

| Field | Type | Source |
|---|---|---|
| `timestamp` | `str` (ISO-8601 UTC) | added automatically by `wal.log_event` |
| `event_type` | `str = "transition"` | constant |
| `atom_id` | `str` | from parsed atom |
| `from_state` | `str` | state before |
| `to_state` | `str` | state persisted |
| `action` | `str` | operator-requested action |
| `gate_result` | `dict` (JSON-serialisable) | full serialisation of the `GateResult`; never null |
| `duration_ms` | `int >= 0` | measured wall-clock |

`gate_result` is the **complete serialised gate outcome**, not a boolean. It is present on every transition event, including actions where the gate does not determine routing (DA-2). A WAL entry missing any field above fails RF-2.5 by definition.

Serialised shape of `gate_result` (mirrors `gate.GateResult` public fields):

```json
{
  "passed": <bool>,
  "gold_score": <int>,
  "pqms_score": <float>,
  "vvv_score": <float>,
  "reasons": ["<str>", ...]
}
```

The conversion from the `GateResult` dataclass to this dict is performed by `execute_transition` before calling `wal.log_event` (which uses `json.dumps` and does not accept arbitrary dataclasses; passing a `GateResult` directly would raise `TypeError`). `reasons` is logged verbatim — no redaction, no truncation.

**WAL location:** `<project_root>/.atomic-dag/wal.jsonl`. The `.atomic-dag/` directory is created lazily by `execute_transition` if absent via `Path(wal_path).parent.mkdir(parents=True, exist_ok=True)` — directory creation is this function's responsibility, **not** the caller's, and preserves the existing `wal.log_event` contract ("parent directory must already exist") without modifying `wal.py`.

## 5. Idempotency (D2, RF-2.4)

Before any side effect, `execute_transition` calls `wal.read_events(wal_path)`. If a prior `transition` event matches `(atom_id, from_state, to_state, action)` **and** the on-disk atom is already in `to_state`, the function:

- returns `TransitionResult(idempotent=True, success=True, ...)`,
- performs **zero** disk writes,
- emits **zero** new WAL entries.

**Falsifiable criterion (RF-2.4 verbatim):** two sequential identical calls both succeed (exit 0), and `read_events` returns a list of length **1** — not 2 — after the second call. A replay never grows the WAL.

## 6. Failure modes and exit-code mapping (D6)

`execute_transition` raises typed errors. The CLI layer (Phase 2.E) maps them to exit codes; the mapping is part of the contract:

| Condition | Error class (typed) | CLI exit | Disk / WAL effect |
|---|---|---|---|
| atom file not found | `AtomNotFoundError` | `2` (structural) | none / none |
| FSM-invalid pair, or any action from a terminal state (`closed`) | `InvalidTransitionError` | `1` (operational) | none / none |
| success (normal) | — | `0` | atom rewritten / 1 WAL event |
| success (idempotent replay) | — | `0` | none / none |
| `check` with gate failing → `returned` | — | `0` | atom → `returned` / 1 WAL event |

A failed gate on `check` is **not an error**. The operator's request was valid; the system routed the atom back for refinement. It is success, exit `0`, with `to_state = "returned"` and `gate_passed = False` recorded in both the `TransitionResult` and the WAL event.

Error messages on the FSM-invalid path **must name** `atom_id`, `action`, and the reason (e.g. current state, terminality) — RF-2.3.

## 7. Crash-safety invariant (D7, D11)

`execute_transition` provides no atomicity across the whole composition — `write_atomic` is atomic, `log_event` is atomic, the sequence of the two is not. The contract on crash (SIGKILL anywhere) is therefore stated as an invariant, not a guarantee of all-or-nothing:

- The atom `.md` is always integral: either the old content or the new content, never a torn write (inherited from `writer.py`, FM-02 closed, 50× SIGKILL proven).
- The WAL is always parseable line-by-line (inherited from `wal.py`, `O_APPEND`, payload `< PIPE_BUF`).
- **D11 — disk never lags the WAL.** For every `transition` event in the WAL, the on-disk atom is in a state equal to or later than that event's `to_state`. The only tolerated SIGKILL outcome is **disk ahead of WAL** (atom advanced, WAL silent) — recoverable, and the explicit responsibility of the Sprint 5 `reconcile` command. The outcome **WAL ahead of disk is forbidden** and is actively attacked by the SIGKILL fuzzer (Phase 2.D); the fuzzer must fail to produce it.

Reconciliation of the tolerated disk-ahead-of-WAL gap is **out of scope for Sprint 2** (Sprint 5).

## 8. Concurrency posture (D8)

Per-atom locking is **deferred to Sprint 5**. FM-01 (concurrent WAL writers) is *mitigated*, not closed, by `O_APPEND` semantics plus event payloads staying below `PIPE_BUF` (atomic line append on POSIX). `execute_transition` introduces **no locking**. Concurrent transitions on distinct atoms are safe and produce one valid WAL line each, in arrival order. Concurrent transitions on the **same** atom are **outside the Sprint 2 contract** — undefined until the Sprint 5 lock lands.

## 9. Inherited primitives (not re-specified here)

These are Sprint 0/1 contracts, used as-is, **not modified** (ADR-003 §Lesson 1):

- `parser.parse_atom(path) -> Atom`; `parser.replace_state_in_frontmatter(content, new_state) -> str`
- `gate.validate_gate(meta) -> GateResult` (`.passed`, `.gold_score`, `.pqms_score`, `.vvv_score`, `.reasons`)
- `fsm.validate_transition(state, action) -> (bool, new_state)`; `fsm.TERMINAL_STATES = {"closed"}`
- `writer.write_atomic(target, content)` (tmp + fsync + rename; FM-02 closed)
- `wal.log_event(path, event)`; `wal.read_events(path) -> list[dict]`

`replace_state_in_frontmatter` is the **one** Sprint-0/1-adjacent helper that does not yet exist; its addition to `parser.py` is Phase 2.C.1, specified separately, and is the **only permitted modification** to a pre-Sprint-2 source file. This is a conscious narrowing of ADR-003 §Lesson 1: the lesson forbids divergence from established modules; adding a pure, surgical helper to `parser.py` (which is itself Sprint 1) is an extension, not a divergence, and is the minimum-surface way to give `transitions.py` the frontmatter-mutation primitive it needs. No behaviour change to existing `parser.py` functions is permitted.

## 10. Test obligations (forward reference)

This contract is falsified or confirmed by `tests/test_transitions*` in Phase 2.D, families 1–10 per the Sprint 2 plan: happy path (RF-2.1, 20 cases), FSM rejection (RF-2.3, 10 cases), idempotency (RF-2.4), SIGKILL fuzzer ×50 (RF-2.2 + D11), gate orchestration (D4), performance p99 `< 100 ms` (RF-2.6), WAL format completeness (RF-2.5), concurrency (D8), parser helper (D2), CLI integration (Phase 2.E). **No clause in this document is considered met by assertion; each is met only by a passing test.**
