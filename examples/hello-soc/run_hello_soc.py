"""Hello SOC — end-to-end demonstration of the atomic-dag bridge.

Runs 3 real atoms through the LLM↔Python boundary. Each atom's body is
generated via `llm_bridge.bridge_transition` on the `do` transition, then
the atom is walked through the rest of its FSM lifecycle (check → verified
→ completed → closed) using `execute_transition` directly — those are
state-only transitions that do not need new content from the LLM.

Two providers:
  - `AnthropicProvider` (real LLM): used when `ANTHROPIC_API_KEY` is set
    and `--real` is passed. Manual runs only.
  - `RecordedProvider` (fixtures): default. Returns pre-recorded responses
    from `recorded/responses.json`. Used by CI and the test suite —
    satisfies ADR-009 D-bridge-5 ("no real LLM in the suite").

The atoms are REAL (real content, real frontmatter, real FSM transitions
through `execute_transition`). Only the provider is recorded in CI. This
satisfies both the roadmap ("end-to-end with real atoms") and D-bridge-5.

Design decision (Sprint 4.D): only `do` invokes `bridge_transition`
(regenerating the body via the LLM). The follow-up transitions `check`,
`next`, `last` are pure state changes — they call `execute_transition`
directly. Per call to the bridge: 1 LLM call. 3 atoms → 3 recorded responses.

Working directory: `main` copies the example into a fresh tmp directory by
default so the in-repo source files are never mutated. Pass `--in-place` to
run against the repo directory (only useful if you want the artifacts to
stay around for inspection — git will show the diff).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from atomic_dag.llm_bridge import AnthropicProvider, LLMProvider, bridge_transition
from atomic_dag.transitions import TransitionResult, execute_transition


class RecordedProvider:
    """Returns pre-recorded responses keyed by call order. CI-safe."""

    def __init__(self, recordings: list[str]) -> None:
        self._recordings = recordings
        self._idx = 0

    def complete(self, prompt: str, *, system: str = "") -> str:
        if self._idx >= len(self._recordings):
            raise RuntimeError(
                f"RecordedProvider exhausted after {self._idx} calls; "
                "add more recordings to responses.json"
            )
        resp = self._recordings[self._idx]
        self._idx += 1
        return resp


def load_recorded_provider(recorded_dir: Path) -> RecordedProvider:
    """Load recorded responses from `responses.json` (ordered list)."""
    data = json.loads((recorded_dir / "responses.json").read_text(encoding="utf-8"))
    return RecordedProvider(list(data["responses"]))


def run(project: Path, provider: LLMProvider) -> list[TransitionResult]:
    """Walk every atom through its full FSM lifecycle.

    Per atom:
        1. bridge_transition(do)         pending → in-progress, body via LLM
        2. execute_transition(check)     in-progress → verified  (gate passes)
        3. execute_transition(next)      verified  → completed
        4. execute_transition(last)      completed → closed

    Returns the final TransitionResult for each atom (state should be 'closed'
    when the gate passes; 'returned' if the gate rejects the atom on step 2).
    """
    atoms_dir = project / "atoms"
    (project / ".atomic-dag").mkdir(parents=True, exist_ok=True)

    finals: list[TransitionResult] = []
    for atom_file in sorted(atoms_dir.glob("*.md")):
        bridge_transition(project, atom_file, "do", provider=provider)
        r_check = execute_transition(atom_file, "check", project_root=project)
        if r_check.to_state == "verified":
            execute_transition(atom_file, "next", project_root=project)
            finals.append(execute_transition(atom_file, "last", project_root=project))
        else:
            finals.append(r_check)
    return finals


def _prepare_workdir(source: Path, in_place: bool) -> Path:
    """Return the working directory for the run.

    With `in_place=False` (default): copy the example into a fresh tmp dir
    and return that path. The in-repo source files stay clean.

    With `in_place=True`: return `source` directly. The run mutates the
    repo example — useful only for ad-hoc inspection. `git restore
    examples/hello-soc/atoms/` reverts the changes.
    """
    if in_place:
        return source
    workdir = Path(tempfile.mkdtemp(prefix="hello-soc-"))
    dst = workdir / "hello-soc"
    shutil.copytree(source, dst)
    return dst


def main(argv: list[str]) -> int:
    source = Path(__file__).parent
    in_place = "--in-place" in argv
    project = _prepare_workdir(source, in_place=in_place)

    use_real = "--real" in argv and bool(os.environ.get("ANTHROPIC_API_KEY"))
    provider: LLMProvider
    if use_real:
        provider = AnthropicProvider()
        provider_kind = "AnthropicProvider (real LLM)"
    else:
        provider = load_recorded_provider(project / "recorded")
        provider_kind = "RecordedProvider (fixtures)"

    print(f"Hello SOC — provider: {provider_kind}")
    print(f"Hello SOC — working dir: {project}")
    finals = run(project, provider)
    states = [r.to_state for r in finals]
    print(f"Hello SOC complete. Final states: {states}")
    return 0 if all(s == "closed" for s in states) else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
