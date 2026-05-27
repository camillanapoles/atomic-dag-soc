"""AtomParser: parses markdown atoms with YAML frontmatter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n?---\s*(\n|$)", re.DOTALL | re.MULTILINE)


class AtomParseError(ValueError):
    """Raised when an atom file cannot be parsed."""

    def __init__(self, filepath: Path | str, reason: str) -> None:
        self.filepath = str(filepath)
        self.reason = reason
        super().__init__(f"{filepath}: {reason}")


@dataclass(frozen=True)
class Atom:
    """A parsed atom: metadata from YAML frontmatter plus markdown body."""

    meta: dict[str, Any]
    body: str
    filepath: Path

    @property
    def atomic_id(self) -> str:
        """The unique identifier of this atom, from frontmatter."""
        return str(self.meta["atomic_id"])

    @property
    def state(self) -> str:
        """Current state of the atom.

        Looks for 'state' first (atomic-dag-soc canonical),
        falls back to 'cursor_state' (SOC V4 / DAW legacy).
        cursor_state may be a plain string or a dict {FROM, THIS, GOTO}.
        """
        state = self.meta.get("state")
        if state:
            return str(state)
        if "cursor_state" in self.meta:
            cs = self.meta["cursor_state"]
            if isinstance(cs, dict):
                # DAW format: {FROM, THIS, GOTO} — "THIS" is current state
                this_val = cs.get("THIS") or cs.get("this")
                if this_val:
                    return str(this_val)
            return str(cs)
        raise AtomParseError(self.filepath, "neither 'state' nor 'cursor_state' present")

    @property
    def deps(self) -> list[str]:
        """Dependency list. Checks meta['deps'] first, then backlinks['deps']."""
        raw = self.meta.get("deps")
        if isinstance(raw, list):
            return [str(d) for d in raw]
        backlinks = self.meta.get("backlinks")
        if isinstance(backlinks, dict):
            raw = backlinks.get("deps")
            if isinstance(raw, list):
                return [str(d) for d in raw]
        return []


def _strip_quad_backtick(content: str) -> str:
    """Strip quad-backtick wrapper if present, noop otherwise."""
    if not content.lstrip().startswith("````"):
        return content

    lines = content.split("\n")
    start_idx = next(
        (i for i, ln in enumerate(lines) if ln.strip().startswith("````")),
        None,
    )
    end_idx = next(
        (i for i in range(len(lines) - 1, -1, -1) if lines[i].strip().startswith("````")),
        None,
    )
    if start_idx is None or end_idx is None or start_idx == end_idx:
        return content

    inner = "\n".join(lines[start_idx + 1 : end_idx])
    return inner if inner.endswith("\n") else inner + "\n"


def parse_atom(filepath: str | Path) -> Atom:
    """Parse a markdown atom file into an Atom object."""
    filepath = Path(filepath)

    try:
        content = filepath.read_text(encoding="utf-8")
    except OSError as exc:
        raise AtomParseError(filepath, str(exc)) from exc

    content = _strip_quad_backtick(content)

    match = _FRONTMATTER_RE.match(content)
    if not match:
        raise AtomParseError(filepath, "no YAML frontmatter found")

    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise AtomParseError(filepath, f"YAML parse error: {exc}") from exc

    if not isinstance(meta, dict):
        raise AtomParseError(
            filepath, f"frontmatter must be a mapping, got {type(meta).__name__}"
        )

    if "atomic_id" not in meta:
        raise AtomParseError(filepath, "missing required field 'atomic_id'")

    if not meta.get("state") and "cursor_state" not in meta:
        raise AtomParseError(
            filepath, "missing required field 'state' (or 'cursor_state')"
        )

    body = content[match.end() :]
    return Atom(meta=meta, body=body, filepath=filepath)


def parse_atom_directory(dir: str | Path) -> dict[str, Atom]:
    """Parse all .md files in a directory, returning {atomic_id: Atom}.

    Raises AtomParseError on duplicate atomic_id.
    """
    dir = Path(dir)
    atoms: dict[str, Atom] = {}

    for path in sorted(dir.glob("*.md")):
        atom = parse_atom(path)
        aid = atom.atomic_id
        if aid in atoms:
            raise AtomParseError(
                path, f"duplicate atomic_id '{aid}' (first seen in {atoms[aid].filepath})"
            )
        atoms[aid] = atom

    return atoms


def replace_state_in_frontmatter(
    content: str,
    new_state: str,
    *,
    filepath: str = "<unknown>",
) -> str:
    """Surgically replace the state value in an atom's YAML frontmatter.

    Performs byte-precise mutation: only the scalar value at the state-bearing
    key changes. Everything else (key order, indentation, quoting style,
    comments, body, quad-backtick envelope) is preserved exactly. No YAML
    round-trip is performed — round-tripping via ``yaml.safe_dump`` would
    reorder keys, normalise quoting and drop comments, regressing bytes that
    do not encode the state.

    Precedence of the state-bearing key mirrors ``Atom.state``:

    1. Top-level ``state:`` when present with a non-empty scalar value.
    2. Top-level ``cursor_state:`` when (a) ``state:`` is absent, or
       (b) ``state:`` is present but empty:

       - inline string form (``cursor_state: <value>``): value is replaced;
       - block-mapping form (``cursor_state:\\n  ...``): the ``THIS`` or
         ``this`` child is replaced, case preserved.

    Idempotency: if the located scalar already equals ``new_state`` (and
    quoting style is preserved), the returned string is byte-identical to
    the input. This supports the Sprint 2 D2 idempotency contract by
    making ``execute_transition``'s "state already matches" short-circuit
    detectable at the byte level.

    Parameters
    ----------
    content : str
        Full atom file content, optionally wrapped in a quad-backtick fence.
    new_state : str
        Target state value to write.
    filepath : str, keyword-only
        Path for ``AtomParseError`` messages. Defaults to ``"<unknown>"``.

    Returns
    -------
    str
        Content with the state mutated; all other bytes unchanged.

    Raises
    ------
    AtomParseError
        If no YAML frontmatter is found, or if no recognised state-bearing
        key (``state``, ``cursor_state``, or ``cursor_state.THIS``) is
        available to update.
    """
    match = _FRONTMATTER_RE.search(content)
    if not match:
        raise AtomParseError(filepath, "no YAML frontmatter found")

    fm_text = match.group(1)
    fm_start, fm_end = match.start(1), match.end(1)

    new_fm = _replace_state_in_fm_text(fm_text, new_state, filepath)
    return content[:fm_start] + new_fm + content[fm_end:]


def _replace_state_in_fm_text(fm_text: str, new_state: str, filepath: str) -> str:
    """Locate the state-bearing key inside the frontmatter text and replace its value."""
    lines = fm_text.split("\n")

    # Pass 1: top-level `state:` (precedence over cursor_state when non-empty)
    state_idx: int | None = None
    state_empty = False
    for i, line in enumerate(lines):
        if re.match(r"^state\s*:", line):
            value = _extract_scalar_value(line)
            state_idx = i
            state_empty = not value
            break

    if state_idx is not None and not state_empty:
        lines[state_idx] = _replace_value_in_line(lines[state_idx], new_state)
        return "\n".join(lines)

    # Pass 2: cursor_state (string, block-dict THIS/this)
    for i, line in enumerate(lines):
        if re.match(r"^cursor_state\s*:", line):
            value = _extract_scalar_value(line)
            if value and not value.lstrip().startswith("{"):
                # Inline string form
                lines[i] = _replace_value_in_line(lines[i], new_state)
                return "\n".join(lines)
            if value and value.lstrip().startswith("{"):
                # Flow-mapping form — not supported in Sprint 2 (out of test scope)
                continue
            # Block-mapping form: scan indented children for THIS/this
            for j in range(i + 1, len(lines)):
                child = lines[j]
                if not child.strip():
                    continue
                if not (child.startswith(" ") or child.startswith("\t")):
                    break  # dedent ends the cursor_state block
                if re.match(r"^\s+(THIS|this)\s*:", child):
                    lines[j] = _replace_value_in_line(child, new_state)
                    return "\n".join(lines)
            # cursor_state block had no THIS/this child; continue to next candidate
            continue

    raise AtomParseError(
        filepath,
        "no state-bearing key (state, cursor_state, or cursor_state.THIS) "
        "found in frontmatter",
    )


def _extract_scalar_value(line: str) -> str:
    """Return the trimmed scalar value of a ``key: value`` line, comment stripped."""
    colon_idx = line.find(":")
    if colon_idx == -1:  # pragma: no cover
        # Structurally unreachable via the public API: this helper is only
        # invoked from _replace_state_in_fm_text on lines that already matched
        # `^state\s*:` or `^cursor_state\s*:`, which guarantees a colon. The
        # branch exists as a defensive return against future refactors that
        # could break the precondition.
        return ""
    after = line[colon_idx + 1 :]
    comment_match = re.search(r"\s+#", after)
    if comment_match:
        after = after[: comment_match.start()]
    return after.strip()


def _replace_value_in_line(line: str, new_state: str) -> str:
    """Substitute the scalar value of ``line``, preserving quoting and trailing comment."""
    colon_idx = line.find(":")
    if colon_idx == -1:  # pragma: no cover
        # Structurally unreachable via the public API: this helper is only
        # invoked on lines that already matched `^state\s*:`,
        # `^cursor_state\s*:`, or `^\s+(THIS|this)\s*:`, all of which require
        # a colon. The branch exists as a defensive return against future
        # refactors that could break the precondition.
        return line

    # Preserve any whitespace immediately following the colon (the YAML separator).
    sep_end = colon_idx + 1
    while sep_end < len(line) and line[sep_end] in (" ", "\t"):
        sep_end += 1
    prefix = line[:sep_end]
    rest = line[sep_end:]

    # Split rest into value-part and trailing (comment or pure whitespace tail).
    comment_match = re.search(r"(\s+#.*)$", rest)
    if comment_match:
        value_part = rest[: comment_match.start()]
        trailing = comment_match.group(0)
    else:
        stripped = rest.rstrip()
        value_part = stripped
        trailing = rest[len(stripped) :]

    # Preserve quoting style of the prior value.
    if len(value_part) >= 2 and value_part.startswith('"') and value_part.endswith('"'):
        new_value = f'"{new_state}"'
    elif len(value_part) >= 2 and value_part.startswith("'") and value_part.endswith("'"):
        new_value = f"'{new_state}'"
    else:
        new_value = new_state

    return prefix + new_value + trailing
