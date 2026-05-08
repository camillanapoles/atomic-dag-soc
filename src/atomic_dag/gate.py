"""
Gate Validator: enforces the triple quality threshold.

An atom advances from 'checked' to 'verified' only if it passes all three
criteria simultaneously:

- Gold score >= 9 out of 10 binary dimensions (PTDISLGEOX).
- PQMS (weighted quality score) >= 9.5 out of 10.
- VVV (Verdade / Validade / Verificação) >= 0.95.

These thresholds are specified in SOC_V4_UAT_FRAMEWORK.md and are not
negotiable - they are the contract that makes the SOC quality claim
falsifiable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

# Binary dimensions of the gold standard.
# P = pseudocode, T = transitions, D = diagram, I = invariants,
# S = soundness, L = log_atomic, G = gitops, E = error_handling,
# O = contracts_io, X = examples.
GOLD_COMPONENTS: Final[tuple[str, ...]] = tuple("PTDISLGEOX")

# Human-readable labels for display.
GOLD_LABELS: Final[dict[str, str]] = {
    "P": "pseudocode",
    "T": "transitions",
    "D": "diagram",
    "I": "invariants",
    "S": "soundness",
    "L": "log_atomic",
    "G": "gitops",
    "E": "error_handling",
    "O": "contracts_io",
    "X": "examples",
}

# PQMS dimensions with weights summing to 1.0.
# CE = completude, PI = precisão, CC = clareza, PRI = profundidade,
# RA = relevância, EIC = estrutura, OVA = originalidade.
PQMS_DIMS: Final[tuple[str, ...]] = ("CE", "PI", "CC", "PRI", "RA", "EIC", "OVA")

PQMS_WEIGHTS: Final[dict[str, float]] = {
    "CE": 0.15,
    "PI": 0.15,
    "CC": 0.10,
    "PRI": 0.20,
    "RA": 0.15,
    "EIC": 0.10,
    "OVA": 0.15,
}

# Thresholds. Any single failure below these is a gate failure.
GOLD_GATE: Final[int] = 9
PQMS_GATE: Final[float] = 9.5
VVV_GATE: Final[float] = 0.95
PQMS_DIM_MIN: Final[float] = 9.0  # No single dimension may be below this

# Circuit breaker: an atom that has been returned for kaizen more than
# this many times is a signal to escalate rather than keep iterating.
MAX_KAIZEN: Final[int] = 10


@dataclass(frozen=True)
class GateResult:
    """Immutable result of a triple-criterion gate check."""

    passed: bool
    gold_score: int
    pqms_score: float
    vvv_score: float
    reasons: tuple[str, ...]

    def __bool__(self) -> bool:
        return self.passed


def count_gold_components(gold_meta: dict[str, Any] | None) -> int:
    """Count how many of the 10 gold binary components are True.

    Only iterates keys in GOLD_COMPONENTS ("PTDISLGEOX"). Any other key
    present in gold_meta — including a self-reported "score" — is ignored.
    This is the anti-inflation design: the system exists because LLMs
    self-report inflated quality (SOC V3 reported 9.44 while audit measured
    4.49). Accepting a "score" field would reproduce exactly the problem
    the system is designed to prevent.
    """
    if not gold_meta:
        return 0
    return sum(1 for k in GOLD_COMPONENTS if gold_meta.get(k))


def compute_pqms(pqms_meta: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """Compute weighted PQMS score from individual dimension scores.

    Returns (weighted_total, per_dim_dict). If no recognized dimensions
    are present, returns (0.0, {}) as a signal that PQMS is absent.
    """
    per_dim: dict[str, float] = {}
    total = 0.0
    for dim in PQMS_DIMS:
        if dim in pqms_meta:
            score = float(pqms_meta[dim])
            per_dim[dim] = score
            total += PQMS_WEIGHTS[dim] * score
    return (total, per_dim)


def validate_gate(meta: dict[str, Any]) -> GateResult:
    """Apply the triple quality criterion to an atom's metadata.

    Extracts gold, pqms, and vvv sub-dicts from meta and checks:
    - Gold: count >= GOLD_GATE (9/10 binary components True)
    - PQMS: weighted total >= PQMS_GATE (9.5) AND no dim < PQMS_DIM_MIN (9.0)
    - VVV: value >= VVV_GATE (0.95)

    Missing fields produce specific reasons rather than crashes.
    """
    reasons: list[str] = []

    # Gold check
    gold_meta = meta.get("gold")
    gold_score = count_gold_components(gold_meta)
    if gold_score < GOLD_GATE:
        reasons.append(f"gold score {gold_score} < {GOLD_GATE} (threshold)")

    # PQMS check (aggregate + individual dims)
    pqms_meta = meta.get("pqms")
    if not pqms_meta:
        pqms_score = 0.0
        reasons.append("PQMS field missing or empty")
    else:
        pqms_score, per_dim = compute_pqms(pqms_meta)
        if not per_dim:
            reasons.append("PQMS field missing or empty")
        else:
            if pqms_score < PQMS_GATE:
                reasons.append(
                    f"PQMS score {pqms_score:.2f} < {PQMS_GATE} (threshold)"
                )
            for dim, val in per_dim.items():
                if val < PQMS_DIM_MIN:
                    reasons.append(
                        f"PQMS dimension {dim}={val} < {PQMS_DIM_MIN}"
                    )

    # VVV check
    if "vvv" not in meta:
        vvv_score = 0.0
        reasons.append("VVV field missing")
    else:
        vvv_score = float(meta["vvv"])
        if vvv_score < VVV_GATE:
            reasons.append(f"VVV score {vvv_score} < {VVV_GATE} (threshold)")

    passed = len(reasons) == 0
    return GateResult(
        passed=passed,
        gold_score=gold_score,
        pqms_score=pqms_score,
        vvv_score=vvv_score,
        reasons=tuple(reasons),
    )
