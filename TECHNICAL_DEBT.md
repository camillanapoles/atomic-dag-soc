# Technical Debt Register

This file tracks known debts in the codebase. Each entry is a fact, not an aspiration. "We should add tests later" is not a valid entry; "function X has 80% coverage because lines 89-94 require mocked OSError; planned for Sprint 1" is.

## Active Debts

### TD-001: Coverage gap in `writer.py` lines 89-94

**Created:** 2026-04-20 (Sprint 0)
**Module:** `src/atomic_dag/writer.py`
**Description:** The error-recovery branch (cleanup of orphan temp files when `os.write` or `os.fsync` raises) is not exercised by any test. Coverage in this module is 80% because of these five lines.
**Why deferred:** Exercising this path requires mocking `os.write` or `os.fsync` to raise mid-operation. The setup is non-trivial and adds little value at Sprint 0 given that the happy path and the SIGKILL path are both proven.
**Plan (atualizado 2026-05-28):** previsão original Sprint 1 NÃO executada; reprogramado para Sprint 5 junto com `reconcile` command. `writer.py` FM-02 já fechado por `write_atomic` (ADR-004); a dívida residual é apenas o branch error-recovery (89-94) que precisa de mock de OSError. Cov 80% mantida; agregado ponderado puxa 98.54%, não bloqueia M3 (≥95% global).
**Owner:** Sprint 5 lead.

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

### TD-002 (Resolved 2026-05-28): Stub modules implemented

**Created:** 2026-04-20 (Sprint 0)
**Resolved:** 2026-05-28 (Sprint 2 close + 2.J)
**Modules:** `src/atomic_dag/parser.py`, `dag.py`, `gate.py`, `cli.py`
**Resolution:** todos os 4 módulos implementados ao longo de Sprint 1 e Sprint 2:
- `parser.py` — Sprint 1; extensão `replace_state_in_frontmatter` em 2.C.1 (`45161a8`)
- `dag.py` — Sprint 1
- `gate.py` — Sprint 1
- `cli.py` — Sprint 2.E `df90620` (wire `transition` command + `--json` + exit codes)

Nenhum permanece em `[tool.coverage.run] omit` no `pyproject.toml`. Coverage global 98.54% em main `07118f6`, com `cli.py` 100%, `transitions.py` 100%, `parser.py` 99%, `writer.py` 80% (TD-001 residual). Suite 256/256 verde.

### TD-003 (Resolved 2026-05-31): FMEA regression test for FM-10 — coupling fixed and proven

**Created:** 2026-04-20 (Sprint 0)
**Resolved:** 2026-05-31 (Sprint 3 — fases 3.C + 3.D)
**Module:** `src/atomic_dag/streaming.py`, `tests/test_fm10_regression.py`
**Resolution:** FM-10 (RPN=162, highest-RPN open item do FMEA SOC V4) fechado:
- **Port + fix (3.C, PR #14):** `streaming.py` implementado; `tick_streaming`
  invoca `advance_cursor` (passo 5, ordem ADR-007 D1). Par Popperiano red→green
  observável no histórico: `1049649` (sem coupling, regressão RED local) →
  `64c3f5e` (coupling ativo, GREEN).
- **Regression test (3.C):** `tests/test_fm10_regression.py` — dois mecanismos
  complementares: comportamental (cursor avança no disco após tick) + estrutural
  (spy confirma `advance_cursor` invocado). Roda em todo push (CI 3-matriz).
- **Prova adversarial (3.D, PR #15):** `test_streaming_sigkill.py` α.3
  determinístico — 50/50 SIGKILL na janela crítica `advance_cursor`→`log_event`,
  zero violações WAL-ahead-of-disk (D7/D11). Perf p99 2.72ms. Concorrência
  4-proc D7-consistente.
**Critério Popperiano-mestre satisfeito:** a afirmação "FM-10 fechada" é
falsificável e ativamente testada — qualquer refactor que desacople
`tick_streaming` de `advance_cursor` falha o CI antes de chegar a `main`.


## Conventions

- New entries get the next available `TD-NNN` identifier.
- An entry stays in "Active" until the listed plan is executed and the resolution is confirmed by passing tests.
- When resolved, move the entry to "Resolved Debts" with a closing date and a one-line note about how it was fixed.
- Never delete entries — the history of past debts is itself useful.
