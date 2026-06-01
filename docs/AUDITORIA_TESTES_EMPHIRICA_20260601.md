# Auditoria Empírica — atomic-dag-soc

> Data: 2026-06-01  
> Auditor: Kimi Code CLI (agente externo, sem viés de confirmação)  
> Mandato: analisar testes, documentação e implementação; comparar doc↔código; propor ajustes  
> Método: epirismo puro — leitura de docs, leitura de código, execução de testes, comparação

---

## 1. O QUE É ESTE PROJETO (compreensão empírica)

**atomic-dag-soc** é um *assembler Python* que implementa uma arquitetura de orquestração de artefatos produzidos por LLMs (Large Language Models), com persistência formal multi-sessão e validação objetiva de qualidade.

### 1.1 Observação fundadora (origem empírica)

O projeto nasce de uma observação mensurável: o sistema **SOC V3** auto-reportou PQMS (Progressive Multi-dimensional Quality Score) de **9.44/10**, mas uma auditoria independente mediu **4.49/10** — inflação de **2.1×**. Das 80 funções referenciadas pelo SOC V3, **73 eram phantoms** (não existiam no código). Esta observação não é narrativa; é dado bruto que motiva toda a arquitetura.

### 1.2 Proposta de valor central

Tornar **falsificáveis** (sentido Popperiano, 1934: testáveis, passíveis de refutação empírica) todas as alegações de progresso de LLMs. O sistema não confia em auto-relatos. Ele produz **evidência observável em disco** que pode ser auditada independentemente.

### 1.3 Interface fundamental

- **Entrada**: átomos markdown com frontmatter YAML (`*.md`)
- **Estado**: `state.json` + Write-Ahead Log (`.atomic-dag/wal.jsonl`)
- **Processamento**: Python determinístico (parser → gate → FSM → writer → WAL)
- **Saída**: átomos em novos estados + log estruturado auditável

### 1.4 Arquitetura (5 camadas concêntricas, Hexagonal/Clean)

```
Camada 1 — Domínio puro: Atom, GateResult, WALEntry (frozen dataclasses)
Camada 2 — Operações puras: parser, dag, gate, fsm (determinísticas, sem I/O além de leitura)
Camada 3 — Persistência: writer, wal, transitions (efeito colateral controlado, atômico)
Camada 4 — Adapters: LLMBridge (Sprint 4 — ainda não implementado)
Camada 5 — Aplicação: CLI Click (status, validate, next, transition, stream)
```

Dependências apontam sempre para dentro. Grafo de importação é um DAG (sem ciclos).

### 1.5 Módulos implementados (Sprint 3 fechado)

| Módulo | Linhas | Sprint | Função |
|--------|--------|--------|--------|
| `parser.py` | 315 | 1 + 2.C.1 | Parse markdown+YAML frontmatter; mutação cirúrgica de estado |
| `dag.py` | 111 | 1 | Ordem topológica (Kahn) com tie-breaking alfabético |
| `gate.py` | 166 | 1 | Scoring triplo: gold (PTDISLGEOX) + PQMS (7 dims) + VVV |
| `fsm.py` | 81 | 1 | Máquina de estados finita; transições válidas/inválidas |
| `writer.py` | 105 | 0 | Escrita atômica: tmp+fsync+rename (mitiga FM-02) |
| `wal.py` | 85 | 1 | Append-only JSON Lines log |
| `transitions.py` | 300 | 2 | Orquestração atômica: parse→gate→FSM→write→WAL |
| `streaming.py` | 142 | 3 | Streaming ticks com cursor advancement (fecha FM-10) |
| `cli.py` | 310 | 2.E + 3.E | Interface Click com 5 subcomandos + exit codes 0/1/2 |

**Total: 1.615 linhas de código Python funcional.**

### 1.6 Suite de testes (estatísticas medidas)

- **337 testes** coletados (`pytest --collect-only`)
- **235 testes rápidos**: passam em **2.55s**, cobertura **98.78%**
- **102 testes slow**: passam em **4.15s** (SIGKILL fuzzer ×50, performance p99, concorrência 4-proc)
- **Ruff**: zero issues
- **MyPy strict**: zero issues

### 1.7 Documentação existente

