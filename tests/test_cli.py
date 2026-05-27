"""Tests for atomic_dag.cli — 24 scenarios (12 herdados + 12 Phase 2.E)."""

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


# ── Family transition: Phase 2.E end-to-end via CLI ────────────────────


# ── Scenario 13: transition happy path pending -> in-progress ─────────


def test_transition_happy_path_pending_do(tmp_path: Path) -> None:
    from atomic_dag.parser import parse_atom

    _write_atom(tmp_path / "a.md", "a", state="pending")
    result = _run("--project", str(tmp_path), "transition", "a", "do")
    assert result.exit_code == 0, result.output
    assert "pending" in result.output
    assert "in-progress" in result.output
    assert parse_atom(tmp_path / "a.md").state == "in-progress"


# ── Scenario 14: transition --json schema ─────────────────────────────


def test_transition_happy_path_json(tmp_path: Path) -> None:
    import json

    _write_atom(tmp_path / "a.md", "a", state="pending")
    result = _run("--project", str(tmp_path), "transition", "a", "do", "--json")
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    expected_keys = {
        "atom_id",
        "from_state",
        "to_state",
        "action",
        "gate_passed",
        "idempotent",
        "duration_ms",
        "success",
    }
    assert set(data.keys()) == expected_keys
    assert data["atom_id"] == "a"
    assert data["from_state"] == "pending"
    assert data["to_state"] == "in-progress"
    assert data["action"] == "do"
    assert data["idempotent"] is False
    assert data["success"] is True
    assert isinstance(data["duration_ms"], int)
    assert data["duration_ms"] >= 0


# ── Scenario 15: atom_id not in project -> exit 2 ─────────────────────


def test_transition_atom_id_not_in_project(tmp_path: Path) -> None:
    _write_atom(tmp_path / "a.md", "a", state="pending")
    result = _run("--project", str(tmp_path), "transition", "nonexistent", "do")
    assert result.exit_code == 2
    # Error message names the missing atom_id explicitly.
    assert "nonexistent" in result.output


# ── Scenario 16: invalid FSM action -> exit 1 ─────────────────────────


def test_transition_invalid_action_exit_1(tmp_path: Path) -> None:
    _write_atom(tmp_path / "a.md", "a", state="pending")
    result = _run("--project", str(tmp_path), "transition", "a", "kaizen")
    assert result.exit_code == 1
    # RF-2.3: error message names atom_id, action, and state verbatim.
    assert "a" in result.output
    assert "kaizen" in result.output
    assert "pending" in result.output


# ── Scenario 17: terminal state -> exit 1 with "terminal" reason ──────


def test_transition_terminal_state_exit_1(tmp_path: Path) -> None:
    _write_atom(tmp_path / "a.md", "a", state="closed")
    result = _run("--project", str(tmp_path), "transition", "a", "do")
    assert result.exit_code == 1
    assert "closed" in result.output
    assert "terminal" in result.output


# ── Scenario 18: check + passing gate -> verified, exit 0 ─────────────


def test_transition_check_with_passing_gate_to_verified(tmp_path: Path) -> None:
    gate = _passing_gate()
    _write_atom(tmp_path / "a.md", "a", state="in-progress", **gate)
    result = _run("--project", str(tmp_path), "transition", "a", "check")
    assert result.exit_code == 0
    # DA-3: 'checked' is transient; persisted state is 'verified' when gate passes.
    assert "verified" in result.output


# ── Scenario 19: check + failing gate -> returned, exit 0 (not error) ─


def test_transition_check_with_failing_gate_to_returned(tmp_path: Path) -> None:
    # No gold/pqms/vvv → gate.validate_gate returns passed=False.
    _write_atom(tmp_path / "a.md", "a", state="in-progress")
    result = _run("--project", str(tmp_path), "transition", "a", "check")
    assert result.exit_code == 0  # D6: gate-fail-on-check is a route, not an error
    assert "returned" in result.output


# ── Scenario 20: idempotent replay -> exit 0 with explicit suffix ─────


def test_transition_idempotent_replay_exit_0(tmp_path: Path) -> None:
    _write_atom(tmp_path / "a.md", "a", state="pending")
    r1 = _run("--project", str(tmp_path), "transition", "a", "do")
    assert r1.exit_code == 0
    r2 = _run("--project", str(tmp_path), "transition", "a", "do")
    assert r2.exit_code == 0
    assert "idempotent" in r2.output


# ── Scenario 21: parse error somewhere in project -> exit 2 ───────────


def test_transition_parse_error_exit_2(tmp_path: Path) -> None:
    _write_atom(tmp_path / "a.md", "a", state="pending")
    # Another atom file in the same project is malformed; _load_atoms fails
    # globally and the transition command exits 2 before ever invoking
    # execute_transition on 'a'.
    (tmp_path / "bad.md").write_text("no frontmatter here\n", encoding="utf-8")
    result = _run("--project", str(tmp_path), "transition", "a", "do")
    assert result.exit_code == 2


# ── Scenario 22: --json after idempotent replay has idempotent=true ───


def test_transition_json_idempotent_field(tmp_path: Path) -> None:
    import json

    _write_atom(tmp_path / "a.md", "a", state="pending")
    _run("--project", str(tmp_path), "transition", "a", "do")  # first call
    result = _run(
        "--project", str(tmp_path), "transition", "a", "do", "--json"
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["idempotent"] is True
    assert data["success"] is True


# ── Scenario 23: --help documents exit codes verbatim ─────────────────


def test_transition_help_documents_exit_codes(tmp_path: Path) -> None:
    """R2: assertion is exact on the 4 substrings of the exit-code block."""
    result = _run("--project", str(tmp_path), "transition", "--help")
    assert result.exit_code == 0
    assert "Exit codes" in result.output
    assert "0 — success" in result.output
    assert "1 — operational" in result.output
    assert "2 — structural" in result.output


# ── Scenario 24: WAL event written end-to-end via CLI (R3) ────────────


def test_transition_wal_event_written(tmp_path: Path) -> None:
    """End-to-end CLI → WAL: after a successful non-idempotent transition,
    the WAL contains exactly one 'transition' event with the schema
    specified in transitions.md §4 (atom_id, to_state, gate_result dict)."""
    from atomic_dag.wal import read_events

    _write_atom(tmp_path / "a.md", "a", state="pending")
    result = _run("--project", str(tmp_path), "transition", "a", "do")
    assert result.exit_code == 0, result.output

    wal_path = tmp_path / ".atomic-dag" / "wal.jsonl"
    assert wal_path.is_file()

    events = read_events(wal_path)
    transition_events = [e for e in events if e.get("event_type") == "transition"]
    assert len(transition_events) == 1

    e = transition_events[0]
    assert e["atom_id"] == "a"
    assert e["from_state"] == "pending"
    assert e["to_state"] == "in-progress"
    assert e["action"] == "do"
    assert isinstance(e["gate_result"], dict)
    # gate_result dict mirrors GateResult public fields (transitions.md §4).
    expected_gr_keys = {"passed", "gold_score", "pqms_score", "vvv_score", "reasons"}
    assert set(e["gate_result"].keys()) == expected_gr_keys
    assert isinstance(e["gate_result"]["reasons"], list)
    assert isinstance(e["duration_ms"], int)
    assert e["duration_ms"] >= 0
