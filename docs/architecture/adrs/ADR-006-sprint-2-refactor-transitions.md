# ADR-006: Sprint 2 Refactor — `transitions` Module Specification

**Status:** Accepted (Phase 2.A — approved before any `transitions.py` code; amended in-place via fix-forward on 2026-05-17 to address Copilot review on PR #1)
**Date:** 2026-05-17
**Deciders:** atomic-dag contributors
**Supersedes:** none
**Constrained by:** ADR-003 (Sprint 1 Lessons) §Lesson 3; `docs/PLANO_ENGENHARIA_SOFTWARE_V1.md` §3.3 (RF-2.1–RF-2.6), §6.2 (sequence), §8.1 (phases 2.A–2.H)
**Deprecates as reference:** `docs/PLANO_CONTINUIDADE_FRACTAL_v3.md` (carries the rejected D3 and a `state.json` naming error; no longer canonical)

## Context

Sprint 2 introduces `execute_transition`, the **first operation in the system with a persistent side effect**. Every Sprint 0/1 module either reads, validates, or writes a single file atomically as an isolated primitive. `execute_transition` is different in kind: it is a *composition* of validated primitives (`parser`, `gate`, `fsm`, `writer`, `wal`) that must behave as a single tolerable-failure operation.

The hard problem is not writing an FSM (exists in `fsm.py`), nor writing atomically (exists in `writer.py`), nor appending an event (exists in `wal.py`). It is the **atomicity boundary of the composition**: `write_atomic` is atomic and `log_event` is atomic, but the *sequence* of the two is not. The window between them is where a SIGKILL produces an inconsistent on-disk picture. The entire framework exists because LLM-driven systems silently degrade; an unprincipled answer to this window would reproduce, at the infrastructure layer, exactly the failure class the project is built to prevent.

A prior design iteration proposed a two-phase WAL (an `intent` event before the write and a `commit` event after). That proposal directly contradicts an already-accepted, already-committed decision (ADR-003 §Lesson 3) and the verbatim prose of the specification (§6.2). This ADR records the conflict, resolves it in favour of the existing authority, and adds a falsifiable regression invariant so the residual risk is verifiable rather than assumed.

## Decision

### Operation ordering (D1)

`execute_transition` performs, in this exact order:

```
parse_atom(filepath) -> Atom
gate.validate_gate(atom.meta) -> GateResult            # ALWAYS called (D4/RF-2.5)
fsm.validate_transition(atom.state, action) -> (valid, new_state)
    invalid  -> return error, exit 1, ZERO disk write, ZERO WAL entry
route resolution:
    action == "check":  gate.passed -> to_state = "verified"
                        not passed  -> to_state = "returned"   (both exit 0)
    otherwise:          to_state = new_state from FSM
content' = parser.replace_state_in_frontmatter(content, to_state)
writer.write_atomic(filepath_md, content')             # local POSIX atomicity
wal.log_event(wal_path, { ... })                       # SINGLE event, AFTER write
```

The WAL event is written **after** the atomic disk write, as a single record. This is the ordering mandated by §6.2 and confirmed by ADR-003 §Lesson 3.

**The gate is computed before the FSM check**, preserving the ADR-003 §Lesson 3 ordering verbatim (`parse → validate_gate → is_valid_transition → atomic_write → log_event_to_wal`) and making the "ALWAYS called" claim of D4 literally true: even transitions that the FSM will subsequently reject invoke the gate first. The gate result on the FSM-invalid path is discarded with the early-return and no WAL entry is emitted (per RF-2.3). The cost is trivial — `gate.validate_gate` is a pure function over the `atom.meta` dict with no I/O — and the benefit is fidelity to the established invariant: tradução fiel takes precedence over paralela optimisation. An earlier draft of D1 inverted this order (FSM-then-gate) as a micro-optimisation; that inversion was reverted on 2026-05-17 because it (a) contradicted ADR-003 §Lesson 3, (b) contradicted the §6.2 sequence diagram verbatim, and (c) made the D4 "ALWAYS called" claim self-contradictory with the FSM-invalid early-return.

### Idempotency by replay (D2)

Before acting, `read_events(wal_path)` is consulted. If a `transition` event already matches `(atom_id, from_state, to_state, action)` **and** the on-disk `.md` is already in `to_state`, the function returns `TransitionResult(idempotent=True)` with exit 0 and performs **zero** disk writes and **zero** new WAL entries. After a replay, `read_events` returns the original single entry (length unchanged) — this is the RF-2.4 falsifiability criterion.

### WAL record schema (D4)

A single event of type `transition` with mandatory fields: `atom_id`, `from_state`, `to_state`, `action`, `gate_result`, `duration_ms`. `timestamp` (ISO-8601 UTC) is added automatically by `wal.log_event`. `gate_result` is **non-optional**: the gate is always invoked even for actions that do not determine routing, because RF-2.5 requires a complete `gate_result` in every WAL entry.

`gate_result` is serialised as a JSON object with the exact shape `{passed: bool, gold_score: int, pqms_score: float, vvv_score: float, reasons: [str, ...]}` — mirroring the public fields of the `gate.GateResult` frozen dataclass. The conversion is performed by `execute_transition` before calling `wal.log_event` (which uses `json.dumps` and does not accept arbitrary dataclasses; passing a `GateResult` directly would raise `TypeError`). `reasons` is logged verbatim, without redaction or truncation — full auditability by design.

### `TransitionResult` type (D5)

A frozen dataclass with `__bool__ = success`, fields `atom_id, from_state, to_state, action, gate_passed, idempotent, duration_ms`. This mirrors the `GateResult` precedent established in Sprint 1 (`gate.py`), keeping the idiom consistent across the codebase.

### Exit-code mapping (D6)

`atom-not-found` → 2 (structural). `FSM-invalid` (illegal `(state, action)` pair, or any action from a terminal state) → 1 (operational). Success → 0, **including** the idempotent case and the gate-fail-on-`check` → `returned` case. A failed gate on `check` is a route, not an error: the operator's transition request was valid; the system merely routed the atom back for refinement.

### Concurrency posture (D8)

Per-atom locking is **deferred to Sprint 5**. FM-01 (concurrent WAL writes) is *mitigated* — not closed — by `O_APPEND` semantics plus the guarantee that event payloads stay below `PIPE_BUF`, making line-level appends atomic on POSIX. `TECHNICAL_DEBT.md` **will record** FM-01 as mitigated with the Sprint 5 closure plan; the entry lands in the Phase 2.F closing commit (commit 13 of the Sprint 2 sequence) alongside the `cov-fail-under` 80→95 bump. No new locking code is introduced in Sprint 2.

### Regression invariant — "disk never lags the WAL" (D11)

For every `transition` event in the WAL, the on-disk `.md` is in a state equal to or later than that event's `to_state`. The only SIGKILL outcome tolerated is **disk ahead of WAL** (atom mutated, WAL silent) — recoverable, and the explicit responsibility of the Sprint 5 `reconcile` command via its divergence-detection path. The outcome **WAL ahead of disk** (WAL claims a transition the disk does not reflect) is **forbidden**; the SIGKILL fuzzer test (D7) actively attempts to produce it and must fail to do so. D11 is the falsifiable guard that makes the risk accepted by the chosen ordering a *verified* property rather than an assumption — it is not an alternative to the ordering, it is its proof obligation.

### Open-question resolutions

- **DA-1 (deps gating): deferred.** `transition` is an explicit operator command. The DTP D2 invariant ("deps pendentes NUNCA despachado") is a *dispatch/selection* invariant and is already honoured by `dag.find_next_actionable` on the dispatch path. Enforcing it inside `transition` would re-implement `next`-path logic in the wrong place and inflate scope. A future `--enforce-deps` flag (Sprint 3+) can add this orthogonally without rewriting `transitions.py`.
- **DA-2 (gate coupling): always called, selectively determinative.** Always invoked because `gate_result` is a mandatory WAL field (RF-2.5). Determinative **only** for `action == "check"` (pass → `verified`, fail → `returned`, both exit 0). For all other actions the gate is computed and logged but does not alter the FSM route.
- **DA-3 (`checked` state): intentional, not a bug.** `checked` is transient and is **never persisted** as a stable state. `in-progress + check` produces FSM `→ checked` (valid); the orchestrator immediately resolves the route via the gate and persists `verified` or `returned` directly. `fsm.py` is **not modified**. This matches the documented behaviour in `tests/test_fsm.py:test_happy_path_pending_to_closed`.

### Nomenclature

There is **no `state.json`** anywhere in the design. An atom is a `.md` file with `state` in its YAML frontmatter. State mutation is a surgical frontmatter edit via `parser.replace_state_in_frontmatter(content, new_state)`, then a full-file rewrite via `writer.write_atomic`. WAL location is `<project>/.atomic-dag/wal.jsonl`.

`execute_transition` is responsible for ensuring the WAL parent directory exists via `Path(wal_path).parent.mkdir(parents=True, exist_ok=True)` before the first call to `wal.log_event` — this preserves the existing `wal.log_event` contract ("parent directory must already exist", documented in `wal.py`) without modifying `wal.py`. The `.atomic-dag/` directory is therefore created lazily by `execute_transition` on first use of the project, not by `wal.log_event` itself.

## Consequences

**Positive.** The chosen ordering guarantees that no SIGKILL can ever produce a false-positive transition claim. Every observable post-crash state is either unchanged or a genuine, completed transition that the WAL merely failed to record — a gap that is detectable and recoverable by design. D11 converts the residual risk into a continuously tested invariant, consistent with the project's Popperian methodology. Reusing five already-validated primitives means the new surface area is the composition logic alone.

**Negative.** A crash in the write→log window leaves an audit gap (atom advanced, WAL silent). This is accepted: it is recoverable, and closing it fully requires the Sprint 5 recovery/`reconcile` machinery. The ARIES-style write-ahead protocol that would close it earlier is unavailable without a recovery manager and would, in isolation, be strictly worse (see Alternatives, item 1).

**Neutral.** The gate is computed on every transition even when non-determinative, a small constant cost justified by the RF-2.5 audit-completeness requirement. `cov-fail-under` rises 80 → 95 in the final Sprint 2 commit.

## Alternatives Considered

1. **Two-phase WAL: `intent` event before `write_atomic`, `commit` event after (the rejected D3).**
   **Rejected**, in conformance with ADR-003 §Lesson 3 and §6.2 verbatim. ADR-003 §Lesson 3 records this exact alternative and its rejection verbatim:

   > Write WAL before atomic_write (reverse order). Rejected because SIGKILL between WAL write and atomic_write would leave WAL claiming a transition that did not occur on disk — a worse inconsistency than the current ordering's risk of disk-without-WAL.

   The asymmetry is decisive and not aesthetic: disk-ahead-of-WAL produces *no false belief* (the transition genuinely occurred; the next reader trusts the disk and is correct; the gap is a recoverable audit hole) whereas WAL-ahead-of-disk produces a *false-positive claim* with no in-system means to detect it absent a recovery manager. The classical ARIES write-ahead protocol (Mohan et al., 1992 — the project's cited source) is only safe because a recovery procedure reconciles log-vs-data with REDO/UNDO at every boot. Two-phase emission without that recovery manager is half-ARIES: it pays the cost of log-first without the benefit of REDO. The "helps detect a crash" argument does not overturn ADR-003, because the Sprint 5 `reconcile` already detects the disk-without-WAL case via its divergence path. Two-phase intent+commit is the correct **end state** (Sprint 5+, paired with a recovery manager), not a Sprint 2 decision.

2. **Mutating an external `state.json` instead of the `.md` frontmatter.**
   **Rejected.** The atom *is* the markdown document; there is no separate state store. Introducing one would split the source of truth, break the "documentation as code" principle the system relies on, and create a second reconciliation surface. Surgical frontmatter mutation keeps the atom self-describing and single-sourced.

3. **Enforcing dependency satisfaction inside `execute_transition` (rejecting DA-1's deferral).**
   **Rejected** for Sprint 2. Deps satisfaction is a dispatch-path invariant already enforced by `dag.find_next_actionable`. Duplicating it in the explicit operator command conflates selection logic with execution logic and inflates Sprint 2 scope; it is cleanly addable later as an orthogonal flag.

4. **Coupling the gate only when it determines the route (rejecting DA-2's "always called").**
   **Rejected** because RF-2.5 makes `gate_result` a mandatory, non-null WAL field for every transition. A WAL entry without a gate result would fail the audit-completeness criterion regardless of whether the gate influenced routing.

5. **D1 ordering with FSM before gate (FSM-then-gate as a micro-optimisation).**
   **Rejected**, on 2026-05-17 fix-forward after Copilot review caught it. Even though placing the FSM check first avoids computing the gate on FSM-invalid transitions, that ordering (a) directly contradicts ADR-003 §Lesson 3 verbatim, (b) contradicts the §6.2 sequence diagram verbatim, and (c) makes the D4 "ALWAYS called" claim self-contradictory with the early-return on FSM-invalid. The optimisation is also trivial in absolute terms (gate is a pure dict read with no I/O). Fidelity to the established ordering is preferred over paralela invention; the same principle that drove the rejection of D3 (item 1 above) applies symmetrically here.
