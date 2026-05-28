# WAL Humano — Sprint 2 do `atomic-dag-soc`

> O WAL técnico (`.atomic-dag/wal.jsonl`, quando existir) registra
> eventos máquina. Este documento registra a história do projeto
> de forma que a operadora se reconheça nela. Cronológico, narrativo,
> com as decisões, as correções, e o que cada erro ensinou.

---

## Como ler este documento

Cada seção é uma fase ou um momento. Decisões aparecem com a justificativa
contemporânea. Correções aparecem com a discrepância detectada e a lição
extraída. Sem amenizar, sem inflar — o WAL humano serve para que ninguém
(nem a operadora, nem um agente futuro, nem um revisor externo) precise
reconstruir contexto do zero.

---

## 0. Estado herdado de Sprint 1 (ponto de partida)

Branch `main` em `2bfecc2f`. Tags `v0.1.0-sprint0` e `v0.2.0-sprint1`
já publicadas. 147 testes verdes, cobertura honesta 97.32% (`omit=[]`).
Sete módulos funcionais em `src/atomic_dag/`: `parser`, `dag`, `gate`,
`cli` (Sprint 1) sobre `writer`, `wal`, `fsm` (Sprint 0). Nenhum deles
muta estado persistido — todo o sistema, até aqui, apenas lê e valida.

Sprint 2 introduz a primeira mutação: `execute_transition`. O sprint
todo gira em torno de costurar primitivas Sprint 0/1 válidas em uma
composição que mantém ACID-local-aproximado sob SIGKILL arbitrário.

---

## 1. Fase 2.A — ADR-006 redigido, com erro

