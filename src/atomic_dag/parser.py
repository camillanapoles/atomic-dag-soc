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
