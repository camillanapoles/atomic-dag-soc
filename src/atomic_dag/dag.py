"""
DAG Computer: computes topological levels from the atom dependency graph.

Given a collection of atoms where each atom declares its dependencies via
frontmatter (backlinks.deps), this module computes the execution order via
topological sort. An atom at level N depends only on atoms at levels 0
through N-1.

This module will be fully implemented in Sprint 1. Sprint 0 provides the
interface only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atomic_dag.parser import Atom


def compute_dag_levels(atoms: dict[str, Atom]) -> dict[int, list[str]]:
    """
    Partition atoms into topological levels.

    Level 0 contains atoms with no dependencies (or whose dependencies are
    not in the current set). Subsequent levels contain atoms whose
    dependencies are all satisfied by earlier levels.

    Parameters
    ----------
    atoms : dict[str, Atom]
        Mapping from atomic_id to Atom.

    Returns
    -------
    dict[int, list[str]]
        Mapping from level number to list of atomic_ids at that level.
        Level 99 is reserved for atoms with circular or unresolvable deps.
    """
    raise NotImplementedError("compute_dag_levels will be implemented in Sprint 1")
