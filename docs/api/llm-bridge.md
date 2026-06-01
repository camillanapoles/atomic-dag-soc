# `atomic_dag.llm_bridge` — Public Protocol

**Status:** Phase 4.B specification · Sprint 4 · Hello SOC bridge
**Source:** `src/atomic_dag/llm_bridge.py` (implemented in 4.C)
**Authority:** ADR-009-llm-bridge-minimal-scope
**Constrained by:** ADR-001 (dual-layer); ADR-003 §Lesson 3 (operation ordering);
ADR-007 §D1 (streaming order); ADR-006 §D1 (transition order)

This document specifies the observable contract of the `llm_bridge` module
before any production implementation exists. `llm_bridge.py` (Phase 4.C)
must satisfy every clause here. Where this document and ADR-009 diverge,
ADR-009 wins.

---

## 1. Public surface

The module exposes exactly these public names:

```python
bridge_transition(project: Path, filepath: Path, action: str, *,
                  provider: LLMProvider, prompt_template: str = "") -> TransitionResult
bridge_stream(project: Path, events: list[StreamEvent], *,
              provider: LLMProvider) -> list[TickResult]
LLMProvider       # Protocol (ABC for provider abstraction)
BridgeAPIError    # exception (LLM API failure)
BridgeParseError  # exception (response unparseable)
```

## 2. `LLMProvider` (Protocol — D-bridge-2)

```python
class LLMProvider(Protocol):
    def complete(self, prompt: str, *, system: str = "") -> str:
        """Single-turn completion. Returns raw text response."""
        ...
```

- Stateless. No conversation history; each call is independent.
- Synchronous. No streaming, no async (Sprint 4 scope).
- Testable. Tests inject a mock that returns predetermined text.

Production default: `AnthropicProvider(model="claude-sonnet-4-20250514")`.
The module provides this implementation, but tests NEVER call it.

## 3. `AnthropicProvider` (concrete — production default)

```python
@dataclass
class AnthropicProvider:
    model: str = "claude-sonnet-4-20250514"
    api_key: str | None = None  # falls back to ANTHROPIC_API_KEY env var

    def complete(self, prompt: str, *, system: str = "") -> str: ...
```

- Uses `anthropic` SDK (declared in `pyproject.toml` as optional dep:
  `pip install atomic-dag-soc[llm]`).
- If `anthropic` is not installed, importing `AnthropicProvider` raises
  `ImportError` with a helpful message.
- If `api_key` is None, reads from `ANTHROPIC_API_KEY` environment variable.
- Raises `BridgeAPIError` on any SDK/network error.

## 4. `bridge_transition` — call LLM + inject into transition pipeline

Processes one atom through the LLM and transitions it.

### Operation ordering (D-bridge-3, inherits ADR-003 §Lesson 3)

1. `parser.parse_atom(filepath)` → Atom (read current content)
2. Construct prompt: `prompt_template.format(atom_content=atom.content,
   atom_state=atom.state, action=action)` (or default template if empty)
3. `provider.complete(prompt, system=<system_prompt>)` → `raw_response`
4. Parse `raw_response` → `new_content` (extract content between markers,
   or use full response if no markers)
5. Write `new_content` to `filepath` (via `writer.write_atomic` — I3
   preserved, the bridge calls writer, does NOT reimplement)
6. `execute_transition(filepath, action, project_root=project)` →
   `TransitionResult`
7. Return `TransitionResult`

### Post-condition

After a successful `bridge_transition`:

