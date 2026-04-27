"""
AtomParser: parses markdown atoms with YAML frontmatter.

This module will be implemented in Sprint 1. For now it defines the public
interface so that other modules and tests can import and reference the type.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Atom:
    """A parsed atom: metadata from YAML frontmatter plus markdown body."""

    meta: dict[str, Any]
    body: str
    filepath: Path

    @property
    def atomic_id(self) -> str:
        """The unique identifier of this atom, from frontmatter."""
        return str(self.meta["atomic_id"])


def parse_atom(filepath: str | Path) -> Atom:
    """
    Parse a markdown atom file into an Atom object.

    NOT YET IMPLEMENTED. Sprint 1 will provide the full implementation
    based on the parse_atom function in soc_orchestrator.py.
    """
    raise NotImplementedError("parse_atom will be implemented in Sprint 1")
