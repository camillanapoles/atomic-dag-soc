# atomic-dag-soc

Python assembler for the **Atomic-DAG framework** — a BPMN-inspired
orchestrator for LLM-produced artifacts with persistent state and multi-session
continuity.

> **Note on the term "falsifiable" used below.** This project uses
> *falsifiable* in the technical sense of Karl Popper (1934): a claim is
> falsifiable when **an experiment exists that could refute it if it were
> false**. This is an **epistemic virtue** — it means *testable*, *auditable*,
> *open to empirical refutation* — **not** "fraudable" or "can be faked". The
> project makes LLM progress claims falsifiable in the sense that every
> "phase complete" assertion passes through a deterministic Python gate that
> can refute it independently of self-reports. See `ADR-007 §0` (Sprint 3)
> and `docs/DOC-SELF-001-atomic-dag-self.md` (preamble) for the full
> treatment.

## Status

**Sprint 2 + 2.H/2.I/2.J/2.K closed** · tag [`v0.3.0-sprint2`](https://github.com/camillanapoles/atomic-dag-soc/releases/tag/v0.3.0-sprint2) · **256/256 tests passing** · global coverage **98.54%** · mypy strict clean · ruff clean.

| Module | Status | Coverage |
|---|---|---|
| `parser.py` | ✅ implemented (Sprint 1 + 2.C.1 extension) | 99% |
| `dag.py` | ✅ implemented (Sprint 1) | 100% |
| `gate.py` | ✅ implemented (Sprint 1, anti-inflation verified) | 100% |
| `fsm.py` | ✅ implemented (Sprint 1) | 100% |
| `writer.py` | ✅ implemented (Sprint 0, FM-02 mitigated) | 80% (TD-001 residual, Sprint 5) |
| `wal.py` | ✅ implemented (Sprint 1) | 100% |
| `transitions.py` | ✅ implemented (Sprint 2.C.2) | 100% |
| `cli.py` | ✅ implemented (Sprint 2.E) | 100% |

Live catalog: [`docs/STATUS.md`](docs/STATUS.md) · dashboard: [`https://camillanapoles.github.io/atomic-dag-soc/`](https://camillanapoles.github.io/atomic-dag-soc/)

## Why this exists

LLMs self-report inflated quality. The founding empirical observation: SOC V3
self-reported PQMS 9.44/10 while audit measured 4.49/10 (ratio 2.1×), with 73
of 80 referenced functions being phantoms.

This system measures quality components objectively, ignoring self-reported
scores. The `test_count_gold_ignores_self_reported_score` test in `gate.py` is
the Popperian falsification target of the claim *"this system trusts
self-reports"* — and that claim is refuted (the test passes regardless of
what `score` self-report says). In Popper's sense, the claim survived an
explicit attempt at refutation — that survival is what corroborates the
architecture, not a proof.

## Architecture

Three pillars from the source thesis (RSL manuscript v2, PQMS 9.68):

- **`state.json`** as persisted state, not memory of context
- **BPMN 2.0** as execution grammar, not just representation
- **Write-Ahead Log (WAL)** for cross-session continuity, extending ARIES
  (Mohan et al., 1992) to LLM agents

For a self-referential walkthrough — the framework documented in its own
9-block schema (Template Master, dimension D4 of the thesis) — see
[`docs/DOC-SELF-001-atomic-dag-self.md`](docs/DOC-SELF-001-atomic-dag-self.md).

For the complete operational specification read by Claude Code in every
session, see [`CLAUDE.md`](CLAUDE.md).

## Local development

```bash
# Clone and enter
git clone https://github.com/camillanapoles/atomic-dag-soc.git
cd atomic-dag-soc

# Setup environment (Python 3.11+)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Verify green state (the canonical 5-command triad)
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src
.venv/bin/python -m pytest --no-cov -q
.venv/bin/python -m pytest --cov=src/atomic_dag --cov-report=term-missing
.venv/bin/python -m pytest -v -m "not slow"
```

CI runs the same triad on Python 3.11/3.12/3.13 on every push and pull
request (the D2 dual-green gate).

## Roadmap

- ✅ **Sprint 0** — Bootstrap + atomic write (FM-02 mitigation) — tag `v0.1.0-sprint0`
- ✅ **Sprint 1** — parser + dag + gate + fsm + wal + writer — tag `v0.2.0-sprint1`
- ✅ **Sprint 2** — transitions + CLI + post-merge sync (2.H/2.I/2.J/2.K) — tag `v0.3.0-sprint2`
- 🎯 **Sprint 3** — FM-10 closure (port `streaming.py`, regression test red→green)
- ⬜ **Sprint 4** — Hello SOC + arXiv submission + Zenodo DOI
- ⬜ **Sprint 5** — Reconcile command + TD-001 writer fix + per-atom locks
- ⬜ **Sprint 6** — External empirical validation (meta-use: the framework
  manages its own development)

## License

MIT — see [LICENSE](LICENSE).
