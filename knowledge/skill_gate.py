#!/usr/bin/env python3
"""P10 — Skill Gate.

Final publication gate: runs all P3 + P4 + spec + structural checks and
produces a single APPROVED / BLOCKED verdict with per-check detail and
automated remediation dispatch.

Six checks (in order):
  1. spec_compliance     [BLOCKING]  — quick_validate.py rules
  2. description_quality [BLOCKING]  — P3 score >= approve_threshold
  3. trigger_f1          [BLOCKING]  — P4 F1 >= f1_approve AND FTR < ftr_approve
  4. body_size           [SOFT]      — SKILL.md body <= 500 lines
  5. evals_present       [SOFT]      — evals/ directory with ≥1 JSON file
  6. references_depth    [SOFT]      — no deeply nested reference chains

Usage:

  # Full gate (runs P3 + validates spec; skip P4 if no eval-results supplied)
  python -m scripts.skill_gate --skill-path ./my-skill

  # Full gate including P4 metrics (pre-computed):
  python -m scripts.skill_gate \\
    --skill-path ./my-skill \\
    --eval-results ./my-skill/evals/results.json

  # Full gate: run P4 from scratch (requires claude -p):
  python -m scripts.skill_gate \\
    --skill-path ./my-skill \\
    --eval-set ./my-skill/evals/trigger_eval.json \\
    --model claude-sonnet-4-6

  # Override any threshold:
  python -m scripts.skill_gate --skill-path ./my-skill \\
    --params '{"f1_approve": 0.75, "description_approve_threshold": 8.0}'

Output schema:
  {
    "skill_name": "...",
    "skill_path": "...",
    "verdict": "APPROVED" | "BLOCKED",
    "checks": {
      "spec_compliance":     {"pass": true,  "blocking": true,  ...},
      "description_quality": {"pass": false, "blocking": true,  ...},
      "trigger_f1":          {"pass": true,  "blocking": true,  ...},
      "body_size":           {"pass": true,  "blocking": false, ...},
      "evals_present":       {"pass": true,  "blocking": false, ...},
      "references_depth":    {"pass": true,  "blocking": false, ...}
    },
    "blocking_failures": [...],
    "soft_warnings": [...],
    "next_action": "RUN_P9_OPT_LOOP" | "FIX_FRONTMATTER" | ... | null,
    "p3_report": {...},    # full P3 output (always present)
    "p4_report": {...},    # full P4 output (present when eval data available)
  }

Exit codes:
  0  →  APPROVED (all blocking checks pass)
  1  →  BLOCKED  (one or more blocking checks failed)
  2  →  Error    (input/config problem)
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Import P3 directly (same package)
from scripts.score_description import score_description as p3_score
from scripts.utils import parse_skill_md


# ---------------------------------------------------------------------------
# Thresholds — all overridable via --params
# ---------------------------------------------------------------------------

DEFAULTS = {
    # P3 thresholds
    "description_approve_threshold": 8.5,
    # P4 thresholds
    "f1_approve":   0.80,
    "ftr_approve":  0.15,
    # Structural limits
    "body_lines_soft_limit": 500,
    "min_evals_files": 1,
    "max_reference_depth": 1,        # references/ files should be 1 level deep
    # run_eval options (used when running P4 from scratch)
    "runs_per_query": 3,
    "trigger_threshold": 0.5,
    "num_workers": 10,
    "eval_timeout": 30,
}

# Spec-level constraints (must match quick_validate.py)
SPEC = {
    "name_max_chars": 64,
    "name_pattern": re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$"),
    "name_reserved": {"anthropic", "claude"},
    "desc_max_chars": 1024,
    "desc_no_xml": re.compile(r"[<>]"),
}


# ---------------------------------------------------------------------------
# Check 1 — Spec compliance (mirrors quick_validate logic inline to avoid
#            subprocess dependency; quick_validate.py stays the authoritative
#            CLI but we don't want to shell-out for a simple text parse)
# ---------------------------------------------------------------------------

def check_spec_compliance(skill_path: Path, name: str, description: str) -> dict:
    errors = []

    # name
    if not name:
        errors.append("'name' field is missing or empty")
    else:
        if len(name) > SPEC["name_max_chars"]:
            errors.append(f"name '{name}' is {len(name)} chars (max {SPEC['name_max_chars']})")
        if not SPEC["name_pattern"].match(name):
            errors.append(f"name '{name}' must be lowercase letters, digits and hyphens only")
        for reserved in SPEC["name_reserved"]:
            if reserved in name:
                errors.append(f"name contains reserved word '{reserved}'")
        if SPEC["desc_no_xml"].search(name):
            errors.append("name contains XML tag characters (< or >)")

    # description
    if not description:
        errors.append("'description' field is missing or empty")
    else:
        if len(description) > SPEC["desc_max_chars"]:
            errors.append(
                f"description is {len(description)} chars "
                f"(hard limit: {SPEC['desc_max_chars']})"
            )
        if SPEC["desc_no_xml"].search(description):
            errors.append("description contains XML tag characters (< or >)")

    return {
        "pass": len(errors) == 0,
        "blocking": True,
        "errors": errors,
        "detail": {
            "name": name,
            "name_len": len(name) if name else 0,
            "desc_len": len(description) if description else 0,
        },
    }


# ---------------------------------------------------------------------------
# Check 2 — Description quality (P3)
# ---------------------------------------------------------------------------

def check_description_quality(description: str, p3_report: dict, threshold: float) -> dict:
    score = p3_report["score"]
    return {
        "pass": score >= threshold and not p3_report["hard_fail"],
        "blocking": True,
        "score": score,
        "threshold": threshold,
        "verdict": p3_report["verdict"],
        "hard_fail": p3_report["hard_fail"],
        "recommendations": p3_report["recommendations"],
    }


# ---------------------------------------------------------------------------
# Check 3 — Trigger F1 (P4)
# ---------------------------------------------------------------------------

def check_trigger_f1(p4_report: dict | None, params: dict) -> dict:
    if p4_report is None:
        return {
            "pass": None,    # None = SKIPPED (no eval data provided)
            "blocking": True,
            "skipped": True,
            "reason": "No eval results provided. Supply --eval-results or --eval-set to enable this check.",
        }

    f1  = p4_report["metrics"]["f1"]
    ftr = p4_report["metrics"]["false_trigger_rate"]
    passed = f1 >= params["f1_approve"] and ftr < params["ftr_approve"]

    return {
        "pass": passed,
        "blocking": True,
        "skipped": False,
        "f1":  f1,
        "false_trigger_rate": ftr,
        "thresholds": {
            "f1_approve":  params["f1_approve"],
            "ftr_approve": params["ftr_approve"],
        },
        "p4_verdict":  p4_report["verdict"],
        "diagnosis":   p4_report["diagnosis"],
    }


# ---------------------------------------------------------------------------
# Check 4 — Body size
# ---------------------------------------------------------------------------

def check_body_size(skill_path: Path, _, content: str, limit: int) -> dict:
    # Count lines in the body (everything after closing ---)
    lines = content.split("\n")
    in_body = False
    front_end = 0
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            front_end = i
            in_body = True
            break
    body_lines = len(lines) - front_end - 1 if in_body else len(lines)

    return {
        "pass": body_lines <= limit,
        "blocking": False,
        "body_lines": body_lines,
        "soft_limit": limit,
        "recommendation": (
            f"SKILL.md body is {body_lines} lines (>{limit}). "
            "Move detailed reference material to references/ to stay under the limit."
            if body_lines > limit else None
        ),
    }


# ---------------------------------------------------------------------------
# Check 5 — Evals present
# ---------------------------------------------------------------------------

def check_evals_present(skill_path: Path, min_files: int) -> dict:
    evals_dir = skill_path / "evals"
    json_files = list(evals_dir.glob("*.json")) if evals_dir.exists() else []
    present = len(json_files) >= min_files
    return {
        "pass": present,
        "blocking": False,
        "evals_dir_exists": evals_dir.exists(),
        "json_files_found": len(json_files),
        "min_required": min_files,
        "recommendation": (
            "No eval set found. Create evals/trigger_eval.json with ≥20 queries "
            "(see Blueprint P4 schema). Triggering accuracy cannot be verified without evals."
            if not present else None
        ),
    }


# ---------------------------------------------------------------------------
# Check 6 — Reference chain depth
# ---------------------------------------------------------------------------

def check_references_depth(skill_path: Path, max_depth: int) -> dict:
    refs_dir = skill_path / "references"
    violations = []
    if refs_dir.exists():
        for f in refs_dir.rglob("*"):
            # depth = number of path parts relative to skill_path
            rel = f.relative_to(skill_path)
            depth = len(rel.parts) - 1  # subtract "references" itself
            if depth > max_depth and f.is_file():
                violations.append(str(rel))

    return {
        "pass": len(violations) == 0,
        "blocking": False,
        "max_depth": max_depth,
        "violations": violations,
        "recommendation": (
            f"Found {len(violations)} deeply-nested reference file(s). "
            "Keep file references one level deep from SKILL.md to avoid "
            "broken reference chains."
            if violations else None
        ),
    }


# ---------------------------------------------------------------------------
# Remediation dispatcher
# ---------------------------------------------------------------------------

REMEDIATION = {
    "spec_compliance":     "FIX_FRONTMATTER",
    "description_quality": "RUN_P9_OPT_LOOP",
    "trigger_f1":          "RUN_P9_OPT_LOOP",
}


def dispatch_remediation(blocking_failures: list[str]) -> str | None:
    """Return the highest-priority remediation action for a set of failing checks."""
    # Priority: spec first, then trigger, then description
    priority_order = ["spec_compliance", "trigger_f1", "description_quality"]
    for check_name in priority_order:
        if check_name in blocking_failures:
            return REMEDIATION[check_name]
    return None


# ---------------------------------------------------------------------------
# P4 runner (optional)
# ---------------------------------------------------------------------------

def run_p4(
    skill_path: Path,
    eval_results_path: Path | None,
    eval_set_path: Path | None,
    model: str | None,
    params: dict,
    verbose: bool,
) -> dict | None:
    """Load or compute P4 report. Returns None if no eval data available."""
    if eval_results_path:
        raw = json.loads(eval_results_path.read_text())
    elif eval_set_path:
        if verbose:
            print("Running P4 eval from scratch via run_eval.py…", file=sys.stderr)
        cmd = [
            sys.executable, "-m", "scripts.run_eval",
            "--skill-path", str(skill_path),
            "--eval-set",   str(eval_set_path),
            "--runs-per-query", str(params["runs_per_query"]),
            "--trigger-threshold", str(params["trigger_threshold"]),
            "--num-workers", str(params["num_workers"]),
            "--timeout",    str(params["eval_timeout"]),
        ]
        if model:
            cmd.extend(["--model", model])
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"run_eval.py failed:\n{result.stderr}", file=sys.stderr)
            return None
        raw = json.loads(result.stdout)
    else:
        return None

    # Run through P4 metrics layer
    from scripts.eval_trigger_metrics import eval_trigger_metrics
    return eval_trigger_metrics(raw, params)


# ---------------------------------------------------------------------------
# Gate orchestrator
# ---------------------------------------------------------------------------

def skill_gate(
    skill_path: Path,
    eval_results_path: Path | None = None,
    eval_set_path: Path | None = None,
    model: str | None = None,
    params: dict | None = None,
    verbose: bool = False,
) -> dict:
    p = {**DEFAULTS, **(params or {})}

    # Parse skill
    try:
        name, description, content = parse_skill_md(skill_path)
    except Exception as e:
        print(f"Error reading SKILL.md: {e}", file=sys.stderr)
        sys.exit(2)

    # P3
    p3_report = p3_score(description, {
        "approve_threshold": p["description_approve_threshold"],
    })

    # P4 (optional)
    p4_report = run_p4(
        skill_path=skill_path,
        eval_results_path=eval_results_path,
        eval_set_path=eval_set_path,
        model=model,
        params=p,
        verbose=verbose,
    )

    # Run all 6 checks
    checks = {
        "spec_compliance":     check_spec_compliance(skill_path, name, description),
        "description_quality": check_description_quality(description, p3_report, p["description_approve_threshold"]),
        "trigger_f1":          check_trigger_f1(p4_report, p),
        "body_size":           check_body_size(skill_path, name, content, p["body_lines_soft_limit"]),
        "evals_present":       check_evals_present(skill_path, p["min_evals_files"]),
        "references_depth":    check_references_depth(skill_path, p["max_reference_depth"]),
    }

    blocking_failures = [
        name_ for name_, c in checks.items()
        if c["blocking"] and c["pass"] is False   # None (skipped) ≠ False
    ]
    soft_warnings = [
        name_ for name_, c in checks.items()
        if not c["blocking"] and c["pass"] is False
    ]

    verdict = "APPROVED" if len(blocking_failures) == 0 else "BLOCKED"
    next_action = dispatch_remediation(blocking_failures) if blocking_failures else None

    return {
        "skill_name":        name,
        "skill_path":        str(skill_path),
        "verdict":           verdict,
        "checks":            checks,
        "blocking_failures": blocking_failures,
        "soft_warnings":     soft_warnings,
        "next_action":       next_action,
        "p3_report":         p3_report,
        "p4_report":         p4_report,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_check_line(name: str, check: dict):
    if check.get("skipped"):
        status = "⏭  SKIP "
    elif check["pass"] is True:
        status = "✅ PASS "
    elif not check["blocking"]:
        status = "⚠️  WARN "
    else:
        status = "❌ FAIL "

    tag = "[BLOCKING]" if check["blocking"] else "[SOFT]    "
    print(f"  {status} {tag}  {name}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="P10 — Skill Gate: full publication readiness check."
    )
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--eval-results", default=None,
                        help="Pre-computed run_eval.py JSON for P4 check")
    parser.add_argument("--eval-set", default=None,
                        help="Trigger eval JSON to run P4 from scratch (requires claude -p)")
    parser.add_argument("--model",    default=None, help="Model for claude -p (P4)")
    parser.add_argument("--params",   default=None, help="JSON threshold overrides")
    parser.add_argument("--verbose",  action="store_true")
    args = parser.parse_args()

    skill_path = Path(args.skill_path)
    if not skill_path.exists():
        print(f"Error: skill path not found: {skill_path}", file=sys.stderr)
        sys.exit(2)

    params = json.loads(args.params) if args.params else None

    report = skill_gate(
        skill_path=skill_path,
        eval_results_path=Path(args.eval_results) if args.eval_results else None,
        eval_set_path=Path(args.eval_set) if args.eval_set else None,
        model=args.model,
        params=params,
        verbose=args.verbose,
    )

    if args.verbose:
        print(f"\n── P10 Skill Gate ────────────────────────────", file=sys.stderr)
        print(f"  Skill:   {report['skill_name']}", file=sys.stderr)
        print(f"  Path:    {report['skill_path']}", file=sys.stderr)
        print(f"\n  Checks:", file=sys.stderr)
        for check_name, check in report["checks"].items():
            _print_check_line(check_name, check)
            # Print key sub-details
            if check_name == "description_quality" and not check["pass"]:
                for rec in check.get("recommendations", []):
                    print(f"           → {rec}", file=sys.stderr)
            if check_name == "spec_compliance" and not check["pass"]:
                for err in check.get("errors", []):
                    print(f"           → {err}", file=sys.stderr)
            if check_name == "trigger_f1" and not check.get("skipped") and not check["pass"]:
                d = check.get("diagnosis", {})
                print(f"           → {d.get('recommended_action', '')}", file=sys.stderr)

        print(f"\n  Verdict:     {report['verdict']}", file=sys.stderr)
        if report["blocking_failures"]:
            print(f"  Blocked by:  {', '.join(report['blocking_failures'])}", file=sys.stderr)
        if report["soft_warnings"]:
            print(f"  Warnings:    {', '.join(report['soft_warnings'])}", file=sys.stderr)
        if report["next_action"]:
            print(f"  Next action: {report['next_action']}", file=sys.stderr)

        # P3 score summary
        p3 = report["p3_report"]
        print(f"\n  P3 Description Score: {p3['score']:.2f}/10.0 ({p3['verdict']})", file=sys.stderr)

        # P4 metrics summary
        if report["p4_report"]:
            m = report["p4_report"]["metrics"]
            print(
                f"  P4 Trigger Metrics:   F1={m['f1']:.3f}  "
                f"FTR={m['false_trigger_rate']:.3f}  "
                f"Precision={m['precision']:.3f}  Recall={m['recall']:.3f}",
                file=sys.stderr,
            )
        else:
            print(f"  P4 Trigger Metrics:   SKIPPED (no eval data)", file=sys.stderr)
        print(file=sys.stderr)

    print(json.dumps(report, indent=2))
    sys.exit(0 if report["verdict"] == "APPROVED" else 1)


if __name__ == "__main__":
    main()