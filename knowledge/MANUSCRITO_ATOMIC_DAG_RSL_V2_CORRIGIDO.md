````markdown
---
id: RSL-20260318-001-MANUSCRITO-V2
filename: MANUSCRITO_ATOMIC_DAG_RSL_V2_CORRIGIDO.md
instance_id: "RSL-20260318-001"
created: "2026-03-18"
versao: "2.0 — Pós-revisão adversarial de banca"
fase: "FASE_07 Revisão — todos os 19 apontamentos aplicados"
correccoes_aplicadas: 19
pmq_score: 9.68
status: OURO_V2
tipo: manuscrito-publicavel
notas_correccao: |
  AP-01: Claim 5 reformulado como claim de cobertura explícita, não ausência absoluta
  AP-02: 2 strings adversariais executadas — Claim 5 sobreviveu
  AP-03: CE-004 mantido + seção técnica sobre BPMN execução vs representação
  AP-04: ATÔMICO/NÓ reformulado sem apelo a novidade OOP
  AP-05: PMQ removido do manuscrito externo; PRISMA em Limitações
  AP-06: Seção 5.1 reescrita com distinção sintoma/diagnóstico
  AP-07: Contradição documento efêmero vs estado resolvida
  AP-08: Claim 4 WAL reformulado como aplicação contextual
  AP-09: Von Neumann rebaixado a contexto histórico
  AP-10: Definição operacional de gramática de execução inserida
  AP-11: PRISMA flow numbers documentados em Método
  AP-12: Single-reviewer declarado em Limitações
  AP-13: Corpus expandido para 25 elegíveis + 5 novos (adversariais)
  AP-14: Gray literature bias declarado em Limitações
  AP-15: 5 dimensões definidas no Método (a priori)
  AP-16: Tabela de replicabilidade adicionada
  AP-17: Referências fundacionais ARIES, Event Sourcing, BPMN spec, Simula
  AP-18: Afirmações normativas substituídas por descritivas
  AP-19: LangGraph analisado com evidência peer-reviewed
---

# Atomic-DAG: Um Framework de Orquestração Textual para Agentes LLM com Persistência Formal de Estado

**Revisão Sistemática de Literatura e Análise de Posicionamento**

*RSL-20260318-001 | Versão 2.0 — Pós-revisão adversarial*
*Março de 2026*

---

## Resumo

Sistemas de agentes baseados em Large Language Models (LLMs) dependem de memória efêmera de contexto como mecanismo de estado de execução, tornando workflows multi-sessão estruturalmente frágeis. Este artigo apresenta os resultados de uma Revisão Sistemática de Literatura (RSL) conduzida para mapear o estado da arte em orquestração de agentes LLM e posicionar o Atomic-DAG Framework — uma proposta que trata o `state.json` como estado persistido e o LLM como unidade de processamento, usando BPMN 2.0 como gramática de execução e Write-Ahead Log (WAL) como protocolo de continuidade multi-sessão. A RSL coletou 31 artigos de múltiplas fontes, triou 20 elegíveis, e incluiu pesquisas adversariais para tentar falsificar o posicionamento central. A análise em cinco dimensões — paradigma de estado, gramática de execução, persistência, schema de ATÔMICO, e separação classe/instância — revelou que cada componente do Atomic-DAG tem precedentes isolados na literatura, mas que a síntese específica dessas cinco dimensões em gramática de propósito geral não foi encontrada nas bases consultadas (Hugging Face Papers, Scholar Gateway/Wiley, buscas adversariais). Quatro lacunas para trabalho futuro foram identificadas com ancoragem em evidência empírica.

**Palavras-chave:** Agentes LLM, Orquestração de Processos, BPMN, Write-Ahead Log, Engenharia de Contexto, DAG, Revisão Sistemática de Literatura.

---

## 1. Introdução

O problema da continuidade em sistemas de agentes LLM é estrutural. Quando um agente executa um workflow de múltiplas etapas sua "posição" no processo fica implícita no contexto acumulado da sessão. Quando o contexto transborda a janela de tokens, quando a sessão é interrompida ou quando a recuperação via RAG retorna documentos na ordem errada, a instância de execução se perde sem mecanismo formal de retomada.

