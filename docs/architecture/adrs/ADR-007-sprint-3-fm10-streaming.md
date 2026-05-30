# ADR-007: Sprint 3 — `streaming` Module Specification (FM-10 Closure)

**Status:** Accepted (Phase 3.A — approved before any `streaming.py` code)
**Date:** 2026-05-30
**Deciders:** atomic-dag contributors
**Supersedes:** none
**Constrained by:** ADR-003 (Sprint 1 Lessons) §Lesson 3; ADR-006 (Sprint 2 Refactor) D1/D2/D4/D11; `docs/PLANO_ENGENHARIA_SOFTWARE_V1.md` §3.4 (Sprint 3 — FM-10); `docs/BRIEFING_PRE_SPRINT_3_v2.md` §C (Plano Sprint 3) and §F (Critério Popperiano-mestre)

## §0 — Nota terminológica (closure durável de D13)

Throughout this ADR (and across the repository — CLAUDE.md §1, README, DOC-SELF-001, dashboard) the term **falsificável** is used in its strict **Popperian** sense, after Karl Popper (*The Logic of Scientific Discovery*, 1934 / English 1959):

> *A statement, a theory, or a system is **falsifiable** when it is testable and could in principle be refuted by empirical evidence. Falsifiability is a **virtue** — it is what distinguishes science from non-science — not a synonym for "fraudable", "fakeable", or "fabricable".*

In atomic-dag-soc, the design goal is to make claims of LLM progress *falsifiable* in this Popperian sense: every claim that a transition occurred (`atomic-dag transition`) or that a stream tick processed an event (`atomic-dag stream`) must be **refutable by inspecting the on-disk state and the WAL**. The system does not trust narrative; it produces evidence that can be tested against reality and would fail the test if the claim were false. That is the entire point of the gate (`gate.py`), the FSM (`fsm.py`), the atomic writer (`writer.py`), the WAL (`wal.py`), the regression invariant D11 of ADR-006 ("disk never lags the WAL"), and — in this ADR — the regression invariant D7 below ("tick that emits a `streaming_tick` event must have advanced the cursor on disk").

The empirical observation that motivated the entire project — SOC V3 self-reporting PQMS 9.44 while audit measured 4.49 — is itself an instance of the Popperian methodology applied: the claim "PQMS 9.44" was *falsified* by the audit, and the framework exists to make such falsifications cheap and routine. Any reading of "falsificável" in repository documentation as a synonym for "fraudable", or as suggesting the system *facilitates* fraud, is a misreading and must be corrected at the source. This §0 is the durable closure of debt **D13** (registered in `docs/STATUS.md`), which was partially closed in Phase 2.L (notes added to `CLAUDE.md §1`, `README`, `DOC-SELF-001`) and is now anchored in an authority-class ADR for future readers — human or LLM — who reach the repo via clone or search and read documents in any order.

## Context

Sprint 3 closes **FM-10**, the highest-RPN open item in the FMEA SOC V4 (RPN = 162). FM-10 is a *coupling failure*: `tick_streaming` (in the original SOC V3 design) processes a stream event but **does not call** `advance_cursor` — the function that would persist the new cursor position to disk. The result, observable in the founding empirical episode, is that streaming runs *appear* to make progress (events consumed, narrative generated, internal counters incremented) while the on-disk cursor remains stale. On the next session, with no persistent record of which events were already processed, the system reprocesses from the last persisted cursor — silently duplicating work and producing inconsistent narratives across sessions. This is the failure mode the entire project's continuity claim must refute.

Sprint 1 was planned to port `tick_streaming` and `advance_cursor` from the original SOC V3 codebase into the Python assembler; that port did not occur, and the gap was registered as **TD-003** ("FM-10 closure") from Sprint 0. Sprint 2 delivered `execute_transition` (the operator-command path) but explicitly deferred the streaming path to Sprint 3. Sprint 3 therefore performs the port and closes the coupling in the same sprint, with the regression invariant committed in main as the gate.

