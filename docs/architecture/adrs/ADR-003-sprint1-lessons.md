# ADR-003: Sprint 1 Lessons Learned and Sprint 2 Calibration

**Status:** Accepted  
**Date:** 2026-05-12  
**Deciders:** atomic-dag contributors

## Context

Sprint 1 closed on 2026-05-07 with tag v0.2.0-sprint1, delivering four
modules (parser, dag, gate, cli) with 147 tests passing, honest global
coverage of 97.32%, and zero warnings on ruff or mypy strict. The sprint
took approximately 5h30 in a single intensive session — within the
estimated 8-12h band but at the lower end.

Three procedural and architectural lessons emerged during execution
that need to be documented before Sprint 2 begins, both to prevent
regression of anti-patterns and to calibrate estimates for the
remaining sprints.

## Decision

We codify three lessons from Sprint 1 as binding constraints on
Sprint 2 and beyond:

### Lesson 1: Coverage omit list for functional code is rejected

During cli.py validation in Sprint 1, an attempt was made to add
`fsm.py`, `wal.py`, and `writer.py` (Sprint 0 functional code with 73
passing tests) to the coverage omit list to elevate apparent coverage
from 69% to 80%+. This proposal was rejected. The correct measurement
with the full test suite returned an honest 97.32% global coverage.

The omit list shall contain only:
- Modules with `NotImplementedError` stubs awaiting future sprints
- Abstract base classes without concrete implementations
- Test utilities themselves (if any)

Adding functional code to omit reproduces against the project the
exact anti-pattern (auto-inflation of metrics) that `gate.py`
exists to prevent. This is the founding constraint of the project
and cannot be violated internally.

### Lesson 2: Delta characteristic for Sprint 1 exceeded initial estimate

The fractal convergence model in `FUNDAMENTACAO_MATEMATICA_INTEGRADA_V1`
estimates delta values per granularity level: ~0.40 for module level.
The empirically observed delta for Sprint 1 module-level work
(parser, dag, gate, cli) was higher, approximately 0.5-0.7 per
iteration, with convergence to PMQ ≥ 9.5 in three to four iterations
instead of the predicted six to seven.

Recalibration for Sprint 2:
- Use delta = 0.5 with uncertainty band of ±30% as central estimate
- This refines the iteration count for Sprint 2 from ~7 to ~4
- Estimated time for Sprint 2: 8-12 hours (consistent with original)
- If observed delta differs significantly, recalibrate again for Sprint 3

### Lesson 3: Order of operations within composite functions

For Sprint 2's `execute_transition`, the order of internal operations
must be: parse → validate_gate → is_valid_transition (FSM) →
atomic_write → log_event_to_wal.

The point of no return is between FSM check (last reversible check)
and atomic_write (first irreversible operation). If SIGKILL occurs
between atomic_write and log_event, the on-disk state is the new
atom state without WAL entry — this is recoverable via the `reconcile`
command planned for Sprint 5. If SIGKILL occurs before atomic_write,
nothing changed and the system remains in the previous state.

This ordering preserves the atomicity invariant: at any point in time,
the system is either fully in the previous state or fully in the new
state, with only one recoverable intermediate scenario.

## Consequences

**Positive.** The three lessons formalize what was learned empirically,
preventing regression. Future sprints can be calibrated using observed
delta values rather than initial estimates. The execute_transition
ordering is documented before implementation, applying the principle
of specification-before-execution.

**Negative.** The recalibration of delta means previous estimates in
`PLANO_CONTINUIDADE_FRACTAL_v2` may be slightly conservative. This
is acceptable because conservative estimates that finish early are
strictly preferable to optimistic estimates that overrun.

**Neutral.** This ADR codifies the workflow contract for Sprint 2 and
beyond. Subsequent ADRs (004, 005, etc.) build on this foundation.

## Alternatives Considered

1. **Allow coverage omit for functional code with NotImplementedError
   wrappers.** Rejected because the wrapper itself would be functional
   code masquerading as a stub, reintroducing the inflation vector
   under a different name.

2. **Keep delta = 0.40 as estimate.** Rejected because empirical
   observation contradicts the initial value. Using observed data
   over prior assumptions is the VVV principle applied to the
   planning process itself.

3. **Write WAL before atomic_write (reverse order).** Rejected
   because SIGKILL between WAL write and atomic_write would leave
   WAL claiming a transition that did not occur on disk — a worse
   inconsistency than the current ordering's risk of disk-without-WAL.

## References

- `knowledge/FUNDAMENTACAO_MATEMATICA_INTEGRADA_V1.md` — fractal
  convergence model and delta characteristic estimates
- `knowledge/FRAMEWORK_FRACTAL_ANALYSIS_MERGED.md` — gold standard
  PTDISLGEOX and anti-inflation principle
- `docs/PLANO_ENGENHARIA_SOFTWARE_V1.md` Part 3.3 — Sprint 2
  requirements specification
- ADR-001 (dual-layer LLM-Python) — architectural foundation this
  ADR builds upon
- ADR-002 (Python 3.11+) — toolchain constraints
