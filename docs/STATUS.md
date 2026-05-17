# STATUS — `atomic-dag-soc`

> Catálogo vivo do repositório. Inventário de documentos relevantes,
> estado da sprint corrente, gates fechados e dívidas em aberto.
> Atualizado a cada fase do Sprint 2.

## Branch corrente

- **Nome:** `claude/setup-atomic-dag-soc-K53NI`
- **Base:** `2bfecc2f` (`main`)
- **HEAD:** `45161a8`
- **Commits ahead de main:** 5

## Os 5 commits do Sprint 2 (do mais recente ao mais antigo)

| SHA | Fase | Data UTC | Mensagem |
|---|---|---|---|
| [`45161a8`](https://github.com/camillanapoles/atomic-dag-soc/commit/45161a8) | **2.C.1** | 2026-05-17 06:34 | `feat(parser): replace_state_in_frontmatter — surgical state mutation` |
| [`1177c2a`](https://github.com/camillanapoles/atomic-dag-soc/commit/1177c2a) | **2.B** | 2026-05-17 05:38 | `docs(api): document transitions module public protocol` |
| [`c40de0e`](https://github.com/camillanapoles/atomic-dag-soc/commit/c40de0e) | **2.A fix** | 2026-05-17 05:21 | `docs(adr): amend ADR-006 — restore ADR-003 §Lesson 3 ordering + 3 clarifs` |
| [`e37bf56`](https://github.com/camillanapoles/atomic-dag-soc/commit/e37bf56) | **CI infra** | 2026-05-17 05:13 | `ci(workflow): trigger on push to claude/** + manual dispatch, dedupe via concurrency` |
| [`dbcb0ce`](https://github.com/camillanapoles/atomic-dag-soc/commit/dbcb0ce) | **2.A** | 2026-05-17 04:27 | `docs(adr): ADR-006 sprint-2-refactor transitions specification` |

Autoria uniforme: `Camilla Napoles <cnmfs@cesar.school>`.

## Gates fechados (validação canônica = CI 3/3 nas matrizes 3.11/3.12/3.13)

| Fase | SHA | Critério | CI |
|---|---|---|---|
| 2.A — ADR-006 transitions spec | `dbcb0ce` | ADR commitado com D1-D8+D11+DA-1/2/3 fixados | ✅ verde |
| 2.A fix — D1 ordering restored | `c40de0e` | Address 4 Copilot review comments | ✅ verde |
| 2.B — public protocol docs | `1177c2a` | `docs/api/transitions.md` com contrato observável | ✅ verde |
| 2.C.1 — `replace_state_in_frontmatter` | `45161a8` | Adição pura a `parser.py`, 27 herdados + 15 novos verdes | ✅ verde |

## Próximo gate — 2.C.2 (aguardando)

`feat(transitions): execute_transition skeleton + happy path` — primeira escrita em `src/atomic_dag/transitions.py`. Cursor de partida: `FROM 45161a8`. Trava I8: plano de tradução do orquestrador + "go 2.C.2" explícito antes de qualquer linha de código.

## Dívidas registradas (destino MPF_LOG no commit 2.H)

| ID | Origem | Descrição | Estado |
|---|---|---|---|
| **D1** | `e37bf56` | `ci.yml` estendido (push:claude/** + workflow_dispatch + concurrency) fora da sequência planejada de 15 commits | aberta |
| **D2** | observação pós-`e37bf56` | concurrency group não deduplica push:claude/** vs pull_request:synchronize (refs divergentes); dois runs verdes redundantes por push | aberta |
| ~~D3~~ | ADR-006 (não-citação) | citação fraca de §Lesson 1 em `transitions.md §9` e ADR-006 header | **fechada em `45161a8`** |

## Catálogo de documentos

### Arquitetura e decisões (`docs/architecture/adrs/`)

| Path | Descrição (1 linha) | Estado |
|---|---|---|
| `ADR-001-dual-layer-llm-python.md` | Camadas LLM ⊥ Python | vigente |
| `ADR-002-python-3-11-plus.md` | Constraint de toolchain Python ≥ 3.11 | vigente |
| `ADR-003-sprint1-lessons.md` | Três lições do Sprint 1: omit honesto, delta=0.5, ordem `parse→gate→fsm→write→wal` | vigente, **autoridade** |
| `ADR-004-atomic-writes.md` | `writer.py` tmp+fsync+rename (FM-02 fechado) | vigente |
| `ADR-005-zenodo-timing-strategy.md` | Defer DOI público até Sprint 4 (Hello SOC + arXiv) | vigente |
| `ADR-006-sprint-2-refactor-transitions.md` | Especificação completa do módulo `transitions`: D1, D2, D4-D8, D11, DA-1/2/3, D3 rejeitado | vigente, **autoridade** |

### Especificações de API (`docs/api/`)

| Path | Descrição | Estado |
|---|---|---|
| `transitions.md` | Contrato observável de `execute_transition` + `TransitionResult` (Phase 2.B) | vigente |

### Planejamento (`docs/`)

| Path | Descrição | Estado |
|---|---|---|
| `PLANO_ENGENHARIA_SOFTWARE_V1.md` | Spec de engenharia para Sprints 2-6 (§3.3 RF-2.1-6, §6.2 sequence, §8.1 fases 2.A-2.H) | vigente, **canônica** |
| `PLANO_CONTINUIDADE_FRACTAL_v1.md` | Plano fractal inicial (histórico) | histórico |
| `PLANO_CONTINUIDADE_FRACTAL_v2.md` | Plano fractal corrigido (referência) | vigente |
| `PRE_EXECUCAO_PLANO_CONTINUIDADE_v2.md` | Checklist meta-gate pré-execução | vigente |
| `PLANO_CONTINUIDADE_FRACTAL_v3.md` | (não-presente no repo) | **DEPRECADO referencialmente** — ADR-006 deprecia explicitamente este artefato carregando D3 inválido e nomenclatura `state.json` |
| `STATUS.md` | Este arquivo: catálogo vivo | vigente |
| `dashboard.html` | Painel estático offline com roadmap + timeline + dívidas | vigente |
| `WAL_HUMANO.md` | WAL traduzido para narrativa humana (decisões + correções + lições) | vigente |

### Knowledge base (`knowledge/`)

17 arquivos canônicos referenciados em ADRs e planejamento. Usados como fonte de fundamentação, não modificados durante sprints técnicos.

| Path | Descrição |
|---|---|
| `MANUSCRITO_ATOMIC_DAG_RSL_V2_CORRIGIDO.md` | RSL pós-revisão adversarial, PQMS 9.68 |
| `HOLISTIC_ITERATIVE_QUALITY_MODULE_v1.0.md` | HIQM: definição canônica de PMQ, base de `gate.py` |
| `FRAMEWORK_FRACTAL_ANALYSIS_MERGED.md` | Gold standard PTDISLGEOX, princípio anti-inflação |
| `FUNDAMENTACAO_MATEMATICA_INTEGRADA_V1.md` | Modelo fractal de convergência, delta characteristics |
| `PESQUISA_VALIDACAO_METODO_2026_V1.md` | Triângulo doutoral — validação |
| `LLM_PVM_FRAMEWORK_V1.md` | Arquitetura DAW-OS / LLM Process Virtual Machine |
| `WINDOW_PROTOCOL_SPEC_V1.md` | Protocolo de janela de contexto |
| `CONTEXT_ENGINEERING_MODULE-v8.0.md` | Engenharia de contexto v8 |
| `STRATEGIC-ACTION-ENGINE-v4.0.md` | Escopo de comandos |
| `PHILOSOPHICAL-ENGINE-v3.0.md` | PEII — 7 fases |
| `decision-topology-protocol.md` | Base de ordenação topológica |
| `DTP-VECTOR.md` | DTP vetorial |
| `run_gate.py`, `eval_trigger_metrics.py`, `score_description.py`, `skill_gate.py`, `opt_loop.py` | Implementações de gate referenciadas em `gate.py` |

### Raiz e infraestrutura

| Path | Descrição | Estado |
|---|---|---|
| `README.md` | README do projeto | vigente |
| `TECHNICAL_DEBT.md` | Registro de dívidas técnicas (TD-001 writer 89-94; TD-002 stubs; TD-003 FM-10 deferido Sprint 3) | vigente |
| `pyproject.toml` | Config Python: deps, pytest, ruff, mypy, coverage (omit=[]) | vigente |
| `.github/workflows/ci.yml` | CI: ruff + mypy strict + pytest, matriz 3.11/3.12/3.13 (ver Dívidas D1, D2) | vigente |

## Mandato operacional (referência rápida)

- **`AGENT_MANDATE_SPRINT2.md`** (operador) — PARTES 1-6: invariantes I1-I8, decisões D1-D11 travadas, lições L1-L3, protocolo de gate, dívidas, próxima fase. PARTE 5 atualizada: I4 herdados = 27 (não 26), testes 2.C.1 = 15 (S27-S41), γ.0 git-identity oficializado, regra de pragma não-genérico ativa.

## Convenções deste catálogo

- "vigente" = referência ativa para decisões correntes
- "histórico" = mantido para auditoria, não-vigente
- "deprecado" = explicitamente substituído; uso desencorajado
- "autoridade" = a fonte de verdade quando há conflito entre documentos
- **canônica** = documento de spec contra o qual outras peças são validadas
