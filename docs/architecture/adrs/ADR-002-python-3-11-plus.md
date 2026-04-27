# ADR-002: Python 3.11+ as the Orchestrator Language

**Status:** Accepted  
**Date:** 2026-04-20

## Context

We need a language for the deterministic side of the dual-layer architecture (ADR-001). The existing `soc_orchestrator.py` is already in Python, the project's documented dependencies (`pyyaml`, `jsonschema`, `jinja2`, `click`, `attrs`) are Python, and the team's expertise is Python. We must also pick a minimum version that gives us modern language features without excluding reasonable user environments.

## Decision

The orchestrator is written in Python 3.11 or higher. CI matrix tests against 3.11, 3.12, and 3.13.

## Consequences

**Positive.** Native `tomllib` simplifies packaging configuration. Improved error messages and meaningful traceback annotations help diagnose bugs faster. PEP 695 type parameter syntax is available in 3.12+ but we avoid it for now to keep 3.11 compatibility.

**Negative.** Users on Python 3.10 or older cannot install. This is acceptable because 3.11 was released in October 2022 and is widely available in 2026.

**Neutral.** Type hints are required throughout (mypy `--strict`) — this raises authoring effort but pays for itself in catching bugs at edit time.

## Alternatives Considered

1. **Rust.** Better runtime guarantees and performance, but team learning cost is high and the bottleneck is rarely runtime speed in this domain.
2. **Node.js / TypeScript.** Would align with the C7 Schema notation, but introduces a second toolchain and ecosystem to maintain.
3. **Python 3.10.** Considered for broader reach but loses native `tomllib`, structural pattern matching is less mature, and modern type syntax (`X | Y`) is less integrated.