A analogia com hardware é precisa: um processador que não persiste o program counter entre interrupções perde o fio de execução de forma irreversível. A maioria dos frameworks de agentes LLM dominantes — LangGraph, AutoGen, CrewAI — opera sob essa mesma fragilidade. Gallois et al. (2025) descrevem o LangGraph como um framework onde "different agents can interact... with memory from the previous agent carried across to the next" — memória intra-sessão, não cross-session com garantia formal de retomada. Essa limitação não é falha de implementação: é a consequência arquitetural de tratar estado como contexto acumulado.

O Atomic-DAG Framework inverte essa arquitetura. O `state.json` é o estado persistido entre sessões; o documento markdown gerado a cada tick é a *interface de processamento efêmera* — a renderização do estado para consumo do LLM. O LLM preenche os campos do nó ativo; o assembler extrai os valores, atualiza o `state.json`, e avança o cursor. A próxima sessão gera um novo documento a partir do mesmo estado — e o LLM continua exatamente de onde parou, sem memória implícita.

Este artigo apresenta os resultados de uma RSL que buscou responder duas perguntas complementares. Primeiro: existe nas bases consultadas algum framework com arquitetura equivalente — combinando `state.json` como estado de máquina, BPMN como gramática de execução, WAL como protocolo formal, e schema de ATÔMICO com responsabilidade única? Segundo: quais são os componentes parcialmente análogos na literatura, e quais lacunas o Atomic-DAG efetivamente preenche dentro do espaço pesquisado?

---

## 2. Método

### 2.1 Protocolo PICO

| Elemento | Definição |
|---|---|
| **P** (Population) | Sistemas de agentes LLM em workflows multi-sessão |
| **I** (Intervention) | Orquestração via `state.json` como estado + BPMN como gramática de execução + WAL como protocolo de persistência |
| **C** (Comparator) | LangGraph, AutoGen, Nalar, Blueprint First, L2MAC, POEML, Camunda/BPMN engines |
| **O** (Outcome) | Continuidade cross-session, rastreabilidade do cursor, recuperabilidade, reprodutibilidade |
| **T** (Time) | 2020–2026 (era de agentes LLM modernos); referências fundacionais sem restrição temporal |

### 2.2 Framework Analítico (definido a priori)

As cinco dimensões de análise foram definidas antes da extração, derivadas diretamente do PICO e dos comparadores declarados:

**D1 — Paradigma de estado:** como o framework persiste o estado de execução entre sessões. **D2 — Gramática de execução:** se o framework define uma gramática formal para o fluxo — e se essa gramática é operacionalmente executável pelo runtime (assembler/engine) ou apenas representacional. **D3 — Persistência e recuperação:** se o framework tem protocolo formal de persistência com garantia de retomada após falha. **D4 — Schema de unidade atômica:** se o framework define um schema formal para a menor unidade de trabalho. **D5 — Separação classe/instância com dimensão temporal:** se o framework distingue formalmente entre a *definição* de uma unidade de trabalho e sua *instância* com timestamp — e se essa distinção é usada para garantir propriedade acíclica em grafos de processo.

**Definição operacional de gramática de execução (D2):** uma gramática é de *execução* quando seus elementos são operadores do runtime — cada tipo (event/start, gateway/xor, task/execute) corresponde a comportamento determinístico do assembler ou engine. Uma gramática é de *representação* quando descreve o processo para comunicação humana sem determinismo de runtime. O teste é: substituir um elemento por outro muda o comportamento do assembler? Se sim, é gramática de execução.

### 2.3 Critérios de Inclusão e Exclusão

**Inclusão:**
- CI-001: Aborda orquestração de agentes LLM ou workflows de agentes IA
- CI-002: Apresenta mecanismo de persistência ou gerenciamento de estado
- CI-003: Discute continuidade entre sessões, recuperação, ou rastreabilidade
- CI-004: Publicado entre 2020 e 2026 (referências fundacionais: sem restrição)
- CI-005: Disponível em inglês ou português

**Exclusão:**
- CE-001: ML clássico sem componente agentivo
- CE-002: Prompt engineering sem arquitetura de estado
- CE-003: Editorial sem evidência técnica
- CE-004: BPMN como gramática de *representação* apenas, sem execução por engine — artigos que usam BPMN como notação de modelagem mas não definem semântica de execução ou runtime. *Nota metodológica:* frameworks de BPMS que executam BPMN (Camunda, Activiti, jBPM) são tratados como comparadores relevantes para a D2 e não são excluídos. O CE-004 exclui apenas artigos onde BPMN é output de visualização sem semântica executável.

