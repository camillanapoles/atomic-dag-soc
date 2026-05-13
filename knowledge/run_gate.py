#!/usr/bin/env python3
"""Full Skill Quality Pipeline.

Orchestrates the complete skill creation / improvement workflow:

  STEP 1 — P3: Score description quality
  STEP 2 — P9: Run opt_loop if description is below threshold (optional)
  STEP 3 — P4: Compute trigger metrics (requires eval set or pre-computed results)
  STEP 4 — P10: Run skill gate → final APPROVED / BLOCKED verdict

Each step is gated: if a blocking failure is detected early (e.g. P3 REJECT),
the pipeline stops unless --force-continue is set.

Usage:

  # Minimal (P3 + P10 structural checks only; no eval run):
  python -m scripts.run_gate --skill-path ./my-skill

  # Full pipeline with eval set (runs P4 from scratch):
  python -m scripts.run_gate \\
    --skill-path ./my-skill \\
    --eval-set ./my-skill/evals/trigger_eval.json \\
    --model claude-sonnet-4-6

  # Full pipeline with pre-computed P4 results:
  python -m scripts.run_gate \\
    --skill-path ./my-skill \\
    --eval-results ./results.json

  # Auto-fix: run opt_loop if P3 or P4 fail, then re-gate:
  python -m scripts.run_gate \\
    --skill-path ./my-skill \\
    --eval-set   ./my-skill/evals/trigger_eval.json \\
    --model      claude-sonnet-4-6 \\
    --auto-fix \\
    --apply

  # Override thresholds:
  python -m scripts.run_gate \\
    --skill-path ./my-skill \\
    --params '{"description_approve_threshold": 8.0, "f1_approve": 0.75}'

Output (stdout, JSON):
  {
    "skill_name": "...",
    "pipeline_verdict": "APPROVED" | "BLOCKED" | "PARTIAL",
    "steps": {
      "p3": { "verdict": "REVISE", "score": 8.3 },
      "p9": { "ran": true, "best_val_f1": 0.84, "iterations_run": 3 },
      "p4": { "verdict": "APPROVED", "f1": 0.82, "ftr": 0.09 },
      "p10": { "verdict": "APPROVED", "blocking_failures": [] }
    },
    "final_description": "...",        # updated if --apply was used
    "p3_report":  {...},               # full P3 output
    "p4_report":  {...},               # full P4 output (if available)
    "p10_report": {...},               # full P10 output
    "p9_report":  {...},               # full P9 output (if ran)
    "recommendations": [...]           # actionable next steps
  }

Exit codes:
  0  →  APPROVED
  1  →  BLOCKED
  2  →  Error (bad input / missing dependency)
"""

import argparse
import json
import sys
from pathlib import Path

from scripts.eval_trigger_metrics import eval_trigger_metrics
from scripts.run_eval import find_project_root, run_eval
from scripts.score_description import score_description as p3_score
from scripts.skill_gate import skill_gate
from scripts.utils import parse_skill_md


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULTS = {
    # P3
    "description_approve_threshold": 8.5,
    "description_optimize_threshold": 7.0,   # below this → opt_loop is mandatory if --auto-fix
    # P4
    "f1_approve": 0.80,
    "ftr_approve": 0.15,
    # P9 opt_loop
    "opt_loop_max_iterations": 5,
    # run_eval passthroughs
    "runs_per_query": 3,
    "trigger_threshold": 0.50,
    "num_workers": 10,
    "eval_timeout": 30,
}


# ---------------------------------------------------------------------------
# P4 runner (same pattern as skill_gate.py but returns raw + metrics)
# ---------------------------------------------------------------------------

def _run_p4(
    skill_path: Path,
    eval_results_path: Path | None,
    eval_set_path: Path | None,
    model: str | None,
    current_description: str,
    skill_name: str,
    params: dict,
    verbose: bool,
) -> tuple[dict | None, dict | None]:
    """Returns (raw_eval_output, p4_metrics_report) or (None, None)."""
    if eval_results_path:
        raw = json.loads(eval_results_path.read_text())
    elif eval_set_path:
        if verbose:
            print("  Running eval (P4)…", file=sys.stderr)
        project_root = find_project_root()
        eval_set = json.loads(eval_set_path.read_text())
        if not isinstance(eval_set, list):
            eval_set = eval_set.get("evals", [])
        raw = run_eval(
            eval_set=eval_set,
            skill_name=skill_name,
            description=current_description,
            num_workers=params["num_workers"],
            timeout=params["eval_timeout"],
            project_root=project_root,
            runs_per_query=params["runs_per_query"],
            trigger_threshold=params["trigger_threshold"],
        )
    else:
        return None, None

    p4_report = eval_trigger_metrics(raw, params)
    return raw, p4_report


