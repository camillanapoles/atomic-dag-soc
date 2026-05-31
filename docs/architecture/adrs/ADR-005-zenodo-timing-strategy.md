# ADR-005: Zenodo DOI Timing Strategy

**Status:** Accepted  
**Date:** 2026-05-12  
**Deciders:** atomic-dag contributors
**Superseded by:** ADR-008 (2026-05-31) — partially. ADR-008 retains this ADR's
"Zenodo requires public repo" mechanism but relocates the public reveal + arXiv
to Sprint 7 and defers DOI minting to Sprint 8 (ordering by permanence +
optimization-before-publication). The Decision items 1-5 below reflect the
original Sprint-4 timing and are HISTORICAL; see ADR-008 for the vigent plan.

## Context

The atomic-dag-soc repository is currently private during doctoral
research development. Zenodo standard (zenodo.org) requires public
GitHub repositories for DOI archiving. Zenodo Sandbox accepts private
repos but generates non-citable test DOIs that are periodically deleted.

Task 2.0.2 of PLANO_CONTINUIDADE_FRACTAL_v2 specified Zenodo integration
during Phase 2.0. The decision now is when to make the repository public
to enable real DOI generation.

## Decision

We defer making the repository public until Sprint 4 closes with Hello
SOC functional end-to-end (expected August 2026). At that point, we
will:

1. Make the repository public via GitHub Settings
2. Create retroactive GitHub releases for all completed sprint tags
   (v0.1.0-sprint0, v0.2.0-sprint1, v0.3.0-sprint2, v0.4.0-sprint3,
   v0.5.0-sprint4)
3. Configure Zenodo webhook to archive all releases automatically
4. Create CITATION.cff with all generated DOIs
5. Submit arXiv preprint in coordination with the public reveal

## Consequences

**Positive.** Public reveal coordinates with Sprint 4 demonstrable
system (Hello SOC), maximizing initial impact. Multiple DOIs generated
simultaneously create stronger narrative than isolated early DOIs.
Coordination with arXiv preprint amplifies academic visibility.
Intermediate work (Sprints 2-3) stays private during iteration.

**Negative.** No real DOI available for citation until August 2026.
Task 2.0.2 of Phase 2.0 remains as scheduled technical debt rather
than completed task.

**Neutral.** Phase 2.0 of the continuity plan is considered functionally
complete with Tasks 2.0.3 and 2.0.1 closed and Task 2.0.2 strategically
deferred with explicit timing.

## Alternatives Considered

1. **Make repository public now** for immediate Zenodo DOI. Rejected
   because Sprint 2 is intermediate infrastructure work without
   demonstrable system; public exposure premature.

2. **Use Zenodo Sandbox** for non-citable test DOIs. Rejected because
   Sandbox DOIs are not citable in peer-reviewed papers and are
   periodically deleted, requiring redo when going public.

3. **Make repository public only at Sprint 5 / v1.0.0-rc1**. Rejected
   because Sprint 4 closing with Hello SOC functional is the natural
   marker for demonstrable system; Sprint 5 adds concurrency features
   but doesn't change the demonstration narrative.