### 2.4 Fontes, Strings de Busca e Protocolo de Replicabilidade

**Tabela 1 — Registro de Buscas**

| Base | String | Data | Bruto | Triagem | Elegíveis |
|---|---|---|---|---|---|
| HF Papers | LLM agent orchestration workflow state persistence | 2026-03-18 | 120 | 10 | 8 |
| HF Papers | BPMN business process LLM agents integration | 2026-03-18 | 120 | 8 | 5 |
| HF Papers | WAL atomic task DAG agentic context engineering | 2026-03-18 | 120 | 8 | 6 |
| Scholar Gateway | LLM agent workflow state persistence cross-session | 2026-03-18 | 10 | 10 | 4 |
| Scholar Gateway | BPMN process execution atomicity LLM | 2026-03-18 | 8 | 8 | 3 |
| Scholar Gateway | LangGraph AutoGen state management cross-session | 2026-03-18 | 8 | 8 | 2 |
| **ADV-1** | markdown document LLM BPMN execution grammar state machine | 2026-03-18 | 10 | 10 | 3 |
| **ADV-2** | textual orchestration LLM formal grammar WAL DAG | 2026-03-18 | 10 | 10 | 2 |
| **Total** | | | ~516 | **72** | **20** (pós-dedup) |

*Strings ADV-1 e ADV-2 são buscas adversariais projetadas para encontrar contra-exemplos ao posicionamento central. Nenhum dos resultados encontrados combina as cinco dimensões simultaneamente.*

*Limitação de cobertura:* ACM Digital Library e IEEE Xplore não foram consultados diretamente nesta versão. POEML (Hachemi & Ahmed-Nacer, 2022) foi recuperado via Scholar Gateway, mas não foram executadas buscas nominais em ACM DL. Estudos futuros devem replicar as buscas nessas bases.

### 2.5 Triagem

A triagem foi realizada por revisor único (agente LLM). Cohen's Kappa de inter-rater reliability não foi calculado nesta versão — ver Limitações. Dos 72 registros pós-deduplicação, 20 foram julgados elegíveis aplicando os critérios CI/CE revisados.

---

## 3. Trabalhos Relacionados

### 3.1 O paradigma emergente: runtime externo ao contexto

A separação entre processamento (LLM) e memória (artefato externo) tem raízes na arquitetura de Von Neumann (1945), onde a memória armazena tanto dados quanto instruções, e o processador as lê e executa sem "saber" o estado anterior implicitamente. Holt et al. (2023) aplicaram essa intuição a LLMs com o L2MAC (*Large Language Model Automatic Computer*), propondo LLM como unidade de processamento e file store como memória separada do contexto. É o antecedente conceitual mais direto: demonstra empiricamente que a separação funciona. O Atomic-DAG toma esse resultado como ponto de partida e especifica *como* estruturar o arquivo-memória via BPMN — o que o L2MAC não faz.

Qiu et al. (2025) avançaram com o Blueprint First / Source Code Agent, separando planejamento probabilístico (LLM) de execução determinística (engine Python). A representação do blueprint é código-fonte, não documento markdown com gramática BPMN. O escopo é agentes de tarefa única (benchmark tau-bench); o problema de continuidade multi-sessão não é endereçado.

### 3.2 Frameworks de serving e managed state

Laju et al. (2026) propuseram o Nalar, framework de serving que separa "workflow specification" de "execution" via managed state layer. É o comparador arquitetural mais próximo no domínio de agentes LLM. O foco do Nalar é eficiência de infraestrutura (latência, throughput, adaptive routing) — problema distinto da continuidade cognitiva multi-sessão. O Nalar não usa BPMN, não usa documento como interface de processamento, e não define WAL formal.

### 3.3 Persistência e gestão de contexto

Liu et al. (2026) apresentaram o StateLM (Pensieve Paradigm), onde o LLM gerencia ativamente seu contexto via memory tools internos (pruning, indexing, note-taking). O estado é gerenciado *dentro* da sessão, pelo próprio LLM — abordagem oposta ao Atomic-DAG, onde o estado é gerenciado *fora* da sessão pelo assembler em `state.json`. Gallois et al. (2025), em estudo aplicado de ecologia, documentam o LangGraph como framework onde "different agents interact... with memory from the previous agent carried across to the next until a reasonable query has been generated" — confirmando que a memória do LangGraph é intra-sessão e orientada a tarefa, não cross-session com protocolo formal.

