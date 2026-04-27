"""
Command-line interface for atomic-dag-soc.

The CLI is built on Click because it offers declarative command
definition, automatic --help generation, and composability that matches
the subcommand-heavy design we need (status, validate, transition,
audit, next, init).

Sprint 0 provides only the skeleton: --version, --help, and placeholders
for the subcommands that will arrive in Sprint 1 and later.
"""

from __future__ import annotations

import sys

import click

from atomic_dag import __version__


@click.group()
@click.version_option(version=__version__, prog_name="atomic-dag")
def main() -> None:
    """atomic-dag: BPMN-inspired orchestrator for LLM-produced artifacts."""


@main.command()
def status() -> None:
    """Show the dashboard of atoms in the current project."""
    click.echo("atomic-dag status: not yet implemented (Sprint 1)")
    sys.exit(0)


@main.command()
def validate() -> None:
    """Validate all atoms against the FSM and gate criteria."""
    click.echo("atomic-dag validate: not yet implemented (Sprint 1)")
    sys.exit(0)


@main.command(name="next")
def next_cmd() -> None:
    """Identify the next atom to work on based on the DAG."""
    click.echo("atomic-dag next: not yet implemented (Sprint 1)")
    sys.exit(0)


@main.command()
@click.argument("atom_id")
@click.argument("action")
def transition(atom_id: str, action: str) -> None:
    """Attempt a state transition on an atom."""
    click.echo(
        f"atomic-dag transition {atom_id} {action}: not yet implemented (Sprint 1)"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