# ---------------------------------------------------------------------------
# Opt-loop runner (calls opt_loop.py as a module function)
# ---------------------------------------------------------------------------

def _run_opt_loop(
    skill_path: Path,
    eval_set_path: Path | None,
    model: str | None,
    params: dict,
    verbose: bool,
) -> dict | None:
    """Run P9 opt_loop. Returns opt_loop result dict or None if skipped."""
    if eval_set_path is None or model is None:
        return None   # cannot run without eval set and model

    from scripts.opt_loop import opt_loop

    eval_set = json.loads(eval_set_path.read_text())
    if not isinstance(eval_set, list):
        eval_set = eval_set.get("evals", [])

    if verbose:
        print("  Running opt_loop (P9)…", file=sys.stderr)

    return opt_loop(
        eval_set=eval_set,
        skill_path=skill_path,
        model=model,
        params={
            "max_iterations": params.get("opt_loop_max_iterations", DEFAULTS["opt_loop_max_iterations"]),
            "f1_converge": params.get("f1_approve", DEFAULTS["f1_approve"]),
            "ftr_converge": params.get("ftr_approve", DEFAULTS["ftr_approve"]),
            "runs_per_query": params.get("runs_per_query", DEFAULTS["runs_per_query"]),
            "trigger_threshold": params.get("trigger_threshold", DEFAULTS["trigger_threshold"]),
        },
        verbose=verbose,
    )


# ---------------------------------------------------------------------------
# Apply description back to SKILL.md
# ---------------------------------------------------------------------------