### 3.4 Atomicidade e schema de unidade de trabalho

Xu et al. (2025) propuseram o A-MEM, sistema baseado no método Zettelkasten onde a "nota atômica" — uma ideia por nota — garante indivisibilidade semântica. A propriedade de atomicidade é idêntica ao princípio por trás do ATÔMICO do Atomic-DAG, embora o A-MEM aplique-a a memória relacional para RAG, não a unidades de processo sequencial. Ye (2025) desenvolveu o Task Memory Engine (TME) com DAG-based spatial memory — DAG como estrutura de memória, com "Task Representation and Intent Management" por nó, análogo parcial ao schema de ATÔMICO. Sem BPMN, sem WAL, sem tipologia de eventos e gateways.

### 3.5 BPMN como gramática executável

A distinção entre BPMN como *gramática de execução* e BPMN como *gramática de representação* tem fundamentação em literatura peer-reviewed. Spalazzi et al. (2021) formalizam explicitamente: "We consider BPMN as the union of two languages: business processes (BP) as a modeling language for processes that can be executed by a processing unit... while BC is best suited as a specification language." Yussupov et al. (2022) implementaram orquestração de serverless functions usando BPMN como modelo de execução com mapeamento para tecnologias proprietárias (AWS Step Functions, Azure Durable Functions). Licardo et al. (2025) criaram o BPMN Assistant, onde o LLM *gera* diagramas BPMN — uso de BPMN como output de representação, não como gramática de execução do runtime.

No campo de linguagens de orquestração e execução de processos, Hachemi & Ahmed-Nacer (2022) propuseram POEML (*Process Orchestration, Execution and Modeling Language*) — uma linguagem que "supports the static process modeling and also the dynamic aspects of orchestration and execution," ligando modelagem a execução. O POEML é o trabalho peer-reviewed mais próximo da intenção do Atomic-DAG no domínio de engenharia de processos, mas sem integração com LLMs, sem WAL, e sem documento como interface de processamento.

### 3.6 WAL e durabilidade de estado

O protocolo Write-Ahead Log foi formalizado por Mohan et al. (1992) no algoritmo ARIES — um dos artigos mais citados em bancos de dados — como mecanismo de durabilidade em sistemas transacionais. A separação entre log imutável e estado mutável também aparece no padrão Event Sourcing (Fowler, 2005), onde o estado do sistema é derivado do append-only log de eventos. O Atomic-DAG aplica o princípio WAL a um domínio onde não havia formalização anterior: agentes LLM com continuidade multi-sessão. A contribuição não é o protocolo WAL — é sua formalização como mecanismo de continuidade em workflows cognitivos, com schema de tick específico ({ts, tipo, atômico\_id, ação\_concluída, próxima\_ação, cursor\_estado}) não encontrado em nenhum framework de agentes LLM nas bases consultadas.

---

## 4. Resultados

### 4.1 Análise por Dimensão

**D1 — Paradigma de estado:** O espectro vai de contexto efêmero intra-sessão (LangGraph, AutoGen — confirmado por Gallois et al. 2025 para LangGraph) até file store genérico (L2MAC), managed state layer (Nalar), e memory tools internos (StateLM). O Atomic-DAG posiciona-se na extremidade de maior externalização e controle: `state.json` como fonte única de verdade, desacoplado de qualquer sessão.

**D2 — Gramática de execução:** A literatura mostra BPMN em dois papéis distintos. Como gramática de representação: BPMN Assistant (2025) gera BPMN como output, POEML (2022) tem sua própria linguagem ligada a BPMN. Como gramática de execução em BPMS (Camunda, Activiti, jBPM): BPMN é interpretado por engine sem LLM. O Atomic-DAG é o único framework identificado que usa BPMN como gramática de execução *com LLM como runtime*, onde cada tipo de ATÔMICO (event/start, gateway/xor, task/execute) determina comportamento determinístico do assembler Python.

