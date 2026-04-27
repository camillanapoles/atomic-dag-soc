# ADR-001: Dual Layer — LLM as Executor, Python as Enforcer

**Status:** Accepted  
**Date:** 2026-04-20  
**Deciders:** atomic-dag contributors

## Context

The SOC V4 architecture proposed by `DAW-enforcement-ESTRUTURAL.md` positioned the LLM itself as the runtime — reading frontmatter, interpreting rules, executing actions, updating state. That proposal has an internal contradiction: the project exists because LLMs degrade progressively in long tasks (empirical evidence: PQMS auto-reported 9.44 vs. measured 4.49), yet the proposed design relies on the LLM to be a reliable state machine. If the LLM drifts, there is no recourse.

## Decision

We maintain the LLM and the Python orchestrator as two distinct components that communicate via markdown files in the filesystem. The LLM writes content. The Python code reads, validates, computes state, and decides the next action. Neither tries to do the other's job.

## Consequences

**Positive.** The Python side is deterministic and testable. The LLM's non-determinism is contained — if the LLM misbehaves, the orchestrator catches it via the gate validator and the atomic writer, and state cannot be silently corrupted.

**Negative.** Two processes means an interface between them, which introduces its own correctness requirements. Specifically, the atomicity of writes (ADR-004) and the structure of the WAL (ADR-005) become critical.

**Neutral.** Mental model shifts from "the LLM runs the system" to "the LLM is a worker in the system, supervised by deterministic tools."

## Alternatives Considered

1. **LLM-only runtime** (original DAW proposal). Rejected because the enforcement becomes conventional rather than computational, reintroducing the degradation problem the project aims to solve.
2. **Python-only system without LLM**. Rejected because then we lose the generative capability that makes document production feasible in the first place.
