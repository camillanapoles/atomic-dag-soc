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
def transition(atom_id: str, action: str) -> None:
    """Attempt a state transition on an atom. (Sprint 2)"""
    click.echo(f"transition {atom_id} {action}: not yet implemented (Sprint 2)")


if __name__ == "__main__":
    main()
