#!/usr/bin/env python3
"""P3 — Description Quality Scorer.

Replaces the subjective "is this description good?" checklist with a
quantitative score across five measurable dimensions.

Output schema:
  {
    "description": "...",
    "score": 8.7,                   # 0.0–10.0
    "verdict": "APPROVED",          # APPROVED | REVISE | REJECT
    "dimensions": {
      "structural_completeness": {"score": 1.8, "weight": 0.20, "detail": {...}},
      "perspective":             {"score": 1.5, "weight": 0.15, "detail": {...}},
      "specificity":             {"score": 2.3, "weight": 0.25, "detail": {...}},
      "pushiness":               {"score": 1.8, "weight": 0.20, "detail": {...}},
      "char_budget":             {"score": 1.4, "weight": 0.20, "detail": {...}}
    },
    "hard_fail": false,             # true if char_count > 1024 (spec limit)
    "recommendations": [...]
  }

Usage:
  # Score from skill directory:
  python -m scripts.score_description --skill-path ./my-skill

  # Score raw description text:
  python -m scripts.score_description --description "Analyze CSV files..."

  # Pipe from another script:
  echo "Use this skill when..." | python -m scripts.score_description --stdin

Thresholds:
  score >= 8.5  →  APPROVED  (ready to proceed)
  score in [7.0, 8.5)  →  REVISE   (rewrite weak dimensions)
  score <  7.0  →  REJECT   (start from scratch)
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants — all tuneable via --params JSON
# ---------------------------------------------------------------------------

DEFAULTS = {
    "approve_threshold": 8.5,
    "revise_threshold": 7.0,
    "char_optimal_center": 500,   # chars — zone [200, 800] scores highest
    "char_hard_limit": 1024,      # spec limit; triggers hard_fail
    "char_min": 50,
    # Dimension weights (must sum to 1.0)
    "w_structural": 0.20,
    "w_perspective": 0.15,
    "w_specificity": 0.25,
    "w_pushiness": 0.20,
    "w_char_budget": 0.20,
}

# Imperative verbs that open a good description (3rd person, present tense)
IMPERATIVE_VERBS = re.compile(
    r"^(Use|Apply|Activate|Analyze|Process|Extract|Generate|Build|Create|"
    r"Run|Execute|Convert|Validate|Parse|Transform|Detect|Evaluate|Score|"
    r"Review|Optimize|Deploy|Manage|Migrate|Merge|Split|Search|Query|"
    r"Summarize|Classify|Cluster|Rank|Schedule|Monitor|Audit|Format|Clean)",
    re.IGNORECASE,
)

# Trigger phrases that describe when to activate (imperative framing)
TRIGGER_PATTERN = re.compile(
    r"(Use when|Use this skill when|Activate when|Use for|Apply when|"
    r"Triggers? (on|when|for)|Call (this|when)|Invoke when|"
    r"whenever the user|any time the user|when the user (asks?|wants?|needs?|mentions?))",
    re.IGNORECASE,
)

# Anti-case signals — tells agent when NOT to use this skill
ANTI_CASE_PATTERN = re.compile(
    r"\b(NOT|do not|avoid|except|don'?t|unless|rather than|instead of|"
    r"not for|not when|should not)\b",
    re.IGNORECASE,
)

# First-person markers that corrupt discovery (description is injected as 3rd person)
FIRST_PERSON = re.compile(r"\b(I\b|my\b|me\b|I'(m|ll|ve|d)\b|I can\b|I will\b)", re.IGNORECASE)

# Generic low-signal words that reduce specificity
GENERIC_WORDS = re.compile(
    r"\b(files?|data|help|process(es|ing)?|things?|stuff|items?|content|"
    r"information|output|result|work(s|ing)?|task)\b",
    re.IGNORECASE,
)

# Pushiness signals — explicit coverage of implicit cases
IMPLICIT_COVERAGE = re.compile(
    r"(even if|even when|regardless of|without.*mention(ing)?|"
    r"whether or not.*mention|implicit(ly)?)",
    re.IGNORECASE,
)
PUSHY_QUANTIFIERS = re.compile(
    r"\b(whenever|always when|any time|every time|all cases where)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Dimension scorers  (each returns a float in [0, weight])
# ---------------------------------------------------------------------------

def score_structural_completeness(desc: str, weight: float) -> dict:
    """D1: Does the description have all required structural elements?"""
    detail = {}

    # 1a. Starts with imperative verb (0.05)
    detail["imperative_verb"] = bool(IMPERATIVE_VERBS.match(desc.strip()))
    points_verb = weight * 0.25 if detail["imperative_verb"] else 0.0

    # 1b. Explicit trigger phrases (up to 3 valued, each worth weight*0.15, cap weight*0.45)
    trigger_hits = len(TRIGGER_PATTERN.findall(desc))
    detail["trigger_phrase_count"] = trigger_hits
    points_triggers = min(trigger_hits * weight * 0.15, weight * 0.45)

    # 1c. At least one anti-case (0.30)
    detail["has_anti_case"] = bool(ANTI_CASE_PATTERN.search(desc))
    points_anti = weight * 0.30 if detail["has_anti_case"] else 0.0

    raw = points_verb + points_triggers + points_anti
    score = min(raw, weight)  # cap at weight

    detail["subscores"] = {
        "imperative_verb": round(points_verb, 4),
        "trigger_phrases": round(points_triggers, 4),
        "anti_case": round(points_anti, 4),
    }
    return {"score": round(score, 4), "weight": weight, "detail": detail}


def score_perspective(desc: str, weight: float) -> dict:
    """D2: Is the description in 3rd person? Penalise first-person occurrences."""
    hits = len(FIRST_PERSON.findall(desc))
    # Linear penalty: each occurrence costs weight*0.05, floor 0
    score = max(0.0, weight - hits * weight * 0.05)
    return {
        "score": round(score, 4),
        "weight": weight,
        "detail": {
            "first_person_occurrences": hits,
            "penalty_per_hit": round(weight * 0.05, 4),
        },
    }


def score_specificity(desc: str, weight: float) -> dict:
    """D3: Domain-specific terms vs generic filler words.

    Technical terms captured:
      - ALL_CAPS acronyms ≥ 2 chars: CSV, TSV, API, SQL, LLM, YAML …
      - CamelCase (not sentence-start): pandas, pdfplumber, langchain …
      - Hyphenated compounds: write-ahead, step-by-step, fine-tuned …
      - Long single tokens ≥ 10 chars: visualization, transformer, spreadsheet …
      - File-type extensions: .csv, .xlsx, .json, .md …
    """
    words = re.findall(r"\b\w+\b", desc)
    total = max(len(words), 1)

    generic_hits = len(GENERIC_WORDS.findall(desc))
    generic_ratio = generic_hits / total

    tech_terms = (
        len(re.findall(r"\b[A-Z]{2,}\b", desc))                            # ALL_CAPS acronyms
        + len(re.findall(r"(?<![.!?\s])\b[a-z][a-z0-9]*[A-Z]\w+\b", desc))# camelCase mid-word
        + len(re.findall(r"\b\w+-\w+\b", desc))                             # hyphenated
        + len(re.findall(r"\b\w{10,}\b", desc))                             # long tokens
        + len(re.findall(r"\.\w{2,5}\b", desc))                             # file extensions
    )
    # Need at least ~5% of words to be technical (ratio vs total)
    specificity_ratio = min(tech_terms / max(total * 0.10, 1), 1.0)

    # Reward specificity, lightly penalise generics (generic is unavoidable)
    raw = weight * specificity_ratio - weight * 0.25 * generic_ratio
    score = max(0.0, min(raw, weight))

    return {
        "score": round(score, 4),
        "weight": weight,
        "detail": {
            "technical_terms_found": tech_terms,
            "generic_word_hits": generic_hits,
            "specificity_ratio": round(specificity_ratio, 4),
            "generic_ratio": round(generic_ratio, 4),
        },
    }


def score_pushiness(desc: str, weight: float) -> dict:
    """D4: Explicit coverage of implicit/indirect trigger cases."""
    implicit_hits = len(IMPLICIT_COVERAGE.findall(desc))
    pushy_hits = len(PUSHY_QUANTIFIERS.findall(desc))

    # 1 implicit-coverage phrase → 60% of weight; 2+ → 80% cap
    # pushy quantifiers supplement: 1 hit → 20% of weight, max 40%
    points_implicit = min(implicit_hits * weight * 0.60, weight * 0.80)
    points_pushy    = min(pushy_hits    * weight * 0.20, weight * 0.40)
    score = min(points_implicit + points_pushy, weight)

    return {
        "score": round(score, 4),
        "weight": weight,
        "detail": {
            "implicit_coverage_hits": implicit_hits,
            "pushy_quantifier_hits": pushy_hits,
        },
    }


def score_char_budget(desc: str, weight: float, params: dict) -> dict:
    """D5: Is the description within spec limits and in the optimal length zone?"""
    n = len(desc)
    center = params["char_optimal_center"]
    hard_limit = params["char_hard_limit"]
    char_min = params["char_min"]

    hard_fail = n > hard_limit

    if hard_fail:
        score = 0.0
        zone = "OVER_LIMIT"
    elif n < char_min:
        score = weight * 0.25
        zone = "TOO_SHORT"
    else:
        # Gaussian-shaped reward: peak at `center`, spreads ±300 chars
        sigma = 300.0
        gaussian = math.exp(-((n - center) ** 2) / (2 * sigma ** 2))
        score = weight * gaussian
        zone = "OPTIMAL" if abs(n - center) < sigma else "ACCEPTABLE"

    return {
        "score": round(score, 4),
        "weight": weight,
        "detail": {
            "char_count": n,
            "hard_limit": hard_limit,
            "optimal_center": center,
            "zone": zone,
            "hard_fail": hard_fail,
        },
    }


# ---------------------------------------------------------------------------
# Main scorer
# ---------------------------------------------------------------------------

def score_description(description: str, params: dict | None = None) -> dict:
    """Compute P3 score for a skill description. Returns full report dict."""
    p = {**DEFAULTS, **(params or {})}

    d1 = score_structural_completeness(description, p["w_structural"])
    d2 = score_perspective(description, p["w_perspective"])
    d3 = score_specificity(description, p["w_specificity"])
    d4 = score_pushiness(description, p["w_pushiness"])
    d5 = score_char_budget(description, p["w_char_budget"], p)

    hard_fail = d5["detail"]["hard_fail"]

    raw_score = d1["score"] + d2["score"] + d3["score"] + d4["score"] + d5["score"]
    score = round(raw_score * 10.0, 2)  # scale [0,1] → [0,10]
    score = 0.0 if hard_fail else score

    if hard_fail or score < p["revise_threshold"]:
        verdict = "REJECT"
    elif score < p["approve_threshold"]:
        verdict = "REVISE"
    else:
        verdict = "APPROVED"

    recommendations = _build_recommendations(d1, d2, d3, d4, d5)

    return {
        "description": description,
        "score": score,
        "verdict": verdict,
        "hard_fail": hard_fail,
        "dimensions": {
            "structural_completeness": d1,
            "perspective": d2,
            "specificity": d3,
            "pushiness": d4,
            "char_budget": d5,
        },
        "thresholds": {
            "approve": p["approve_threshold"],
            "revise": p["revise_threshold"],
        },
        "recommendations": recommendations,
    }


def _build_recommendations(d1, d2, d3, d4, d5) -> list[str]:
    recs = []

    if not d1["detail"]["imperative_verb"]:
        recs.append(
            "Start with an imperative verb (e.g. 'Use this skill when...', "
            "'Analyze...', 'Process...')."
        )
    if d1["detail"]["trigger_phrase_count"] < 2:
        recs.append(
            "Add at least 2 explicit trigger phrases ('Use when X', 'Activate when Y')."
        )
    if not d1["detail"]["has_anti_case"]:
        recs.append(
            "Add one anti-case: what this skill does NOT handle "
            "(e.g. 'NOT for simple one-step queries', 'avoid when...')."
        )
    if d2["detail"]["first_person_occurrences"] > 0:
        recs.append(
            f"Remove {d2['detail']['first_person_occurrences']} first-person "
            "reference(s). Descriptions must be in 3rd person — they are injected "
            "as context, not spoken by Claude."
        )
    if d3["detail"]["specificity_ratio"] < 0.15:
        recs.append(
            "Increase domain-specific terminology. Replace generic words "
            f"({d3['detail']['generic_word_hits']} found) with precise domain terms."
        )
    if d4["detail"]["implicit_coverage_hits"] == 0:
        recs.append(
            "Add 'pushiness': cover implicit triggers "
            "(e.g. 'even if they don\\'t explicitly mention X')."
        )
    if d5["detail"]["zone"] == "OVER_LIMIT":
        recs.append(
            f"Description is {d5['detail']['char_count']} chars — OVER the 1024-char "
            "hard limit. Trim immediately; it will be truncated by the spec."
        )
    elif d5["detail"]["zone"] == "TOO_SHORT":
        recs.append(
            "Description is very short. Add trigger contexts and domain terms "
            "to improve coverage."
        )

    return recs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="P3 — Score a skill description on 5 quantitative dimensions."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--skill-path", help="Path to skill directory (reads SKILL.md)")
    group.add_argument("--description", help="Raw description string to score")
    group.add_argument("--stdin", action="store_true", help="Read description from stdin")
    parser.add_argument(
        "--params",
        default=None,
        help="JSON string of parameter overrides (e.g. '{\"approve_threshold\": 9.0}')",
    )
    parser.add_argument("--verbose", action="store_true", help="Print human-readable summary to stderr")
    args = parser.parse_args()

    # Resolve description
    if args.skill_path:
        skill_path = Path(args.skill_path)
        if not (skill_path / "SKILL.md").exists():
            print(f"Error: No SKILL.md at {skill_path}", file=sys.stderr)
            sys.exit(1)
        # Inline parse to avoid circular import issues when run standalone
        from scripts.utils import parse_skill_md
        _, description, _ = parse_skill_md(skill_path)
    elif args.description:
        description = args.description
    else:
        description = sys.stdin.read().strip()

    params = json.loads(args.params) if args.params else None
    report = score_description(description, params)

    if args.verbose:
        print(f"\n── P3 Description Score ──────────────────────", file=sys.stderr)
        print(f"  Score:   {report['score']:.2f} / 10.0", file=sys.stderr)
        print(f"  Verdict: {report['verdict']}", file=sys.stderr)
        if report["hard_fail"]:
            print(f"  ⚠ HARD FAIL: description exceeds 1024-char spec limit", file=sys.stderr)
        print(f"\n  Dimensions:", file=sys.stderr)
        for name, dim in report["dimensions"].items():
            pct = dim["score"] / dim["weight"] * 100 if dim["weight"] else 0
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            print(f"    {name:<28} {bar}  {dim['score']:.3f}/{dim['weight']:.2f}", file=sys.stderr)
        if report["recommendations"]:
            print(f"\n  Recommendations:", file=sys.stderr)
            for rec in report["recommendations"]:
                print(f"    • {rec}", file=sys.stderr)
        print(file=sys.stderr)

    print(json.dumps(report, indent=2))
    sys.exit(0 if report["verdict"] == "APPROVED" else 1)


if __name__ == "__main__":
    main()