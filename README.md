# atomic-dag-soc

> Document-in-DAG-Flow: BPMN-inspired modular orchestration for LLM-produced artifacts.

[![CI](https://github.com/OWNER/atomic-dag-soc/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/atomic-dag-soc/actions/workflows/ci.yml)

## What is this?

`atomic-dag-soc` is a Python package that enforces the **SOC V4 (Sistema de Orquestração Cognitiva)** protocol for LLM-produced artifacts. It treats each markdown document as an atomic unit in a Directed Acyclic Graph (DAG), with a formal finite-state machine governing its lifecycle and a quality gate (gold ≥ 9/10, PQMS ≥ 9.5, VVV ≥ 0.95) controlling advancement.

The key insight: **documentation is code when paired with a deterministic validator**. The LLM writes content. This orchestrator audits, enforces invariants, detects self-evaluation inflation, and propagates state — things an LLM alone cannot be trusted to do reliably.

## Status

**Alpha — Sprint 0 (infrastructure bootstrap).** Not yet functional. See `docs/architecture/` for the execution roadmap.

## Development

```bash
git clone https://github.com/OWNER/atomic-dag-soc.git
cd atomic-dag-soc
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Verify installation
ruff check src tests
mypy src
pytest
```

## License

MIT — see [LICENSE](LICENSE).
