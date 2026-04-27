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

This module exposes the constants in Sprint 0 so other modules can
reference them. The full validate_gate function will be implemented in
Sprint 1.
"""

from __future__ import annotations

from typing import Final

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