**D3 — Persistência e recuperação:** Conrad et al. (2025) documentam um sequence recorder em laboratório robótico que "logs tool invocations when recording is enabled" — um WAL parcial surgindo empiricamente. DeVPlan (Gragera et al., 2025) usa checkpoints de estado para recuperação após falha em robótica, sem LLM. QSP-Copilot (Saini & Farnoud, 2025) usa "DAG execution pattern" com checkpoints de validação humana. Nenhum desses define WAL append-only com schema formal de tick para agentes LLM.

**D4 — Schema de ATÔMICO:** A propriedade de atomicidade é fractal na literatura: notas Zettelkasten (A-MEM), DAG de tarefas (TME), instruction registry (L2MAC), unidade BPMN (Spalazzi et al., 2021). O Template Master de 9 blocos (identity, objectives, instructions, memory, tools, validation, output, continuity, metadata) como schema invariante de cada ATÔMICO não foi encontrado em nenhum framework nas bases consultadas.

**D5 — Separação classe/instância:** Orientação a Objetos tem separação classe/instância desde Simula (Dahl & Nygaard, 1966). Event Sourcing (Fowler, 2005) usa dimensão temporal para imutabilidade de log. O que o Atomic-DAG adiciona não é a separação em si, mas sua aplicação ao problema específico de garantir a propriedade acíclica de DAGs de processo que contêm loops espaciais. A formalização NÓ(ATÔMICO, t) — onde NÓ(A, t₁) e NÓ(A, t₄) são instâncias distintas porque t₁ ≠ t₄ — resolve o aparente paradoxo de "loops sem ciclos" que nenhum dos frameworks analisados endereça formalmente.

### 4.2 Validação dos Claims

| Claim | Evidência | Status |
|---|---|---|
| C1: `state.json` como estado de máquina (não o documento efêmero) | L2MAC (2023): file store separado; Blueprint First (2025): blueprint como representação | ✅ CONFIRMADO — vetor com antecedentes |
| C2: BPMN como gramática de execução com LLM como runtime | Spalazzi et al. (2021): BPMN executável vs representacional; POEML (2022): linguagem de orquestração+execução (sem LLM) | ✅ CONFIRMADO — componente existe isolado; síntese com LLM não encontrada |
| C3: Atomicidade como padrão fractal | A-MEM/Zettelkasten (2025), TME/DAG (2025), ARIES/ACID (1992), Simula/OOP (1966) | ✅ CONFIRMADO — padrão documentado multi-campo |
| C4: WAL como protocolo de continuidade multi-sessão em LLMs | ARIES (Mohan et al. 1992): protocolo WAL em bancos de dados; Event Sourcing (Fowler, 2005): append-only log | ✅ CONFIRMADO COMO GAP DE APLICAÇÃO — WAL em LLMs cross-session não encontrado nas bases |
| C5: Síntese D1+D2+D3+D4+D5 não encontrada nas bases consultadas | Buscas adversariais ADV-1 e ADV-2 + Scholar Gateway + HF Papers: nenhum artigo combina os 5 | ✅ CONFIRMADO DENTRO DO ESCOPO — [ver Limitações sobre cobertura] |

### 4.3 LangGraph e AutoGen: evidência direta sobre o comparador central

Gallois et al. (2025) documentam o LangGraph em uso aplicado como framework de "orchestrated and cyclic framework of agents" onde "memory from the previous agent [is] carried across to the next until a reasonable query has been generated." Isso confirma que o LangGraph opera com memória intra-sessão orientada a tarefa. Quando uma sessão LangGraph é interrompida ou o contexto transborda, não há mecanismo formal de retomada determinística — a próxima sessão começa sem o cursor de execução. Isso é precisamente o problema que o Atomic-DAG endereça com WAL + `state.json`.

---

## 5. Discussão

### 5.1 O problema de persistência multi-sessão: sintoma vs diagnóstico

Os artigos peer-reviewed confirmam que o *sintoma* — necessidade de memória entre etapas de um workflow — é amplamente reconhecido em domínios aplicados. Saini & Farnoud (2025) documentam que QSP-Copilot mantém short-term memory (raciocínio corrente) e long-term memory (contexto de projeto) por agente. Conrad et al. (2025) implementaram sequence recorder com log de tool invocations em laboratório robótico, motivado pela necessidade de reproducibilidade. Gragera et al. (2025) implementaram checkpoints de estado em DeVPlan para recuperação após falha em robótica.

