#!/usr/bin/env python3
"""P9 — Description Optimization Loop.

Replaces run_loop.py's pass/fail-only heuristic with F1/FTR-driven diagnosis
(BROADEN | NARROW | REFRAME | CONVERGED) and Jaccard anti-overfit guard.

Key differences from run_loop.py:
  - Uses P4 compute_metrics() → real F1, FTR, precision, recall per iteration
  - BROADEN/NARROW/REFRAME dispatch based on narrowness_signal + broadness_signal
  - Jaccard guard: rejects candidate if keyword overlap with failed queries > 0.40
  - Selects best_description by validation F1 (not train pass rate)
  - Stratified 60/40 train/val split (reproducible with --seed)
  - Backward-compatible JSON output (superset of run_loop.py schema)

Usage:
  python -m scripts.opt_loop \\
    --skill-path ./my-skill \\
    --eval-set   ./my-skill/evals/trigger_eval.json \\
    --model      claude-sonnet-4-6 \\
    --max-iterations 5 \\
    --verbose

  # Override thresholds:
  python -m scripts.opt_loop \\
    --skill-path ./my-skill \\
    --eval-set   ./my-skill/evals/trigger_eval.json \\
    --model      claude-sonnet-4-6 \\
    --params '{"f1_approve": 0.85, "anti_overfit_jaccard_max": 0.35}'

Output (stdout, JSON):
  {
    "exit_reason": "f1_converged | max_iterations | train_all_passed",
    "best_description": "...",          # selected by val_f1, not last iter
    "best_val_f1": 0.87,
    "best_iteration": 3,
    "original_description": "...",
    "iterations_run": 5,
    "history": [                        # one entry per iteration
      {
        "iteration": 1,
        "description": "...",
        "action": "BROADEN",
        "train_metrics": { "f1": 0.70, "false_trigger_rate": 0.12, ... },
        "val_metrics":   { "f1": 0.72, "false_trigger_rate": 0.10, ... },
        "diagnosis": { "signal": "NARROW", "narrowness_signal": 0.35, ... },
        "jaccard_guard_triggered": false
      }
    ]
  }
"""

import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

from scripts.eval_trigger_metrics import compute_metrics, DEFAULTS as P4_DEFAULTS
from scripts.run_eval import find_project_root, run_eval
from scripts.utils import parse_skill_md


# ---------------------------------------------------------------------------
# Defaults — all overridable via --params
# ---------------------------------------------------------------------------

