# ADR-009: LLM Bridge — Minimal Scope for Sprint 4

**Status:** Accepted
**Date:** 2026-05-31
**Deciders:** atomic-dag contributors
**Authority for:** docs/api/llm-bridge.md, src/atomic_dag/llm_bridge.py (Phase 4.C)
**Constrained by:** ADR-001 (dual-layer LLM⊥Python), ADR-003 §Lesson 3 (operation
ordering), ADR-007 §D1 (streaming operation order)

## Context

ADR-001 established the dual-layer architecture: the LLM writes content, Python
reads/validates/computes. Sprints 2-3 implemented the Python side (`transitions`,
`streaming`) with full adversarial proof. Sprint 4 bridges the gap: `llm_bridge.py`
is the component that calls an LLM, captures its output, and feeds it into the
existing assembler pipeline.

The knowledge base (LLM_PVM_FRAMEWORK_V1.md) describes an ambitious vision: the
LLM as a Process Virtual Machine, with automatic pattern detection, FPG canonical
schema, PMQ gate as FSM guard, and PEII refinement loops. That vision is valid as
a long-term architecture but inappropriate as Sprint 4 scope — the project is at
the "Hello SOC" demonstration stage and needs a minimal, testable bridge, not a
full PVM runtime.

## Decision

### D-bridge-1: Minimal scope (binding)

`llm_bridge.py` exposes exactly these capabilities for Sprint 4:

1. **Call an LLM** via API (provider-agnostic interface; default: Anthropic
   claude-sonnet-4-20250514). The call is synchronous, single-turn, stateless
   from the bridge's perspective (state lives in `state.json` per ADR-001).

2. **Parse the response** from unstructured text/markdown into a structured
   result that the assembler can consume (atom content for `transition`,
   or event payload for `streaming`).

3. **Inject into the pipeline** by calling `execute_transition` or
   `tick_streaming` with the parsed result. The bridge is a CALLER of the
   existing modules, not a replacement.

The bridge does NOT:
- Detect patterns automatically (LLM_PVM Pattern Detector — future sprint)
- Construct FPG canonical schemas (LLM_PVM — future sprint)
- Use PMQ gate as FSM guard condition (existing `gate.py` suffices)
- Run PEII refinement loops (future sprint, after validation)
- Manage conversation history or multi-turn context (stateless per-call;
  cross-session continuity is the WAL + state.json, not the bridge)

### D-bridge-2: Provider abstraction (binding)

The bridge accepts a `provider` parameter (protocol/ABC with a `complete`
method) so that tests can inject a mock provider. Production default is
Anthropic. The provider interface:

```python
class LLMProvider(Protocol):
    def complete(self, prompt: str, *, system: str = "") -> str: ...
```

This is the MINIMUM viable interface. No streaming, no tool_use, no multi-modal
— those are future extensions that don't change the protocol (they'd be new
methods or overloads, not changes to `complete`).

### D-bridge-3: Operation ordering (binding, inherits ADR-003 §Lesson 3)

A bridge call follows this order:

1. Load atom/state from disk (parse_atom or read state.json)
2. Construct prompt from atom content + template
3. Call provider.complete(prompt) → raw_response
4. Parse raw_response → structured result (atom content or event payload)
5. Call execute_transition or tick_streaming (which internally do
   gate→FSM→write→WAL per ADR-003 §Lesson 3 / ADR-007 §D1)

The bridge NEVER writes to disk directly — it delegates all state mutation to
the existing modules. This preserves every invariant (I3, D11, atomicity).

### D-bridge-4: Error handling (binding)

- LLM API failure (network, rate limit, auth): raise `BridgeAPIError` → CLI exit 2
- LLM response unparseable: raise `BridgeParseError` → CLI exit 2
- Downstream errors (StreamCursorMismatchError, InvalidTransitionError):
  propagated as-is → CLI exit 1 (per existing exit code contracts)
- Success: CLI exit 0

### D-bridge-5: Testability without real LLM (binding)

All tests use a mock provider (returns predetermined text). No real API call in
the test suite. The bridge is tested as a composition orchestrator, not as an LLM
evaluator — quality of LLM output is outside scope (that's the Hello SOC
demonstration in 4.D, not the bridge unit tests in 4.C).

## Consequences

**Positive.** Minimal surface = minimal risk. The bridge adds no new state
mutation paths (delegates to existing modules). Every invariant (I3, D11,
atomicity, WAL ordering) is preserved by construction. Testable without LLM.

**Negative.** No automatic pattern detection, no refinement loop, no multi-turn
context. These are real capabilities from LLM_PVM_FRAMEWORK that are deferred.
Mitigated: the bridge interface (D-bridge-2) is extensible without breaking
change.

**Neutral.** The bridge is the first module that crosses the LLM↔Python boundary
operationally (ADR-001 described it architecturally). This makes the Hello SOC
(4.D) possible.

## Alternatives Considered

1. **Full LLM-PVM runtime in Sprint 4.** Rejected: over-scoped for a
   demonstration sprint. Pattern Detector + FPG schema are research-grade
   components that deserve their own ADR and sprint when the project reaches
   that maturity. (ADR-008 ordering rule: optimize before publish.)

2. **No bridge module — Hello SOC calls LLM directly in script.** Rejected:
   violates ADR-001's separation. A script that calls the LLM and writes to
   disk directly bypasses gate/FSM/WAL, reintroducing the trust problem the
   project exists to solve.

3. **Bridge with built-in PMQ gate.** Rejected for Sprint 4: the existing
   `gate.py` already validates quality. Adding PMQ-as-guard to the bridge
   couples two concerns. Future sprint may compose them.