- 7 ADRs (ADR-001 a ADR-007), sendo ADR-003 e ADR-006/007 marcados como **autoridade**
- 2 contratos de API (`transitions.md`, `streaming.md`)
- `PLANO_ENGENHARIA_SOFTWARE_V1.md` — spec canônica (673 linhas, PMQ 9.64)
- `PLANO_CONTINUIDADE_FRACTAL_v2.md` — plano de continuidade
- `STATUS.md` — catálogo vivo (inventário + estado + dívidas)
- `CLAUDE.md` — instruções de boot para agente @executor (Layer-1)
- `TECHNICAL_DEBT.md` — registro de dívidas (TD-001 ativa, TD-002/003 resolvidas)
- `WAL_HUMANO.md` / `WAL_HUMANO_SPRINT3.md` — narrativa histórica
- `DOC-SELF-001-atomic-dag-self.md` — auto-documentação como instância do framework
- Dashboard HTML em `/docs`

### 1.8 Processo de desenvolvimento (observado)

- **Sprints com fases** (A→G): spec → impl → testes → validação tríade → commit → PR → merge
- **Tríade canônica**: ruff + mypy strict + pytest (cov ≥ 95%)
- **CI 3-matriz**: Python 3.11 / 3.12 / 3.13 (afirmado na documentação)
- **Mandatos**: PMQ ≥ 9.5, VVV = 1.0, cov ≥ 95%, tríade verde antes de commit, cursor FROM/THIS/GOTO
- **Protocolo de comunicação**: @cnmfs (operador humano), @orquestrador (Claude no chat), @executor (Claude Code no terminal)
- **Invariante I8-ext**: CI verde é pré-condição, NUNCA gatilho; nenhuma fase inicia sem `go`

---

## 2. ANÁLISE: DOCUMENTAÇÃO vs IMPLEMENTAÇÃO

### 2.1 Alinhamentos fortes (o que está correto)

| Área | Documentação | Implementação | Veredito |
|------|-------------|---------------|----------|
| Arquitetura em camadas | ADR-001, PLANO §5.1 | `src/atomic_dag/` organizado em 5 camadas | ✅ Alinhado |
| Atomic writes | ADR-004 (FM-02) | `writer.py` usa tmp+fsync+rename | ✅ Alinhado |
| Gate anti-inflação | HIQM, FRAMEWORK_FRACTAL | `gate.py` ignora campo `score` auto-reportado | ✅ Alinhado |
| FSM | `fsm.py` + ADR-006 | Estados e transições implementados | ✅ Alinhado |
| WAL schema | `transitions.md` §5, `streaming.md` D4 | `wal.log_event` gera JSON Lines com campos obrigatórios | ✅ Alinhado |
| Exit codes | ADR-006 D6, ADR-007 D5 | `cli.py` mapeia 0/1/2 corretamente | ✅ Alinhado |
| Idempotência | `transitions.md` §5 | `_find_idempotent_prior_event` verifica WAL antes de side effects | ✅ Alinhado |
| D11 (disk never lags WAL) | ADR-003 §Lesson 3, ADR-006 | `write_atomic` antes de `wal.log_event` em transitions e streaming | ✅ Alinhado |
| FM-10 closure | ADR-007 D7 | `tick_streaming` invoca `advance_cursor` antes do WAL | ✅ Alinhado |
| Popperian falsifiability | ADR-007 §0 | `test_fm10_regression.py` com mecanismos comportamental+estrutural | ✅ Alinhado |
| SIGKILL fuzzer | RF-2.2, RF-3.3 | `test_transitions_sigkill.py` e `test_streaming_sigkill.py` com 50 trials cada | ✅ Alinhado |
| Performance budget | RF-2.6 (p99 < 100ms) | `test_streaming_performance.py` mede e asserta p99 | ✅ Alinhado |
| Cobertura honesta | Mandato M3 (≥95%) | 98.78% medida, omit list vazio | ✅ Alinhado |
| Type safety | Mandato M4 (mypy strict) | `mypy src` passa sem erros | ✅ Alinhado |

### 2.2 Desalinhamentos críticos (gaps encontrados)

#### Gap C1 — CI/CD AUSENTE no repositório

**Documentação afirma:**
- README.md: "CI runs the same triad on Python 3.11/3.12/3.13 on every push and pull request"
- STATUS.md: referencia commit `e37bf56` com "ci(workflow): trigger on push:claude/** + manual dispatch (D1)"
- PLANO_ENGENHARIA: "integração contínua é deliberadamente simples: tríade ruff + mypy + pytest rodando local pre-commit, complementada por GitHub Actions"

**Realidade medida:**
- `.github/workflows/` **NÃO EXISTE** no checkout atual (`main` em `c324e58`)
- `find . -name "*.yml" -o -name "*.yaml"` no repo não retorna workflows