**Commit:** [`dbcb0ce`](https://github.com/camillanapoles/atomic-dag-soc/commit/dbcb0ce) (2026-05-17 04:27 UTC)

O orquestrador apresentou plano de tradução de `execute_transition`
travando D1 (ordem das operações), D2 (idempotência), D4 (schema WAL),
D5 (TransitionResult), D6 (exit codes), D8 (concorrência diferida),
D11 (invariante "disco nunca atrasa o WAL"), e resoluções DA-1/2/3.
Operadora aprovou linha a linha. ADR-006 foi commitado como autoridade.

A operadora pediu ao agente para confirmar aderência aos onze pontos
do checklist. O agente respondeu **"aderência reconfirmada nos onze
pontos, sem desvio"** — e estava errado. O D1 do ADR tinha a ordem
invertida (`parse → fsm → gate`), contradizendo a ordem que o próprio
ADR cita como autoridade (`ADR-003 §Lesson 3`: `parse → gate → fsm`)
e o `§6.2` do PLANO_ENGENHARIA verbatim.

**Lição L1 (registrada no mandato):** auto-relato de conformidade não
é verificação. Reconfirmação confiante sem releitura da fonte é
exatamente o anti-padrão SOC V3 (PMQ 9.44 reportado vs 4.49 auditado)
que o projeto inteiro existe para impedir. A operadora aceitou o
auto-relato de boa-fé porque ele veio com confiança.

---

## 2. CI infra — `ci.yml` estendido fora do plano

**Commit:** [`e37bf56`](https://github.com/camillanapoles/atomic-dag-soc/commit/e37bf56) (2026-05-17 05:13 UTC)

Detectado que `ci.yml` original só disparava em `push:main` e
`pull_request:main` — o que tornava cada commit em branch de feature
invisível ao CI até a PR ser sincronizada. Para o protocolo de gate
incremental funcionar (cada fase validada pelo CI antes da próxima),
o trigger precisou ser ampliado:

- `push.branches += 'claude/**'`
- `workflow_dispatch:` para re-trigger manual
- `concurrency:` group para cancelar runs obsoletos

**Dívida D1 registrada:** o commit é necessário e correto, mas
está fora da sequência planejada de 15 commits do Sprint 2. Registro
em MPF_LOG no 2.H para que plano e repositório não divirjam em
silêncio.

**Dívida D2 (descoberta depois):** o `concurrency.group` definido como
`${{ github.workflow }}-${{ github.ref }}` não deduplica entre eventos
`push` e `pull_request.synchronize` porque `github.ref` é diferente
nos dois (`refs/heads/...` vs `refs/pull/N/merge`). Resultado: dois
runs verdes redundantes por push enquanto a PR está aberta. Detectado
ao observar a Check Runs API retornando 6 runs (2 × 3 matrizes) onde
era esperado 3. Candidato a `concurrency.group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}` em sprint futura.

---

## 3. Copilot review → 4 catches → fix-forward 2.A

**Commit:** [`c40de0e`](https://github.com/camillanapoles/atomic-dag-soc/commit/c40de0e) (2026-05-17 05:21 UTC)

Copilot revisou ADR-006 e devolveu 4 comentários inline. Três eram
clarificações pequenas (schema de `gate_result` para `json.dumps`;
responsabilidade do `mkdir` do `.atomic-dag/`; tempo verbal do
TECHNICAL_DEBT sobre FM-01). O quarto era a captura crítica:

> "D1 conflicts with ADR-003 §Lesson 3 ordering [...] runs `fsm.validate_transition` before `gate.validate_gate`, and also labels the gate as 'ALWAYS called' despite the preceding early-return on invalid FSM transitions."

Copilot leu o pseudocódigo e o cruzou contra a fonte citada. O agente
não tinha feito isso ao "reconfirmar". O documento contradizia a si
mesmo (D1 dizia "always called" e D4 também, mas a ordem D1
permitia FSM-rejeitar antes do gate ser invocado).

**Decisão da operadora:** D1 revertido para `gate-antes-de-FSM`
(ordem ADR-003 §Lesson 3 verbatim). A "otimização" FSM-first foi
documentada como **Alternativa-5 rejeitada** no próprio ADR-006,
junto da rejeição original de D3 (two-phase WAL). Princípio simétrico:
fidelidade à ordem estabelecida > otimização paralela inventada.

**Lição L2:** o D1 invertido foi forma de inflação metodológica — o
agente repetiu de memória ("a ordem que está no plano") em vez de
ler a fonte ("a ordem que ADR-003 §Lesson 3 prescreve"). Memória
diverge da fonte sem aviso; verbatim junto da afirmação é a única
forma de não cair nessa armadilha.

---

## 4. Fase 2.B — contrato observável de `transitions`

**Commit:** [`1177c2a`](https://github.com/camillanapoles/atomic-dag-soc/commit/1177c2a) (2026-05-17 05:38 UTC)

`docs/api/transitions.md` redigido como contrato observável da função
`execute_transition` antes de qualquer linha de código. Dez seções
fixam a superfície pública (`execute_transition` + `TransitionResult`,
nada mais), a ordem D1, o schema WAL, idempotência por replay,
exit codes, invariante de crash D11, postura de concorrência. §10
explicita: "nenhuma cláusula vale por afirmação, só por teste passando."

O documento é especificação prévia, não derivação posterior. É um
gate para 2.C: o código tem que satisfazer esse contrato; se não
satisfizer, é o código que está errado, não o contrato.

Notado para correção futura: §9 do `transitions.md` citou
"ADR-003 §Lesson 1" como autoridade para "não modificar módulos
Sprint 0/1". Citação fraca — `§Lesson 1` verbatim trata apenas
do `omit-list` para cobertura. Foi registrada como **dívida D3**
para fix-forward na Phase 2.C.1.

---

## 5. Fase 2.C.1 — primeira escrita: `replace_state_in_frontmatter`

**Commit:** [`45161a8`](https://github.com/camillanapoles/atomic-dag-soc/commit/45161a8) (2026-05-17 06:34 UTC)

Primeira adição de código em `parser.py` desde Sprint 1. Função pura
que muta cirurgicamente o estado no frontmatter YAML preservando bytes
fora da substituição (ordem de chaves, comentários, aspas, envelope
quad-backtick). Sem round-trip via `yaml.safe_dump`.

15 testes novos (S27-S41) cobrindo cada decisão de design e cada
branch alcançável. 2 `# pragma: no cover` em helpers privados
estruturalmente inalcançáveis via API pública (cada um com comentário
explicando o motivo concreto). Cobertura final do módulo: 99%.

Três correções metodológicas pegadas nesta fase, registradas como
emendas ao mandato:

### 5.1 — Discrepância 26 → 27 testes herdados

O mandato I4 falava em "26 testes herdados de `test_parser.py`",
herdado do docstring `"Tests for atomic_dag.parser — 26 scenarios."`
do próprio arquivo. `pytest --collect-only` retornou 27. A 27ª função
(`test_malformed_deps_string`) tinha sido adicionada no Sprint 1
sem atualização do docstring. **Lição:** paráfrase do docstring é
paráfrase de paráfrase; a fonte é a contagem real do collect.
Docstring corrigido no mesmo commit (`26 → 42`, refletindo 27 herdados
+ 15 novos).

### 5.2 — Discrepância de cobertura X/Y/Z

Após primeira passagem dos 12 testes inicialmente planejados (S27-S38),
cobertura caiu de 97.32% para 96.07% (parser.py 94%). 9 linhas missing
em branches defensivas/erro da função nova. Três caminhos foram
considerados:

- **X** (aceitar): viola o espírito "passou o piso = bom" (anti-SOC-V3).
- **Y** (adicionar S39-S41 + pragmas em 266/278 estruturalmente
  inalcançáveis): cumpre o escopo do que foi planejado, não excede.
- **Z** (só pragmas): mascararia código testável como `omit` disfarçado.

A operadora escolheu (Y), articulando: "12 testes" era estimativa,
não teto; descobrir que cobertura honesta pede 15 é o número 12 ter
sido impreciso, não exceder mandato. Cobertura final voltou a subir:
97.77% global (acima do baseline Sprint 1), parser.py 99% (acima de 98%).

### 5.3 — Discrepância de autoria pré-push

Após commit local, autor mostrou `Claude <noreply@anthropic.com>` —
identidade default do `git config` da sessão, diferente dos 4 commits
anteriores do branch (`Camilla Napoles <cnmfs@cesar.school>`, via MCP).
Pushar introduziria uma terceira identidade na cadeia.

**O agente parou antes do push.** PARTE 6 #3 do mandato em ação:
detectar conflito → reportar → não escolher um lado. Operadora
escolheu opção (q): `git reset --soft HEAD~1` + `git config` local
(`cnmfs@cesar.school`) + recommit byte-idêntico em conteúdo, só
identidade corrigida. I5 (sem amend) preservado porque o commit
errado nunca foi pushado — `reset --soft` sobre não-publicado não
é reescrita de história, é não-ter-publicado-ainda.

**γ.0 oficializado no mandato:** fixar identidade git local
(`user.name`/`user.email`) ao repo antes do baseline de qualquer
fase futura. Prevenção na origem, não verificação pós-fato.

### 5.4 — Dívida D3 fechada na origem

A citação fraca de §Lesson 1 em `transitions.md §9` foi reescrita
no mesmo commit que adicionou a função:
- Antes: "**not modified** (ADR-003 §Lesson 1)" categórico
- Depois: "**not modified** (Sprint 2 scope invariant; ADR-003 §Lesson 1
  literally addresses only the coverage omit list and is cited only
  where it applies directly)"

A regra que protege os 5 módulos (writer/wal/fsm/gate/dag) continua
válida; o que muda é a paternidade documental — ela vive no escopo
Sprint 2 (este protocolo + ADR-006), não em §Lesson 1 do ADR-003.

---

## 6. Padrões que emergiram

Lendo as 5 fases junto, três padrões se repetem o suficiente para
serem registrados como propriedades estáveis do trabalho:

### 6.1 Verificação verbatim, não memória

Toda vez que o agente afirmou conformidade contra um documento sem
re-ler o documento, surgiu uma inconsistência (D1 invertido, §Lesson 1
paráfrase, 26 vs 27 herdados). Toda vez que a fonte foi colada
junto da afirmação, a inconsistência foi pega antes de virar commit.
Verbatim não é ritual — é o mecanismo concreto que separa "acho
que está alinhado" de "está alinhado, eis a prova".

### 6.2 Captura precoce, custo barato

D1 invertido foi pego por Copilot antes de qualquer código ser
construído sobre ADR-006. §Lesson 1 paráfrase foi pega pela
verificação verbatim antes de virar regra citada em mais lugares.
Autoria errada foi pega no `git log -1` local antes do push.
Todas as três correções foram baratas porque foram detectadas no
momento mais cedo possível. Se a primeira tivesse vazado para a
implementação, o fix custaria múltiplos commits e revalidação.
Se a terceira tivesse virado push, custaria reescrita de história.

### 6.3 Severidade calibrada, sem inflar nem deflacionar

A captura de §Lesson 1 começou como "nota não-bloqueante" (sub-classificação),
escalou para "fabricação total" (super-classificação), aterrissou como
"citação imprecisa de regra bem-fundamentada — não-bloqueante mas
registrável" (medição correta). A lição (L3 do mandato) é que auditoria
honesta corta nos dois sentidos: a tentação de minimizar é simétrica
à tentação de dramatizar. Medir o achado contra critérios explícitos,
não contra o instinto do momento.

---

## Phase 2.D — Adversarial battery (2026-05-27 23:04 UTC, SHA `086b823`)

Bateria adversarial para `transitions.py`: SIGKILL ×50, performance p99,
concorrência multi-process. Três arquivos novos em `tests/`, zero modificação
em `src/`.

**Decisão arquitetural — SIGKILL α.3 após D4 evidence-driven failure.** A
primeira estratégia (D4: parent-side uniform random sleep ∈ [0, 50ms] +
SIGKILL) foi instrumentada com gate empírico: ≥40/50 trials precisavam landar
em `in_critical_window` (janela entre `write_atomic` e `log_event`) para o
fuzzer ser considerado adequado. Resultado medido: **1/50 in_critical_window,
6/50 pre_write, 43/50 post_log**. A janela crítica é microsegundo-escala
(dict construction + json.dumps + file append < 1ms); o sleep range de 50ms
quase sempre cai antes (kill cedo) ou depois (kill tardio) da janela. Gate
falhou — parou per §9 stop condition, sem implementar D1 sem autorização.

Operadora autorizou α.3: child subprocess **monkey-patch de `wal.log_event`
para SIGSTOP antes do append real**. Parent usa `waitpid(WUNTRACED)` para
bloquear até o stop chegar; aí dispara SIGKILL. Por construção, o kill cai
deterministicamente após `write_atomic` completar e antes de qualquer linha
de WAL ser escrita. Resultado: **50/50 in_critical_window, zero violação D11**.

Lição L4: **gate empírico falhando é informação, não falha do agente**. D4
deu 1/50 não por bug — a estratégia simplesmente não estressava a janela.
O reporting honesto da distribuição abriu caminho para α.3 ser pedida pela
operadora; tentar inflar D4 ("provavelmente OK") teria mascarado o gap.

**Pattern reutilizável:** monkey-patch + SIGSTOP é viável para falsificar
qualquer invariante "X acontece antes de Y" onde Y é uma função
substituível. Documentado no próprio test_transitions_sigkill.py para
referência futura.

Dívidas D5 (ci.yml lacks `-m "not slow"` filter) e D6 (Copilot App check
falhando análogo a D4) abertas nesta fase.

---

## Phase 2.E — CLI wire (2026-05-27 23:20 UTC, SHA `df90620`)

Wire do comando `atomic-dag transition` ao `execute_transition`. Substitui
o placeholder de Sprint 1.

`atomic-dag --project P transition ATOM_ID ACTION [--json]` — atom_id (str)
resolvido via `parse_atom_directory` para obter filepath; passado a
`execute_transition`. Exit codes literais per D6 / transitions.md §6:

- **0** — success (incluindo idempotent replay e gate-fail-on-check → returned)
- **1** — operational (FSM-invalid, terminal state)
- **2** — structural (atom_id não encontrado no projeto, parse error)

Output JSON `--json` emite campos de `TransitionResult` direto, sem
expansão do `gate_result` (que continua disponível no WAL). 12 testes
herdados em `test_cli.py` inalterados + 12 novos S13-S24 cobrindo exit
codes, schema JSON, replay idempotente, gate-routing em check, WAL
end-to-end via CLI.

Cobertura `cli.py`: **100%** (91/91 statements), com 2 pragmas
justificados (race AtomNotFoundError defensivo + `if __name__ ==
"__main__"` guard estruturalmente fora do alcance do CliRunner).

Decisão pequena registrada: campo `wal_event_logged: bool` proposto na
revisão (R1) e cancelado por redundância com `idempotent` (que já
distingue "no-op replay" de "transição real").

---

## Phase 2.F — Cov bump + TD-004 (2026-05-27 23:26 UTC, SHA `d9a785b`)

`pyproject.toml`: `addopts --cov-fail-under=80` → `--cov-fail-under=95`.
`TECHNICAL_DEBT.md`: TD-004 adicionada após TD-003.

TD-004 — **FM-01 concurrent WAL writers (mitigated, not closed)**. Mitigação
atual: `O_APPEND` semantics + payload < PIPE_BUF (4096 bytes) → atomic line
append em POSIX. Concurrent transitions em átomos distintos são seguros
(testado em test_transitions_concurrency.py). Concurrent transitions no
mesmo átomo ficam fora do contrato Sprint 2 (`transitions.md §8`).
Fechamento real: Sprint 5 com per-atom locking + reconcile.

Gate canônico de 95% atingido pela margem 3.54 pp (global 98.54%).
`writer.py` continua em 80% (TD-001 herdado, branch de erro orphan-cleanup
não-testado) mas o agregado pondera por número de statements: 5 misses em
484 total = ~1% do peso, não move o threshold.

Zero mudança em `src/` ou `tests/` — chore puramente de housekeeping.
Diff total: 2 arquivos, 16 inserções, 1 deleção.

---

## Phase 2.G — Merge to main (2026-05-27 23:34 UTC, SHA `da46621`)

PR #1 mergeado em main com estratégia `--no-ff` (merge commit).

**Por que não squash:** STATUS.md, este WAL_HUMANO, ADR-006, todos
referenciam SHAs específicos dos 11 commits do branch. Squash colapsaria
em 1 SHA e os referências apontariam para commits órfãos.

**Por que não rebase:** rebase reescreve hashes; quebraria os mesmos
links. Linear history não é objetivo declarado do projeto.

**Merge commit `--no-ff`:** preserva os 11 SHAs como ancestrais
reachable de `main`. `git log da46621` mostra a história completa.
Tag `v0.3.0-sprint2` em `d9a785b` continua válida — `d9a785b` é
reachable de `main` via `da46621`.

**Blocker observado — D7:** tag `v0.3.0-sprint2` foi criada localmente
(annotated) em `d9a785b`, mas `git push origin refs/tags/...` falhou
com HTTP 403 via `local_proxy`. Tentativa A (`gh release create`)
indisponível (gh CLI ausente do ambiente). **Decisão β (postergar
push, manter SHA estável):** aceitar — `d9a785b` é SHA imutável, tag
idempotente em qualquer momento futuro, postergação não muda alvo.
Dívida D7 registrada.

D7 posteriormente fechada via UI (operadora criou release manualmente).
Discrepância cosmética detectada: tag remota é **lightweight**
(criada via UI sem objeto annotated), precedente `v0.1.0-sprint0` /
`v0.2.0-sprint1` é **annotated**. Registrada como D8 (cosmética,
não-bloqueante).

**Sprint 2 estatística final:**

- 11 commits + 1 merge commit em main, todos com cursor FROM/THIS/GOTO
- Autoria uniforme `Camilla Napoles <cnmfs@cesar.school>` (γ.0 ativo em todos)
- Suite final: 256/256 verde
- Coverage: `transitions.py` 100%, global 98.54%
- CI canônico: 3/3 matrizes verde em cada fase + no merge
- D11 falsificável e validada: 50/50 in critical window, zero violação
- Dívidas abertas: D1, D2, D4 (descartável), D5, D6 (descartável), D8
- Dívidas fechadas: D3 (em `45161a8`), D7 (via UI pós-merge)
- TD-001 (Sprint 0 herdada), TD-003 (Sprint 3 alvo), TD-004 (Sprint 5 alvo)

---

## 7. Onde estamos, em uma frase

Sprint 2 fechada em `da46621` (merge PR #1 em main). 11 commits + 1
merge commit, autoria uniforme, todos com cursor narrativo. Suite
256/256 verde, cov global 98.54%, `transitions.py` 100%. Tag
`v0.3.0-sprint2` publicada em `d9a785b` (lightweight; D8). Próxima
fase: Sprint 3 endereçando FM-10/TD-003 (port de `tick_streaming` +
fix + regression test red→green).

---

## 8. Aviso sobre este documento

Este WAL humano é narrativo, não-canônico. Quando houver conflito
entre o que está aqui e o que está em um ADR ou no
`PLANO_ENGENHARIA_SOFTWARE_V1.md`, o ADR/spec vence. Este
documento é a história contada para humanos; a especificação
contra a qual o código é validado vive em outro lugar.

Atualizado a cada fase fechada do Sprint 2.
