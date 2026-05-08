"""Tests for atomic_dag.gate — 19 scenarios."""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from atomic_dag.gate import (
    GOLD_COMPONENTS,
    PQMS_DIMS,
    PQMS_WEIGHTS,
    GateResult,
    compute_pqms,
    count_gold_components,
    validate_gate,
)


def _full_gold(overrides: dict[str, bool] | None = None) -> dict[str, bool]:
    """Return gold dict with all 10 components True, applying overrides."""
    gold = {k: True for k in GOLD_COMPONENTS}
    if overrides:
        gold.update(overrides)
    return gold


def _full_pqms(score: float = 10.0) -> dict[str, float]:
    return {dim: score for dim in PQMS_DIMS}


def _passing_meta() -> dict[str, Any]:
    return {"gold": _full_gold(), "pqms": _full_pqms(), "vvv": 1.0}


# ── Scenario 1: count_gold all True ─────────────────────────────────


def test_count_gold_all_true() -> None:
    assert count_gold_components(_full_gold()) == 10


# ── Scenario 2: count_gold 9 True, 1 False ──────────────────────────


def test_count_gold_nine_true() -> None:
    assert count_gold_components(_full_gold({"X": False})) == 9


# ── Scenario 3: count_gold None input ───────────────────────────────


def test_count_gold_none() -> None:
    assert count_gold_components(None) == 0


# ── Scenario 4: ANTI-INFLATION — score field ignored ─────────────────


def test_count_gold_ignores_self_reported_score() -> None:
    gold = {k: False for k in GOLD_COMPONENTS}
    gold["score"] = 10
    assert count_gold_components(gold) == 0


# ── Scenario 5: count_gold empty dict ────────────────────────────────


def test_count_gold_empty_dict() -> None:
    assert count_gold_components({}) == 0


# ── Scenario 6: count_gold extra non-GOLD fields ignored ─────────────


def test_count_gold_extra_fields_ignored() -> None:
    gold = _full_gold()
    gold["extra"] = True
    gold["another"] = True
    assert count_gold_components(gold) == 10


# ── Scenario 7: compute_pqms all dims 10.0 ──────────────────────────


def test_compute_pqms_all_max() -> None:
    total, per_dim = compute_pqms(_full_pqms(10.0))
    assert total == 10.0
    assert all(v == 10.0 for v in per_dim.values())
    assert set(per_dim.keys()) == set(PQMS_DIMS)


# ── Scenario 8: compute_pqms mixed dims ──────────────────────────────


def test_compute_pqms_mixed() -> None:
    pqms = {
        "CE": 10.0,
        "PI": 8.0,
        "CC": 9.0,
        "PRI": 10.0,
        "RA": 7.0,
        "EIC": 9.0,
        "OVA": 10.0,
    }
    total, per_dim = compute_pqms(pqms)
    expected = sum(PQMS_WEIGHTS[d] * pqms[d] for d in PQMS_DIMS)
    assert abs(total - expected) < 1e-9
    assert len(per_dim) == 7


# ── Scenario 9: compute_pqms empty dict ──────────────────────────────


def test_compute_pqms_empty() -> None:
    total, per_dim = compute_pqms({})
    assert total == 0.0
    assert per_dim == {}


# ── Scenario 10: validate_gate all passing ───────────────────────────


def test_validate_gate_all_passing() -> None:
    result = validate_gate(_passing_meta())
    assert result.passed is True
    assert result.gold_score == 10
    assert result.pqms_score == 10.0
    assert result.vvv_score == 1.0
    assert result.reasons == ()


# ── Scenario 11: validate_gate gold below ────────────────────────────


def test_validate_gate_gold_below() -> None:
    meta = _passing_meta()
    meta["gold"] = _full_gold({"X": False, "E": False})  # 8/10
    result = validate_gate(meta)
    assert result.passed is False
    assert any("gold" in r for r in result.reasons)


# ── Scenario 12: validate_gate PQMS below ────────────────────────────


def test_validate_gate_pqms_below() -> None:
    meta = _passing_meta()
    meta["pqms"] = {dim: 5.0 for dim in PQMS_DIMS}
    result = validate_gate(meta)
    assert result.passed is False
    assert any("PQMS score" in r for r in result.reasons)


# ── Scenario 13: PQMS aggregate passes BUT dim individual fails ──────


def test_validate_gate_pqms_dim_individual_below() -> None:
    meta = _passing_meta()
    # 6 dims at 10.0 + PRI at 8.5 (weight 0.20)
    # total = 0.80 * 10.0 + 0.20 * 8.5 = 9.7 >= 9.5 (passes aggregate)
    # but PRI=8.5 < 9.0 (fails individual)
    pqms = {dim: 10.0 for dim in PQMS_DIMS}
    pqms["PRI"] = 8.5
    meta["pqms"] = pqms
    result = validate_gate(meta)
    assert result.passed is False
    assert any("PRI=8.5" in r for r in result.reasons)
    # Aggregate should NOT be in reasons (it passes)
    assert not any("PQMS score" in r for r in result.reasons)


# ── Scenario 14: validate_gate VVV below ─────────────────────────────


def test_validate_gate_vvv_below() -> None:
    meta = _passing_meta()
    meta["vvv"] = 0.80
    result = validate_gate(meta)
    assert result.passed is False
    assert any("VVV" in r for r in result.reasons)


# ── Scenario 15: validate_gate no gold/pqms/vvv fields ───────────────


def test_validate_gate_all_missing() -> None:
    result = validate_gate({})
    assert result.passed is False
    assert len(result.reasons) == 3
    assert any("gold" in r for r in result.reasons)
    assert any("PQMS field missing" in r for r in result.reasons)
    assert any("VVV field missing" in r for r in result.reasons)


# ── Scenario 16: GateResult __bool__ ─────────────────────────────────


def test_gate_result_bool() -> None:
    r_true = GateResult(
        passed=True, gold_score=10, pqms_score=10.0, vvv_score=1.0, reasons=()
    )
    assert bool(r_true) is True
    r_false = GateResult(
        passed=False, gold_score=0, pqms_score=0.0, vvv_score=0.0, reasons=("fail",)
    )
    assert bool(r_false) is False


# ── Scenario 17: GateResult frozen ───────────────────────────────────


def test_gate_result_frozen() -> None:
    result = GateResult(
        passed=True, gold_score=10, pqms_score=10.0, vvv_score=1.0, reasons=()
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.passed = False  # type: ignore[misc]


# ── Scenario 18: validate_gate VVV missing (not zero) ────────────────


def test_validate_gate_vvv_missing() -> None:
    meta = _passing_meta()
    del meta["vvv"]
    result = validate_gate(meta)
    assert result.passed is False
    assert any("VVV field missing" in r for r in result.reasons)
    # NOT "VVV score 0.0 < 0.95"
    assert not any("VVV score" in r for r in result.reasons)


# ── Scenario 19: PQMS present but no recognized dims ─────────────────


def test_validate_gate_pqms_unknown_dims() -> None:
    meta = _passing_meta()
    meta["pqms"] = {"unknown_dim": 10.0, "another_unknown": 9.5}
    result = validate_gate(meta)
    assert result.passed is False
    assert any("PQMS field missing or empty" in r for r in result.reasons)