DEFAULTS = {
    **P4_DEFAULTS,
    # Loop control
    "max_iterations": 5,
    "holdout_fraction": 0.40,          # val set size (40% = stratified)
    "seed": 42,
    # P9-specific
    "anti_overfit_jaccard_max": 0.40,  # reject candidate if Jaccard > this
    "f1_converge": 0.80,               # stop early if val F1 ≥ this
    "ftr_converge": 0.15,              # stop early if FTR ≤ this
    # run_eval passthroughs
    "runs_per_query": 3,
    "trigger_threshold": 0.50,
    "num_workers": 10,
    "eval_timeout": 30,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stratified_split(eval_set: list[dict], holdout: float, seed: int) -> tuple[list[dict], list[dict]]:
    """Stratified 60/40 split preserving pos/neg ratio in both halves."""
    rng = random.Random(seed)
    pos = [q for q in eval_set if q["should_trigger"]]
    neg = [q for q in eval_set if not q["should_trigger"]]
    rng.shuffle(pos)
    rng.shuffle(neg)

    n_pos_val = max(1, round(len(pos) * holdout))
    n_neg_val = max(1, round(len(neg) * holdout))

    val  = pos[:n_pos_val]  + neg[:n_neg_val]
    train = pos[n_pos_val:] + neg[n_neg_val:]
    return train, val


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful tokens (≥4 chars, not stopwords) from text."""
    STOPWORDS = {
        "this", "that", "with", "from", "when", "even", "they", "their",
        "have", "will", "want", "need", "dont", "about", "into", "which",
        "skill", "user", "task", "using", "used", "uses", "should", "would",
        "could", "make", "help", "does", "more", "than", "also", "some",
    }
    tokens = re.findall(r"\b[a-z]{4,}\b", text.lower())
    return {t for t in tokens if t not in STOPWORDS}


def _jaccard(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _eval_to_metrics(results_list: list[dict], params: dict) -> dict:
    """Wrap a list of per-query result dicts → P4 metrics dict."""
    return compute_metrics(results_list, params)


def _call_claude(prompt: str, model: str, timeout: int = 300) -> str:
    """Run claude -p and return text output. Same pattern as improve_description.py."""
    cmd = ["claude", "-p", "--output-format", "text"]
    if model:
        cmd.extend(["--model", model])
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    result = subprocess.run(cmd, input=prompt, capture_output=True, text=True, env=env, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"claude -p failed ({result.returncode}): {result.stderr}")
    return result.stdout


def _build_improvement_prompt(
    skill_name: str,
    skill_content: str,
    current_description: str,
    diagnosis: dict,
    failed_triggers: list[dict],
    false_triggers: list[dict],
    history: list[dict],
    train_metrics: dict,
    val_metrics: dict | None,
) -> str:
    action = diagnosis["signal"]           # NARROW | BROAD | MIXED | OK

    action_instruction = {
        "NARROW": (
            "The description is TOO NARROW — it misses queries it should trigger for.\n"
            "ACTION: Broaden the scope. Cover the general CATEGORY of intent these queries "
            "represent, NOT their specific keywords (that would be overfitting).\n"
            "Hint: add implicit-coverage phrases like 'even if they don't explicitly mention X'."
        ),
        "BROAD": (
            "The description is TOO BROAD — it triggers on queries it shouldn't.\n"
            "ACTION: Add anti-cases to narrow the scope. Describe what this skill does NOT "
            "handle (adjacent tasks, simpler variants, different domains)."
        ),
        "MIXED": (
            "The description is both narrow AND broad. A structural reframe is needed — "
            "incremental edits won't fix both problems at once.\n"
            "ACTION: Write a structurally DIFFERENT description. Different sentence structure, "
            "different framing. Do NOT iterate on the current version."
        ),
        "OK": (
            "Metrics are acceptable but not yet at threshold. Refine the weakest dimension."
        ),
    }.get(action, "Improve the description based on the failures.")

    # Build metrics summary
    val_summary = (
        f"  Val:   F1={val_metrics['metrics']['f1']:.3f}  "
        f"FTR={val_metrics['metrics']['false_trigger_rate']:.3f}  "
        f"Precision={val_metrics['metrics']['precision']:.3f}  "
        f"Recall={val_metrics['metrics']['recall']:.3f}"
        if val_metrics else "  Val: N/A"
    )
    train_summary = (
        f"  Train: F1={train_metrics['metrics']['f1']:.3f}  "
        f"FTR={train_metrics['metrics']['false_trigger_rate']:.3f}  "
        f"Precision={train_metrics['metrics']['precision']:.3f}  "
        f"Recall={train_metrics['metrics']['recall']:.3f}"
    )

    prompt = f"""You are optimizing a skill description for "{skill_name}".

CURRENT DESCRIPTION:
"{current_description}"

METRICS:
{train_summary}
{val_summary}

DIAGNOSIS: {action}
{action_instruction}

"""
    if failed_triggers:
        prompt += "FAILED TO TRIGGER (should have — represent the category, don't copy keywords):\n"
        for r in failed_triggers:
            prompt += f'  - "{r["query"]}" ({r["triggers"]}/{r["runs"]} runs triggered)\n'
        prompt += "\n"

    if false_triggers:
        prompt += "FALSE TRIGGERS (triggered but shouldn't have — these define the boundary):\n"
        for r in false_triggers:
            prompt += f'  - "{r["query"]}" ({r["triggers"]}/{r["runs"]} runs triggered)\n'
        prompt += "\n"

    if history:
        prompt += "PREVIOUS ATTEMPTS (do NOT repeat — try something different):\n"
        for h in history[-3:]:             # show last 3 only
            m = h.get("train_metrics", {}).get("metrics", {})
            f1 = m.get("f1", "?")
            ftr = m.get("false_trigger_rate", "?")
            prompt += f'  [iter {h["iteration"]} | F1={f1:.3f} FTR={ftr:.3f}] "{h["description"][:120]}"\n'
        prompt += "\n"

    prompt += f"""SKILL CONTENT (for context on what it does):
{skill_content[:2000]}

RULES:
- Max 1024 characters (hard limit — will be truncated otherwise)
- Third person only (NOT "I can help you...")
- Generalise from failures to categories — do NOT copy specific query keywords
- Write in imperative framing ("Use this skill when...", "Analyze...", etc.)
- Include at least one anti-case (what this skill does NOT handle)

Respond with ONLY the new description inside <new_description> tags."""

    return prompt


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def opt_loop(
    eval_set: list[dict],
    skill_path: Path,
    model: str,
    description_override: str | None = None,
    params: dict | None = None,
    verbose: bool = False,
) -> dict:
    p = {**DEFAULTS, **(params or {})}
    project_root = find_project_root()
    name, original_description, content = parse_skill_md(skill_path)
    current_description = description_override or original_description

    train_set, val_set = _stratified_split(eval_set, p["holdout_fraction"], p["seed"])
    if verbose:
        print(
            f"Split: {len(train_set)} train / {len(val_set)} val "
            f"(seed={p['seed']}, holdout={p['holdout_fraction']})",
            file=sys.stderr,
        )

    history: list[dict] = []
    best_description = current_description
    best_val_f1 = -1.0
    best_iteration = 0
    exit_reason = "max_iterations"

    for iteration in range(1, p["max_iterations"] + 1):
        if verbose:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"Iteration {iteration}/{p['max_iterations']}", file=sys.stderr)
            print(f"Description: {current_description[:120]}...", file=sys.stderr)

        # ── Evaluate train + val in one batch ─────────────────────────────
        all_queries = train_set + val_set
        all_results_raw = run_eval(
            eval_set=all_queries,
            skill_name=name,
            description=current_description,
            num_workers=p["num_workers"],
            timeout=p["eval_timeout"],
            project_root=project_root,
            runs_per_query=p["runs_per_query"],
            trigger_threshold=p["trigger_threshold"],
        )

        train_queries = {q["query"] for q in train_set}
        train_results = [r for r in all_results_raw["results"] if r["query"] in train_queries]
        val_results   = [r for r in all_results_raw["results"] if r["query"] not in train_queries]

        train_metrics = _eval_to_metrics(train_results, p)
        val_metrics   = _eval_to_metrics(val_results, p) if val_results else None

        diagnosis = train_metrics["diagnosis"]
        val_f1    = val_metrics["metrics"]["f1"] if val_metrics else train_metrics["metrics"]["f1"]
        val_ftr   = val_metrics["metrics"]["false_trigger_rate"] if val_metrics else train_metrics["metrics"]["false_trigger_rate"]

        if verbose:
            tm = train_metrics["metrics"]
            print(
                f"  Train F1={tm['f1']:.3f}  FTR={tm['false_trigger_rate']:.3f}  "
                f"P={tm['precision']:.3f}  R={tm['recall']:.3f}",
                file=sys.stderr,
            )
            if val_metrics:
                vm = val_metrics["metrics"]
                print(
                    f"  Val   F1={vm['f1']:.3f}  FTR={vm['false_trigger_rate']:.3f}  "
                    f"P={vm['precision']:.3f}  R={vm['recall']:.3f}",
                    file=sys.stderr,
                )
            print(f"  Diagnosis: {diagnosis['signal']}", file=sys.stderr)

        # Track best by validation F1
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_description = current_description
            best_iteration = iteration

        iter_record: dict = {
            "iteration": iteration,
            "description": current_description,
            "action": diagnosis["signal"],
            "train_metrics": train_metrics,
            "val_metrics": val_metrics,
            "diagnosis": diagnosis,
            "jaccard_guard_triggered": False,
        }

        # ── Convergence check ─────────────────────────────────────────────
        train_f1  = train_metrics["metrics"]["f1"]
        train_ftr = train_metrics["metrics"]["false_trigger_rate"]
        all_passed = all(r["pass"] for r in train_results)

        if all_passed:
            exit_reason = f"train_all_passed (iter {iteration})"
            history.append(iter_record)
            if verbose:
                print(f"  ✓ All train queries passed.", file=sys.stderr)
            break

        if val_f1 >= p["f1_converge"] and val_ftr <= p["ftr_converge"]:
            exit_reason = f"f1_converged (iter {iteration}, val_F1={val_f1:.3f})"
            history.append(iter_record)
            if verbose:
                print(f"  ✓ Val F1 converged at {val_f1:.3f}.", file=sys.stderr)
            break

        if iteration == p["max_iterations"]:
            history.append(iter_record)
            break

        # ── Propose new description ────────────────────────────────────────
        failed_triggers = [r for r in train_results if r["should_trigger"]  and not r["pass"]]
        false_triggers  = [r for r in train_results if not r["should_trigger"] and not r["pass"]]

        prompt = _build_improvement_prompt(
            skill_name=name,
            skill_content=content,
            current_description=current_description,
            diagnosis=diagnosis,
            failed_triggers=failed_triggers,
            false_triggers=false_triggers,
            history=history,
            train_metrics=train_metrics,
            val_metrics=val_metrics,
        )

        t0 = time.time()
        try:
            raw_output = _call_claude(prompt, model)
        except Exception as e:
            if verbose:
                print(f"  ⚠ claude -p failed: {e}", file=sys.stderr)
            history.append(iter_record)
            break

        elapsed = time.time() - t0
        match = re.search(r"<new_description>(.*?)</new_description>", raw_output, re.DOTALL)
        candidate = match.group(1).strip().strip('"') if match else raw_output.strip().strip('"')

        # Hard limit enforcement
        if len(candidate) > 1024:
            candidate = candidate[:1021] + "..."

        # ── Jaccard anti-overfit guard ─────────────────────────────────────
        failed_query_keywords = set()
        for r in failed_triggers:
            failed_query_keywords |= _extract_keywords(r["query"])

        candidate_keywords = _extract_keywords(candidate)
        jaccard = _jaccard(candidate_keywords, failed_query_keywords)
        guard_triggered = jaccard > p["anti_overfit_jaccard_max"]

        if guard_triggered:
            if verbose:
                print(
                    f"  ⚠ Jaccard guard triggered ({jaccard:.3f} > {p['anti_overfit_jaccard_max']}). "
                    f"Requesting category-level rewrite.",
                    file=sys.stderr,
                )
            # One follow-up call to generalise
            rewrite_prompt = (
                f"{prompt}\n\n---\nPrevious attempt was rejected (Jaccard keyword overlap "
                f"{jaccard:.2f} > {p['anti_overfit_jaccard_max']} — too close to failed query text):\n\n"
                f'"{candidate}"\n\n'
                "Please rewrite using CATEGORY-level language instead of the specific terms "
                "from failed queries. Respond only in <new_description> tags."
            )
            try:
                raw_output2 = _call_claude(rewrite_prompt, model)
                match2 = re.search(r"<new_description>(.*?)</new_description>", raw_output2, re.DOTALL)
                candidate = match2.group(1).strip().strip('"') if match2 else candidate
                if len(candidate) > 1024:
                    candidate = candidate[:1021] + "..."
            except Exception:
                pass  # keep original candidate if rewrite also fails

        iter_record["jaccard_guard_triggered"] = guard_triggered
        iter_record["jaccard_score"] = round(jaccard, 4)
        iter_record["proposed_description"] = candidate
        iter_record["improve_elapsed_s"] = round(elapsed, 1)
        history.append(iter_record)

        if verbose:
            print(f"  Proposed ({elapsed:.1f}s): {candidate[:120]}...", file=sys.stderr)

        current_description = candidate

    if verbose:
        print(f"\nExit: {exit_reason}", file=sys.stderr)
        print(f"Best: iter={best_iteration}  val_F1={best_val_f1:.3f}", file=sys.stderr)
        print(f"Best description: {best_description[:140]}", file=sys.stderr)

    return {
        "exit_reason": exit_reason,
        "original_description": original_description,
        "best_description": best_description,
        "best_val_f1": round(best_val_f1, 4),
        "best_iteration": best_iteration,
        "final_description": current_description,
        "iterations_run": len(history),
        "train_size": len(train_set),
        "val_size": len(val_set),
        "holdout_fraction": p["holdout_fraction"],
        "params_used": {k: p[k] for k in [
            "f1_converge", "ftr_converge", "anti_overfit_jaccard_max",
            "runs_per_query", "trigger_threshold",
        ]},
        "history": history,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="P9 — F1/FTR-driven description optimization loop with anti-overfit guard."
    )
    parser.add_argument("--skill-path",      required=True, help="Path to skill directory")
    parser.add_argument("--eval-set",        required=True, help="Path to trigger eval JSON")
    parser.add_argument("--model",           required=True, help="Model for claude -p improvement calls")
    parser.add_argument("--description",     default=None,  help="Override starting description")
    parser.add_argument("--max-iterations",  type=int, default=None, help="Override max iterations")
    parser.add_argument("--params",          default=None,  help="JSON overrides for any threshold")
    parser.add_argument("--apply",           action="store_true",
                        help="Write best_description back to SKILL.md frontmatter when done")
    parser.add_argument("--verbose",         action="store_true")
    args = parser.parse_args()

    params = json.loads(args.params) if args.params else {}
    if args.max_iterations is not None:
        params["max_iterations"] = args.max_iterations

    skill_path = Path(args.skill_path)
    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md at {skill_path}", file=sys.stderr)
        sys.exit(1)

    eval_set = json.loads(Path(args.eval_set).read_text())
    if not isinstance(eval_set, list):
        # Support both bare list and {"evals": [...]} format
        eval_set = eval_set.get("evals", eval_set)

    output = opt_loop(
        eval_set=eval_set,
        skill_path=skill_path,
        model=args.model,
        description_override=args.description,
        params=params or None,
        verbose=args.verbose,
    )

    # Optionally apply best description back to SKILL.md
    if args.apply:
        skill_md_path = skill_path / "SKILL.md"
        content = skill_md_path.read_text()
        _, old_desc, _ = parse_skill_md(skill_path)
        new_content = content.replace(old_desc, output["best_description"], 1)
        skill_md_path.write_text(new_content)
        if args.verbose:
            print(f"\nApplied best_description to {skill_md_path}", file=sys.stderr)

    print(json.dumps(output, indent=2))
    sys.exit(0 if output["best_val_f1"] >= (params.get("f1_converge") or DEFAULTS["f1_converge"]) else 1)


if __name__ == "__main__":
    main()