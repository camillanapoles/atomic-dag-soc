# Technical Debt Register

This file tracks known debts in the codebase. Each entry is a fact, not an aspiration. "We should add tests later" is not a valid entry; "function X has 80% coverage because lines 89-94 require mocked OSError; planned for Sprint 1" is.

## Active Debts

### TD-001: Coverage gap in `writer.py` lines 89-94

**Created:** 2026-04-20 (Sprint 0)  
**Module:** `src/atomic_dag/writer.py`  
**Description:** The error-recovery branch (cleanup of orphan temp files when `os.write` or `os.fsync` raises) is not exercised by any test. Coverage in this module is 80% because of these five lines.  
**Why deferred:** Exercising this path requires mocking `os.write` or `os.fsync` to raise mid-operation. The setup is non-trivial and adds little value at Sprint 0 given that the happy path and the SIGKILL path are both proven.  
**Plan:** Sprint 1 — write a test using `unittest.mock` to inject failures and verify orphan-temp-file cleanup.  
**Owner:** Sprint 1 lead.

### TD-002: Stub modules awaiting implementation

**Created:** 2026-04-20 (Sprint 0)  
**Modules:** `src/atomic_dag/parser.py`, `dag.py`, `gate.py`, `cli.py`  
**Description:** Four modules expose only public interfaces and `NotImplementedError` placeholders. They are excluded from coverage measurement via `pyproject.toml` `[tool.coverage.run] omit`.  
**Why deferred:** Sprint 0 is infrastructure bootstrap. Implementing logic here would violate the sprint scope.  
**Plan:** Sprint 1 — implement `parse_atom`, `compute_dag_levels`, `validate_gate`, and the real CLI commands. Remove each from the `omit` list as it is implemented.  
**Owner:** Sprint 1 lead.

### TD-003: No FMEA regression test for FM-10 yet

**Created:** 2026-04-20 (Sprint 0)  
**Description:** FM-10 (`tick_streaming` not calling `advance_cursor`, RPN=162) is the highest-RPN open item from the SOC V4 FMEA. We have not yet written the regression test that would fail without the fix and pass with it.  
**Why deferred:** The `tick_streaming` and `advance_cursor` functions are part of the orchestrator that will be ported in Sprint 1. The regression test must follow the port.  
**Plan:** Sprint 3 (according to PLANO_EXECUCAO_ENGENHARIA.md §6.4) — port the orchestrator code, write `tests/test_fm10_regression.py`, fix the coupling, verify the test goes from red to green.  
**Owner:** Sprint 3 lead.

### TD-004: FM-01 — concurrent WAL writers (mitigated, not closed)

**Status:** mitigated  
**Sprint origem:** 2 (ADR-006 §D8)  
**Sprint fechamento previsto:** 5 (per-atom locking)  
**Descrição:** múltiplos processos chamando `wal.log_event` simultaneamente
no mesmo `wal.jsonl`. Mitigação atual via `O_APPEND` semantics + payload
< PIPE_BUF (4096 bytes) → atomic line append no POSIX. Concurrent
transitions em átomos distintos: seguro (testado em
`test_transitions_concurrency.py` Phase 2.D, 4 procs × 4 átomos, 4 WAL
lines parsáveis). Concurrent transitions no MESMO átomo: fora do contrato
Sprint 2 (`transitions.md §8`).

**Fechamento:** Sprint 5 introduz lock per-atom + reconcile command.

## Resolved Debts

_None yet — this is the first sprint._

## Conventions

- New entries get the next available `TD-NNN` identifier.
- An entry stays in "Active" until the listed plan is executed and the resolution is confirmed by passing tests.
- When resolved, move the entry to "Resolved Debts" with a closing date and a one-line note about how it was fixed.
- Never delete entries — the history of past debts is itself useful.