- The atom file contains LLM-generated content
- The atom state has transitioned per FSM rules
- WAL has one `transition` event (logged by `execute_transition`, not bridge)
- `state.json` is unchanged (transitions don't touch streaming cursor)

### Error behavior

- `BridgeAPIError`: LLM call failed → atom file unchanged, no transition
- `BridgeParseError`: LLM response unparseable → atom file unchanged, no
  transition
- `InvalidTransitionError`: FSM rejected → atom file has new content but
  state unchanged (this is by design: the content was generated but the
  transition was invalid; the content is recoverable from the file)

## 5. `bridge_stream` — call LLM + inject into streaming pipeline

Processes a batch of stream events, calling the LLM for each event's payload
generation if needed, then feeding into `tick_streaming`.

### Operation ordering

1. For each `StreamEvent` in `events`:
   a. If event payload is empty and provider is given: construct prompt
      from event metadata → `provider.complete()` → fill payload
   b. `tick_streaming(project, event)` → `TickResult`
2. Return list of `TickResult`s

### Note

In the Hello SOC workflow (4.D), the LLM is called OUTSIDE `bridge_stream`
to generate atom content, and `bridge_stream` handles the cursor advancement.
The two functions (`bridge_transition` for content generation + state change,
`bridge_stream` for cursor tracking) compose to form the full pipeline.

## 6. `BridgeAPIError` and `BridgeParseError`

```python
class BridgeAPIError(Exception):
    """Raised when the LLM API call fails (network, auth, rate limit)."""

class BridgeParseError(Exception):
    """Raised when the LLM response cannot be parsed into usable content."""
```

Both map to CLI exit 2 (structural error) when surfaced through the CLI layer.

## 7. WAL interaction

The bridge writes NO WAL events directly. All WAL entries are created by
`execute_transition` and `tick_streaming` (the downstream modules the bridge
calls). This is by design (D-bridge-3): the bridge is a caller, not a state
manager.

The WAL schema for `transition` and `streaming_tick` events is unchanged
from api/transitions.md §4 and api/streaming.md §7.

## 8. Default prompt template

The bridge includes a minimal default template for atom processing:

```
You are processing an atomic document in the Atomic-DAG framework.

Current atom state: {atom_state}
Action requested: {action}

Current content:
---
{atom_content}
---

Produce the updated content for this atom. Return ONLY the content,
no preamble, no explanation.
```

This template is overridable via `prompt_template` parameter. The Hello SOC
example (4.D) will provide domain-specific templates.

## 9. CLI integration (Phase 4.C or later)

Optional: `atomic-dag bridge` subcommand. If included:

```
atomic-dag --project PATH bridge ATOM_FILE ACTION [--provider anthropic]
  [--model claude-sonnet-4-20250514] [--template FILE] [--json]
```

Exit codes: 0 (success), 1 (downstream operational error),
2 (API/parse/structural).

This is OPTIONAL for 4.C — the bridge can be used programmatically from
Hello SOC (4.D) without CLI. If the executor includes CLI integration, it
follows the same I4 pattern (fase dedicada, purely additive,
status/validate/next/transition/stream intactos).

## 10. Usage example (Hello SOC preview)

```python
from pathlib import Path
from atomic_dag.llm_bridge import bridge_transition, AnthropicProvider

provider = AnthropicProvider()  # uses ANTHROPIC_API_KEY env var
project = Path("./examples/hello-soc")

# Process atom through LLM and transition it
result = bridge_transition(
    project=project,
    filepath=project / "atoms" / "introduction.md",
    action="advance",
    provider=provider,
)

# result.success == True
# result.to_state == "verified" or "draft" (depends on gate)
# WAL has one transition event (logged by execute_transition)
```

## 11. Test obligations (Phase 4.C — forward reference)

All tests use a mock provider returning predetermined text. NO real LLM call
in the test suite. Test families:

1. Happy path: `bridge_transition` with mock → `TransitionResult` success
2. Provider failure: mock raises → `BridgeAPIError`
3. Parse failure: mock returns garbage → `BridgeParseError`
4. FSM rejection: valid LLM response but invalid action → `InvalidTransitionError`
5. Idempotency: `bridge_transition` twice → second is idempotent (via
   `execute_transition`'s idempotency, not bridge's)
6. `bridge_stream`: batch of events → list of `TickResult`s
7. Provider protocol: `AnthropicProvider` satisfies `LLMProvider` Protocol
