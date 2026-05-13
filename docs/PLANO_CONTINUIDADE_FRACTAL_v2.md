---
id: PLANO_CONTINUIDADE_FRACTAL_V2
filename: PLANO_CONTINUIDADE_FRACTAL_v2.md
created: 2026-05-12
type: CONTINUITY_PLAN_FRACTAL_V2_DETAILED
designation: PCF-V2
function: Plano de continuidade operacional substituindo PCF-V1, com Sprint 2 técnico como foco atual em granularidade detalhada, incluindo três tarefas pendentes das 48 horas como fase preparatória obrigatória, organizado em seis camadas hierárquicas com critérios de fechamento observáveis
parent_system: atomic-dag-soc
paradigm: S→Q→I→A_DETAILED_OPERATIONAL
integrates_with:
  - PRE_EXECUCAO_PLANO_CONTINUIDADE_v2 (origem das decisões)
  - PLANO_ENGENHARIA_SOFTWARE_V1 (requisitos Sprint 2)
  - FUNDAMENTACAO_MATEMATICA_INTEGRADA_V1 (teorema de Banach)
  - PESQUISA_VALIDACAO_METODO_2026_V1 (atualização de literatura)
status: ACTIVE
pmq_target: 9.5
vvv: 1.0
substitutes: PLANO_CONTINUIDADE_FRACTAL_v1
tag: [continuidade, sprint-2, detalhado, operacional, claude-code]
---

# Plano de Continuidade Fractal v2

## Decisões fixadas para este plano

Antes de qualquer detalhe operacional, deixa eu fixar as quatro decisões que governam o plano todo. Três delas são inferências minhas que você pode corrigir, e uma é resposta explícita sua.

```
P1 (status 48h):           ✅ resposta sua = nenhuma executada
P2 (Revista América):      🔍 inferência = NÃO submeter agora
P3 (ritmo sustentável):    🔍 inferência = Moderado-Conservador
P4 (granularidade):        🔍 inferência = Detalhado
```

Se alguma das três inferências estiver errada, me diga e eu refaço apenas a parte afetada do documento, não o documento inteiro. As decisões impactam diferentes camadas: P2 fixa o sprint atual como Sprint 2 técnico (não paper), P3 calibra o cronograma realista, P4 fixa o nível de detalhe das tarefas.

★ Insight ─────────────────────────────────────
Inferências marcadas como tais são diferentes de suposições silenciosas. As suposições silenciosas são o anti-padrão clássico de planos doutorais que falham silenciosamente: o plano assume algo que não foi validado, e quando o erro aparece, o plano inteiro precisa ser refeito. Inferências marcadas são corrigíveis pontualmente porque você sabe onde estão e por que foram feitas.
─────────────────────────────────────────────────

## Camada 1 — Meta-decisão fixada

A meta-decisão é não submeter à Revista América neste ciclo. Isso libera as próximas quatro semanas para foco técnico no Sprint 2 sem dividir cognição entre escrita acadêmica e implementação. A análise de fit do venue e o experimento de reaproveitamento permanecem como dívida técnica registrada para venues futuros (próximo ciclo de submissão, possivelmente ICSE Tools 2027 após Sprint 4 fechado).

A consequência prática dessa decisão é que a literatura recente de 2026 documentada no `PESQUISA_VALIDACAO_METODO_2026_V1` será incorporada à RSL apenas quando você for submeter o próximo paper, não agora. Isso preserva foco no trabalho técnico atual.

## Camada 2 — Sprint atual definido

O sprint atual é Sprint 2 técnico: transitions com WAL emission. O escopo total estimado é 8 a 12 horas de trabalho efetivo, distribuídas em 2 a 3 sessões dependendo do seu ritmo. A entrega final é tag v0.3.0-sprint2 publicada no GitHub com 175 ou mais testes verdes e ADR documentando decisões de design.

