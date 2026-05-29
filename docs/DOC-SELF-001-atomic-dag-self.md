---
atomic_id: DOC-SELF-001
state: in-progress
deps: []
node_instance: "NÓ(DOC-SELF-001, t₀=2026-05-29T19:30Z)"
schema: template-master-9-blocos
fonte_de_verdade: "main@1d6217e (verificado via conector GitHub 2026-05-29)"
---

# Atomic-DAG — Documentação Auto-Referente

> **O que este documento é.** Uma explicação do Atomic-DAG escrita *como um
> ATÔMICO do próprio Atomic-DAG*. O sistema documenta a si mesmo na gramática
> que ele propõe: 9 blocos de schema invariante, uma máquina de estados, um
> cursor de retomada, e um Write-Ahead Log. Se a tese do framework é correta —
> que um documento markdown estruturado pode servir de interface de
> processamento para um estado externo — então este arquivo é uma prova de
> existência: ele *é* um nó executável, não apenas um texto sobre nós.

> **Nota terminológica universal deste documento.** *"Falsificável"* aqui é
> usado no sentido técnico de **Karl Popper** (*Lógica da Pesquisa Científica*,
> 1934): uma afirmação é falsificável quando **existe um experimento capaz de
> refutá-la se ela for falsa**. Isso é uma **virtude epistêmica** — significa
> **testável**, **auditável**, **passível de refutação empírica** — *não*
> significa "fraudável". Astrologia é infalsificável (explica tudo, prediz
> nada); a relatividade é falsificável (previu desvio da luz em 1919; se a luz
> não desviasse, estaria refutada). O projeto torna falsificáveis afirmações
> de progresso de LLMs no sentido de que toda alegação "fase concluída" passa
> por um gate Python determinístico que pode refutá-la, independentemente do
> auto-reporte. Tratado em profundidade em `ADR-007 §0` (Sprint 3).

---

## 0. A lógica em uma frase

**O Atomic-DAG inverte onde mora o estado.** Num agente LLM comum, a "posição"
no processo vive implícita no contexto acumulado da sessão — e morre quando a
janela transborda ou a sessão cai. No Atomic-DAG, o estado vive num arquivo
externo (`state.json` / frontmatter do `.md`); o LLM é apenas a unidade de
processamento que lê o nó ativo, preenche os campos, e devolve. O documento que
você lê é efêmero; o estado que ele renderiza é persistente. **Troca-se memória
implícita por estado explícito.**

A analogia exata vem do hardware: um processador que não persiste o *program
counter* entre interrupções perde o fio da execução de forma irreversível. A
maioria dos frameworks dominantes (LangGraph, AutoGen, CrewAI) opera sob essa
fragilidade — não por bug, mas por arquitetura: tratam estado como contexto
acumulado. O Atomic-DAG externaliza o program counter para um WAL.

---

## BLOCO 1 — IDENTITY (Identidade)

