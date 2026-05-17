"""Tests for atomic_dag.parser — 42 scenarios (27 herdados + 15 Phase 2.C.1)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from atomic_dag.parser import (
    AtomParseError,
    parse_atom,
    parse_atom_directory,
    replace_state_in_frontmatter,
)


def _write_atom(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


# ── Scenario 1: Happy path minimal ──────────────────────────────────


def test_parse_minimal_atom(tmp_path: Path) -> None:
    f = _write_atom(tmp_path / "a.md", "---\natomic_id: c7\nstate: pending\n---\nBody.\n")
    atom = parse_atom(f)
    assert atom.atomic_id == "c7"
    assert atom.state == "pending"
    assert atom.body == "Body.\n"
    assert atom.filepath == f


# ── Scenario 2: Full frontmatter ────────────────────────────────────


def test_parse_full_frontmatter(tmp_path: Path) -> None:
    f = _write_atom(
        tmp_path / "full.md",
        "---\natomic_id: c13\ncursor_state: verified\ndeps: [c7]\n---\nFull body.\n",
    )
    atom = parse_atom(f)
    assert atom.atomic_id == "c13"
    assert atom.state == "verified"
    assert atom.deps == ["c7"]


# ── Scenario 3: Quad-backtick wrapper stripped ──────────────────────


def test_quad_backtick_wrapper(tmp_path: Path) -> None:
    content = "````\n---\natomic_id: x\nstate: active\n---\nWrapped.\n````"
    f = _write_atom(tmp_path / "w.md", content)
    atom = parse_atom(f)
    assert atom.atomic_id == "x"
    assert atom.body == "Wrapped.\n"


# ── Scenario 4: No quad-backtick accepted ───────────────────────────


def test_no_quad_backtick(tmp_path: Path) -> None:
    f = _write_atom(tmp_path / "n.md", "---\natomic_id: y\nstate: draft\n---\nPlain.\n")
    atom = parse_atom(f)
    assert atom.atomic_id == "y"


# ── Scenario 5: No frontmatter ──────────────────────────────────────


def test_no_frontmatter(tmp_path: Path) -> None:
    f = _write_atom(tmp_path / "nf.md", "Just plain text.\n")
    with pytest.raises(AtomParseError, match="no YAML frontmatter"):
        parse_atom(f)


# ── Scenario 6: Invalid YAML ────────────────────────────────────────


def test_invalid_yaml(tmp_path: Path) -> None:
    f = _write_atom(tmp_path / "bad.md", "---\n{invalid yaml: [\n---\nBody.\n")
    with pytest.raises(AtomParseError, match="YAML parse error"):
        parse_atom(f)


# ── Scenario 7: Empty frontmatter ───────────────────────────────────


def test_empty_frontmatter(tmp_path: Path) -> None:
    f = _write_atom(tmp_path / "e.md", "---\n---\nBody.\n")
    with pytest.raises(AtomParseError, match="frontmatter must be a mapping"):
        parse_atom(f)


# ── Scenario 8: YAML parses to None ─────────────────────────────────


def test_yaml_none(tmp_path: Path) -> None:
    f = _write_atom(tmp_path / "n.md", "---\n---\n")
    with pytest.raises(AtomParseError, match="frontmatter must be a mapping"):
        parse_atom(f)


# ── Scenario 9: YAML parses to string ───────────────────────────────


def test_yaml_string(tmp_path: Path) -> None:
    f = _write_atom(tmp_path / "s.md", "---\njust a string\n---\nBody.\n")
    with pytest.raises(AtomParseError, match="frontmatter must be a mapping"):
        parse_atom(f)


# ── Scenario 10: Missing atomic_id ──────────────────────────────────


def test_missing_atomic_id(tmp_path: Path) -> None:
    f = _write_atom(tmp_path / "mi.md", "---\nstate: pending\n---\nBody.\n")
    with pytest.raises(AtomParseError, match="missing required field 'atomic_id'"):
        parse_atom(f)


# ── Scenario 11: Missing state and cursor_state ─────────────────────


def test_missing_state_and_cursor_state(tmp_path: Path) -> None:
    f = _write_atom(tmp_path / "ms.md", "---\natomic_id: c1\n---\nBody.\n")
    with pytest.raises(AtomParseError, match="missing required field 'state'"):
        parse_atom(f)


# ── Scenario 12: Has state field ────────────────────────────────────


def test_state_property(tmp_path: Path) -> None:
    f = _write_atom(tmp_path / "st.md", "---\natomic_id: c1\nstate: active\n---\n\n")
    atom = parse_atom(f)
    assert atom.state == "active"


# ── Scenario 13: cursor_state as string (legacy SOC V4) ─────────────


def test_cursor_state_string(tmp_path: Path) -> None:
    f = _write_atom(
        tmp_path / "cs.md", "---\natomic_id: c1\ncursor_state: verified\n---\n\n"
    )
    atom = parse_atom(f)
    assert atom.state == "verified"


# ── Scenario 14a: cursor_state as dict uppercase THIS ───────────────


def test_cursor_state_dict_uppercase(tmp_path: Path) -> None:
    f = _write_atom(
        tmp_path / "d1.md",
        "---\natomic_id: c1\ncursor_state:\n  FROM: pending\n  THIS: active\n  GOTO: done\n---\n\n",
    )
    atom = parse_atom(f)
    assert atom.state == "active"


# ── Scenario 14b: cursor_state as dict lowercase this ───────────────


def test_cursor_state_dict_lowercase(tmp_path: Path) -> None:
    f = _write_atom(
        tmp_path / "d2.md",
        "---\natomic_id: c1\ncursor_state:\n  from: pending\n  this: draft\n  goto: done\n---\n\n",
    )
    atom = parse_atom(f)
    assert atom.state == "draft"


# ── Scenario 15: state takes priority over cursor_state ─────────────


def test_state_priority(tmp_path: Path) -> None:
    f = _write_atom(
        tmp_path / "sp.md",
        "---\natomic_id: c1\nstate: pending\ncursor_state: verified\n---\n\n",
    )
    atom = parse_atom(f)
    assert atom.state == "pending"


# ── Scenario 16: Deps via meta["deps"] ──────────────────────────────


def test_deps_direct(tmp_path: Path) -> None:
    f = _write_atom(
        tmp_path / "dd.md",
        "---\natomic_id: c1\nstate: pending\ndeps: [c7, c3]\n---\n\n",
    )
    atom = parse_atom(f)
    assert atom.deps == ["c7", "c3"]


# ── Scenario 17: Deps via backlinks (legacy) ────────────────────────


def test_deps_backlinks(tmp_path: Path) -> None:
    f = _write_atom(
        tmp_path / "db.md",
        "---\natomic_id: c1\nstate: pending\nbacklinks:\n  deps: [c7]\n---\n\n",
    )
    atom = parse_atom(f)
    assert atom.deps == ["c7"]


# ── Scenario 18: No deps at all ─────────────────────────────────────


def test_deps_empty(tmp_path: Path) -> None:
    f = _write_atom(tmp_path / "de.md", "---\natomic_id: c1\nstate: pending\n---\n\n")
    atom = parse_atom(f)
    assert atom.deps == []


# ── Scenario 19: parse_atom_directory ───────────────────────────────


def test_parse_directory(tmp_path: Path) -> None:
    _write_atom(tmp_path / "a.md", "---\natomic_id: a1\nstate: pending\n---\nA\n")
    _write_atom(tmp_path / "b.md", "---\natomic_id: b1\nstate: active\n---\nB\n")
    atoms = parse_atom_directory(tmp_path)
    assert set(atoms.keys()) == {"a1", "b1"}
    assert atoms["a1"].body == "A\n"


# ── Scenario 20: Duplicate atomic_id ────────────────────────────────


def test_duplicate_atomic_id(tmp_path: Path) -> None:
    _write_atom(tmp_path / "a.md", "---\natomic_id: dup\nstate: pending\n---\n\n")
    _write_atom(tmp_path / "b.md", "---\natomic_id: dup\nstate: active\n---\n\n")
    with pytest.raises(AtomParseError, match="duplicate atomic_id"):
        parse_atom_directory(tmp_path)


# ── Scenario 21: Atom is frozen ─────────────────────────────────────


def test_atom_frozen(tmp_path: Path) -> None:
    f = _write_atom(tmp_path / "f.md", "---\natomic_id: c1\nstate: pending\n---\n\n")
    atom = parse_atom(f)
    with pytest.raises(dataclasses.FrozenInstanceError):
        atom.body = "mutated"  # type: ignore[misc]


# ── Scenario 22: Body contains --- (tables/hr) ──────────────────────


def test_body_with_dashes(tmp_path: Path) -> None:
    f = _write_atom(
        tmp_path / "dash.md",
        "---\natomic_id: c1\nstate: pending\n---\n| a | b |\n|---|---|\n| 1 | 2 |\n",
    )
    atom = parse_atom(f)
    assert "---" in atom.body
    assert "| a | b |" in atom.body


# ── Scenario 23: Empty body ─────────────────────────────────────────


def test_empty_body(tmp_path: Path) -> None:
    f = _write_atom(tmp_path / "eb.md", "---\natomic_id: c1\nstate: pending\n---\n")
    atom = parse_atom(f)
    assert atom.body == ""


# ── Scenario 24: Nonexistent file → AtomParseError ──────────────────


def test_nonexistent_file(tmp_path: Path) -> None:
    with pytest.raises(AtomParseError, match="No such file"):
        parse_atom(tmp_path / "nonexistent.md")


# ── Scenario 25: Empty state string falls through to cursor_state ───


def test_empty_state_fallback(tmp_path: Path) -> None:
    f = _write_atom(
        tmp_path / "es.md",
        "---\natomic_id: c1\nstate: ''\ncursor_state: active\n---\n\n",
    )
    atom = parse_atom(f)
    assert atom.state == "active"


# ── Scenario 26: Malformed deps (string instead of list) ────────────


def test_malformed_deps_string(tmp_path: Path) -> None:
    f = _write_atom(
        tmp_path / "md.md",
        "---\natomic_id: c1\nstate: pending\ndeps: 'c7,c3'\n---\n\n",
    )
    atom = parse_atom(f)
    assert atom.deps == []


# ── Family 9 — replace_state_in_frontmatter (Phase 2.C.1) ────────────


# ── Scenario 27: state: simple — value replaced; rest byte-identical ──


def test_s27_replace_state_simple() -> None:
    content = "---\natomic_id: a\nstate: pending\n---\nBody.\n"
    result = replace_state_in_frontmatter(content, "in-progress")
    assert result == "---\natomic_id: a\nstate: in-progress\n---\nBody.\n"


# ── Scenario 28: cursor_state as inline string ────────────────────────


def test_s28_replace_cursor_state_string() -> None:
    content = "---\natomic_id: a\ncursor_state: pending\n---\nBody.\n"
    result = replace_state_in_frontmatter(content, "in-progress")
    assert result == "---\natomic_id: a\ncursor_state: in-progress\n---\nBody.\n"


# ── Scenario 29: cursor_state dict, THIS uppercase — THIS replaced; siblings intact ──


def test_s29_replace_cursor_state_dict_THIS_uppercase() -> None:
    content = (
        "---\n"
        "atomic_id: a\n"
        "cursor_state:\n"
        "  FROM: created\n"
        "  THIS: pending\n"
        "  GOTO: in-progress\n"
        "---\n"
        "Body.\n"
    )
    expected = (
        "---\n"
        "atomic_id: a\n"
        "cursor_state:\n"
        "  FROM: created\n"
        "  THIS: in-progress\n"
        "  GOTO: in-progress\n"
        "---\n"
        "Body.\n"
    )
    assert replace_state_in_frontmatter(content, "in-progress") == expected


# ── Scenario 30: cursor_state dict, this lowercase — case preserved ───


def test_s30_replace_cursor_state_dict_this_lowercase() -> None:
    content = (
        "---\n"
        "atomic_id: a\n"
        "cursor_state:\n"
        "  from: created\n"
        "  this: pending\n"
        "  goto: in-progress\n"
        "---\n"
        "Body.\n"
    )
    expected = (
        "---\n"
        "atomic_id: a\n"
        "cursor_state:\n"
        "  from: created\n"
        "  this: in-progress\n"
        "  goto: in-progress\n"
        "---\n"
        "Body.\n"
    )
    assert replace_state_in_frontmatter(content, "in-progress") == expected


# ── Scenario 31: state empty + cursor_state present → writes to cursor_state ──


def test_s31_replace_state_empty_falls_through_to_cursor_state() -> None:
    content = (
        "---\n"
        "atomic_id: a\n"
        "state:\n"
        "cursor_state: pending\n"
        "---\n"
        "Body.\n"
    )
    expected = (
        "---\n"
        "atomic_id: a\n"
        "state:\n"
        "cursor_state: in-progress\n"
        "---\n"
        "Body.\n"
    )
    assert replace_state_in_frontmatter(content, "in-progress") == expected


# ── Scenario 32: state and cursor_state both present → state takes precedence ──


def test_s32_replace_state_takes_precedence_over_cursor_state() -> None:
    content = (
        "---\n"
        "atomic_id: a\n"
        "state: pending\n"
        "cursor_state: pending\n"
        "---\n"
        "Body.\n"
    )
    expected = (
        "---\n"
        "atomic_id: a\n"
        "state: in-progress\n"
        "cursor_state: pending\n"
        "---\n"
        "Body.\n"
    )
    assert replace_state_in_frontmatter(content, "in-progress") == expected


# ── Scenario 33: byte-level idempotency — already at target → output == input ──


def test_s33_replace_state_idempotent_byte_exact() -> None:
    # Plain scalar
    content = (
        "---\n"
        "atomic_id: a\n"
        "state: pending\n"
        "---\n"
        "Body with trailing newline.\n"
    )
    assert replace_state_in_frontmatter(content, "pending") == content
    # Double-quoted scalar — quoting style preserved
    content_dq = (
        "---\n"
        "atomic_id: a\n"
        'state: "pending"\n'
        "---\n"
        "Body.\n"
    )
    assert replace_state_in_frontmatter(content_dq, "pending") == content_dq
    # Single-quoted scalar — quoting style preserved
    content_sq = (
        "---\n"
        "atomic_id: a\n"
        "state: 'pending'\n"
        "---\n"
        "Body.\n"
    )
    assert replace_state_in_frontmatter(content_sq, "pending") == content_sq


# ── Scenario 34: quad-backtick envelope preserved on output ──────────


def test_s34_replace_state_preserves_quad_backtick_envelope() -> None:
    content = (
        "````markdown\n"
        "---\n"
        "atomic_id: a\n"
        "state: pending\n"
        "---\n"
        "Body.\n"
        "````\n"
    )
    expected = (
        "````markdown\n"
        "---\n"
        "atomic_id: a\n"
        "state: in-progress\n"
        "---\n"
        "Body.\n"
        "````\n"
    )
    assert replace_state_in_frontmatter(content, "in-progress") == expected


# ── Scenario 35: body containing --- intact after replacement ────────


def test_s35_replace_state_preserves_body_with_horizontal_rule() -> None:
    content = (
        "---\n"
        "atomic_id: a\n"
        "state: pending\n"
        "---\n"
        "Before.\n"
        "\n"
        "---\n"
        "\n"
        "After.\n"
    )
    expected = (
        "---\n"
        "atomic_id: a\n"
        "state: in-progress\n"
        "---\n"
        "Before.\n"
        "\n"
        "---\n"
        "\n"
        "After.\n"
    )
    assert replace_state_in_frontmatter(content, "in-progress") == expected


# ── Scenario 36: no frontmatter → AtomParseError, filepath in message ──


def test_s36_replace_state_no_frontmatter_raises_with_filepath() -> None:
    content = "no frontmatter here\n"
    with pytest.raises(AtomParseError) as exc_info:
        replace_state_in_frontmatter(
            content, "in-progress", filepath="/path/to/atom.md"
        )
    # DA-C1 (ii): the keyword-only filepath argument must reach the error
    # message; otherwise it is decorative and fails the coherence rationale.
    rendered = str(exc_info.value)
    assert "/path/to/atom.md" in rendered
    assert "frontmatter" in rendered.lower()


# ── Scenario 37: YAML comment within frontmatter preserved ───────────


def test_s37_replace_state_preserves_yaml_comment() -> None:
    content = (
        "---\n"
        "atomic_id: a\n"
        "state: pending  # initial state\n"
        "---\n"
        "Body.\n"
    )
    expected = (
        "---\n"
        "atomic_id: a\n"
        "state: in-progress  # initial state\n"
        "---\n"
        "Body.\n"
    )
    assert replace_state_in_frontmatter(content, "in-progress") == expected


# ── Scenario 38: round-trip semantic — parse_atom(replaced).state == target ──


def test_s38_replace_state_semantic_round_trip(tmp_path: Path) -> None:
    cases: list[tuple[str, str]] = [
        (
            "state_key",
            "---\natomic_id: a\nstate: pending\n---\nBody.\n",
        ),
        (
            "cursor_state_string",
            "---\natomic_id: a\ncursor_state: pending\n---\nBody.\n",
        ),
        (
            "cursor_state_dict_THIS",
            (
                "---\n"
                "atomic_id: a\n"
                "cursor_state:\n"
                "  FROM: created\n"
                "  THIS: pending\n"
                "  GOTO: next\n"
                "---\n"
                "Body.\n"
            ),
        ),
    ]
    for label, content in cases:
        new_content = replace_state_in_frontmatter(content, "in-progress")
        path = tmp_path / f"{label}.md"
        path.write_text(new_content, encoding="utf-8")
        atom = parse_atom(path)
        assert atom.state == "in-progress", f"round-trip failed for {label}"


# ── Scenario 39: cursor_state block, no THIS/this, dedent then atomic_id-like ──
# Exercises: dedent break (cursor_state block ended by non-indented line) +
# outer-loop continue after exhausted inner scan + raise (no state-bearing key
# located).


def test_s39_cursor_state_block_without_THIS_raises() -> None:
    content = (
        "---\n"
        "atomic_id: a\n"
        "cursor_state:\n"
        "  FROM: created\n"
        "  GOTO: in-progress\n"
        "extra: trailing\n"
        "---\n"
        "Body.\n"
    )
    with pytest.raises(AtomParseError) as exc_info:
        replace_state_in_frontmatter(content, "in-progress", filepath="/x.md")
    rendered = str(exc_info.value)
    assert "/x.md" in rendered
    assert "state-bearing key" in rendered.lower() or "frontmatter" in rendered.lower()


# ── Scenario 40: cursor_state in flow-mapping form — out-of-scope, skipped ──
# Exercises: flow-mapping continue branch (Sprint 2 does not support
# `cursor_state: {THIS: ...}`; the function skips this form and, with no other
# state-bearing key present, raises).


def test_s40_cursor_state_flow_mapping_out_of_scope_raises() -> None:
    content = (
        "---\n"
        "atomic_id: a\n"
        "cursor_state: {FROM: created, THIS: pending, GOTO: in-progress}\n"
        "---\n"
        "Body.\n"
    )
    with pytest.raises(AtomParseError) as exc_info:
        replace_state_in_frontmatter(content, "in-progress", filepath="/x.md")
    rendered = str(exc_info.value)
    assert "/x.md" in rendered


# ── Scenario 41: cursor_state block with blank line between header and THIS ──
# Exercises: blank-line continue inside the inner block scan. The THIS child is
# still located despite the blank line; the blank line is preserved byte-exact
# in the output.


def test_s41_cursor_state_block_with_blank_line_inside() -> None:
    content = (
        "---\n"
        "atomic_id: a\n"
        "cursor_state:\n"
        "  FROM: created\n"
        "\n"
        "  THIS: pending\n"
        "  GOTO: in-progress\n"
        "---\n"
        "Body.\n"
    )
    expected = (
        "---\n"
        "atomic_id: a\n"
        "cursor_state:\n"
        "  FROM: created\n"
        "\n"
        "  THIS: in-progress\n"
        "  GOTO: in-progress\n"
        "---\n"
        "Body.\n"
    )
    assert replace_state_in_frontmatter(content, "in-progress") == expected