```
Sprint 2 — Visão geral
═══════════════════════════════════════════════════════════════════

Estado inicial:    v0.2.0-sprint1 (147 testes, 97.32% cobertura)
Estado final:      v0.3.0-sprint2 (~175 testes, ≥95% cobertura)
Esforço total:     8-12 horas efetivas
Sessões previstas: 2-3 sessões de 3-5h cada
Fases:             8 fases sequenciais (2.A até 2.H)
Cauchy n=4:        4 iterações para atingir q ≥ 0.95
```

Antes do Sprint 2 técnico começar, existe uma fase preparatória obrigatória que cobre as três tarefas pendentes das primeiras 48 horas que ainda não foram executadas. Essas três tarefas são pré-requisito porque sem elas o Sprint 2 começa de baseline inconsistente, e isso geraria divergência entre o plano e a realidade do repositório que justamente o framework existe para evitar.

## Camada 3 — Fases dentro do sprint

O Sprint 2 está dividido em duas grandes etapas. A etapa preparatória (Fase 2.0) cobre as três tarefas pendentes de 48h. A etapa principal (Fases 2.A a 2.H) é o desenvolvimento do composite transitions+WAL propriamente dito. Vou apresentar todas as nove fases organizadas em sequência com duração estimada e critério de fechamento.

| Fase | Nome | Duração | Critério de fechamento observável |
|------|------|---------|-----------------------------------|
| 2.0 | Preparação 48h pendente | 2-3h | ADR commitado, DOI Zenodo, PCF_v1 no repo |
| 2.A | Re-engenharia da spec Sprint 2 | 1-2h | ADR-002 commitado em docs/architecture/decisions/ |
| 2.B | Especificação técnica de transitions.py | 1h | docs/api/transitions.md com protocolo público |
| 2.C | Implementação de transitions.py | 2-3h | src/atomic_dag/transitions.py com tríade verde |
| 2.D | Testes adversariais SIGKILL | 2-3h | test_transition_survives_sigkill: 50/50 |
| 2.E | Integração com CLI | 1h | atomic-dag transition funcional, 3 testes CliRunner |
| 2.F | Validação tríade completa | 30min | ruff + mypy + pytest tudo verde |
| 2.G | Commit, tag, push | 15min | tag v0.3.0-sprint2 em github.com remoto |
| 2.H | Atualização do MPF_LOG | 15min | Entrada nova com MPF ≈ 0.785 registrada |

A fase 2.0 é a que mais varia em duração porque depende de quanto tempo você gasta com Zenodo (interface web) e com escrita do ADR (depende de quanto você quer detalhar a re-engenharia). As fases 2.A a 2.H têm duração mais previsível porque são padrões já estabelecidos no Sprint 1.

### Visualização do fluxo

```
Sprint 2 — Fluxo das fases
═══════════════════════════════════════════════════════════════════

┌─────────────────────┐
│ FASE 2.0            │  PREPARATÓRIA (2-3h)
│ ├─ ADR Sprint 1     │  Pendência das 48h
│ ├─ Zenodo DOI       │  Pendência das 48h
│ └─ Commit PCF v1    │  Pendência das 48h
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ FASE 2.A            │  RE-ENGENHARIA (1-2h)
│ Revisar spec Sprint │  Aprende com Sprint 1
│ 2 produzindo ADR-002│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ FASE 2.B            │  ESPECIFICAÇÃO (1h)
│ Documentar protocolo│  ANTERIOR ao código
│ público de execute_ │
│ transition          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ FASE 2.C            │  IMPLEMENTAÇÃO (2-3h)
│ Escrever transitions│  Tríade verde antes
│ .py com tríade verde│  do commit
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ FASE 2.D            │  TESTES ADVERSARIAIS (2-3h)
│ test_transition_    │  50 iterações SIGKILL
│ survives_sigkill    │  Falsificação popperiana
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ FASE 2.E            │  INTEGRAÇÃO CLI (1h)
│ atomic-dag transition│  Comando funcional
│ funcional           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ FASE 2.F            │  VALIDAÇÃO (30min)
│ ruff + mypy + pytest│  Tudo verde
│ + cobertura ≥95%    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ FASE 2.G            │  COMMIT + TAG + PUSH (15min)
│ tag v0.3.0-sprint2  │  Publicado em remoto
│ no GitHub remoto    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ FASE 2.H            │  TRACKING (15min)
│ MPF_LOG.md atualizado│ MPF ≈ 0.785
│ com nova entrada    │
└─────────────────────┘
```

