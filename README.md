# atomic-dag-soc

Python assembler for the **Atomic-DAG framework** — a BPMN-inspired orchestrator for LLM-produced artifacts with persistent state and multi-session continuity.

## Status

Sprint 1 in progress (3/4 modules complete):

| Module | Status | Coverage |
|--------|--------|----------|
| `parser.py` | ✅ Implemented | 98% |
| `dag.py` | ✅ Implemented | 100% |
| `gate.py` | ✅ Implemented (anti-inflation verified) | 100% |
| `cli.py` | 🔄 In progress | — |

**135/135 tests passing**, mypy strict clean, ruff clean.

## Why this exists

LLMs self-report inflated quality. The founding empirical observation: SOC V3 self-reported PQMS 9.44/10 while audit measured 4.49/10 (ratio 2.1×), with 73 of 80 referenced functions being phantoms.

This system measures quality components objectively, ignoring self-reported scores. The `test_count_gold_ignores_self_reported_score` test in `gate.py` is the Popperian falsification of "this system trusts self-reports" — and it passes.

## Architecture

Three pillars from the source thesis (RSL, manuscript v2 PMQ 9.68):

- **`state.json`** as persisted state, not memory of context
- **BPMN 2.0** as execution grammar, not just representation
- **Write-Ahead Log (WAL)** for cross-session continuity, extending ARIES (Mohan et al., 1992) to LLM agents

See [`CLAUDE.md`](CLAUDE.md) for the complete architectural specification.

## Local development

```bash
# Clone and enter
git clone <this-repo-url>
cd atomic-dag-soc

# Setup environment (Python 3.11+)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Verify green state
python scripts/verify_setup.py
ruff check src tests
mypy src
pytest -v
```

## Roadmap

- ✅ Sprint 0: Bootstrap + atomic write (FM-02 mitigation)
- 🔄 Sprint 1: parser + dag + gate + CLI
- ⬜ Sprint 2: Transitions + WAL emission
- ⬜ Sprint 3: FM-10 closure
- ⬜ Sprint 4: LLM bridge + Hello SOC
- ⬜ Sprint 5: Concurrency (per-atom locks) + reconcile
- ⬜ Sprint 6: External empirical validation

## License

MIT — see [LICENSE](LICENSE).
