# STATUS — `atomic-dag-soc`

> Catálogo vivo do repositório. Inventário de documentos relevantes,
> estado da sprint corrente, gates fechados e dívidas em aberto.
> Atualizado a cada fase fechada (Sprint 2 concluído em `da46621`).

## Branch corrente

- **Nome:** `main` (Sprint 2 mergeada via PR #1; 2.H/2.I/2.J/2.K mergeadas via PRs #2/#7/#3/#8 respectivamente)
- **HEAD:** `1d6217e` (merge PR #8 — 2.K Pages redirect + protocolo PR-comments oficial)
- **Tag mais recente:** `v0.3.0-sprint2` em `d9a785b` (publicada via UI; lightweight no remoto vs annotated local — D8 cosmético)
- **Commits ahead de main:** 0 (mergeada em main)
- **Pages:** publicado em `https://camillanapoles.github.io/atomic-dag-soc/` (build automático via push to main em `/docs`); root redireciona para `/dashboard.html` desde 2.K (D11 fechada)

### Fases pós-merge Sprint 2

| SHA | Fase | Quando | Mensagem |
|---|---|---|---|
| [`1d6217e`](https://github.com/camillanapoles/atomic-dag-soc/commit/1d6217e) | **2.K MERGE** | 2026-05-29 19:02Z | `Merge pull request #8 from camillanapoles/claude/sync-2k-pages-protocol` |
| [`1de7072`](https://github.com/camillanapoles/atomic-dag-soc/commit/1de7072) | **2.K** | 2026-05-29 13:32Z | `docs(2.k): Pages root redirect + protocolo PR-comments oficial` |
| [`39d020c`](https://github.com/camillanapoles/atomic-dag-soc/commit/39d020c) | **2.I MERGE** | 2026-05-29 03:54Z | `Merge pull request #7 from camillanapoles/claude/sync-status-2i` |
| [`838ce11`](https://github.com/camillanapoles/atomic-dag-soc/commit/838ce11) | **2.I** | 2026-05-28 20:01Z | `docs(2.i): sync catalog + add CLAUDE.md §3.5 MCP capabilities` |
| [`07118f6`](https://github.com/camillanapoles/atomic-dag-soc/commit/07118f6) | **2.J MERGE** | 2026-05-28 19:15Z | `Merge pull request #3 from camillanapoles/claude/add-claude-md` |
| [`2e06aaf`](https://github.com/camillanapoles/atomic-dag-soc/commit/2e06aaf) | **2.J** | 2026-05-28 19:07Z | `docs: add CLAUDE.md — session boot context for @executor` |
| [`45d2ede`](https://github.com/camillanapoles/atomic-dag-soc/commit/45d2ede) | **2.H MERGE** | 2026-05-28 18:52Z | `Merge pull request #2 from camillanapoles/claude/sync-sprint2-docs-2h` |
| [`0a85ef4`](https://github.com/camillanapoles/atomic-dag-soc/commit/0a85ef4) | **2.H** | 2026-05-28 03:14Z | `docs(2.h): sync STATUS + WAL_HUMANO + dashboard reflecting Sprint 2 closed` |

## Sprint 2 — 11 commits + 1 merge commit em `main` (todos verdes na matriz 3.11/3.12/3.13)

| SHA | Fase | Mensagem |
|---|---|---|
| [`da46621`](https://github.com/camillanapoles/atomic-dag-soc/commit/da46621) | **2.G MERGE** | `Merge pull request #1 from camillanapoles/claude/setup-atomic-dag-soc-K53NI` |
| [`d9a785b`](https://github.com/camillanapoles/atomic-dag-soc/commit/d9a785b) | **2.F** | `chore(2.f): raise cov-fail-under 80→95 + TECHNICAL_DEBT TD-004 FM-01` |
| [`df90620`](https://github.com/camillanapoles/atomic-dag-soc/commit/df90620) | **2.E** | `feat(cli): wire transition command — execute_transition + --json + exit codes` |
| [`086b823`](https://github.com/camillanapoles/atomic-dag-soc/commit/086b823) | **2.D** | `test(transitions): adversarial battery — SIGKILL ×50, perf, concurrency` |
| [`04db5fa`](https://github.com/camillanapoles/atomic-dag-soc/commit/04db5fa) | STATUS | `docs(status): catalog 2.C.2 — execute_transition skeleton` |
| [`1d5f18f`](https://github.com/camillanapoles/atomic-dag-soc/commit/1d5f18f) | **2.C.2** | `feat(transitions): execute_transition skeleton + happy path` |
| [`267e06f`](https://github.com/camillanapoles/atomic-dag-soc/commit/267e06f) | orientação | `docs(status): operator orientation artifacts — catalog, dashboard, WAL` |
| [`45161a8`](https://github.com/camillanapoles/atomic-dag-soc/commit/45161a8) | **2.C.1** | `feat(parser): replace_state_in_frontmatter — surgical state mutation` |
| [`1177c2a`](https://github.com/camillanapoles/atomic-dag-soc/commit/1177c2a) | **2.B** | `docs(api): document transitions module public protocol` |
| [`c40de0e`](https://github.com/camillanapoles/atomic-dag-soc/commit/c40de0e) | **2.A fix** | `docs(adr): amend ADR-006 — restore ADR-003 §Lesson 3 ordering + 3 clarifs` |
| [`e37bf56`](https://github.com/camillanapoles/atomic-dag-soc/commit/e37bf56) | CI infra | `ci(workflow): trigger on push:claude/** + manual dispatch (D1)` |
| [`dbcb0ce`](https://github.com/camillanapoles/atomic-dag-soc/commit/dbcb0ce) | **2.A** | `docs(adr): ADR-006 sprint-2-refactor transitions specification` |

Suite final: 256/256 verdes. Cov global: 98.54%. Tag `v0.3.0-sprint2` em `d9a785b`.
Autoria uniforme: `Camilla Napoles <cnmfs@cesar.school>`.

## Gates fechados (validação canônica = CI 3/3 nas matrizes 3.11/3.12/3.13)

| Fase | SHA | Critério | CI |
|---|---|---|---|
| 2.A — ADR-006 transitions spec | `dbcb0ce` | ADR commitado com D1-D8+D11+DA-1/2/3 fixados | ✅ verde |
| 2.A fix — D1 ordering restored | `c40de0e` | Address 4 Copilot review comments | ✅ verde |
| 2.B — public protocol docs | `1177c2a` | `docs/api/transitions.md` com contrato observável | ✅ verde |
| 2.C.1 — `replace_state_in_frontmatter` | `45161a8` | Adição pura a `parser.py`, 27 herdados + 15 novos verdes | ✅ verde |
| 2.C.2 — execute_transition skeleton | `1d5f18f` | `transitions.py` 100% cov, 30 testes verdes, idempotência §5 antes do FSM | ✅ verde |
| 2.D — adversarial battery | `086b823` | SIGKILL ×50 α.3 determinístico (50/50 in-critical-window, zero D11 violation); perf p99 < 100ms; concurrency 4-proc | ✅ verde |
| 2.E — CLI wire | `df90620` | `atomic-dag transition` com `--json` e exit codes 0/1/2 (D6); 12 herdados + 12 novos verdes | ✅ verde |
| 2.F — cov bump + TD-004 | `d9a785b` | `cov-fail-under` 80→95 (gate atingido com global 98.54%); TD-004 FM-01 documentada | ✅ verde |
| 2.G — merge to main | `da46621` | PR #1 mergeado `--no-ff`; tag `v0.3.0-sprint2` em `d9a785b` reachable de main | ✅ verde |
| 2.H — sync docs pós-Sprint-2 | `45d2ede` | STATUS+WAL+dashboard refletindo Sprint 2 closed; escopo docs-only; CI 6/6 verde (D2 ok) | ✅ verde |
| 2.J — CLAUDE.md boot context | `07118f6` | Layer-1 system instructions (166 linhas, ~1.6K tokens); carrega em toda sessão @executor; protocolo nicknames + canais Discussions; escopo docs-only; CI 6/6 verde (D2 ok, flake D5 em 3.13 resolvido em rerun) | ✅ verde |
| 2.I — sync catalog + §3.5 MCP | `39d020c` | HEAD bump da46621→07118f6; CLAUDE.md em catálogo; TD-002 Resolved; §3.5 documenta toolsets MCP + fallbacks; D9+D10 registradas; CI 6/6 verde D2 sem flake | ✅ verde |
| 2.K — Pages root redirect + protocolo PR-comments oficial | `1d6217e` | docs/index.html meta-refresh; CLAUDE.md §3 fluxo híbrido Discussions+PR-comments oficial; D11 fechada; D12 registrada (proxy executor); CI 6/6 verde D2 sem flake | ✅ verde |

## Próximo gate — Sprint 3 (FM-10 / TD-003)

Sprint 2 fechada em `da46621` (merge PR #1). Próxima sprint endereça **FM-10
closure** — `tick_streaming` não chama `advance_cursor`, RPN=162 (highest open
no FMEA SOC V4). TD-003 registrado para fechamento em Sprint 3 desde Sprint 0.

Pré-condição descoberta na derivada de caminho pós-Sprint-2: o port de
`tick_streaming`/`advance_cursor` planejado originalmente para Sprint 1 não
ocorreu. Sprint 3 portará primeiro, depois implementará o fix, depois o
regression test red→green.

Fases planejadas (espelham Sprint 2): 3.A ADR-007 → 3.B api/streaming.md →
3.C.1/3.C.2 implementação → 3.D adversarial battery → 3.E CLI wire → 3.F cov +
TD-003 Resolved → 3.G merge --no-ff + tag v0.4.0-sprint3.

Cursor de partida: `FROM 1d6217e` (HEAD main pós-2.K merge + 2.L expandida com DOC-SELF-001 / README sync / CLAUDE.md §1 nota terminológica).

## Dívidas registradas (pós-Sprint 2)

| ID | Origem | Descrição | Estado |
|---|---|---|---|
| **D1** | `e37bf56` | `ci.yml` estendido (push:claude/** + workflow_dispatch + concurrency) fora da sequência planejada de 15 commits | aberta |
| **D2** | observação pós-`e37bf56` | concurrency group não deduplica push:claude/** vs pull_request:synchronize (refs divergentes); dois runs verdes redundantes por push | aberta |
| ~~D3~~ | ADR-006 (não-citação) | citação fraca de §Lesson 1 em `transitions.md §9` e ADR-006 header | **fechada em `45161a8`** |
| **D4** | claude GitHub App | check falha sem companion workflow no repo (`@claude` mentions disparam app sem rota) | descartável (opção C: ignorar conscientemente) |
| **D5** | Phase 2.D | `ci.yml` lacks `-m "not slow"`; slow tests rodam em CI até filter ser adicionado | aberta |
| **D6** | copilot GitHub App | check falha sem companion workflow (mesma classe que D4 mas para Copilot) | descartável (opção C) |
| **D7** | Phase 2.G | tag `v0.3.0-sprint2` push pendente (HTTP 403 via git proxy local) | **fechada via UI**: tag publicada em `d9a785b` no remoto (lightweight) |
| **D8** | Phase 2.G | tag remota `v0.3.0-sprint2` é lightweight; precedente (`v0.1.0-sprint0`, `v0.2.0-sprint1`) é annotated | aberta, cosmética (não-bloqueante) |
| **D9** | Phase 2.J (descoberta no merge) | `git push origin --delete claude/add-claude-md` retornou HTTP 403 via local_proxy (mesmo padrão D7); branch remota não-deletada | aberta, cosmética |
| **D10** | Phase 2.I (descoberta no ATO 1) | MCP `github-mcp-server` do @executor está no toolset core (52 tools, zero `discussion_*`); ativação de `discussions` é config do harness (`settings.json` `mcpServers` → endpoint `/mcp/x/all`), fora do escopo runtime do @executor. CLAUDE.md §3.5 documenta servidor esperado + fallback paste manual via @cnmfs. | aberta, cosmética operacional |
| **D11** | Phase 2.I (descoberta pós-merge) | Pages habilitado (`Settings → Pages → Source: main /docs`); root URL `https://camillanapoles.github.io/atomic-dag-soc/` retornava 404 sem `index.html` em `/docs` | **fechada em 2.K**: `docs/index.html` criado com meta-refresh redirect para `dashboard.html` |
| **D12** | Phase 2.I (descoberta no ATO 4) | `local_proxy` do @executor filtra outbound para `*.github.io` (`x-deny-reason: host_not_allowed`); @executor não verifica Pages diretamente | aberta, cosmética operacional (config do harness, mesma classe que D7/D9/D10); fallback: @orquestrador verifica via conector |
| **D13** | Phase 2.I (descoberta pós-2.K por releitura) | Termo "falsificável" usado em CLAUDE.md §1 e README sem nota terminológica Popperiana anexa; risco de má leitura indutora de erro em pontos de boot/entrada (humano externo ou LLM externo lendo o repo via clone/busca) | **fechada em 3.A**: closure durável em ADR-007 §0 (autoridade); parcial inicial em 2.L (CLAUDE.md §1 + README + DOC-SELF-001) |
| **A4** | Phase 2.I (descoberta pós-2.K por releitura) | README.md em main defasado: "Sprint 1 in progress 3/4 modules / 135 tests" vs realidade `1d6217e` (Sprint 2.K closed / 9 / 256) | **fechada em 2.L**: README reescrito integralmente |
| **I-DASH** | Phase 2.M | Toda fase que fecha DEVE bumpar `dashboard.html` + `STATUS.md` no mesmo PR; checkbox ☐→☑ do mapa de produção é parte do gate da fase; @orquestrador valida via conector. Automação N2 (`scripts/build_dashboard.py`) é entregável Sprint 4. | ativa |

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
| `ADR-007-sprint-3-fm10-streaming.md` | Especificação completa do módulo `streaming` (Sprint 3, FM-10 closure): §0 nota terminológica Popperiana (closure durável D13), D1-D8 (ordem operação, StreamEvent/TickResult, idempotência, WAL schema, exit codes, concorrência, regression invariant D7 = critério Popperiano-mestre, bateria adversarial), DA-1/2/3 resolvidos, 4 alternativas rejeitadas | vigente, **autoridade** |

### Especificações de API (`docs/api/`)

| Path | Descrição | Estado |
|---|---|---|
| `transitions.md` | Contrato observável de `execute_transition` + `TransitionResult` (Phase 2.B) | vigente |
| `streaming.md` | Contrato observável de `tick_streaming` + `advance_cursor` + `StreamEvent` + `TickResult` + `StreamCursorMismatchError` + WAL schema `streaming_tick` + exit codes 0/1/2 (Phase 3.B) | vigente |

### Planejamento (`docs/`)

| Path | Descrição | Estado |
|---|---|---|
| `PLANO_ENGENHARIA_SOFTWARE_V1.md` | Spec de engenharia para Sprints 2-6 (§3.3 RF-2.1-6, §6.2 sequence, §8.1 fases 2.A-2.H) | vigente, **canônica** |
| `PLANO_CONTINUIDADE_FRACTAL_v1.md` | Plano fractal inicial (histórico) | histórico |
| `PLANO_CONTINUIDADE_FRACTAL_v2.md` | Plano fractal corrigido (referência) | vigente |
| `PRE_EXECUCAO_PLANO_CONTINUIDADE_v2.md` | Checklist meta-gate pré-execução | vigente |
| `PLANO_CONTINUIDADE_FRACTAL_v3.md` | (não-presente no repo) | **DEPRECADO referencialmente** — ADR-006 deprecia explicitamente este artefato carregando D3 inválido e nomenclatura `state.json` |
| `STATUS.md` | Este arquivo: catálogo vivo | vigente |
| `dashboard.html` | Painel estático offline — programa completo Sprint 0→6 (5W1H + expectativa + mapa de produção navegável por Sprint) + timeline + dívidas + invariante I-DASH | vigente |
| `WAL_HUMANO.md` | WAL traduzido para narrativa humana (decisões + correções + lições) | vigente |
| `DOC-SELF-001-atomic-dag-self.md` | Documentação auto-referente — Atomic-DAG explicado *como* um ATÔMICO do próprio Atomic-DAG (9 blocos Template Master, frontmatter válido, cursor I-WAL, ancorado em main@1d6217e); demonstra D4 por instanciação; ponte pedagógica para Sprint 6 / US-07 (meta-uso) — quando `.atomic-dag/state.json` gerenciar este arquivo como instância operacional | vigente, **artefato pedagógico** |

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
| `CLAUDE.md` | Layer-1 system instructions lido pelo Claude Code no boot de toda sessão; nicknames + canais Discussions + fluxo + mandatos M1-M5 + invariantes + capacidades MCP (§3.5) + mapa de fontes (166→~210 linhas após §3.5) | vigente, **boot context** |
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