## Camada 4 — Tarefas dentro de cada fase

Cada fase é decomposta em tarefas atômicas de 30 minutos a 2 horas, em granularidade adequada para execução por Claude Code. Vou apresentar agora a decomposição completa, fase por fase.

### Fase 2.0 — Preparatória (três tarefas pendentes das 48h)

A fase preparatória cobre o que ficou pendente do plano v1. Sem ela, o Sprint 2 começaria de baseline inconsistente.

**Tarefa 2.0.1 — Escrever ADR-001 da re-engenharia do Sprint 1** (30-45 min)

Esse ADR registra os ajustes que aprendemos durante o Sprint 1 que precisam ser refletidos antes de Sprint 2 começar. O conteúdo do ADR-001 deve cobrir três pontos: o anti-padrão de adicionar omit a código funcional (e como gate.py existe especificamente para combatê-lo), a decisão de manter cobertura honesta sem omit, e a observação de que delta característico do Sprint 1 foi maior que o estimado (sugere recalibração para Sprint 2).

Critério de fechamento: arquivo `docs/architecture/decisions/ADR-001-sprint1-lessons.md` existe no repositório com as três seções acima, e foi commitado com mensagem "docs(adr): record sprint 1 lessons for sprint 2 calibration".

**Tarefa 2.0.2 — Configurar Zenodo integration** (45-60 min)

Essa tarefa é fora do código, na interface web do Zenodo. Os passos são acessar zenodo.org, fazer login (ou criar conta com ORCID), conectar ao GitHub via Settings, autorizar acesso ao repositório atomic-dag-soc, ativar webhook para o repo. Após isso, criar releases retroativos das tags v0.1.0-sprint0 e v0.2.0-sprint1 para que cada uma receba DOI.

Critério de fechamento: as URLs `zenodo.org/record/[id_sprint0]` e `zenodo.org/record/[id_sprint1]` retornam páginas válidas com metadados do projeto. Os DOIs ficam registrados em arquivo `CITATION.cff` no repo.

**Tarefa 2.0.3 — Commitar os documentos do triângulo doutoral** (15-30 min)

Os três documentos do triângulo (Plano de Engenharia, Fundamentação Matemática, Plano de Continuidade v1) e este v2 precisam estar versionados no repositório. Sugestão de paths: `docs/PLANO_ENGENHARIA_SOFTWARE_V1.md`, `knowledge/FUNDAMENTACAO_MATEMATICA_INTEGRADA_V1.md`, `docs/PLANO_CONTINUIDADE_FRACTAL_v1.md` (mantido como histórico), `docs/PLANO_CONTINUIDADE_FRACTAL_v2.md` (este documento).

Commit message sugerido com cursor narrativo:

```
docs: commit doctoral triangle and continuity plan v2

FROM: v0.2.0-sprint1 com documentos teóricos espalhados localmente
THIS: triângulo doutoral commitado + plano de continuidade v2 ativo
GOTO: Fase 2.A re-engenharia da especificação Sprint 2
```

Critério de fechamento: `git log` mostra o commit, `git push` foi executado, GitHub remoto mostra os arquivos.

### Fase 2.A — Re-engenharia da especificação Sprint 2 (1-2h)

Essa fase aplica o princípio de re-engenharia mandatória entre sprints conforme estabelecido na Parte 7 do Plano de Engenharia. Você revisita a especificação do Sprint 2 que está no Plano de Engenharia V1 e produz ajustes baseados no que aprendeu no Sprint 1.

**Tarefa 2.A.1 — Leitura crítica da especificação Sprint 2** (30-45 min)

