# ADR-008: Publication Ordering Rule + Optimization-Before-Publication + Continuous Replanning

**Status:** Accepted
**Date:** 2026-05-31
**Deciders:** atomic-dag contributors
**Supersedes:** ADR-005 partially (DOI/arXiv timing items 1-5 of its Decision; the Zenodo-requires-public mechanism is retained)
**Inherits:** ADR-003 §Lesson 2 (recalibrate planning from observed data — VVV applied to the plan itself)
**Constrained by:** docs/PLANO_ENGENHARIA_SOFTWARE_V1.md (sprint sequence, recalibrable)

## Context

ADR-005 (Accepted, 2026-05-12) fixed repository-public + arXiv preprint + ALL
Zenodo DOIs at Sprint 4 close (Hello SOC functional), and explicitly rejected
deferring DOI minting to Sprint 5/v1.0.0. Operating experience through Sprint 3
surfaced two distinctions ADR-005 collapsed:

1. **Permanence asymmetry.** An arXiv preprint is RETRACTABLE — a v2 is a normal,
   expected submission. A Zenodo DOI is PERMANENT — it cites a fixed artifact
   forever. Minting a permanent DOI over a system whose robustness layer
   (reconcile, writer error-recovery TD-001, per-atom locking FM-01) is still
   open would permanently cite an immature system. The two artifacts must not
   share a gate.

2. **Optimization precedes publication.** What is published (preprint) and what
   is permanently cited (DOI) should describe an OPTIMIZED system — performance,
   coverage, and structural quality consolidated — not a merely-functional one.
   A dedicated optimization phase precedes each publication.

Per ADR-003 §Lesson 2, the project recalibrates its plan from observed data at
each sprint boundary. Fixing a precise DOI date now (as ADR-005 did) repeats the
over-early-commitment that this ADR corrects. The remedy is to fix the ORDERING
RULE, not the dates.

## Decision

### Ordering rule (binding — D-pub-1)

Publication artifacts are ordered by permanence, and each is preceded by an
optimization phase:

- A **retractable** artifact (arXiv preprint) is published only after the system
  it describes is (a) robust — reconcile + writer error-recovery + per-atom
  locking closed — and (b) optimized in a dedicated phase. Target: Sprint 7.
- A **permanent** artifact (Zenodo DOI) is the LAST ACT of the program, minted
  only over a finalized, externally-validated, benchmarked, re-optimized release
  (v1.0.0), on a gate that contains no other scope. Target: Sprint 8.
- The DOI never shares a gate with non-publication work. (Analogue, at program
  scale, of ADR-006 §D11's "point of no return" discipline: the irreversible act
  gets maximum deliberation and minimum surrounding noise.)

### Current vigent sequence (recalibrable per ADR-003 §Lesson 2 — D-pub-2)

- **Sprint 4** (v0.5.0): Hello SOC + llm-bridge + build_dashboard. No publication.
- **Sprint 5** (v0.6.0): robustness — writer TD-001 fix → reconcile → per-atom
  locking (closes FM-01/TD-004). No publication.
- **Sprint 6** (v0.7.0): meta-use (US-07 / DOC-SELF-001 self-management) +
  external validation + benchmarks.
- **Sprint 7** (v0.8.0): OPTIMIZATION (perf/coverage/refactor) + arXiv preprint.
  Repo becomes public here; Zenodo webhook ARMED (not fired); retroactive
  releases; CITATION.cff scaffold.
- **Sprint 8** (v1.0.0): final OPTIMIZATION + DOI MINT (isolated gate). Fires the
  webhook armed in Sprint 7. Permanent. Irreversible.

This sequence is the plan of record AS OF 2026-05-31 and is re-evaluated at each
sprint close. A future sprint MAY reorder later sprints if observed data warrants,
provided the ordering rule (D-pub-1) holds.

### Repo-public mechanism (retained from ADR-005 — D-pub-3)

ADR-005's mechanism — public reveal, retroactive GitHub releases for all sprint
tags, Zenodo webhook configuration, CITATION.cff — is retained, but RELOCATED to
the arXiv gate (Sprint 7), and split: the webhook is armed at Sprint 7; only the
DOI MINT fires at Sprint 8.

## Consequences

**Positive.** DOI permanence protected (cites only a finalized, optimized v1.0.0).
arXiv quality protected (preprint describes a robust, optimized system). Planning
honesty preserved: the ordering rule is fixed; the dates are explicitly
recalibrable, consistent with ADR-003 §Lesson 2.

**Negative.** No citable DOI until Sprint 8 (~v1.0.0). Mitigated: the arXiv
preprint is citable-as-preprint from Sprint 7. No citable artifact at all until
Sprint 7 — a deliberate trade of early visibility for published quality.

**Neutral.** ADR-005's public-reveal mechanism survives; only the timing (split
arXiv vs DOI), the optimization-before-publication rule, and the recalibration
clause are new.

## Alternatives Considered

1. **Keep ADR-005 (all DOIs at Sprint 4).** Rejected: mints a permanent DOI over
   a pre-reconcile, un-optimized system. (FDC-U O-505, Σ 6.30.)

2. **arXiv at Sprint 4, DOI right after robustness (Sprint 5/6).** Rejected:
   publishing before a dedicated optimization phase publishes a merely-functional
   system; quality of the published artifact is below the project's bar.

3. **arXiv and DOI in the same late sprint.** Rejected: collapses the permanence
   asymmetry the operator identified — a retractable preprint and a permanent DOI
   should not share a gate, and an irreversible act deserves an isolated gate.

4. **Fix the DOI date rigidly in this ADR.** Rejected: repeats ADR-005's
   over-early-commitment error; ADR-003 §Lesson 2 mandates recalibration from
   observed data. The ordering rule is binding; the dates are the current
   recalibrable plan.