The hard problem is not writing a `streaming.py` module (the primitives `parser`/`gate`/`fsm`/`writer`/`wal` already exist and were validated in Sprints 0-2), nor is it inventing a new cursor concept (the cursor is the atom's `state` in the FSM lattice, persisted in `.md` frontmatter and `.atomic-dag/state.json`). The hard problem is **the regression invariant**: how to make the claim "FM-10 is closed" itself falsifiable, so that any future refactor that re-introduces the decoupling fails CI before reaching main. The answer is **D7** below — a regression test (`test_fm10_regression.py`) which is RED at the SHA where `streaming.py` exists without coupling (3.C.1) and GREEN at the SHA where `advance_cursor` is invoked (3.C.2), with the pair committed in main and run on every subsequent push.

This ordering follows the Sprint 2 pattern exactly: spec before code (ADR-007 in 3.A, api/streaming.md in 3.B), then code in two atomic commits to make the regression empirically observable (3.C.1 = skeleton without coupling = RED; 3.C.2 = coupling active = GREEN), then the adversarial battery (3.D), then the CLI wire (3.E), then the coverage gate maintenance and TD-003 closure (3.F), then merge and tag (3.G). Every phase has a CI 3-matrix gate; every artifact has a falsifiable acceptance criterion.

## Decision

### Operation ordering (D1)

`tick_streaming(project: Path, event: StreamEvent) -> TickResult` performs, in this exact order:

```
parse_atom(project / event.atom_id_path) -> Atom
gate.validate_gate(atom.meta) -> GateResult           # ALWAYS called (mirrors D4/ADR-006)
fsm.validate_transition(atom.state, event.action) -> (valid, new_state)
    invalid -> return TickResult(success=False, ...), exit 1, ZERO disk write, ZERO WAL entry
route resolution:
    event.action == "check": gate.passed -> to_state = "verified"
                             not passed  -> to_state = "returned"   (both exit 0)
    otherwise:               to_state = new_state from FSM
content' = parser.replace_state_in_frontmatter(content, to_state)
advance_cursor(state_path, new_cursor)                # <-- THE COUPLING (FM-10 closure)
writer.write_atomic(filepath_md, content')            # local POSIX atomicity
writer.write_atomic(state_path, json.dumps(new_state_json))  # cursor persisted atomically
wal.log_event(wal_path, { type: "streaming_tick", ... })     # SINGLE event, AFTER writes
```

Two `write_atomic` calls (atom `.md` and `.atomic-dag/state.json`) are sequenced before the WAL entry. The cursor advancement is **explicit and mandatory** — `advance_cursor` is called for every successful tick, not as a side-effect of `write_atomic`. This makes D7 (below) directly observable: if a `streaming_tick` event is in the WAL and the cursor on disk is unchanged, the test fails. The §Lesson 3 ordering of ADR-003 (`parse → gate → fsm → write → wal`) is preserved verbatim; `advance_cursor` is the cursor-write step within `write`.

`advance_cursor` is a thin helper that reads the current state.json, updates the `cursor` field, and returns the new dict; the actual disk write is performed by `writer.write_atomic` (the only authorized writer). `advance_cursor` is **pure** (no I/O); it can be unit-tested in isolation and composed safely. `writer.py` is **not modified** by this sprint — I3 preserved.

### `StreamEvent` and `TickResult` types (D2)

Two frozen dataclasses in `streaming.py`:

```python
@dataclass(frozen=True)
class StreamEvent:
    atom_id: str                  # e.g. "A-042"
    action: str                   # FSM action: "check", "approve", "reject", ...
    payload: dict[str, Any]       # opaque event-specific data; logged in WAL verbatim
    timestamp_iso: str            # ISO-8601 UTC, source-provided (NOT auto-stamped)

@dataclass(frozen=True)
class TickResult:
    success: bool
    atom_id: str
    from_state: str
    to_state: str
    action: str
    cursor_before: str            # e.g. "A-041" or "<start>"
    cursor_after: str             # e.g. "A-042"
    gate_passed: bool
    idempotent: bool
    duration_ms: float
    def __bool__(self) -> bool: return self.success
```

`TickResult.__bool__ = success` mirrors the `GateResult` / `TransitionResult` precedent. `cursor_before` and `cursor_after` are **mandatory fields** — they are the falsifiability anchor. A `TickResult` where `cursor_before == cursor_after` and `success == True` is structurally impossible for non-idempotent ticks (D7 enforces this at runtime).

### Idempotency by replay (D3)

Before acting, `read_events(wal_path)` is consulted. If a `streaming_tick` event already matches `(atom_id, from_state, to_state, action, cursor_before, cursor_after)` **and** the on-disk `.md` is already in `to_state` **and** state.json cursor equals `cursor_after`, the function returns `TickResult(idempotent=True, success=True, ...)` with exit 0 and performs **zero** disk writes and **zero** new WAL entries. After a replay, `read_events` returns the original single entry (length unchanged). Idempotency is checked **before** the FSM check — mirrors ADR-006 §5 exactly.

### WAL record schema (D4)

A single event of type `streaming_tick` with mandatory fields:

```
{
  "ts": "<ISO-8601 UTC, auto-stamped by wal.log_event>",
  "type": "streaming_tick",
  "atom_id": "<str>",
  "from_state": "<str>",
  "to_state": "<str>",
  "action": "<str>",
  "cursor_before": "<str>",
  "cursor_after": "<str>",
  "gate_result": { "passed": <bool>, "gold_score": <int>, "pqms_score": <float>, "vvv_score": <float>, "reasons": [<str>, ...] },
  "duration_ms": <float>,
  "event_payload": <dict, verbatim from StreamEvent.payload>
}
```

`gate_result` is non-optional (RF-2.5 extended). `event_payload` is logged verbatim — no redaction, no truncation. `cursor_before` and `cursor_after` are non-optional — D7 reads these.

### Exit-code mapping (D5)

Mirrors D6 of ADR-006:
- `atom-not-found` (event references a non-existent atom file) → exit **2** (structural)
- `FSM-invalid` (action illegal from current state, or any action from a terminal state) → exit **1** (operational)
- success → exit **0** (including idempotent case and gate-fail-on-check → returned)

### Concurrency posture (D6)

Per-stream serialization is **deferred to Sprint 5** (same fate as FM-01 per-atom locks in ADR-006 D8). FM-01 mitigation extends to streaming: WAL events from concurrent `tick_streaming` calls remain atomic at the line level thanks to `O_APPEND` + payload < `PIPE_BUF`. Per-stream locks land in Sprint 5 alongside `reconcile` and `writer.py` cov-to-100% (TD-001).

The Sprint 3 stress test (D8 below, 4-process concurrency on distinct atoms) is identical in form to the 2.D battery — concurrent ticks on **different atoms** must produce parseable WAL lines and consistent state files; concurrent ticks on **the same atom** are not exercised in Sprint 3 (that is Sprint 5's domain).

### Regression invariant — FM-10 closure (D7) — *the Popperian master criterion*

For every `streaming_tick` event in the WAL with `cursor_after = X`, the on-disk `.atomic-dag/state.json` has `cursor == X` (or a cursor lexicographically later than X, in the case of a subsequent successful tick that overwrote it). The only SIGKILL outcome tolerated is **disk ahead of WAL** (cursor advanced, WAL silent) — recoverable by the Sprint 5 `reconcile` command via WAL replay against state.json divergence detection. The outcome **WAL ahead of disk** (WAL claims a `streaming_tick` event with `cursor_after = X` but state.json cursor is still the pre-tick value) is **forbidden**; the SIGKILL fuzzer test in Phase 3.D actively attempts to produce it and must fail to do so.

**The regression test `tests/test_fm10_regression.py` is the falsifiability anchor.** It is committed twice:

- At **SHA X-1** (end of Phase 3.C.1), `streaming.py` exists with `tick_streaming` implemented as a skeleton that processes the event and writes the atom `.md` but **does not call `advance_cursor`**. The regression test `test_tick_streaming_advances_cursor_on_disk` is RED at this SHA. This is the **literal recreation of FM-10** — required by the Popperian protocol: the regression must be observed failing before it is observed passing, otherwise the test could be vacuously passing on a degenerate input.

- At **SHA X** (end of Phase 3.C.2), `advance_cursor` is implemented and `tick_streaming` calls it as specified in D1. The regression test is GREEN at this SHA. The diff between X-1 and X is *the addition of the `advance_cursor(state_path, new_cursor)` line* (plus the helper implementation in the same diff).

The pair (X-1 RED, X GREEN) is committed to **main** through PR merge — both SHAs reachable from `main`. Any future refactor that decouples `tick_streaming` from `advance_cursor` will re-introduce the FM-10 failure mode, and the test — now running on every CI push — will fail. **This is the Popperian master criterion: FM-10 is closed iff the red→green commit pair is in main's history and the green commit is the current ancestor.** Coverage, lint, performance, narrative — none of these are non-negotiable for Sprint 3 closure. **Only D7 is.**

### Adversarial battery (D8)

Mirrors 2.D in form and intent:

- **SIGKILL ×50, strategy α.3 determinístico**: subprocess monkey-patches `wal.log_event` to `SIGSTOP` before the append; parent uses `waitpid(WUNTRACED)` to detect pause; parent sends `SIGKILL` in the critical window between `advance_cursor`+`write_atomic(state.json)` and `wal.log_event`. After the kill, the test inspects (a) atom `.md` state, (b) state.json cursor, (c) WAL. Acceptance: 50/50 trials in_critical_window with **zero violations of D7** (WAL never ahead of disk). The fuzzer is the empirical proof obligation of D7, parallel to how 2.D was the proof obligation of ADR-006 D11.
- **Idempotency adversarial**: re-running an already-applied tick produces `TickResult(idempotent=True)` with no new WAL line and no disk change. Acceptance: 50/50 trials.
- **Concurrency 4-proc**: 4 processes call `tick_streaming` on **4 distinct atoms** in parallel. Acceptance: 4 parseable WAL lines, 4 state.json transitions, all D7-consistent.
- **Performance**: p99 < 100 ms over 100 sequential calls (mirrors RF-2.6 from Sprint 2 — same threshold).

### Open-question resolutions (DA-1, DA-2, DA-3)

- **DA-1 (cursor type — monotonic integer vs lexicographic string): lexicographic string `"A-042"`.** Rejected the monotonic integer alternative because atoms are addressed by their `atomic_id` (frontmatter), which is a string by ADR-001. Introducing a parallel integer index would split source of truth (analogous to the rejected `state.json`-as-atom alternative in ADR-006). The lexicographic ordering of `atomic_id` already provides the monotonicity needed for `cursor_after > cursor_before` comparisons.
- **DA-2 (replay safety on partial WAL): rely on existing `wal.read_events` semantics.** `read_events` already filters malformed lines (existing contract from Sprint 0). Sprint 3 introduces no new WAL parsing — the streaming tick reads through the same path. If the WAL has a partial last line from a previous SIGKILL, `read_events` skips it; idempotency replay (D3) then proceeds against the well-formed prefix.
- **DA-3 (`stream` CLI subcommand vs `transition --streaming` flag): separate subcommand.** `atomic-dag stream <event-source>` is a separate CLI verb (Phase 3.E), parallel to `atomic-dag transition`. Rejected the `--streaming` flag because the inputs differ: `transition` takes `(atom_id, action)` as positional args; `stream` consumes a sequence of `StreamEvent` (from stdin JSONL or `--events-file`). Conflating them under one verb would require ambiguous flag combinations.

### Nomenclature

`.atomic-dag/state.json` is introduced in this sprint as the operational cursor store. Its schema is minimal:

```json
{
  "cursor": "<atomic_id of the last successfully ticked atom, or '<start>' if none>",
  "updated_at": "<ISO-8601 UTC>"
}
```

The atom `.md` files remain the authority for atom state (FSM `state` field in frontmatter — unchanged from Sprint 2). `state.json` is the *cursor index*, not a parallel state store. This nomenclature is consistent with ADR-006's rejection of `state.json`-as-atom (alternative #2 there): there is still no `state.json` carrying atom state; there is now a `state.json` carrying *only the streaming cursor pointer*. The two roles are distinct and the file is purpose-narrow.

## Consequences

**Positive.** D7 makes FM-10 closure a tested property — not a documented intention. The red→green commit pair in main's history is itself the artifact: any future PR that re-introduces the decoupling will fail CI on the regression test, and a reviewer reading the diff will see the test going from green to red, which is the inverse motion of the Popperian protocol and a clear signal of regression. The streaming path reuses all Sprint 0-2 primitives unchanged — surface area added is `streaming.py` (new module, no coupling to I3-frozen modules beyond imports) and `advance_cursor` (pure helper within `streaming.py`). The `.atomic-dag/state.json` schema is minimal and purpose-narrow, avoiding the ADR-006-rejected pattern of a parallel state store.

**Negative.** A SIGKILL between `advance_cursor`+`write_atomic(state.json)` and `wal.log_event` leaves an audit gap (cursor advanced on disk, WAL silent). This is **accepted**, in exact symmetry with ADR-006's accepted gap (atom advanced on disk, WAL silent). It is recoverable by Sprint 5's `reconcile`. The ARIES-style write-ahead alternative (rejected for `execute_transition` in ADR-006 Alternative #1) is rejected here for the same reason: WAL-ahead-of-disk is a strictly worse inconsistency, and a recovery manager is required to close the gap fully — that work is correctly placed in Sprint 5, not Sprint 3.

**Neutral.** The gate is computed on every streaming tick even when non-determinative (same as ADR-006 D4) — small constant cost for audit completeness. `cov-fail-under` stays at 95 (set in 2.F). `streaming.py` aims for 100% cov by 3.F.

## Alternatives Considered

1. **Couple `tick_streaming` to `advance_cursor` via callback injection rather than direct call.**
   **Rejected.** Callback injection adds a configuration surface (which callback to inject?) and a failure mode (callback misconfigured → coupling silently disabled, FM-10 re-introduced *without test failure*). Direct call within `tick_streaming` keeps the coupling structural — the only way to remove it is to edit `streaming.py` itself, which makes the diff visible in code review and trips D7 in CI.

2. **Cursor in atom frontmatter rather than `state.json`.**
   **Rejected.** Putting the streaming cursor in atom frontmatter would mean the cursor moves with the *current atom*, conflating the cursor (a pointer to the last-ticked atom) with the atom's state. The cursor is global to the project's streaming run; the atom state is local to each atom. Separation of concerns demands separate stores. `.atomic-dag/state.json` is the project-scoped operational store; atom frontmatter remains atom-scoped.

3. **Defer `streaming.py` to Sprint 4 (Hello SOC), implement the regression test against a stub.**
   **Rejected.** The regression test must be *grounded in the actual coupling*, not a stub. Testing against a stub gives a vacuous green: the test passes because the stub is trivially correct, not because the production code couples correctly. The Popperian protocol requires the test to be *informative* — it must fail when FM-10 is open and pass when FM-10 is closed. A stub-based test fails this informativeness criterion.

4. **Two-phase WAL for streaming (`tick_intent` before writes, `tick_commit` after).**
   **Rejected** for the identical reasons as ADR-006 Alternative #1 (the rejected D3 there). WAL-ahead-of-disk is the worse inconsistency; the asymmetry between disk-ahead-of-WAL (recoverable, no false belief) and WAL-ahead-of-disk (false-positive claim, no in-system detection) is decisive. Two-phase emission without a recovery manager is half-ARIES and pays the cost of log-first without the benefit of REDO. Sprint 5 + `reconcile` is the correct end state.

## References

- ADR-003 §Lesson 3 — order `parse → gate → fsm → write → wal` (authority, preserved)
- ADR-006 — `transitions` module spec; D1/D2/D4/D11 patterns reused in this ADR
- ADR-004 — `writer.py` tmp+fsync+rename (used unchanged; I3 preserved)
- `docs/PLANO_ENGENHARIA_SOFTWARE_V1.md` §3.4 — Sprint 3 FM-10 spec
- `docs/BRIEFING_PRE_SPRINT_3_v2.md` §C, §F — phase decomposition and Popperian master criterion
- `knowledge/MANUSCRITO_ATOMIC_DAG_RSL_V2_CORRIGIDO.md` §FMEA — FM-10 RPN=162 origin
- Popper, K. (1934/1959) — *The Logic of Scientific Discovery*; "falsifiability" definition used throughout this ADR (see §0)
- Mohan et al. (1992) — *ARIES: A Transaction Recovery Method...* — cited in ADR-006 Alternative #1, same logic applies here (Alternative #4)