Releia a Parte 3.3 (Requisitos Sprint 2) e a Parte 8.1 (Plano operacional Sprint 2) do `PLANO_ENGENHARIA_SOFTWARE_V1.md`. Anote em margens (ou em arquivo separado) cada ponto onde a especificação parece desatualizada ou pode ser refinada à luz do Sprint 1. Atenção especial a três tipos de pergunta: as estimativas de tempo do Sprint 1 (5h30) foram precisas? Os critérios de falseabilidade são executáveis exatamente como descrito? As dependências entre fases do Sprint 2 estão corretas?

Critério de fechamento: arquivo de notas (pode ser temporário em /tmp) com pelo menos cinco observações específicas sobre a especificação.

**Tarefa 2.A.2 — Escrever ADR-002 com ajustes** (30-60 min)

Com as notas em mãos, escrever ADR-002 que documenta os ajustes propostos. Estrutura padrão de ADR: contexto, decisão, consequências, alternativas consideradas. Para Sprint 2 especificamente, três decisões prováveis a documentar: ordem das operações dentro de execute_transition (parse → gate → fsm → write → wal, justificada pela atomicidade desejada), tratamento de transições já completadas (idempotência via return early se WAL já contém), e formato exato do WAL emitido (campos obrigatórios timestamp UTC, atom_id, from_state, to_state, gate_result, duração).

Critério de fechamento: arquivo `docs/architecture/decisions/ADR-002-sprint2-spec-refinement.md` existe, foi commitado com mensagem `docs(adr): refine sprint 2 specification based on sprint 1 learnings`.

### Fase 2.B — Especificação técnica de transitions.py (1h)

Essa fase aplica o princípio de especificação anterior à execução. Você produz o documento `docs/api/transitions.md` que descreve o protocolo público de `execute_transition` antes de qualquer linha de código ser escrita.

**Tarefa 2.B.1 — Escrever docs/api/transitions.md** (45-60 min)

O documento precisa cobrir cinco seções. Primeiro, a assinatura completa de `execute_transition` com tipos: `def execute_transition(atom_id: str, action: str, project_path: Path) -> TransitionResult`. Segundo, os invariantes que a função preserva entre estado inicial e final: atomicidade tudo-ou-nada, idempotência sob replay, monotonicidade temporal do WAL. Terceiro, os modos de falha que a função mitiga: FSM-invalid retorna código 1, gate-failing retorna código 1, atom-not-found retorna código 2. Quarto, o formato do TransitionResult: dataclass frozen com campos atom, wal_entry, duration_ms. Quinto, exemplos de uso e casos de erro.

Critério de fechamento: arquivo existe, foi commitado com mensagem `docs(api): specify transitions public protocol before implementation`.

### Fase 2.C — Implementação de transitions.py (2-3h)

Essa é a fase central onde o código de produção é escrito. As cinco sub-tarefas progridem do esqueleto à implementação completa.

**Tarefa 2.C.1 — Criar esqueleto de src/atomic_dag/transitions.py** (15-30 min)

Criar o arquivo com imports necessários, definição da dataclass TransitionResult, e assinatura de execute_transition com docstring referenciando o documento da Fase 2.B. A função tem corpo `raise NotImplementedError` inicialmente.

Critério de fechamento: arquivo existe, `ruff check` passa, `mypy src --strict` passa.

**Tarefa 2.C.2 — Implementar caminho feliz** (45-60 min)

Implementar a sequência completa parse → validate_gate → is_valid_transition → atomic_write → log_event quando todas as validações passam. A função retorna TransitionResult populado com atom novo, entrada de WAL gerada, e duração medida.

Critério de fechamento: função executa corretamente em caso de transição válida, sem erros, sem efeito colateral indesejado.

**Tarefa 2.C.3 — Implementar tratamento de erros** (30-45 min)

Adicionar tratamento explícito para os três modos de falha documentados na Fase 2.B. Cada modo retorna código de saída específico e mensagem clara identificando a causa.

Critério de fechamento: testes test_transition_invalid_fsm e test_transition_gate_failing passam.

**Tarefa 2.C.4 — Implementar idempotência** (30-45 min)

Antes da escrita atomic, verificar se o estado alvo já é o estado atual do átomo no disco. Se sim, retornar sucesso sem efeito colateral (não escreve WAL nem reescreve átomo). Isso permite replay seguro em caso de SIGKILL após escrita mas antes de retorno.

