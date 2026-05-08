"""Tests for atomic_dag.parser — 26 scenarios."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from atomic_dag.parser import AtomParseError, parse_atom, parse_atom_directory


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