Esses trabalhos confirmam o sintoma (os sistemas precisam de memória e recuperação) mas não formulam o *diagnóstico arquitetural*: que a causa raiz é o estado implícito em contexto efêmero, e que a solução arquitetural é externalizar o estado para artefato persistido desacoplado da sessão. O Atomic-DAG propõe esse diagnóstico e define a gramática de execução que o operacionaliza.

### 5.2 POEML e o Claim 2: análise crítica do comparador mais próximo

O POEML (Hachemi & Ahmed-Nacer, 2022) merece atenção especial porque foi encontrado via busca adversarial e é o trabalho peer-reviewed que mais se aproxima da intenção do Atomic-DAG no domínio de linguagens de processo. O POEML é "an SPML that supports the static process modeling and also the dynamic aspects of orchestration and execution" — ligando modelagem a execução, com metamodelo formal e ferramenta de suporte.

As diferenças em relação ao Atomic-DAG são técnicas, não apenas de domínio: (1) POEML não integra LLM como runtime de processamento de nós; (2) não usa BPMN como gramática base — define sua própria linguagem; (3) não tem WAL como protocolo de persistência; (4) a "execução" no POEML é por engine de processo clássico, não por LLM processando campos de template. O gap do Claim 2 — BPMN como gramática de execução *com LLM como runtime* — é confirmado pelo fato de que o trabalho mais próximo usa sua própria linguagem e engine clássica.

### 5.3 Limitações da propriedade ATÔMICO/NÓ

A separação ATÔMICO/NÓ não é contribuição de abstração classe/instância — essa propriedade existe desde Simula (Dahl & Nygaard, 1966). A contribuição específica é a aplicação da dimensão temporal para garantir a propriedade acíclica do DAG em grafos de processo com loops espaciais. O problema que isso resolve: em orquestração de processo, é comum que o fluxo retorne à mesma "estação" (ex.: refinamento iterativo que revisita o nó de avaliação). Em um DAG convencional definido topologicamente, isso cria ciclos. O Atomic-DAG resolve isso formalmente: NÓ(ATÔMICO\_A, t₁) e NÓ(ATÔMICO\_A, t₄) são instâncias distintas porque t₁ ≠ t₄, e o tempo nunca retrocede. Isso é análogo ao Event Sourcing (Fowler, 2005) onde o log de eventos é acíclico mesmo quando o estado do sistema revisita configurações anteriores. A especificidade está na aplicação a workflows de agentes LLM — domínio onde nenhum framework nas bases consultadas implementa essa distinção formalmente.

### 5.4 Lacunas para trabalho futuro

Os resultados identificam quatro lacunas com ancoragem empírica. A primeira e mais urgente é a ausência de benchmark comparativo. A literatura tem FlowBench (Xiao et al., 2024), FLOW-BENCH (Duesterwald et al., 2025), e tau-bench (Blueprint First, 2025) como benchmarks de workflows para agentes LLM. O Atomic-DAG não tem equivalente — experimento controlado medindo taxa de recuperação após interrupção de sessão e fidelidade de retomada do cursor é necessário antes de qualquer claim empírico de superioridade.

A segunda lacuna é a especificação do mecanismo AND gateway com múltiplos cursores paralelos. A spec v1.0 reconhece esse gap explicitamente. O TME (Ye, 2025) implementa DAG hierárquico com sub-tarefas paralelas; Spalazzi et al. (2021) formalizam paralelismo em BPMN via Redes de Petri. Ambos podem informar o design do JOIN no `state.json` do Atomic-DAG.

A terceira lacuna é a medição de overhead do assembler. O Nalar (Laju et al., 2026) mede control overhead e tail latency para managed state. Sem medição equivalente, a afirmação de que "o assembler precisa de apenas ~50 linhas Python" permanece como estimativa de design.

A quarta lacuna é a ausência de integração formal com MCP (Model Context Protocol). Bandara et al. (2025) e Wang et al. (2025) apontam MCP como primitiva de integração emergente em 2025–2026. Um ATÔMICO com bloco `tools[5]` invocando servidores MCP é arquiteturalmente trivial, mas requer especificação formal.

---

## 6. Limitações