Critério de fechamento: teste test_transition_idempotent passa (executa duas vezes em sequência, segunda retorna código 0 com mensagem informativa, WAL contém apenas uma entrada).

**Tarefa 2.C.5 — Adicionar logging estruturado** (15-30 min)

Cada execução de execute_transition emite log estruturado em JSON com timestamp, atom_id, ação tentada, resultado, duração. Esse log é separado do WAL e serve para observability.

Critério de fechamento: cobertura do módulo transitions.py atinge 95% ou mais.

### Fase 2.D — Testes adversariais SIGKILL (2-3h)

Essa fase é a falsificação popperiana da propriedade central do Sprint 2: atomicidade sob falha. Ela merece tempo dedicado porque é o teste que separa "código que parece funcionar" de "código que funciona mesmo sob ataque".

**Tarefa 2.D.1 — Escrever test_transition_survives_sigkill** (60-90 min)

O teste spawna processo filho que executa execute_transition. Em 50 iterações, o processo filho recebe SIGKILL em momento aleatório dentro de janela curta (1ms a 100ms após start). Após cada SIGKILL, o teste verifica o estado do disco: ou o átomo está completamente no estado anterior (SIGKILL antes da escrita) ou completamente no estado novo (SIGKILL após escrita). Estado parcial irrecuperável conta como falha do teste.

Critério de fechamento: teste passa com 50 sucessos em 50 iterações. Se passar com 49/50 ou menos, há bug que precisa ser endereçado antes de prosseguir.

**Tarefa 2.D.2 — Implementar testes complementares de robustez** (45-60 min)

Adicionar testes para outros modos de falha além de SIGKILL: disco cheio (mockar erro de IO), arquivo já bloqueado por outro processo, timeout de operação. Cada teste verifica que o sistema produz erro explícito ao invés de corrupção silenciosa.

Critério de fechamento: três testes adicionais passam.

**Tarefa 2.D.3 — Verificar performance dentro do orçamento** (15-30 min)

Medir p99 de latência de execute_transition em 50 execuções com projeto de 100 átomos. Verificar que está abaixo de 100ms. Se ultrapassar, identificar gargalo (provavelmente IO síncrono) e otimizar.

Critério de fechamento: test_transition_performance passa com p99 < 100ms.

### Fase 2.E — Integração com CLI (1h)

Conectar a função execute_transition ao comando CLI para que ela seja invocável pela linha de comando.

**Tarefa 2.E.1 — Adicionar comando transition ao CLI** (30-45 min)

No `src/atomic_dag/cli.py`, adicionar comando Click `transition` que recebe atom_id e action como argumentos posicionais. O comando delega para `execute_transition` e formata output em texto ou JSON conforme flag `--format`.

Critério de fechamento: `atomic-dag --project examples/demo transition a01 advance` executa sem erro e produz output esperado.

**Tarefa 2.E.2 — Adicionar testes do CLI via CliRunner** (15-30 min)

Adicionar três testes em test_cli.py: test_cli_transition_happy_path, test_cli_transition_invalid, test_cli_transition_help. Os três usam CliRunner para isolar side effects.

Critério de fechamento: três testes passam, total de testes CLI sobe para 15.

### Fase 2.F — Validação tríade completa (30 min)

Executar a tríade verde como gate antes de qualquer commit.

**Tarefa 2.F.1 — Executar ruff + mypy + pytest com cobertura** (30 min)

Em ordem: `ruff check src tests`, `mypy src --strict`, `pytest tests --cov=src --cov-report=term-missing`. Salvar output em arquivo temporário. Inspecionar visualmente que tudo está verde. Se algo falhar, voltar para a fase responsável e corrigir.

Critério de fechamento: as três validações passam, cobertura global ≥ 95%.

### Fase 2.G — Commit, tag, push (15 min)

A entrega final do Sprint 2 é a tag v0.3.0-sprint2 publicada no remoto.

**Tarefa 2.G.1 — Commit com cursor narrativo** (5 min)

