"""
DAG Computer: topological level computation via Kahn's algorithm.

Given a collection of atoms where each atom declares its dependencies via
frontmatter, this module computes the execution order via topological sort.
An atom at level N depends only on atoms at levels 0 through N-1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atomic_dag.parser import Atom

CYCLE_LEVEL = -1


class DAGCycleError(ValueError):
    """Raised when strict DAG computation encounters a cycle."""


def compute_dag_levels(atoms: dict[str, Atom]) -> dict[int, list[str]]:
    """Partition atoms into topological levels using Kahn's algorithm.

    Level 0: atoms with no internal deps (or all deps external).
    Level N: atoms whose internal deps are all at levels < N.
    CYCLE_LEVEL (-1): atoms in circular dependency chains.

    Within each level, atomic_ids are sorted alphabetically for determinism.
    External deps (not present in atoms) are treated as satisfied.
    """
    if not atoms:
        return {}

    # Build in-degree (count of internal deps) and reverse adjacency
    in_degree: dict[str, int] = {}
    dependents: dict[str, list[str]] = {}

    for aid, atom in atoms.items():
        internal_deps = [d for d in atom.deps if d in atoms]
        in_degree[aid] = len(internal_deps)
        for dep in internal_deps:
            dependents.setdefault(dep, []).append(aid)

    # Kahn's algorithm
    current = sorted(aid for aid, deg in in_degree.items() if deg == 0)
    levels: dict[int, list[str]] = {}
    assigned: set[str] = set()
    level_num = 0

    while current:
        levels[level_num] = current
        assigned.update(current)

        next_level: list[str] = []
        for aid in current:
            for dep_id in dependents.get(aid, []):
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    next_level.append(dep_id)

        current = sorted(next_level)
        level_num += 1

    # Remaining atoms are in cycles
    remaining = sorted(aid for aid in atoms if aid not in assigned)
    if remaining:
        levels[CYCLE_LEVEL] = remaining

    return levels


def compute_dag_levels_strict(atoms: dict[str, Atom]) -> dict[int, list[str]]:
    """Like compute_dag_levels but raises DAGCycleError if cycles exist."""
    levels = compute_dag_levels(atoms)
    if CYCLE_LEVEL in levels:
        raise DAGCycleError(
            f"cycle detected among atoms: {', '.join(levels[CYCLE_LEVEL])}"
        )
    return levels


def find_next_actionable(atoms: dict[str, Atom]) -> str | None:
    """Return the atomic_id of the next actionable atom.

    An atom is actionable when:
    - Its state is 'pending'
    - All its internal dependencies have state 'verified'

    External deps (not in atoms) are treated as satisfied.
    Tie-breaking: alphabetical by atomic_id.
    Returns None if nothing is actionable.
    """
    candidates: list[str] = []
    for aid, atom in atoms.items():
        if atom.state != "pending":
            continue
        internal_deps = [d for d in atom.deps if d in atoms]
        if all(atoms[d].state == "verified" for d in internal_deps):
            candidates.append(aid)
    return sorted(candidates)[0] if candidates else None


def state_summary(atoms: dict[str, Atom]) -> dict[str, int]:
    """Count atoms by state."""
    counts: dict[str, int] = {}
    for atom in atoms.values():
        state = atom.state
        counts[state] = counts.get(state, 0) + 1
    return counts