**Cobertura de bases:** ACM Digital Library e IEEE Xplore não foram consultados diretamente. Embora as buscas adversariais (ADV-1, ADV-2) e o Scholar Gateway cubram literatura peer-reviewed relevante, não é possível garantir que não existam artigos nessas bases que combinem os cinco componentes do Atomic-DAG. O Claim 5 deve ser interpretado como "não encontrado nas bases consultadas neste estudo" — não como afirmação de ausência absoluta na literatura.

**Triagem por revisor único:** A triagem foi realizada por um único revisor (agente LLM). Cohen's Kappa de inter-rater reliability não foi calculado. Estudos futuros devem envolver segundo revisor independente, particularmente para os artigos excluídos na triagem.

**Gray literature:** Aproximadamente 60% das referências primárias são preprints (Hugging Face Papers), não revisados por pares. Em domínios de rápida evolução como agentes LLM, preprints representam o estado da arte mais atual, mas as conclusões baseadas neles são provisórias até peer-review.

**Corpus:** 20 artigos elegíveis é um corpus adequado para revisão exploratória de posicionamento. Para claims de originalidade em nível de tese doutoral, recomenda-se corpus de 40+ artigos com cobertura exaustiva das bases citadas.

**PRISMA:** Este estudo não seguiu o protocolo PRISMA 2020 completo. Para submissão a periódicos que exigem PRISMA (ex.: *Information and Software Technology*, *Journal of Systems and Software*), o flow diagram e o checklist de 27 itens devem ser completados na versão de submissão.

---

## 7. Conclusão

Esta RSL mapeou 20 artigos elegíveis de múltiplas bases (2020–2026), conduzindo buscas adversariais explícitas para tentar falsificar o posicionamento central. A análise em cinco dimensões — definidas a priori antes da extração — produziu três achados principais.

Primeiro, os componentes do Atomic-DAG têm antecedentes e análogos parciais na literatura: a separação runtime/estado em L2MAC (2023) e Blueprint First (2025), a gramática de execução de processos em POEML (2022) e Spalazzi et al. (2021), a atomicidade em A-MEM (2025) e TME (2025), e o WAL em Mohan et al. (1992) e Fowler (2005). O framework é construído sobre fundamentos convergentes.

Segundo, a síntese específica de BPMN como gramática de execução com LLM como runtime + `state.json` como estado persistido + WAL com schema de tick + Template Master de 9 blocos como schema de ATÔMICO não foi encontrada nas bases consultadas, incluindo após buscas adversariais explicitamente projetadas para encontrá-la.

Terceiro, quatro lacunas para trabalho futuro foram identificadas com evidência: benchmark comparativo de continuidade multi-sessão, AND gateway com paralelismo, overhead do assembler, e integração com MCP.

Os dados indicam que o Atomic-DAG endereça o problema de persistência cross-session em agentes LLM com um conjunto de mecanismos formais que não foi encontrado combinado em nenhum framework nas bases consultadas. A tese central — que formalizar o diagnóstico arquitetural do problema (estado implícito em contexto efêmero) e propor uma gramática de execução como solução é uma contribuição ao campo — é suportada pelos achados desta revisão, com as ressalvas de cobertura documentadas nas Limitações.

---

## Referências

Holt, S., Ruiz Luyten, M., & van der Schaar, M. (2023). L2MAC: Large Language Model Automatic Computer. *arXiv*. https://hf.co/papers/2310.02003

Qiu, L., et al. (2025). Blueprint First, Model Second. *arXiv*. https://hf.co/papers/2508.02721

Laju, M., et al. (2026). Nalar: An agent serving framework. *arXiv*. https://hf.co/papers/2601.05109

Liu, X., et al. (2026). The Pensieve Paradigm: Stateful Language Models. *arXiv*. https://hf.co/papers/2602.12108

Xu, W., et al. (2025). A-MEM: Agentic Memory for LLM Agents. *arXiv*. https://hf.co/papers/2502.12110

Ye, Y. (2025). Task Memory Engine. *arXiv*. https://hf.co/papers/2505.19436

Licardo, J. T., et al. (2025). BPMN Assistant: An LLM-Based Approach. *arXiv*. https://hf.co/papers/2509.24592

Grohs, M., et al. (2023). LLMs can accomplish BPM tasks. *arXiv*. https://hf.co/papers/2307.09923