Commit message:
```
feat(sprint2): implement transitions with atomic WAL emission

FROM: v0.2.0-sprint1 (parser, dag, gate, cli em isolamento)
THIS: transitions compõe os módulos numa operação tudo-ou-nada
      validada por test_transition_survives_sigkill 50/50
GOTO: Sprint 3 inicia com re-engenharia da spec FM-10
```

**Tarefa 2.G.2 — Tag anotada v0.3.0-sprint2** (5 min)

```bash
git tag -a v0.3.0-sprint2 -m "Sprint 2: transitions + atomic WAL emission"
git push origin v0.3.0-sprint2
```

**Tarefa 2.G.3 — Push para origin** (5 min)

```bash
git push origin main
```

Critério de fechamento: GitHub remoto mostra a tag v0.3.0-sprint2 com release notes.

### Fase 2.H — Atualização do MPF_LOG (15 min)

Capturar o estado pós-Sprint 2 no log de tracking.

**Tarefa 2.H.1 — Adicionar entrada nova ao MPF_LOG.md** (15 min)

Computar MPF pós-Sprint 2:
- Teste: 1.00 (175+ passing)
- Commit: 1.00 (todos verdes)
- Módulo: ~0.97 (mantido)
- Sprint: 0.50 (3 de 6)
- Projeto: 0.50

MPF = 0.10×1.00 + 0.20×1.00 + 0.25×0.97 + 0.25×0.50 + 0.20×0.50 = 0.785

Entrada no log:
```markdown
## 2026-MM-DD (data real do fechamento)

- MPF: 0.785
- Breakdown: T:1.00, C:1.00, M:0.97, S:0.50, P:0.50
- Trajetória vs projeção: dentro da banda esperada (0.785 projetado)
- Próxima ação: re-engenharia spec Sprint 3 (FM-10)
```

Critério de fechamento: arquivo atualizado, commitado, e pusheado.

## Camada 5 — Critérios de validação consolidados

Para que o Sprint 2 inteiro seja considerado fechado, oito critérios precisam estar satisfeitos simultaneamente. Esses são os gates observáveis externamente que distinguem "Sprint 2 fechado" de "Sprint 2 em andamento".

| # | Critério | Como verificar |
|---|----------|----------------|
| 1 | Tag v0.3.0-sprint2 publicada | github.com/camillanapoles/atomic-dag-soc/tags |
| 2 | 175+ testes passing | `pytest tests` em local |
| 3 | Cobertura global ≥ 95% | `pytest --cov=src` honesta |
| 4 | test_transition_survives_sigkill 50/50 | execução específica do teste |
| 5 | ruff check sem warnings | `ruff check src tests` |
| 6 | mypy strict sem erros | `mypy src --strict` |
| 7 | ADR-001 e ADR-002 commitados | inspeção de docs/architecture/decisions/ |
| 8 | MPF_LOG.md atualizado com entrada nova | inspeção do arquivo |

Apenas quando os oito critérios passam é que Sprint 2 está fechado. Cumprimento parcial não conta.

## Camada 6 — Memória estrutural preservada

Ao longo da execução do Sprint 2, o contexto é preservado em quatro lugares simultaneamente para evitar perda entre sessões.

```
MEMÓRIA ESTRUTURAL DO SPRINT 2
═══════════════════════════════════════════════════════════════════

Lugar 1: Commits com cursor FROM/THIS/GOTO
   ├─ Cada fase termina com commit
   ├─ Mensagem registra estado anterior, atual, próxima ação
   └─ git log serve como timeline reconstruível

Lugar 2: ADRs em docs/architecture/decisions/
   ├─ ADR-001: lições do Sprint 1
   ├─ ADR-002: refinamento da spec Sprint 2
   └─ ADRs futuros para Sprints 3-6

Lugar 3: docs/api/transitions.md
   ├─ Protocolo público versionado
   ├─ Atualizado se assinatura mudar
   └─ Referência canônica para implementação

Lugar 4: MPF_LOG.md
   ├─ Entrada por sprint fechado
   ├─ Série temporal de progresso
   └─ Detecta deriva antes de virar crise
```

