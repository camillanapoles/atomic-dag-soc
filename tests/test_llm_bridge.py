"""Tests for atomic_dag.llm_bridge — MOCK provider only (ADR-009 D-bridge-5).

NEVER calls a real LLM. All provider interactions go through MockProvider or
injected fake `anthropic` modules via monkeypatch.setitem on sys.modules.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from atomic_dag.llm_bridge import (
    AnthropicProvider,
    BridgeAPIError,
    BridgeParseError,
    LLMProvider,
    _parse_response,
    bridge_stream,
    bridge_transition,
)
from atomic_dag.streaming import StreamEvent
from atomic_dag.transitions import InvalidTransitionError

# --- Mock provider (D-bridge-5: zero real LLM) ------------------------------


class MockProvider:
    """Returns predetermined text. NEVER calls a real LLM."""

    def __init__(
        self,
        response: str = "Generated body content.\n",
        raises: Exception | None = None,
    ) -> None:
        self._response = response
        self._raises = raises
        self.calls: list[tuple[str, str]] = []

    def complete(self, prompt: str, *, system: str = "") -> str:
        self.calls.append((prompt, system))
        if self._raises is not None:
            raise self._raises
        return self._response


# --- Helpers ---------------------------------------------------------------


def _mk_atom(tmp_path: Path, state: str = "pending") -> Path:
    """Write an atom file with valid frontmatter + body. State defaults to
    'pending' so action 'do' is valid under the real FSM (→ 'in-progress').
    """
    p = tmp_path / "atom.md"
    p.write_text(
        "---\n"
        "atomic_id: A-001\n"
        f"state: {state}\n"
        "gold_score: 10\n"
        "pqms_score: 9.6\n"
        "vvv_score: 1.0\n"
        "---\n"
        "original body\n",
        encoding="utf-8",
    )
    return p


def _mk_project(tmp_path: Path) -> Path:
    (tmp_path / ".atomic-dag").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _mk_stream_project(tmp_path: Path, cursor: str = "C-001") -> Path:
    project = _mk_project(tmp_path)
    (project / "state.json").write_text(
        json.dumps({"cursor": cursor, "updated_at": "2026-06-01T00:00:00Z"}),
        encoding="utf-8",
    )
    (project / ".atomic-dag" / "wal.jsonl").write_text("", encoding="utf-8")
    return project


# --- Family 1: happy path --------------------------------------------------


def test_bridge_transition_happy_path(tmp_path: Path) -> None:
    project = _mk_project(tmp_path)
    fp = _mk_atom(tmp_path, state="pending")
    mock = MockProvider(response="New LLM body.\n")

    r = bridge_transition(project, fp, "do", provider=mock)

    assert r.success
    assert r.from_state == "pending"
    assert r.to_state == "in-progress"
    assert mock.calls, "provider should have been called once"
    content = fp.read_text(encoding="utf-8")
    assert "New LLM body." in content
    assert "atomic_id: A-001" in content  # frontmatter byte-preserved
    assert "state: in-progress" in content  # state mutated by execute_transition


# --- Family 2: provider failure -------------------------------------------


def test_provider_failure_raises_bridge_api_error(tmp_path: Path) -> None:
    project = _mk_project(tmp_path)
    fp = _mk_atom(tmp_path)
    mock = MockProvider(raises=BridgeAPIError("network down"))

    with pytest.raises(BridgeAPIError, match="network down"):
        bridge_transition(project, fp, "do", provider=mock)
    assert "original body" in fp.read_text(encoding="utf-8")  # atom intact


# --- Family 3: parse failure ----------------------------------------------


def test_parse_failure_empty_response(tmp_path: Path) -> None:
    project = _mk_project(tmp_path)
    fp = _mk_atom(tmp_path)
    mock = MockProvider(response="   \n  ")

    with pytest.raises(BridgeParseError, match="empty after strip"):
        bridge_transition(project, fp, "do", provider=mock)


def test_parse_failure_only_frontmatter(tmp_path: Path) -> None:
    project = _mk_project(tmp_path)
    fp = _mk_atom(tmp_path)
    mock = MockProvider(response="---\nfoo: bar\n---\n")

    with pytest.raises(BridgeParseError, match="no body after frontmatter strip"):
        bridge_transition(project, fp, "do", provider=mock)


def test_parse_response_unit_branches() -> None:
    assert _parse_response("hello").endswith("\n")
    assert _parse_response("hello\n") == "hello\n"
    # malformed frontmatter (only one ---) → text kept as-is (no 3-way split)
    assert "incomplete" in _parse_response("---incomplete")


# --- Family 4: FSM rejection propagates ------------------------------------


def test_fsm_rejection_propagates(tmp_path: Path) -> None:
    project = _mk_project(tmp_path)
    fp = _mk_atom(tmp_path, state="closed")  # terminal — no actions out
    mock = MockProvider(response="body\n")

    with pytest.raises(InvalidTransitionError):
        bridge_transition(project, fp, "do", provider=mock)


# --- Family 5: defensive frontmatter stripping (D-bridge-3) ----------------


def test_frontmatter_stripped_defensively(tmp_path: Path) -> None:
    project = _mk_project(tmp_path)
    fp = _mk_atom(tmp_path, state="pending")
    mock = MockProvider(response="---\nstate: hacked\n---\nclean body\n")

    bridge_transition(project, fp, "do", provider=mock)

    content = fp.read_text(encoding="utf-8")
    assert "hacked" not in content  # LLM-supplied frontmatter discarded
    assert "clean body" in content
    assert "atomic_id: A-001" in content  # real frontmatter preserved


# --- Family 6: bridge_stream ----------------------------------------------


def test_bridge_stream_fills_empty_payload(tmp_path: Path) -> None:
    project = _mk_stream_project(tmp_path, cursor="C-001")
    mock = MockProvider(response="payload data\n")
    events = [StreamEvent("e1", "2026-06-01T00:00:00Z", {}, "C-001")]

    results = bridge_stream(project, events, provider=mock)

    assert len(results) == 1
    assert results[0].advanced_cursor_to == "C-002"
    assert mock.calls, "LLM called to fill empty payload"


def test_bridge_stream_preserves_existing_payload(tmp_path: Path) -> None:
    project = _mk_stream_project(tmp_path, cursor="C-001")
    mock = MockProvider(response="should not be used")
    events = [
        StreamEvent("e1", "t", {"k": "v"}, "C-001"),
    ]

    results = bridge_stream(project, events, provider=mock)

    assert len(results) == 1
    assert results[0].advanced_cursor_to == "C-002"
    assert mock.calls == [], "non-empty payload skips the LLM call"


# --- Family 7: LLMProvider Protocol + AnthropicProvider --------------------


def test_anthropic_provider_satisfies_protocol() -> None:
    assert isinstance(AnthropicProvider(), LLMProvider)


def test_mock_provider_satisfies_protocol() -> None:
    assert isinstance(MockProvider(), LLMProvider)


def test_anthropic_provider_import_error_without_sdk(monkeypatch: Any) -> None:
    """`import anthropic` finds None in sys.modules → ImportError."""
    monkeypatch.setitem(sys.modules, "anthropic", None)
    with pytest.raises(ImportError, match=r"atomic-dag-soc\[llm\]"):
        AnthropicProvider().complete("x")


def test_anthropic_provider_complete_success(monkeypatch: Any) -> None:
    """Inject fake anthropic module so the inner success path is exercised."""

    class _Block:
        def __init__(self, text: str) -> None:
            self.text = text

    class _Msg:
        def __init__(self) -> None:
            self.content = [_Block("hello "), _Block("world"), object()]  # last has no .text

    class _Messages:
        def create(self, **_: Any) -> _Msg:
            return _Msg()

    class _Anthropic:
        def __init__(self, api_key: str | None = None) -> None:
            self.api_key = api_key
            self.messages = _Messages()

    fake = types.SimpleNamespace(Anthropic=_Anthropic)
    monkeypatch.setitem(sys.modules, "anthropic", fake)

    out = AnthropicProvider(model="test", api_key="k").complete("hi", system="be brief")
    assert out == "hello world"


def test_anthropic_provider_complete_uses_env_key(monkeypatch: Any) -> None:
    """When api_key is None, reads ANTHROPIC_API_KEY from env."""
    captured: dict[str, Any] = {}

    class _Messages:
        def create(self, **kwargs: Any) -> Any:
            return types.SimpleNamespace(content=[types.SimpleNamespace(text="ok")])

    class _Anthropic:
        def __init__(self, api_key: str | None = None) -> None:
            captured["api_key"] = api_key
            self.messages = _Messages()

    fake = types.SimpleNamespace(Anthropic=_Anthropic)
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")

    AnthropicProvider().complete("hi")
    assert captured["api_key"] == "from-env"


def test_anthropic_provider_complete_default_system_prompt(monkeypatch: Any) -> None:
    """When system='' is passed, AnthropicProvider falls back to _SYSTEM_PROMPT."""
    captured: dict[str, Any] = {}

    class _Messages:
        def create(self, **kwargs: Any) -> Any:
            captured.update(kwargs)
            return types.SimpleNamespace(content=[types.SimpleNamespace(text="x")])

    class _Anthropic:
        def __init__(self, api_key: str | None = None) -> None:
            self.messages = _Messages()

    fake = types.SimpleNamespace(Anthropic=_Anthropic)
    monkeypatch.setitem(sys.modules, "anthropic", fake)

    AnthropicProvider().complete("hi", system="")
    assert "frontmatter" in captured["system"].lower()


def test_anthropic_provider_complete_wraps_api_error(monkeypatch: Any) -> None:
    """A failure inside the client call is wrapped as BridgeAPIError."""

    class _Anthropic:
        def __init__(self, api_key: str | None = None) -> None:
            raise RuntimeError("network down")

    fake = types.SimpleNamespace(Anthropic=_Anthropic)
    monkeypatch.setitem(sys.modules, "anthropic", fake)

    with pytest.raises(BridgeAPIError, match="network down"):
        AnthropicProvider().complete("hi")
