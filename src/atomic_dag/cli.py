"""
Command-line interface for atomic-dag-soc.

Exit codes:
  0 = success (all validate pass, status OK, next found)
  1 = validate found failing atoms (expected operational result)
  2 = structural error (parse error, inaccessible project)
"""

from __future__ import annotations

import json as json_mod
import sys
from typing import TYPE_CHECKING, Any

import click

from atomic_dag import __version__
from atomic_dag.dag import compute_dag_levels, find_next_actionable, state_summary
from atomic_dag.gate import validate_gate
from atomic_dag.parser import AtomParseError, parse_atom_directory
from atomic_dag.transitions import (
    AtomNotFoundError,
    InvalidTransitionError,
    execute_transition,
)

if TYPE_CHECKING:
    from atomic_dag.parser import Atom


@click.group()
@click.version_option(version=__version__, prog_name="atomic-dag")
@click.option(
    "-p",
    "--project",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Path to project directory with atom .md files.",
)
@click.pass_context
def main(ctx: click.Context, project: str) -> None:
    """atomic-dag: BPMN-inspired orchestrator for LLM-produced artifacts."""
    ctx.ensure_object(dict)
    ctx.obj["project"] = project


def _load_atoms(ctx: click.Context) -> dict[str, Atom]:
    """Load atoms from project dir. Exits with code 2 on parse errors."""
    assert ctx.obj is not None
    try:
        return parse_atom_directory(ctx.obj["project"])
    except AtomParseError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def status(ctx: click.Context, as_json: bool) -> None:
    """Show dashboard of atoms in the project."""
    atoms = _load_atoms(ctx)
    summary = state_summary(atoms)
    levels = compute_dag_levels(atoms)

    if as_json:
        data: dict[str, Any] = {
            "total": len(atoms),
            "states": summary,
            "levels": {str(k): v for k, v in levels.items()},
        }
        click.echo(json_mod.dumps(data, indent=2))
    else:
        states_str = ", ".join(f"{k}: {v}" for k, v in sorted(summary.items()))
        levels_parts = [
            f"L{k}: [{', '.join(levels[k])}]"
            for k in sorted(levels)
            if k >= 0
        ]
        click.echo(f"Total: {len(atoms)} atoms | {states_str}")
        if levels_parts:
            click.echo(f"Levels: {' | '.join(levels_parts)}")


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def validate(ctx: click.Context, as_json: bool) -> None:
    """Validate all atoms against the gate criteria.

    Exit codes: 0 = all pass, 1 = some fail, 2 = structural error.
    """
    atoms = _load_atoms(ctx)
    results: list[dict[str, Any]] = []
    all_passed = True

    for aid in sorted(atoms):
        result = validate_gate(atoms[aid].meta)
        results.append(
            {
                "atom": aid,
                "passed": result.passed,
                "reasons": list(result.reasons),
            }
        )
        if not result.passed:
            all_passed = False

    if as_json:
        click.echo(
            json_mod.dumps({"results": results, "all_passed": all_passed}, indent=2)
        )
    else:
        for r in results:
            if r["passed"]:
                click.echo(f"PASS {r['atom']}")
            else:
                click.echo(f"FAIL {r['atom']} ({'; '.join(r['reasons'])})")

    if not all_passed:
        sys.exit(1)


@main.command(name="next")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def next_cmd(ctx: click.Context, as_json: bool) -> None:
    """Identify the next atom to work on based on the DAG."""
    atoms = _load_atoms(ctx)
    next_id = find_next_actionable(atoms)

    if as_json:
        click.echo(json_mod.dumps({"next_id": next_id}, indent=2))
    else:
        if next_id:
            click.echo(f"Next actionable: {next_id}")
        else:
            click.echo("Nothing to do.")


@main.command()
@click.argument("atom_id")
@click.argument("action")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def transition(
    ctx: click.Context, atom_id: str, action: str, as_json: bool
) -> None:
    """Execute a state transition on an atom.

    Exit codes (D6 / transitions.md §6):
      0 — success (including idempotent replay and gate-fail-on-check → returned)
      1 — operational (FSM-invalid, terminal state)
      2 — structural (atom_id not in project, parse error)
    """
    project_root = ctx.obj["project"]
    atoms = _load_atoms(ctx)  # exits 2 on AtomParseError
    if atom_id not in atoms:
        click.echo(
            f"Error: atom_id {atom_id!r} not found in project {project_root}",
            err=True,
        )
        sys.exit(2)
    filepath = atoms[atom_id].filepath

    try:
        result = execute_transition(filepath, action, project_root=project_root)
    except AtomNotFoundError as exc:  # pragma: no cover
        # Defensive: race between _load_atoms (which already confirmed
        # atom_id presence via parse_atom_directory) and
        # execute_transition's own filepath.exists() check. Structurally
        # unreachable via the normal CLI flow because the lookup miss
        # above filters missing atom_ids; only an external file deletion
        # between the two calls could fire this branch.
        click.echo(f"Error: {exc}", err=True)
        sys.exit(2)
    except InvalidTransitionError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if as_json:
        click.echo(
            json_mod.dumps(
                {
                    "atom_id": result.atom_id,
                    "from_state": result.from_state,
                    "to_state": result.to_state,
                    "action": result.action,
                    "gate_passed": result.gate_passed,
                    "idempotent": result.idempotent,
                    "duration_ms": result.duration_ms,
                    "success": result.success,
                },
                indent=2,
            )
        )
    else:
        suffix = " (idempotent replay, no-op)" if result.idempotent else ""
        click.echo(
            f"transition {atom_id} {action}: "
            f"{result.from_state} -> {result.to_state}{suffix}"
        )


if __name__ == "__main__":  # pragma: no cover
    # Script entry point. Pytest imports `main` directly via CliRunner
    # and never triggers this guard; covering it would require spawning
    # cli.py as a subprocess in tests, which adds CI complexity for no
    # falsifiable benefit (Click already validates the dispatch).
    main()