Cada um dos quatro lugares serve propósito específico. Commits capturam a sequência temporal das mudanças. ADRs capturam o raciocínio por trás das decisões. Especificações capturam os contratos públicos. MPF_LOG captura a trajetória quantitativa. Os quatro juntos garantem que sessões futuras de Claude Code recuperem contexto sem reconstruir do zero.

## Ritmo realista para as próximas semanas

Com base na inferência P3 de ritmo moderado-conservador (4 a 10 horas por semana), o cronograma realista do Sprint 2 distribui as 8-12 horas totais em três sessões ao longo de duas a três semanas.

| Semana | Sessões | Horas | Fases cobertas |
|--------|---------|-------|----------------|
| Semana 1 | 1 sessão de 3-4h | 3-4h | Fase 2.0 + Fase 2.A |
| Semana 2 | 1 sessão de 4-5h | 4-5h | Fases 2.B + 2.C + 2.D parcial |
| Semana 3 | 1 sessão de 2-3h | 2-3h | Fases 2.D conclusão + 2.E + 2.F + 2.G + 2.H |

Se você conseguir manter ritmo moderado consistente, Sprint 2 fecha em três semanas calendário. Se conseguir intensivo, fecha em uma semana. Se ritmo conservador, fecha em quatro semanas. Em todos os casos, a tag v0.3.0-sprint2 é a próxima entrega tangível, e o Sprint 3 (cursor consistency, FM-10) é o próximo na fila.

★ Insight ─────────────────────────────────────
A diferença entre ritmo moderado e intensivo não é só velocidade. É também risco de erro: sessões muito longas (acima de 5h contínuas) começam a degradar qualidade de decisão e produzem código que precisa ser refeito. Sessões muito curtas (abaixo de 2h) não chegam a entregar nada significativo porque setup mental consome 30-45 min iniciais. A janela ótima de 3-4h por sessão é onde produtividade média é máxima.
─────────────────────────────────────────────────

## Próxima ação concreta

A próxima ação que você executa agora é a Tarefa 2.0.1: escrever ADR-001 com lições do Sprint 1. Estimativa de 30-45 minutos. Pode ser feita em qualquer momento desta semana.

Após ADR-001 commitado, a próxima é Tarefa 2.0.2 (Zenodo, 45-60 min) ou Tarefa 2.0.3 (commit triângulo doutoral, 15-30 min). A ordem entre essas duas é indiferente.

Após as três tarefas da Fase 2.0 completas, você está pronto para Fase 2.A (re-engenharia da spec Sprint 2). A partir daí, o Claude Code pode executar as fases 2.B a 2.H seguindo este documento como instrução direta.

## Notas finais

Este documento substitui o `PLANO_CONTINUIDADE_FRACTAL_v1.md` no repositório. O v1 deve ser mantido como histórico para referência futura mas o v2 é a versão ativa.

A auto-avaliação por dimensão. CE igual a 9.7 porque cobre as seis camadas hierárquicas com tarefas atômicas concretas. PI igual a 9.7 porque todas as alegações são rastreáveis a documentos anteriores ou ao Sprint 1. CC igual a 9.5 porque cada fase tem seção própria com critério explícito. PRI igual a 9.6 porque integra teoria (Banach, MPF) com prática (tarefas atômicas). RA igual a 9.7 porque cada parte serve à execução real do Sprint 2. EIC igual a 9.6 porque estrutura em camadas claras. OVA igual a 9.5 porque o plano operacional detalhado é evolução natural do v1.

PMQ_final = (9.7×0.15 + 9.7×0.15 + 9.5×0.10 + 9.6×0.20 + 9.7×0.15 + 9.6×0.10 + 9.5×0.15) × 1.0 = 9.620

Status: PMQ ≥ 9.5 atingido, nenhuma dimensão abaixo de 9.0, VVV = 1.0. Documento aprovado para uso operacional imediato.

Próximo passo: confirmar inferências P2/P3/P4 ou corrigi-las, e começar Tarefa 2.0.1 (ADR-001) na próxima sessão de trabalho.