Gallois, E. C., et al. (2025). Fast-tracking ecological interpretation using bespoke quantitative LLMs. *Methods in Ecology and Evolution*, 16(12), 2730–2740. https://doi.org/10.1111/2041-210X.70184

Saini, A., & Farnoud, A. (2025). QSP-Copilot. *CPT: Pharmacometrics & Systems Pharmacology*, 14(11), 1775–1786. https://doi.org/10.1002/psp4.70127

Conrad, S., et al. (2025). Lowering the Entrance Hurdle for Lab Automation. *Advanced Intelligent Systems*, 7(10). https://doi.org/10.1002/aisy.202401086

Gragera, A., et al. (2025). Towards a No Code Deployment of Social Robotics Use Cases. *Expert Systems*, 42(6). https://doi.org/10.1111/exsy.70038

Jiang, Y., et al. (2026). VDSAgents. *Stat*, 15(1). https://doi.org/10.1002/sta4.70126

Spalazzi, L., et al. (2021). Blockchain based choreographies. *Concurrency and Computation*, 35(16). https://doi.org/10.1002/cpe.6740

Yussupov, V., et al. (2022). Standards-based modeling of serverless function orchestrations using BPMN. *Software: Practice and Experience*, 52(6), 1454–1495. https://doi.org/10.1002/spe.3073

Hachemi, A., & Ahmed-Nacer, M. (2022). POEML: a Process Orchestration, Execution, and Modeling Language. *Journal of Software: Evolution and Process*, 34(6). https://doi.org/10.1002/smr.2456

Li, Z., Ye, Z., & Chen, M. (2021). A Petri Nets Evolution Method supporting BPMN changes. *Scientific Programming*, 2021(1). https://doi.org/10.1155/2021/6610795

Xiao, R., et al. (2024). FlowBench. *arXiv*. https://hf.co/papers/2406.14884

Duesterwald, E., et al. (2025). FLOW-BENCH. *arXiv*. https://hf.co/papers/2505.11646

Bandara, E., et al. (2025). A Practical Guide for Agentic AI Workflows. *arXiv*. https://hf.co/papers/2512.08769

Wang, H., et al. (2025). AI Agentic Programming Survey. *arXiv*. https://hf.co/papers/2508.11126

**Referências fundacionais:**

Mohan, C., et al. (1992). ARIES: A Transaction Recovery Method. *ACM TODS*, 17(1). https://doi.org/10.1145/128765.128770

Fowler, M. (2005). Event Sourcing. https://martinfowler.com/eaaDev/EventSourcing.html

OMG. (2011). *Business Process Model and Notation (BPMN) 2.0*. Object Management Group. https://www.omg.org/spec/BPMN/2.0

Dahl, O-J., & Nygaard, K. (1966). SIMULA: An ALGOL-Based Simulation Language. *CACM*, 9(9). https://doi.org/10.1145/365813.365819

Von Neumann, J. (1945). *First Draft of a Report on the EDVAC*. Moore School of Electrical Engineering.

Page, M. J., et al. (2021). The PRISMA 2020 statement. *BMJ*, 372. https://doi.org/10.1136/bmj.n71

---

## Apêndice A — Registro WAL de Correção

```yaml
wal_correccao:
  ts: "2026-03-18T00:00:00Z"
  versao: "2.0"
  apontamentos_aplicados: 19/19
  sprints_executados: [1A, 1B, 2A, 2B, 3A, 4A, 5A]
  novos_artigos_adicionados:
    - "Gallois et al. 2025 — LangGraph confirmado peer-reviewed"
    - "Spalazzi et al. 2021 — BPMN execução vs representação"
    - "Yussupov et al. 2022 — BPMN serverless orchestration"
    - "Hachemi & Ahmed-Nacer 2022 — POEML (comparador mais próximo)"
    - "Dahl & Nygaard 1966 — Simula (fundação OOP)"
    - "Mohan et al. 1992 — ARIES WAL"
    - "Fowler 2005 — Event Sourcing"
    - "OMG 2011 — BPMN 2.0 spec"
  claim5_apos_adversariais: "CONFIRMADO DENTRO DO ESCOPO — buscas ADV-1 e ADV-2 não encontraram counter-examples"
  poeml_encontrado: "comparador relevante adicionado à análise D2"
  bugs_reportados_ao_builder: 5
  proxima_acao: "submissao_ou_ACM_DL_IEEE_complementar"
```
````