| Campo | Valor |
|---|---|
| **Nome** | Atomic-DAG Framework |
| **Tipo** | Gramática de orquestração textual para agentes LLM com persistência formal de estado |
| **Repositório** | `github.com/camillanapoles/atomic-dag-soc` (público) |
| **Estado canônico** | `main @ 1d6217e` (merge PR #8, fase 2.K), verificado via conector em 2026-05-29 |
| **Tese acadêmica** | `MANUSCRITO_ATOMIC_DAG_RSL_V2_CORRIGIDO.md`, PQMS 9.68, status OURO_V2 |
| **Implementação** | 9 módulos Python em `src/atomic_dag/`, suíte 256/256 verde, cobertura global 98.54% |

**O nome decomposto:**

- **Atomic** — a menor unidade de trabalho (o ATÔMICO) tem responsabilidade
  única e schema invariante. Atomicidade no sentido de indivisibilidade
  semântica (como a "nota atômica" do Zettelkasten) *e* no sentido transacional
  (ACID, do ARIES).
- **DAG** — *Directed Acyclic Graph*. O fluxo é um grafo dirigido sem ciclos.
  O truque que torna isso possível mesmo com loops (refinamento iterativo que
  revisita o mesmo passo) está no Bloco 8.

---

## BLOCO 2 — OBJECTIVES (Objetivos)

O framework existe para resolver **um** problema estrutural, declarado como
diagnóstico e não como sintoma:

> **Diagnóstico:** a causa raiz da fragilidade multi-sessão em agentes LLM é o
> *estado implícito em contexto efêmero*. **Solução:** externalizar o estado
> para um artefato persistido, desacoplado de qualquer sessão, governado por
> uma gramática de execução.

Objetivos mensuráveis derivados:

1. **Continuidade cross-session** — uma sessão interrompida retoma exatamente
   de onde parou, lendo o cursor do WAL. Sem memória implícita.
2. **Rastreabilidade do cursor** — a qualquer momento é possível responder
   "em que passo estamos e como chegamos aqui" lendo um log append-only.
3. **Recuperabilidade** — após uma falha (até `SIGKILL` no meio de uma
   transição), o estado em disco nunca fica *atrás* do WAL (invariante D11).
4. **Reprodutibilidade** — o mesmo `state.json` gera o mesmo nó, determinístico.

★ **Insight — sintoma vs. diagnóstico.** Muitos trabalhos (QSP-Copilot,
DeVPlan, sequence recorders de robótica) *implementam* memória e checkpoints —
reconhecem o sintoma. O que a tese do Atomic-DAG reivindica como contribuição
não é "ter memória", é **nomear a causa arquitetural** e propor a gramática que
a operacionaliza. É a diferença entre tomar antitérmico e diagnosticar a
infecção.

---

## BLOCO 3 — INSTRUCTIONS (Como o sistema processa — a máquina real)

Esta é a parte onde o sistema descreve seu próprio motor. A lógica de execução
vive em `transitions.py::execute_transition`, e a ordem das operações **não é
arbitrária** — cada passo está onde está por uma razão verificada (ancorada em
ADR-003 §Lesson 3 e ADR-006).

### 3.1 A máquina de estados (`fsm.py`)

Um ATÔMICO vive em exatamente um de **nove estados canônicos**:

```
pending → contracted → in-progress → checked → verified → returned
                                                → completed → closed → attention
```

A matriz de transição é um dicionário `(estado, ação) → novo_estado`. Qualquer
par fora do dicionário é uma transição inválida. Pontos não óbvios, lidos
direto do código:

- **`closed` é terminal** (`TERMINAL_STATES = frozenset({"closed"})`). Nenhuma
  ação sai dele.
- **`checked` nunca é persistido como estado estável.** Ele não aparece como
  *origem* de nenhuma transição na matriz. A ação `check` resolve direto para
  `verified` (gate passou) ou `returned` (gate falhou). Isto é a decisão DA-3.
- **Não existem self-loops.** Nenhuma transição leva um estado a si mesmo. Essa
  ausência é o que torna a idempotência detectável (ver 3.3).

### 3.2 A ordem de execução (as 9 etapas)

```
1. exists() pre-check          → AtomNotFoundError (exit 2) se o arquivo não existe
2. parser.parse_atom           → extrai meta, body; obtém atom_id e from_state
3. gate.validate_gate          → SEMPRE chamado, ANTES do FSM (D4). Função pura sobre dict.
4. idempotency pre-check       → §5: ANTES de qualquer efeito colateral E antes do FSM
5. fsm.validate_transition     → inválido ⇒ raise SEMPRE (zero disco, zero WAL)
6. route resolution            → action=="check" roteia via gate (verified|returned)
7. read_text + replace_state   → re-lê o .md cru e troca só o escalar de estado (cirúrgico)
8. writer.write_atomic         → escrita atômica POSIX (tmp + fsync + rename)
9. wal.log_event               → UM evento, DEPOIS da escrita
```

★ **Insight — por que o gate vem antes do FSM (passo 3 antes do 5).** Intuição
diria "valide a transição primeiro, só então rode o gate caro". Mas a decisão
D4 exige que o gate seja *always called*. A resolução: o gate é uma função
**pura sobre um dict** (custo trivial, zero I/O), então chamá-lo antes não
desperdiça nada — e garante que toda transição, mesmo as que o FSM vai rejeitar,
passou pelo gate. A ordem inverte a intuição porque o custo real do gate aqui é
≈ zero.

★ **Insight — por que a idempotência vem antes do FSM (passo 4 antes do 5).**
Este é o detalhe mais sutil do sistema. Como a matriz FSM **não tem
self-loops**, repetir uma ação que já foi aplicada *sempre parece inválida ao
FSM* (o disco já está no estado-destino, e dali aquela ação não existe). Se o
FSM rodasse primeiro, todo replay legítimo levantaria `InvalidTransitionError`.
Então o replay precisa ser detectado *antes*: o sistema procura no WAL um evento
`transition` anterior com mesmo `atom_id`, mesma `action`, e cujo `to_state`
seja igual ao estado atual em disco. Se achou, é um replay — retorna
`idempotent=True` sem tocar em nada. A ausência de self-loops, que parece um
detalhe, é exatamente o que torna a idempotência *decidível*.

### 3.3 O Write-Ahead Log (`wal.py`)

Formato **JSON Lines** (`.jsonl`): um objeto JSON por linha, append-only, UTF-8.
Compatível com `grep`, `jq`, `tail`. Cada evento de transição registra:
`timestamp` (ISO-8601 UTC), `event_type`, `atom_id`, `from_state`, `to_state`,
`action`, `gate_result` (dict serializável), `duration_ms`.

Duas garantias críticas no código:

- **Serializa antes de escrever.** `json.dumps` roda *antes* do `open(...,"a")`,
  para que um erro de serialização nunca deixe meia-linha corrompida no arquivo.
- **Append atômico no nível de linha.** No POSIX, escritas menores que
  `PIPE_BUF` (≈4096 bytes) em modo append são atômicas — e todo payload de
  evento cabe nisso. Esta é a base do FM-01 (escritores concorrentes).

---

## BLOCO 4 — MEMORY (Memória / Estado persistido)

O ponto onde o paradigma se materializa:

| Camada | Onde vive | Mutável? | Papel |
|---|---|---|---|
| **Estado** | `state.json` / frontmatter do `.md` | sim | A fonte única de verdade. O "program counter". |
| **Log** | `.atomic-dag/wal.jsonl` | append-only | Histórico imutável. Permite replay e recuperação. |
| **Interface** | o documento `.md` renderizado | efêmero | O que o LLM lê e preenche. Descartável a cada tick. |

★ **Insight — o documento é a *interface*, não o *estado*.** Esta inversão é a
contribuição central. O `.md` que o LLM processa é como a tela de um terminal:
mostra o estado atual e aceita entrada, mas não *é* o estado. O assembler extrai
o que o LLM preencheu, atualiza o `state.json`, avança o cursor, e a próxima
sessão renderiza um documento novo a partir do mesmo estado. O LLM "continua de
onde parou" sem nunca ter carregado memória implícita — porque a memória nunca
esteve nele.

**Paralelo formal:** isto é Event Sourcing (Fowler, 2005) aplicado a cognição.
O estado do sistema é derivável do log append-only de eventos. O WAL é o log;
o `state.json` é a projeção materializada.

---

## BLOCO 5 — TOOLS (Ferramentas / Composição de módulos)

Um ATÔMICO declara as ferramentas que invoca. `execute_transition` é,
literalmente, a **composição** de cinco módulos puros, mais o parser:

```
execute_transition = parser ∘ gate ∘ fsm ∘ writer ∘ wal
```

| Módulo | LOC | Responsabilidade única | Dependências externas |
|---|---|---|---|
| `parser.py` | ~340 | Ler frontmatter, mutar estado cirurgicamente | nenhuma |
| `gate.py` | ~160 | Avaliar qualidade (PQMS/VVV/gold) — função pura sobre dict | nenhuma |
| `fsm.py` | ~80 | Validar `(estado, ação)` contra a matriz | nenhuma |
| `writer.py` | ~110 | Escrita atômica POSIX (tmp+fsync+rename) | nenhuma |
| `wal.py` | ~80 | Append e leitura do log JSONL | stdlib apenas |
| `transitions.py` | ~290 | Orquestrar os 5 acima na ordem canônica | os 5 acima |
| `cli.py` | ~220 | Superfície de comando + exit codes 0/1/2 | transitions |

★ **Insight — 5 módulos com zero dependências externas.** `fsm`, `wal`,
`writer`, `gate`, `parser` dependem apenas da stdlib. Isso não é acaso: a
invariante **I3** congela esses 5 módulos como intocados desde o Sprint 1.
Toda a complexidade nova é absorvida pela *composição* (`transitions.py`), nunca
pela mutação das peças. É o princípio "não construir sobre base instável"
materializado em política de commits.

---

## BLOCO 6 — VALIDATION (Validação / Gates e invariantes)

Nada é "done" sem evidência de funcionamento real. A validação opera em três
níveis.

> **Nota terminológica local — §6.** As colunas "Como é falsificável" abaixo
> usam *falsificável* no sentido técnico Popperiano (testável, passível de
> refutação empírica — virtude epistêmica). Cada invariante listada vem
> acompanhada de um **experimento concreto que conseguiria refutá-la**, caso
> a afirmação fosse falsa. Definição completa do termo no preâmbulo deste
> documento e em `ADR-007 §0`.

### 6.1 Gate de qualidade (`gate.py`)

Avalia cada atom contra três scores: `gold_score`, `pqms_score`, `vvv_score`.
A regra de ouro: **VVV sem validação é ZERO** (falha segura). Informação não
verificável nunca passa o threshold.

### 6.2 Invariantes do framework (verificadas a cada sprint)

| ID | Invariante | Como é falsificável (= experimento que a refutaria se fosse falsa) |
|---|---|---|
| **I3** | 5 módulos intocados pós-Sprint-1 | `git diff main..HEAD -- src/atomic_dag/{writer,wal,fsm,gate,dag}.py` vazio |
| **D4** | Gate SEMPRE chamado antes do FSM | grep verbatim na ordem de `execute_transition` |
| **D11** | Disco nunca atrasa o WAL | bateria SIGKILL ×50 determinística |
| **§5** | Idempotência antes de qualquer efeito colateral | teste de replay: WAL não cresce, bytes/mtime inalterados |
| **I-WAL** | Cursor é o último ato da sessão | confirmação na fonte (conector), nunca na memória |

★ **Insight — a invariante D11 é falsificável, e foi falsificada-tentada.** A
prova de que "o disco nunca atrasa o WAL" não é um argumento — é um experimento.
A bateria de testes monkey-patcha `wal.log_event` para emitir `SIGSTOP` *antes*
do append real; o processo-pai detecta a pausa via `waitpid(WUNTRACED)` e
dispara `SIGKILL` na janela crítica exata entre a escrita atômica e o log.
Resultado: **50/50 trials na janela crítica, ZERO violação de D11**. E tudo isso
sem modificar uma linha de `src/` — o fault-injection vive só no teste,
preservando I3. Esta é a diferença entre afirmar uma garantia e *prová-la*
(no sentido Popperiano: a garantia sobreviveu a uma tentativa séria de
refutação; não foi provada absolutamente).

---

## BLOCO 7 — OUTPUT (Saída / O que o sistema produz)

A saída observável de uma transição é um `TransitionResult` — um dataclass
**frozen** (imutável), cujo `__bool__` retorna `success`:

```python
TransitionResult(
    atom_id, from_state, to_state, action,
    gate_passed, idempotent, duration_ms, success
)
```

E os **exit codes** do CLI codificam a taxonomia de falha (D6):

| Exit | Classe | Quando |
|---|---|---|
| **0** | sucesso | transição normal, replay idempotente, ou `check` que roteou para `returned` |
| **1** | operacional | transição FSM-inválida, ou ação a partir de estado terminal |
| **2** | estrutural | atom_id não existe no projeto, ou erro de parse |

★ **Insight — `check`-que-falha sai com 0, não com erro.** Um gate que reprova
(`check` → `returned`) é um resultado *válido* do processo, não uma falha do
sistema. O atom voltou para refinamento; isso é o fluxo funcionando. Exit 0.
A distinção entre "o processo decidiu reprovar" e "o sistema quebrou" está
codificada na superfície do CLI.

---

## BLOCO 8 — CONTINUITY (Continuidade / O paradoxo dos loops sem ciclos)

Aqui mora a resolução mais elegante do framework.

**O problema:** processos reais têm loops. Refinamento iterativo revisita o nó
de avaliação várias vezes. Num DAG definido topologicamente, revisitar um nó
cria um *ciclo* — e DAG significa, por definição, *acyclic*. Contradição.

**A resolução — separação ATÔMICO vs. NÓ com dimensão temporal:**

```
ATÔMICO = a definição (a "classe"): schema, responsabilidade, transições possíveis
NÓ      = uma instância no tempo: NÓ(ATÔMICO, t)

NÓ(ATÔMICO_A, t₁)  ≠  NÓ(ATÔMICO_A, t₄)   porque   t₁ ≠ t₄
```

O fluxo pode voltar ao "mesmo" ATÔMICO_A quantas vezes quiser. Mas cada visita é
um **NÓ distinto**, carimbado com um timestamp diferente. E como o tempo nunca
retrocede, o grafo de *nós* (não de átomos) é estritamente acíclico. O loop
existe no espaço dos átomos; o DAG existe no espaço dos nós-instância.

★ **Insight — isto é OOP + Event Sourcing aplicados a topologia de processo.**
A separação classe/instância existe desde Simula (1966) — não é nova. A dimensão
temporal para imutabilidade existe desde o Event Sourcing. O que o Atomic-DAG
faz de específico é **combinar as duas para garantir a propriedade acíclica de
grafos de processo com loops espaciais** — um domínio onde, segundo a RSL
conduzida, nenhum framework de agentes LLM nas bases consultadas implementa essa
distinção formalmente. A novidade não está em nenhuma peça; está na síntese.

### Cursor I-WAL (a retomada)

O cursor de retomada é o último ato de toda sessão, escrito **só depois** do
trabalho concluído:

```
FROM:  <SHA / estado de onde partimos>
THIS:  <o que esta sessão fez>
GOTO:  <a próxima ação>
```

E a regra de ouro da retomada: **toda retomada confirma o volátil na fonte
(via conector), nunca confia no cursor isolado.** A memória do modelo é
hipótese; a fonte é veredito. (Foi exatamente por seguir essa regra que esta
documentação descobriu que `main` não estava mais em `da46621` como dizia o
cursor de continuidade, mas em `1d6217e` — cinco merges adiante.)

---

## BLOCO 9 — METADATA (Metadados / Posicionamento e proveniência)

### 9.1 As cinco dimensões (o framework analítico da tese)

A RSL avaliou o framework e seus comparadores em cinco dimensões definidas
*a priori*:

| Dim | Pergunta | Posição do Atomic-DAG |
|---|---|---|
| **D1** Paradigma de estado | Como o estado persiste entre sessões? | `state.json` como fonte única, externo à sessão (extremidade de maior externalização) |
| **D2** Gramática de execução | A gramática é executável pelo runtime ou só representa? | BPMN como gramática de execução *com LLM como runtime* — cada tipo determina comportamento do assembler |
| **D3** Persistência/recuperação | Há protocolo formal com garantia de retomada? | WAL append-only com schema de tick |
| **D4** Schema de unidade atômica | Há schema formal da menor unidade? | Template Master de 9 blocos (este documento o instancia) |
| **D5** Classe/instância temporal | Distingue definição de instância com tempo? | ATÔMICO vs. NÓ(ATÔMICO, t) — resolve loops-sem-ciclos |

### 9.2 O claim central e seu escopo honesto

> **Cada componente do Atomic-DAG tem precedente isolado na literatura. A
> síntese específica das cinco dimensões em gramática de propósito geral não
> foi encontrada nas bases consultadas** — incluindo após buscas adversariais
> explicitamente projetadas para tentar refutá-la (sentido Popperiano).

A honestidade do escopo é parte da tese: o Claim 5 é "não encontrado nas bases
consultadas", **não** "ausência absoluta na literatura". ACM DL e IEEE Xplore
não foram consultados diretamente; a triagem foi de revisor único; ~60% das
fontes são preprints. Estas limitações estão declaradas, não escondidas.

### 9.3 Antecedentes (sobre quais ombros)

| Componente | Antecedente | Campo |
|---|---|---|
| Runtime ⊥ estado | L2MAC (2023), Blueprint First (2025) | Agentes LLM |
| Gramática de execução de processo | POEML (2022), Spalazzi et al. (2021) | Linguagens de processo |
| Atomicidade | A-MEM/Zettelkasten (2025), ARIES/ACID (1992) | Memória / BD |
| WAL | ARIES (Mohan et al., 1992), Event Sourcing (Fowler, 2005) | Bancos de dados |
| Classe/instância | Simula (Dahl & Nygaard, 1966) | OOP |

### 9.4 Lacunas declaradas (trabalho futuro)

1. **Benchmark comparativo** de continuidade multi-sessão (a mais urgente — sem ele, nenhum claim empírico de superioridade).
2. **AND gateway** com múltiplos cursores paralelos (o JOIN ainda não especificado).
3. **Overhead do assembler** medido (o "~50 linhas Python" é estimativa de design).
4. **Integração formal com MCP** (arquiteturalmente trivial, falta especificar).

### 9.5 Posição deste documento no roadmap

| Sprint | Relação com este documento |
|---|---|
| 0 – 2.K (closed) | Construíram a base que este documento descreve |
| **3** (FM-10) | Adicionará `streaming.py`; este doc passará por amendment de Bloco 5 quando o módulo nascer |
| 4 (Hello SOC + arXiv) | Este doc é candidato a artefato público acompanhando o manuscrito |
| 5 (reconcile + writer fix) | TD-001 fechada; Bloco 5 LOC do `writer.py` será atualizado |
| **6** (meta-uso / US-07) | **Este doc passa a ser um ATÔMICO operacional real**: `.atomic-dag/state.json` gerencia `DOC-SELF-001` como instância; a transição `check` deste arquivo passa a ser executável por `atomic-dag transition DOC-SELF-001 check`. **O sistema valida a si mesmo** — prova última da tese |

---

## Cursor desta documentação (I-WAL)

```
FROM:  pedido do operador — "leia recursivamente, compreenda a lógica do
       Atomic-DAG, e inicie uma documentação aplicando o próprio sistema a
       si mesmo"
THIS:  DOC-SELF-001 — o Atomic-DAG documentado como um ATÔMICO de 9 blocos,
       ancorado em main@1d6217e verificado via conector (não na memória),
       com notas terminológicas Popperianas (preâmbulo + §6) endereçando D13.
       Estado: in-progress → aguarda check (gate)
GOTO:  - fase 2.L mini (docs-only): incluir este doc em docs/ com sync
         de README + nota CLAUDE.md §1; cursor de saída do merge fecha
         A4 + endereça D13
       - Sprint 3 (3.A → 3.G): após merge 2.L, este doc não é tocado;
         possível amendment de Bloco 5 (LOC de streaming.py) só pós-3.G
       - Sprint 6 (US-07, meta-uso): este doc deixa de ser apenas
         pedagógico e passa a ser ATÔMICO operacional do framework

VERIFICADO via conector nesta sessão:
  - main HEAD = 1d6217e (merge PR #8, fase 2.K) — NÃO mais da46621
  - 9 módulos em src/atomic_dag/ presentes (fsm, transitions, wal verbatim)
  - STATUS.md confirma Sprint 2 fechada + fases 2.H/2.I/2.J/2.K mergeadas
  - próximo gate real: Sprint 3 (FM-10 / TD-003), FROM 1d6217e
```

---

**Fim de DOC-SELF-001.**
**Schema:** Template Master de 9 blocos (D4).
**Estado:** `in-progress` → aguardando gate (`check`) via merge da fase 2.L.
**Fonte de verdade:** `main@1d6217e`, verificado via conector GitHub em 2026-05-29.