def _apply_description(skill_path: Path, new_description: str, verbose: bool) -> bool:
    """Overwrite description in SKILL.md frontmatter. Returns True on success."""
    skill_md = skill_path / "SKILL.md"
    try:
        _, old_desc, content = parse_skill_md(skill_path)
        if old_desc == new_description:
            return True
        # Replace first occurrence of old description in content
        new_content = content.replace(old_desc, new_description, 1)
        skill_md.write_text(new_content)
        if verbose:
            print(f"  Applied new description to {skill_md}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"  Warning: could not apply description: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_gate_pipeline(
    skill_path: Path,
    eval_results_path: Path | None = None,
    eval_set_path: Path | None = None,
    model: str | None = None,
    params: dict | None = None,
    auto_fix: bool = False,
    apply: bool = False,
    force_continue: bool = False,
    verbose: bool = False,
) -> dict:
    p = {**DEFAULTS, **(params or {})}

    # ── Parse skill ────────────────────────────────────────────────────────
    try:
        skill_name, description, _ = parse_skill_md(skill_path)
    except Exception as e:
        print(f"Error reading SKILL.md: {e}", file=sys.stderr)
        sys.exit(2)

    steps: dict = {}
    p3_report = p9_report = p4_report = p10_report = None
    current_description = description

    # ── STEP 1: P3 — Description Score ────────────────────────────────────
    if verbose:
        print("\n[STEP 1] P3 — Description Score", file=sys.stderr)

    p3_report = p3_score(current_description, {"approve_threshold": p["description_approve_threshold"]})
    steps["p3"] = {
        "verdict": p3_report["verdict"],
        "score":   p3_report["score"],
        "hard_fail": p3_report["hard_fail"],
    }

    if verbose:
        print(f"  Score={p3_report['score']:.2f}  Verdict={p3_report['verdict']}", file=sys.stderr)

    p3_blocked = p3_report["verdict"] in ("REJECT", "REVISE")

    # ── STEP 2: P9 — Opt Loop (if description weak + auto_fix) ────────────
    steps["p9"] = {"ran": False}
    if p3_blocked and auto_fix and eval_set_path and model:
        if verbose:
            print("\n[STEP 2] P9 — Opt Loop (description weak, auto_fix=True)", file=sys.stderr)

        p9_report = _run_opt_loop(skill_path, eval_set_path, model, p, verbose)
        if p9_report:
            steps["p9"] = {
                "ran": True,
                "best_val_f1": p9_report["best_val_f1"],
                "iterations_run": p9_report["iterations_run"],
                "best_iteration": p9_report["best_iteration"],
                "exit_reason": p9_report["exit_reason"],
            }
            current_description = p9_report["best_description"]

            # Re-score P3 with new description
            p3_report = p3_score(current_description, {"approve_threshold": p["description_approve_threshold"]})
            steps["p3"]["score_after_p9"] = p3_report["score"]
            steps["p3"]["verdict_after_p9"] = p3_report["verdict"]

            if apply:
                _apply_description(skill_path, current_description, verbose)
    elif p3_blocked and not auto_fix:
        if verbose:
            print(
                f"\n[STEP 2] P9 — Skipped (description weak but --auto-fix not set). "
                f"Run with --auto-fix --model <model> to fix automatically.",
                file=sys.stderr,
            )
        steps["p9"]["skipped_reason"] = "auto_fix=False; description needs improvement"
    else:
        if verbose:
            print("\n[STEP 2] P9 — Skipped (description already acceptable)", file=sys.stderr)

    # ── STEP 3: P4 — Trigger Metrics ──────────────────────────────────────
    if verbose:
        print("\n[STEP 3] P4 — Trigger Metrics", file=sys.stderr)

    _, p4_report = _run_p4(
        skill_path=skill_path,
        eval_results_path=eval_results_path,
        eval_set_path=eval_set_path,
        model=model,
        current_description=current_description,
        skill_name=skill_name,
        params=p,
        verbose=verbose,
    )

    if p4_report:
        m = p4_report["metrics"]
        steps["p4"] = {
            "verdict":            p4_report["verdict"],
            "f1":                 m["f1"],
            "false_trigger_rate": m["false_trigger_rate"],
            "precision":          m["precision"],
            "recall":             m["recall"],
        }
        if verbose:
            print(
                f"  F1={m['f1']:.3f}  FTR={m['false_trigger_rate']:.3f}  "
                f"P={m['precision']:.3f}  R={m['recall']:.3f}  "
                f"Verdict={p4_report['verdict']}",
                file=sys.stderr,
            )

        # ── P9 auto-fix for P4 if trigger metrics failed ───────────────────
        if (
            p4_report["verdict"] != "APPROVED"
            and auto_fix
            and eval_set_path
            and model
            and not steps["p9"]["ran"]
        ):
            if verbose:
                print(
                    f"\n  P4 verdict={p4_report['verdict']} — running P9 opt_loop",
                    file=sys.stderr,
                )
            p9_report = _run_opt_loop(skill_path, eval_set_path, model, p, verbose)
            if p9_report:
                steps["p9"].update({
                    "ran": True,
                    "triggered_by": "p4_fail",
                    "best_val_f1": p9_report["best_val_f1"],
                    "iterations_run": p9_report["iterations_run"],
                    "exit_reason": p9_report["exit_reason"],
                })
                current_description = p9_report["best_description"]
                if apply:
                    _apply_description(skill_path, current_description, verbose)

                # Re-run P4 with improved description
                if verbose:
                    print("  Re-running P4 after opt_loop…", file=sys.stderr)
                _, p4_report = _run_p4(
                    skill_path=skill_path,
                    eval_results_path=None,
                    eval_set_path=eval_set_path,
                    model=model,
                    current_description=current_description,
                    skill_name=skill_name,
                    params=p,
                    verbose=verbose,
                )
                if p4_report:
                    m2 = p4_report["metrics"]
                    steps["p4"]["f1_after_p9"]  = m2["f1"]
                    steps["p4"]["ftr_after_p9"] = m2["false_trigger_rate"]
                    steps["p4"]["verdict_after_p9"] = p4_report["verdict"]
    else:
        steps["p4"] = {"ran": False, "skipped_reason": "no eval data (provide --eval-set or --eval-results)"}
        if verbose:
            print("  P4 — Skipped (no eval data)", file=sys.stderr)

    # ── STEP 4: P10 — Skill Gate ───────────────────────────────────────────
    if verbose:
        print("\n[STEP 4] P10 — Skill Gate", file=sys.stderr)

    p10_report = skill_gate(
        skill_path=skill_path,
        eval_results_path=eval_results_path,
        eval_set_path=eval_set_path,
        model=model,
        params=p,
        verbose=False,
    )
    steps["p10"] = {
        "verdict":           p10_report["verdict"],
        "blocking_failures": p10_report["blocking_failures"],
        "soft_warnings":     p10_report["soft_warnings"],
        "next_action":       p10_report["next_action"],
    }

    if verbose:
        print(f"  Verdict={p10_report['verdict']}", file=sys.stderr)
        if p10_report["blocking_failures"]:
            print(f"  Blocked by: {', '.join(p10_report['blocking_failures'])}", file=sys.stderr)
        if p10_report["soft_warnings"]:
            print(f"  Warnings:   {', '.join(p10_report['soft_warnings'])}", file=sys.stderr)

    # ── Final verdict ──────────────────────────────────────────────────────
    pipeline_verdict = p10_report["verdict"]  # APPROVED | BLOCKED

    # Build actionable recommendations
    recommendations = _build_recommendations(steps, p10_report, p3_report, p4_report)

    output = {
        "skill_name":        skill_name,
        "pipeline_verdict":  pipeline_verdict,
        "steps":             steps,
        "final_description": current_description,
        "original_description": description,
        "description_changed": current_description != description,
        "recommendations":   recommendations,
        "p3_report":         p3_report,
        "p4_report":         p4_report,
        "p9_report":         p9_report,
        "p10_report":        p10_report,
    }

    if verbose:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"PIPELINE VERDICT: {pipeline_verdict}", file=sys.stderr)
        if recommendations:
            print("RECOMMENDATIONS:", file=sys.stderr)
            for rec in recommendations:
                print(f"  • {rec}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

    return output


# ---------------------------------------------------------------------------
# Recommendations builder
# ---------------------------------------------------------------------------

def _build_recommendations(
    steps: dict,
    p10_report: dict,
    p3_report: dict | None,
    p4_report: dict | None,
) -> list[str]:
    recs = []

    # P3
    if p3_report and p3_report["verdict"] != "APPROVED":
        for rec in p3_report.get("recommendations", []):
            recs.append(f"[P3 Description] {rec}")

    # P4
    if p4_report and p4_report["verdict"] != "APPROVED":
        d = p4_report["diagnosis"]
        recs.append(
            f"[P4 Triggering] {d['recommended_action']} "
            f"(F1={p4_report['metrics']['f1']:.3f}, "
            f"FTR={p4_report['metrics']['false_trigger_rate']:.3f})"
        )

    # P10 structural
    for check_name in p10_report.get("soft_warnings", []):
        check = p10_report["checks"].get(check_name, {})
        if check.get("recommendation"):
            recs.append(f"[P10 Soft] {check['recommendation']}")

    # P9 opt_loop
    p9 = steps.get("p9", {})
    if not p9.get("ran") and steps.get("p3", {}).get("verdict") in ("REJECT", "REVISE"):
        recs.append(
            "[P9] Run opt_loop to auto-improve description: "
            "--auto-fix --model <model> --eval-set <path>"
        )

    return recs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Full skill quality pipeline: P3 → P9 → P4 → P10 gate."
    )
    parser.add_argument("--skill-path",     required=True, help="Path to skill directory")
    parser.add_argument("--eval-set",       default=None,  help="Trigger eval JSON (runs P4 + P9 from scratch)")
    parser.add_argument("--eval-results",   default=None,  help="Pre-computed run_eval.py JSON (skip live P4 run)")
    parser.add_argument("--model",          default=None,  help="Model for claude -p calls (P9 + P4)")
    parser.add_argument(
        "--auto-fix", action="store_true",
        help="Automatically run P9 opt_loop if P3 or P4 fail",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Write best_description back to SKILL.md when P9 runs",
    )
    parser.add_argument(
        "--force-continue", action="store_true",
        help="Continue pipeline even after blocking failures",
    )
    parser.add_argument("--params", default=None, help="JSON threshold overrides")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    skill_path = Path(args.skill_path)
    if not skill_path.exists():
        print(f"Error: {skill_path} does not exist", file=sys.stderr)
        sys.exit(2)

    params = json.loads(args.params) if args.params else None

    output = run_gate_pipeline(
        skill_path=skill_path,
        eval_results_path=Path(args.eval_results) if args.eval_results else None,
        eval_set_path=Path(args.eval_set)     if args.eval_set     else None,
        model=args.model,
        params=params,
        auto_fix=args.auto_fix,
        apply=args.apply,
        force_continue=args.force_continue,
        verbose=args.verbose,
    )

    print(json.dumps(output, indent=2))
    sys.exit(0 if output["pipeline_verdict"] == "APPROVED" else 1)


if __name__ == "__main__":
    main()