**Impacto:** A afirmação "CI 3-matriz verde em cada PR" não é verificável. O projeto tem 337 testes, lint e typecheck limpos, mas **zero automação de pipeline**. Isso contradiz o mandato D2 ("Dupla CI verde — push + PR — para o gate") e o mandato I8-ext (autogate proibido, mas sem CI o gate é manual).

**Causa provável:** O commit `e37bf56` que adicionou o workflow pode estar em um branch não mergeado, ou o workflow foi removido, ou existe em outro remote. O STATUS.md menciona D1 e D2 como dívidas abertas relacionadas ao CI.

#### Gap C2 — Configuração pytest quebra testes slow

**Documentação afirma:**
- `pyproject.toml`: `addopts = "-ra --cov=atomic_dag --cov-report=term-missing --cov-fail-under=95"`
- STATUS.md D5: "`ci.yml` lacks `-m 'not slow'`; slow tests rodam em CI até filter ser adicionado"
- WAL_HUMANO_SPRINT3: "Confirmado em CI que os testes slow rodaram (327 passed, não 225)"

**Realidade medida:**
```bash
pytest -m slow
# Resultado: FAIL — coverage 56.60% < 95%
# Os 102 testes slow PASSAM, mas o coverage cai porque usam subprocessos/multiprocessing
```

**Impacto:** Qualquer execução de `pytest` sem `-m "not slow"` ou qualquer tentativa de rodar o SIGKILL fuzzer em CI resulta em **falso-falha**. O STATUS.md reconhece D5 como aberta, mas a correção nunca foi aplicada no `pyproject.toml`.

#### Gap C3 — writer.py 80% cobertura (TD-001) persistindo

**Documentação afirma:**
- TECHNICAL_DEBT.md TD-001: "reprogramado para Sprint 5 junto com `reconcile` command"
- PLANO_ENGENHARIA: "writer.py cov-to-100%" é entregável do Sprint 5

**Realidade medida:**
- Linhas 89-94 de `writer.py` (branch error-recovery quando `os.write` ou `os.fsync` falha) **não são exercitadas por nenhum teste**
- Cobertura medida: 80% (5 das 25 linhas não cobertas)

**Impacto:** Técnicamente não bloqueia (98.78% global > 95%), mas contradiz o mandato de "cobertura honesta sem omit list". O projeto tem SIGKILL fuzzers sofisticados mas não testa um simples `OSError` no writer.

#### Gap C4 — Referências a capacidades MCP não verificáveis

**Documentação afirma:**
- CLAUDE.md §3.5: enumera toolsets MCP esperados (pull_requests, repos, actions, discussions)
- STATUS.md D10: "MCP github-mcp-server do @executor está no toolset core (52 tools, zero discussion_*)"

**Realidade medida:**
- Não há como verificar externamente se as tools MCP estão disponíveis nesta sessão
- O fallback documentado (paste manual via @cnmfs) indica que a capacidade plena NÃO está ativa

**Impacto:** Operacional, não técnico. O projeto assume uma infraestrutura de agentes que pode não estar completamente funcional.

---

## 3. ANÁLISE DOS TESTES (empírica, não confirmacional)

### 3.1 Estrutura da suite

A suite é **excepcionalmente bem estruturada** para um projeto de pesquisa acadêmica:

- **Testes falsificáveis Popperianos**: cada alegação central tem um teste que a refutaria se falsa
- **Testes de regressão estrutural**: `test_fm10_regression.py` usa spy (`unittest.mock.patch`) para garantir que `advance_cursor` é invocado, mesmo que o comportamento pareça correto
- **SIGKILL fuzzers**: 50 trials determinísticos com monkey-patching de `wal.log_event` para injetar SIGSTOP no momento exato entre `advance_cursor` e `log_event`
- **Performance budgets**: p99 < 100ms para 100 ticks sequenciais
- **Concorrência real**: 4 processos paralelos via `multiprocessing.Pool`
- **Parametrização sistemática**: `@pytest.mark.parametrize` para cursores, estados, ações

### 3.2 O que os testes realmente verificam (análise de propósito)

Os testes não verificam apenas "funciona"; verificam **propriedades arquiteturais**:

1. **Atomicidade**: SIGKILL em qualquer ponto não corrompe estado (disk-ahead-of-WAL é tolerável; WAL-ahead-of-disk é proibido)
2. **Idempotência**: replay de transição já completa é no-op sem novo WAL entry
3. **Anti-inflação**: gate ignora scores auto-reportados
4. **Acoplamento obrigatório**: `tick_streaming` DEVE chamar `advance_cursor` (teste estrutural)
5. **Ordenação**: `write_atomic` antes de `wal.log_event` (D11)
6. **Performance**: operações terminam em <100ms
7. **Concorrência**: múltiplos processos em projetos distintos não corrompem WAL

### 3.3 O que os testes NÃO verificam (lacunas)

1. **Falha de I/O no writer**: TD-001 — `os.write`/`os.fsync` levantando `OSError` não é testado
2. **Integração com LLM real**: Sprint 4 não iniciado; não há `AnthropicBridge`
3. **Concorrência no MESMO átomo**: ADR-006 D8 / TD-004 — "concurrent transitions no MESMO átomo: fora do contrato Sprint 2"
4. **Reconciliação**: Sprint 5 não iniciado; comando `reconcile` não existe
5. **Hello SOC end-to-end**: Sprint 4 não iniciado
6. **Locks per-atom**: Sprint 5 não iniciado
7. **Validação empírica externa**: Sprint 6 não iniciado

Estas lacunas são **deliberadas e documentadas** — não são surpresas. Cada uma está mapeada para um sprint futuro.

---

## 4. VEREDICTO EMPÍRICO

### 4.1 Qualidade do código e testes

| Critério | Nota | Base empírica |
|----------|------|---------------|
| Cobertura de testes | A+ | 98.78% medido, 337 testes, omit list vazio |
| Qualidade dos testes | A+ | Falsificadores Popperianos, fuzzers SIGKILL, budgets de performance |
| Arquitetura | A+ | 5 camadas sem ciclos, dependências apontando para dentro |
| Documentação | A+ | 7 ADRs, contratos de API, plano de engenharia, auto-documentação |
| Type safety | A+ | mypy strict zero issues |
| Lint | A+ | ruff zero issues |
| CI/CD | F | Zero pipelines automatizados no repo |
| Configuração de testes | C | Bug de pytest-cov quebra execução de slow tests |
| Dívida técnica ativa | B | TD-001 conhecida e documentada, mas aberta há 40+ dias |

### 4.2 Riscos identificados

1. **Risco alto — Sem CI**: Sem pipeline automatizada, regressões só são detectadas manualmente. Isso contradiz o próprio propósito do projeto (tornar falsificações baratas e rotineiras).
2. **Risco médio — Bug de config pytest**: Dev que rodar `pytest` sem saber do marker `slow` verá falso-falha e pode perder tempo debugando coverage em vez de código.
3. **Risco baixo — TD-001**: Branch de erro no writer não testado. Impacto limitado porque o happy path e SIGKILL path estão ambos provados.

### 4.3 Recomendações (priorizadas)

1. **🔴 Criar `.github/workflows/ci.yml`** com matriz 3.11/3.12/3.13, rodando ruff + mypy + pytest rápidos + pytest slow (sem coverage)
2. **🔴 Corrigir `pyproject.toml`** para separar config de coverage dos testes slow
3. **🟡 Adicionar teste para TD-001** (mock de `os.write` com `side_effect=OSError`)
4. **🟢 Adicionar job nightly** para rodar SIGKILL fuzzer com mais trials (100-500)
5. **🟢 Adicionar `pytest-xdist`** para paralelizar testes rápidos

---

## 5. REFERÊNCIAS (fontes primárias usadas nesta auditoria)

- `README.md` — propósito, status, instalação
- `CLAUDE.md` — protocolo de comunicação, mandatos, invariantes
- `docs/STATUS.md` — catálogo vivo, gates fechados, dívidas
- `docs/PLANO_ENGENHARIA_SOFTWARE_V1.md` — spec canônica completa
- `docs/architecture/adrs/ADR-001..007` — decisões arquiteturais
- `docs/api/transitions.md` + `streaming.md` — contratos observáveis
- `docs/WAL_HUMANO_SPRINT3.md` — narrativa histórica Sprint 3
- `TECHNICAL_DEBT.md` — registro de dívidas
- `src/atomic_dag/*.py` — código implementado (1.615 linhas)
- `tests/test_*.py` — 17 arquivos de teste
- `pyproject.toml` — configuração de tooling
- Execução local: `pytest --collect-only`, `pytest -m "not slow"`, `pytest -m slow`, `ruff check`, `mypy src`
