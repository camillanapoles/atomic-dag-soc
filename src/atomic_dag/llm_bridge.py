"""atomic_dag.llm_bridge — the LLM↔Python operational boundary (ADR-001).

Calls an LLM, parses the response into atom body content, and INJECTS into
the existing assembler pipeline (execute_transition / tick_streaming). The
bridge is a CALLER of the existing modules, never a replacement (ADR-009
D-bridge-1/3). It writes only the atom BODY (content); all STATE mutation
is delegated to execute_transition (frontmatter is never touched by the
bridge). See docs/api/llm-bridge.md and ADR-009.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from atomic_dag import parser, writer
from atomic_dag.streaming import StreamEvent, TickResult, tick_streaming
from atomic_dag.transitions import TransitionResult, execute_transition


class BridgeAPIError(Exception):
    """Raised when the LLM API call fails (network, auth, rate limit)."""


class BridgeParseError(Exception):
    """Raised when the LLM response cannot be parsed into usable content."""


@runtime_checkable
class LLMProvider(Protocol):
    """Single-turn, stateless completion provider (ADR-009 D-bridge-2).

    Implementations return raw text from a one-shot prompt. Stateless from
    the bridge's perspective: each call is independent. Synchronous only.
    """

    def complete(self, prompt: str, *, system: str = "") -> str: ...


_DEFAULT_TEMPLATE = """You are processing an atomic document in the Atomic-DAG framework.

Current atom state: {atom_state}
Action requested: {action}

Current content:
---
{atom_content}
---

Produce the updated content for this atom. Return ONLY the body content,
no frontmatter, no preamble, no explanation.
"""

_SYSTEM_PROMPT = (
    "You produce ONLY the markdown body of an atom — never the YAML "
    "frontmatter (the --- block), never preamble or explanation."
)


@dataclass
class AnthropicProvider:
    """Production default. Uses the `anthropic` SDK (optional dep [llm]).

    Lazy import so that `from atomic_dag.llm_bridge import AnthropicProvider`
    works even when the SDK is absent; only `complete()` requires the SDK.
    """

    model: str = "claude-sonnet-4-20250514"
    api_key: str | None = None

    def complete(self, prompt: str, *, system: str = "") -> str:
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ImportError(
                "AnthropicProvider requires the 'anthropic' SDK. "
                "Install with: pip install atomic-dag-soc[llm]"
            ) from exc
        key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        try:
            client = anthropic.Anthropic(api_key=key)
            msg = client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system or _SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(b.text for b in msg.content if hasattr(b, "text"))
        except Exception as exc:
            raise BridgeAPIError(f"LLM API call failed: {exc}") from exc


def _parse_response(raw: str) -> str:
    """Extract usable body content from the LLM response.

    Strips surrounding whitespace. If the response is empty after stripping,
    raises BridgeParseError. If the LLM wrongly returned a frontmatter block
    despite instructions, strip it defensively (the bridge owns frontmatter,
    not the LLM — ADR-009 D-bridge-3).
    """
    text = raw.strip()
    if not text:
        raise BridgeParseError("LLM response empty after strip")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2].lstrip("\n")
    if not text:
        raise BridgeParseError("LLM response had no body after frontmatter strip")
    return text if text.endswith("\n") else text + "\n"


def bridge_transition(
    project: Path,
    filepath: Path,
    action: str,
    *,
    provider: LLMProvider,
    prompt_template: str = "",
) -> TransitionResult:
    """Call LLM to regenerate atom body, then transition via execute_transition.

    Ordering (ADR-009 D-bridge-3, inherits ADR-003 §Lesson 3):

        parse_atom → format prompt → provider.complete → _parse_response
          → write BODY (frontmatter byte-preserved) → execute_transition

    The bridge writes only the BODY of the atom; the frontmatter (including
    `state`) is preserved byte-for-byte. All STATE mutation is delegated to
    `execute_transition`, which is the sole owner of frontmatter rewrites.
    This preserves I3 (writer/wal/fsm/gate not modified) and the dual-layer
    separation (ADR-001).

    Raises
    ------
    BridgeAPIError
        Provider call failed (atom file unchanged, no transition).
    BridgeParseError
        Provider response unparseable (atom file unchanged, no transition).
    InvalidTransitionError
        FSM rejected the action. By design: the body has been rewritten with
        the LLM-generated content (recoverable from the file), but the state
        has not changed. Propagated from `execute_transition`.
    AtomNotFoundError
        Filepath does not exist (raised by `parse_atom`).
    """
    atom = parser.parse_atom(filepath)
    template = prompt_template or _DEFAULT_TEMPLATE
    prompt = template.format(
        atom_content=atom.body, atom_state=atom.state, action=action
    )
    raw = provider.complete(prompt, system=_SYSTEM_PROMPT)
    new_body = _parse_response(raw)

    raw_full = filepath.read_text(encoding="utf-8")
    frontmatter_prefix = raw_full[: len(raw_full) - len(atom.body)]
    writer.write_atomic(filepath, frontmatter_prefix + new_body)

    return execute_transition(filepath, action, project_root=project)


def bridge_stream(
    project: Path,
    events: list[StreamEvent],
    *,
    provider: LLMProvider,
) -> list[TickResult]:
    """Process a batch of stream events, filling empty payloads via the LLM.

    For each event: if `payload` is empty, call the LLM to generate it,
    then invoke `tick_streaming`. The bridge never advances the cursor or
    writes the WAL directly — both are owned by `tick_streaming` (D-bridge-3,
    ADR-007 D1/D11 preserved by delegation).
    """
    results: list[TickResult] = []
    for ev in events:
        if not ev.payload:
            raw = provider.complete(
                f"Generate payload for event {ev.event_id}",
                system=_SYSTEM_PROMPT,
            )
            generated: dict[str, Any] = {"generated": _parse_response(raw)}
            ev = StreamEvent(
                event_id=ev.event_id,
                ts=ev.ts,
                payload=generated,
                expected_cursor_from=ev.expected_cursor_from,
            )
        results.append(tick_streaming(project, ev))
    return results
