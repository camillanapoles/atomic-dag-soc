#!/usr/bin/env python3
"""P4 — Trigger Rate Metrics.

Wraps run_eval.py's raw trigger results with proper classification metrics:
Precision, Recall, F1, and False-Trigger-Rate (FTR).

Replaces the single `passed/total` pass-rate with a multi-metric report that
distinguishes between failing to trigger when needed (recall gap) and triggering
when it shouldn't (precision gap) — two very different problems with different
remediation strategies.

Output schema:
  {
    "skill_name": "...",
    "description": "...",
    "metrics": {
      "precision":          0.90,    # TP / (TP + FP)
      "recall":             0.80,    # TP / (TP + FN)
      "f1":                 0.85,    # harmonic mean
      "false_trigger_rate": 0.10,    # FP / N_negative queries
      "accuracy":           0.85,    # (TP + TN) / total
      "pass_rate":          0.85     # original metric (backward compat)
    },
    "diagnosis": {
      "signal": "NARROW" | "BROAD" | "MIXED" | "OK",
      "narrowness_signal": 0.40,   # fraction of positives that failed to trigger
      "broadness_signal":  0.10,   # fraction of negatives that false-triggered
    },
    "verdict": "APPROVED" | "OPTIMIZE" | "REWRITE",
    "thresholds": {...},
    "per_query": [...],             # pass-through from run_eval
    "summary": {...}                # pass-through from run_eval
  }

Two usage modes:
  A) Post-process existing run_eval.py JSON output:
     python -m scripts.eval_trigger_metrics --eval-results path/to/results.json

  B) Run the full eval from scratch (wraps run_eval internally):
     python -m scripts.eval_trigger_metrics \\
       --skill-path ./my-skill \\
       --eval-set ./my-skill/evals/trigger_eval.json \\
       --model claude-sonnet-4-6 \\
       --runs-per-query 3

Thresholds (configurable via --params):
  f1 >= 0.80 AND ftr < 0.15  →  APPROVED
  f1 in [0.60, 0.80) OR ftr in [0.15, 0.30)  →  OPTIMIZE  (run description loop)
  f1 < 0.60 OR ftr >= 0.30  →  REWRITE  (description needs full rewrite)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULTS = {
    "f1_approve": 0.80,
    "f1_optimize": 0.60,
    "ftr_approve": 0.15,    # false-trigger rate
    "ftr_optimize": 0.30,
    "narrowness_broaden_threshold": 0.30,   # P9: trigger BROADEN action
    "broadness_narrow_threshold": 0.25,     # P9: trigger NARROW action
    "epsilon": 1e-9,
}


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_metrics(results: list[dict], params: dict) -> dict:
    """Compute classification metrics from per-query trigger results.

    Each result item is expected to have:
      - should_trigger: bool
      - trigger_rate:   float  (triggers / runs)
      - pass:           bool   (evaluated at threshold already by run_eval)
    """
    eps = params["epsilon"]

    tp = sum(1 for r in results if     r["should_trigger"] and     r["pass"])
    tn = sum(1 for r in results if not r["should_trigger"] and     r["pass"])
    fp = sum(1 for r in results if not r["should_trigger"] and not r["pass"])
    fn = sum(1 for r in results if     r["should_trigger"] and not r["pass"])

    total = len(results)
    n_positive = tp + fn   # queries that SHOULD trigger
    n_negative = tn + fp   # queries that should NOT trigger

    precision = tp / (tp + fp + eps)
    recall    = tp / (tp + fn + eps)
    f1        = 2 * precision * recall / (precision + recall + eps)
    ftr       = fp / (n_negative + eps)       # false-trigger rate
    accuracy  = (tp + tn) / (total + eps)

    # P9 signals
    narrowness_signal = fn / (n_positive + eps)   # fraction of positives missed
    broadness_signal  = fp / (n_negative + eps)   # fraction of negatives triggered

    diagnosis = _diagnose(narrowness_signal, broadness_signal, params)
    verdict   = _verdict(f1, ftr, params)

    return {
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "n_positive": n_positive,
        "n_negative": n_negative,
        "metrics": {
            "precision":          round(precision, 4),
            "recall":             round(recall, 4),
            "f1":                 round(f1, 4),
            "false_trigger_rate": round(ftr, 4),
            "accuracy":           round(accuracy, 4),
            "pass_rate":          round((tp + tn) / (total + eps), 4),
        },
        "diagnosis": diagnosis,
        "verdict": verdict,
    }


def _diagnose(narrowness: float, broadness: float, params: dict) -> dict:
    nb_thresh = params["narrowness_broaden_threshold"]
    bn_thresh = params["broadness_narrow_threshold"]

    if narrowness > nb_thresh and broadness > bn_thresh:
        signal = "MIXED"
        action = "REFRAME — both narrow and broad; try structurally different description"
    elif narrowness > nb_thresh:
        signal = "NARROW"
        action = "BROADEN — description misses relevant queries; expand scope or add implicit triggers"
    elif broadness > bn_thresh:
        signal = "BROAD"
        action = "NARROW — description activates on irrelevant queries; add anti-cases"
    else:
        signal = "OK"
        action = "No structural issue detected"

    return {
        "signal": signal,
        "narrowness_signal": round(narrowness, 4),
        "broadness_signal":  round(broadness, 4),
        "recommended_action": action,
    }


def _verdict(f1: float, ftr: float, params: dict) -> str:
    if f1 >= params["f1_approve"] and ftr < params["ftr_approve"]:
        return "APPROVED"
    if f1 < params["f1_optimize"] or ftr >= params["ftr_optimize"]:
        return "REWRITE"
    return "OPTIMIZE"


# ---------------------------------------------------------------------------
# run_eval integration
# ---------------------------------------------------------------------------

def run_eval_subprocess(
    skill_path: Path,
    eval_set_path: Path,
    model: str | None,
    runs_per_query: int,
    trigger_threshold: float,
    num_workers: int,
    timeout: int,
    verbose: bool,
) -> dict:
    """Call run_eval.py as a subprocess and return parsed JSON output."""
    cmd = [
        sys.executable, "-m", "scripts.run_eval",
        "--skill-path", str(skill_path),
        "--eval-set",   str(eval_set_path),
        "--runs-per-query", str(runs_per_query),
        "--trigger-threshold", str(trigger_threshold),
        "--num-workers", str(num_workers),
        "--timeout",    str(timeout),
    ]
    if model:
        cmd.extend(["--model", model])
    if verbose:
        cmd.append("--verbose")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"run_eval failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def eval_trigger_metrics(
    eval_results: dict,
    params: dict | None = None,
) -> dict:
    """Compute P4 metrics from a run_eval.py results dict."""
    p = {**DEFAULTS, **(params or {})}

    computed = compute_metrics(eval_results["results"], p)

    return {
        "skill_name":  eval_results.get("skill_name", ""),
        "description": eval_results.get("description", ""),
        **computed,
        "thresholds": {
            "f1_approve":   p["f1_approve"],
            "f1_optimize":  p["f1_optimize"],
            "ftr_approve":  p["ftr_approve"],
            "ftr_optimize": p["ftr_optimize"],
        },
        "per_query": eval_results["results"],
        "summary":   eval_results["summary"],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="P4 — Compute Precision/Recall/F1/FTR metrics for skill trigger evaluation."
    )

    # Input: either pre-computed results or run from scratch
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--eval-results",
        help="Path to run_eval.py JSON output (post-process mode)",
    )
    input_group.add_argument(
        "--skill-path",
        help="Path to skill directory (runs eval from scratch; requires --eval-set)",
    )

    # Run-from-scratch options
    parser.add_argument("--eval-set",          help="Path to trigger eval JSON (required with --skill-path)")
    parser.add_argument("--model",             default=None, help="Model for claude -p")
    parser.add_argument("--runs-per-query",    type=int,   default=3)
    parser.add_argument("--trigger-threshold", type=float, default=0.5)
    parser.add_argument("--num-workers",       type=int,   default=10)
    parser.add_argument("--timeout",           type=int,   default=30)

    parser.add_argument(
        "--params",
        default=None,
        help="JSON overrides for metric thresholds",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    # Resolve raw eval results
    if args.eval_results:
        raw = json.loads(Path(args.eval_results).read_text())
    else:
        if not args.eval_set:
            print("Error: --eval-set is required when using --skill-path", file=sys.stderr)
            sys.exit(1)
        raw = run_eval_subprocess(
            skill_path=Path(args.skill_path),
            eval_set_path=Path(args.eval_set),
            model=args.model,
            runs_per_query=args.runs_per_query,
            trigger_threshold=args.trigger_threshold,
            num_workers=args.num_workers,
            timeout=args.timeout,
            verbose=args.verbose,
        )

    params = json.loads(args.params) if args.params else None
    report = eval_trigger_metrics(raw, params)

    if args.verbose:
        m = report["metrics"]
        d = report["diagnosis"]
        print(f"\n── P4 Trigger Rate Metrics ───────────────────", file=sys.stderr)
        print(f"  Skill:     {report['skill_name']}", file=sys.stderr)
        print(f"  Verdict:   {report['verdict']}", file=sys.stderr)
        print(f"\n  Metrics:", file=sys.stderr)
        print(f"    Precision:          {m['precision']:.3f}", file=sys.stderr)
        print(f"    Recall:             {m['recall']:.3f}", file=sys.stderr)
        print(f"    F1:                 {m['f1']:.3f}", file=sys.stderr)
        print(f"    False-Trigger Rate: {m['false_trigger_rate']:.3f}", file=sys.stderr)
        print(f"    Accuracy:           {m['accuracy']:.3f}", file=sys.stderr)
        cm = report["confusion"]
        print(f"\n  Confusion matrix:  TP={cm['tp']}  TN={cm['tn']}  FP={cm['fp']}  FN={cm['fn']}", file=sys.stderr)
        print(f"\n  Diagnosis:  {d['signal']}", file=sys.stderr)
        print(f"    narrowness={d['narrowness_signal']:.3f}  broadness={d['broadness_signal']:.3f}", file=sys.stderr)
        print(f"    → {d['recommended_action']}", file=sys.stderr)
        print(file=sys.stderr)

    print(json.dumps(report, indent=2))
    exit_code = 0 if report["verdict"] == "APPROVED" else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()