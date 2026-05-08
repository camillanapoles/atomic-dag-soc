"""Tests for atomic_dag.cli — 12 scenarios."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click.testing
import yaml

from atomic_dag.cli import main

_GOLD_KEYS = list("PTDISLGEOX")
_PQMS_KEYS = ["CE", "PI", "CC", "PRI", "RA", "EIC", "OVA"]


def _write_atom(
    path: Path,
    aid: str,
    state: str = "pending",
    deps: list[str] | None = None,
    **extra: Any,
) -> None:
    """Write a minimal atom .md file with YAML frontmatter."""
    meta: dict[str, Any] = {"atomic_id": aid, "state": state}
    if deps:
        meta["deps"] = deps
    meta.update(extra)
    content = f"---\n{yaml.dump(meta, default_flow_style=False).strip()}\n---\nBody of {aid}."
    path.write_text(content, encoding="utf-8")


def _passing_gate() -> dict[str, Any]:
    """Return gate metadata that passes all three criteria."""
    return {
        "gold": {k: True for k in _GOLD_KEYS},
        "pqms": {k: 10.0 for k in _PQMS_KEYS},
        "vvv": 1.0,
    }


def _run(*args: str) -> click.testing.Result:
    runner = click.testing.CliRunner()
    return runner.invoke(main, args)


# ── Scenario 1: status with valid project ──────────────────────────────


def test_status_valid_project(tmp_path: Path) -> None:
    _write_atom(tmp_path / "a.md", "a", state="pending")
    _write_atom(tmp_path / "b.md", "b", state="verified")
    result = _run("--project", str(tmp_path), "status")
    assert result.exit_code == 0
    assert "Total: 2 atoms" in result.output
    assert "pending: 1" in result.output
    assert "verified: 1" in result.output


# ── Scenario 2: status --json ──────────────────────────────────────────


def test_status_json(tmp_path: Path) -> None:
    _write_atom(tmp_path / "a.md", "a", state="pending")
    result = _run("--project", str(tmp_path), "status", "--json")
    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data["total"] == 1
    assert "states" in data
    assert "levels" in data


# ── Scenario 3: validate all pass ───────────────────────────────────────


def test_validate_all_pass(tmp_path: Path) -> None:
    gate = _passing_gate()
    _write_atom(tmp_path / "good.md", "good", state="verified", **gate)
    result = _run("--project", str(tmp_path), "validate")
    assert result.exit_code == 0
    assert "PASS good" in result.output


# ── Scenario 4: validate some fail (exit 1) ─────────────────────────────


def test_validate_some_fail(tmp_path: Path) -> None:
    gate = _passing_gate()
    _write_atom(tmp_path / "good.md", "good", state="verified", **gate)
    _write_atom(tmp_path / "bad.md", "bad", state="pending")
    result = _run("--project", str(tmp_path), "validate")
    assert result.exit_code == 1
    assert "PASS good" in result.output
    assert "FAIL bad" in result.output


# ── Scenario 5: validate --json ─────────────────────────────────────────


def test_validate_json(tmp_path: Path) -> None:
    _write_atom(tmp_path / "a.md", "a", state="pending")
    result = _run("--project", str(tmp_path), "validate", "--json")
    import json

    data = json.loads(result.output)
    assert data["all_passed"] is False
    assert len(data["results"]) == 1
    assert data["results"][0]["atom"] == "a"


# ── Scenario 6: next with actionable ────────────────────────────────────


def test_next_actionable(tmp_path: Path) -> None:
    _write_atom(tmp_path / "a.md", "a", state="pending")
    result = _run("--project", str(tmp_path), "next")
    assert result.exit_code == 0
    assert "Next actionable: a" in result.output


# ── Scenario 7: next nothing to do ──────────────────────────────────────


def test_next_nothing(tmp_path: Path) -> None:
    _write_atom(tmp_path / "a.md", "a", state="verified")
    result = _run("--project", str(tmp_path), "next")
    assert result.exit_code == 0
    assert "Nothing to do" in result.output


# ── Scenario 8: next --json ─────────────────────────────────────────────


def test_next_json(tmp_path: Path) -> None:
    _write_atom(tmp_path / "a.md", "a", state="pending")
    result = _run("--project", str(tmp_path), "next", "--json")
    import json

    data = json.loads(result.output)
    assert data["next_id"] == "a"


# ── Scenario 9: status empty project ────────────────────────────────────


def test_status_empty(tmp_path: Path) -> None:
    result = _run("--project", str(tmp_path), "status")
    assert result.exit_code == 0
    assert "Total: 0 atoms" in result.output


# ── Scenario 10: --project nonexistent ──────────────────────────────────


def test_project_nonexistent(tmp_path: Path) -> None:
    result = _run("--project", str(tmp_path / "nope"), "status")
    assert result.exit_code != 0


# ── Scenario 11: parse error returns exit 2 ─────────────────────────────


def test_parse_error_exit_2(tmp_path: Path) -> None:
    (tmp_path / "bad.md").write_text("no frontmatter here\n", encoding="utf-8")
    result = _run("--project", str(tmp_path), "status")
    assert result.exit_code == 2


# ── Scenario 12: --version without --project ────────────────────────────


def test_version_without_project() -> None:
    result = _run("--version")
    assert result.exit_code == 0
    assert "atomic-dag" in result.output
