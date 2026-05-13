````markdown
---
Id: DTP-v1.0
Filename: decision-topology-protocol.md
Created: 2025-02-25
Tag: [protocol, decision-making, orchestration, meta-protocol]
Status: DRAFT → Aguardando validação
Depends-on: [MODUS-OPERANDI, CHECK-MATE, WAL]
Role: Orquestrador de decisões acima dos protocolos de execução
---

# 🎯 DECISION TOPOLOGY PROTOCOL (DTP) v1.0

> **Propósito único:** Dado N caminhos possíveis, determinar a ordem ótima
> de execução que MINIMIZA retrabalho e MAXIMIZA qualidade + eficiência,
> mantendo coerência com o OBJETIVO GLOBAL em todo momento.

> **Analogia matemática:**
> - O DTP é o **gradiente** que aponta a direção de subida mais íngreme
> - Cada decisão move o estado no espaço de soluções
> - O objetivo global é o **ponto ótimo** da função
> - Refatoração = voltar no espaço porque subiu na direção errada

---

## 0. INVARIANTES (Constitutional — nunca violados)

```
INVARIANTE_1: Objetivo Global é IMUTÁVEL durante o ciclo DTP
             (se mudar, novo DTP é instanciado)

INVARIANTE_2: Nenhuma decisão é executada sem dependências resolvidas

INVARIANTE_3: Estado Atual é atualizado APÓS cada execução
             (nunca operar sobre estado stale)

INVARIANTE_4: Re-avaliação é OBRIGATÓRIA após cada execução
             (o campo de jogo SEMPRE muda)

INVARIANTE_5: DTP é PERSISTIDO entre sessões via WAL-handoff
             (decisões pendentes + estado + scores sobrevivem)
```

---

## 1. ESTRUTURA DO ARTEFATO DTP (Persistente)

O DTP como artefato contém 4 seções que são atualizadas continuamente:

```
┌─────────────────────────────────────────────────────────────┐
│ DTP INSTANCE                                                │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ A. OBJETIVO GLOBAL (imutável)                           │ │
│ │    → O que define "terminado com sucesso"               │ │
│ │    → Critérios de aceitação mensuráveis                 │ │
│ │    → Escopo: o que está DENTRO e FORA                   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ B. ESTADO ATUAL [N] (mutável, versionado)               │ │
│ │    → Snapshot do que existe agora                        │ │
│ │    → O que já foi decidido/executado                     │ │
│ │    → O que mudou desde Estado [N-1]                      │ │
│ │    → Delta: o que o último resultado alterou             │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ C. GRAFO DE DECISÕES (DAG) (mutável, recomputado)       │ │
│ │    → Nós: decisões candidatas                           │ │
│ │    → Arestas: dependências                              │ │
│ │    → Scores: matriz de impacto por nó                   │ │
│ │    → Status por nó: pending|active|done|invalidated     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ D. FILA DE EXECUÇÃO (derivada do DAG)                   │ │
│ │    → Ordem topológica ponderada                         │ │
│ │    → Próxima ação recomendada                           │ │
│ │    → Dispatch: qual protocolo executa (MO | CM)         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ E. LOG DE DECISÕES (append-only, histórico)             │ │
│ │    → [timestamp] Decisão X: executada via MO/CM         │ │
│ │    → Resultado: sucesso/falha                           │ │
│ │    → Impacto observado no estado                        │ │
│ │    → Decisões invalidadas/criadas como consequência     │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. CICLO DTP (Fluxo Operacional)

```
                    ┌─────────────────────┐
                    │  OBJETIVO GLOBAL    │ (âncora fixa)
                    └────────┬────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│ [FASE 0] CAPTURA DE ESTADO                                   │
│                                                              │
│  ➞ Qual é o estado REAL agora? (não assumir, verificar)      │
│  ➞ O que mudou desde a última decisão?                       │
│  ➞ Registrar Estado [N]                                      │
│                                                              │
│  INPUT: evidências concretas (código, docs, logs, testes)    │
│  OUTPUT: Estado [N] documentado                              │
│                                                              │
│  ⚠️ Se entre sessões: CONSUMIR WAL-handoff primeiro          │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ [FASE 1] ENUMERAÇÃO DE CANDIDATOS                            │
│                                                              │
│  Para cada ação possível, registrar:                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ID: D-001                                              │  │
│  │ Descrição: [o que é]                                   │  │
│  │ Tipo: CRIAÇÃO | CORREÇÃO | REFATORAÇÃO | INVESTIGAÇÃO  │  │
│  │ Valor: [o que entrega ao objetivo global]              │  │
│  │ Custo: [esforço estimado: tokens/tempo/complexidade]   │  │
│  │ Depende-de: [IDs de decisões pré-requisito]            │  │
│  │ Bloqueia: [IDs de decisões que dependem desta]         │  │
│  │ Reversível: SIM (custo baixo) | PARCIAL | NÃO         │  │
│  │ Risco-se-adiado: [o que acontece se não fizer agora]   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  REGRA: Se candidato tem tipo INVESTIGAÇÃO,                  │
│         ele SEMPRE precede decisões que dependem             │
│         da informação que ele produz.                        │
│         (não decidir sem dados)                              │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ [FASE 2] CONSTRUÇÃO DO DAG                                   │
│                                                              │
│  2.1 Mapear dependências:                                    │
│      Para todo par (Di, Dj):                                 │
│        Di → Dj significa "Di DEVE preceder Dj"               │
│                                                              │
│  2.2 Detectar ciclos:                                        │
│      Se ciclo encontrado:                                    │
│        ➞ DECOMPOR decisões até eliminar ciclo                │
│        ➞ Ciclo = sinal de granularidade insuficiente         │
│                                                              │
│  2.3 Identificar:                                            │
│      • NÓS RAIZ → podem começar imediatamente               │
│      • CAMINHO CRÍTICO → sequência mais longa                │
│      • NÓS FOLHA → só executam depois de tudo acima          │
│                                                              │
│  Visualização:                                               │
│                                                              │
│      D-001 ──→ D-003 ──→ D-005                              │
│        │                    ↑                                │
│        └──→ D-004 ──────────┘                                │
│      D-002 ──→ D-006                                         │
│      (raiz)    (folha)                                       │
│                                                              │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ [FASE 3] SCORING (Matriz de Impacto)                         │
│                                                              │
│  Para cada candidato Di:                                     │
│                                                              │
│  Score(Di) = Σ (peso_k × score_k)                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Dimensão              │ Peso  │ Score [0-10] │ Nota    │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │ Valor ao Obj. Global  │ 0.25  │              │         │  │
│  │ Custo de execução     │ 0.15  │ (invertido)  │ 10-raw  │  │
│  │ Risco se adiado       │ 0.20  │              │         │  │
│  │ Nº de dependentes     │ 0.15  │              │ desbloq │  │
│  │ Irreversibilidade     │ 0.15  │              │ cautela │  │
│  │ Alinhamento c/ estado │ 0.10  │              │ fit now │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  REGRA DE CAUTELA:                                           │
│  Se Irreversibilidade ≥ 8 E Valor ≥ 7:                      │
│    ➞ Análise com profundidade 2x (mais investigação)         │
│    ➞ Considerar: "existe caminho reversível alternativo?"    │
│                                                              │
│  REGRA DE THRESHOLD:                                         │
│  Se Custo ≤ 2 E Reversível == SIM:                           │
│    ➞ Fast-track: executar sem protocolo completo             │
│    ➞ Registrar no log, mas sem scoring formal                │
│                                                              │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ [FASE 4] ORDENAÇÃO → FILA DE EXECUÇÃO                        │
│                                                              │
│  Algoritmo:                                                  │
│                                                              │
│  ```                                                         │
│  function build_execution_queue(candidates):                 │
│      dag = build_dag(candidates)                             │
│      assert no_cycles(dag)                                   │
│      levels = topological_sort_by_levels(dag)                │
│                                                              │
│      queue = []                                              │
│      for level in levels:                                    │
│          # Dentro do mesmo nível: sem dependência mútua      │
│          # Ordenar por score decrescente                     │
│          level.sort(key=lambda d: d.score, reverse=True)     │
│          queue.extend(level)                                 │
│                                                              │
│      return queue                                            │
│  ```                                                         │
│                                                              │
│  OUTPUT:                                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Pos │ ID    │ Score │ Tipo       │ Dispatch         │  │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  1  │ D-002 │ 8.7   │ INVESTIG.  │ (inline)         │  │  │
│  │  2  │ D-001 │ 8.2   │ CRIAÇÃO    │ → MODUS OPERANDI │  │  │
│  │  3  │ D-004 │ 7.5   │ CORREÇÃO   │ → CHECK-MATE     │  │  │
│  │  4  │ D-003 │ 6.9   │ CRIAÇÃO    │ → MODUS OPERANDI │  │  │
│  │ ... │       │       │            │                  │  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ [FASE 5] DISPATCH + EXECUÇÃO                                 │
│                                                              │
│  Pegar próximo da fila:                                      │
│                                                              │
│  ┌─ GATE DE PRÉ-EXECUÇÃO ─────────────────────────────────┐ │
│  │                                                         │ │
│  │  ✓ Dependências deste nó estão em status=done?          │ │
│  │  ✓ Estado atual ainda suporta esta decisão?             │ │
│  │  ✓ Score ainda é válido? (contexto não mudou?)          │ │
│  │                                                         │ │
│  │  Se QUALQUER ✓ falha:                                   │ │
│  │    ➞ VOLTAR à FASE 2 (recomputar DAG)                   │ │
│  │    ➞ NÃO executar com premissa inválida                 │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  Se gate passou:                                             │
│                                                              │
│  SWITCH (tipo):                                              │
│    CRIAÇÃO      → INVOCAR: MODUS OPERANDI (PIER)            │
│    CORREÇÃO     → INVOCAR: CHECK-MATE (branch + fix)        │
│    REFATORAÇÃO  → INVOCAR: CHECK-MATE (branch)              │
│                   + MODUS OPERANDI (rebuild)                 │
│    INVESTIGAÇÃO → INLINE: pesquisar, coletar, documentar    │
│                                                              │
│  Cada protocolo invocado reporta:                            │
│    → resultado: SUCCESS | FAIL | PARTIAL                     │
│    → artefatos produzidos                                    │
│    → efeitos colaterais observados                           │
│                                                              │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ [FASE 6] PÓS-EXECUÇÃO: RE-AVALIAÇÃO (MANDATÓRIA)            │
│                                                              │
│  ➞ 6.1 ATUALIZAR ESTADO                                     │
│     Estado [N+1] = Estado [N] + Delta(resultado)             │
│                                                              │
│  ➞ 6.2 VERIFICAR DISTÂNCIA AO OBJETIVO GLOBAL               │
│     Progresso = f(critérios_aceitação_atendidos /            │
│                   critérios_aceitação_totais)                 │
│                                                              │
│     Se Progresso == 100% → FIM (FASE 7)                      │
│     Se Progresso regrediu → ALERTA: investigar causa         │
│                                                              │
│  ➞ 6.3 REVALIDAR DECISÕES PENDENTES                         │
│     Para cada Dj ainda em status=pending:                    │
│       • Premissas ainda válidas?                             │
│       • Score mudou com novo estado?                         │
│       • Surgiu dependência nova?                             │
│       • Decisão ainda necessária?                            │
│         (talvez resultado anterior já a resolveu)            │
│                                                              │
│     Atualizar status:                                        │
│       → invalidated: premissas quebraram                     │
│       → rescored: score mudou significativamente             │
│       → absorbed: resultado anterior já cobriu               │
│                                                              │
│  ➞ 6.4 VERIFICAR EMERGENTES                                 │
│     O resultado revelou decisões NOVAS não previstas?        │
│     Se sim: adicionar como candidatos → VOLTAR FASE 1        │
│                                                              │
│  ➞ 6.5 REGISTRAR NO LOG                                     │
│     [Estado N → N+1] Decisão D-XXX executada via [protocolo] │
│     Resultado: [SUCCESS/FAIL/PARTIAL]                        │
│     Progresso: [X%] → [Y%]                                   │
│     Invalidadas: [D-YYY, D-ZZZ]                              │
│     Emergentes: [D-NEW1]                                     │
│                                                              │
│  ➞ LOOP → VOLTAR FASE 4 (reordenar fila com estado N+1)     │
│                                                              │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│ [FASE 7] CRITÉRIO DE PARADA                                  │
│                                                              │
│  CONDIÇÃO 1 (sucesso):                                       │
│    Progresso == 100% do Objetivo Global                      │
│    + Todas decisões: done | invalidated | absorbed           │
│                                                              │
│  CONDIÇÃO 2 (parada racional):                               │
│    Custo marginal da próxima decisão > Valor marginal        │
│    (diminishing returns — não vale mais continuar)           │
│    ➞ Documentar: "parado em X% porque..."                    │
│                                                              │
│  CONDIÇÃO 3 (bloqueio externo):                              │
│    Decisão pendente depende de input externo indisponível    │
│    ➞ Documentar: "bloqueado em D-XXX por [razão]"            │
│    ➞ WAL-handoff com estado completo para retomada           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. INTEGRAÇÃO COM PROTOCOLOS EXISTENTES

```
┌───────────────────────────────────────────────────────────┐
│                                                           │
│                    ┌─────────┐                            │
│                    │   DTP   │  ← Orquestrador            │
│                    │ (Decide │     "O QUE e QUANDO"       │
│                    │  ordem) │                            │
│                    └────┬────┘                            │
│                         │                                │
│              ┌──────────┼──────────┐                     │
│              │          │          │                      │
│              ▼          ▼          ▼                      │
│        ┌──────────┐ ┌────────┐ ┌────────┐               │
│        │  MODUS   │ │ CHECK  │ │INLINE  │               │
│        │ OPERANDI │ │  MATE  │ │(invest)│               │
│        │          │ │        │ │        │               │
│        │ "COMO    │ │ "COMO  │ │"COMO   │               │
│        │  criar"  │ │ corrig"│ │ saber" │               │
│        └──────────┘ └────────┘ └────────┘               │
│              │          │          │                      │
│              └──────────┼──────────┘                     │
│                         │                                │
│                         ▼                                │
│                    ┌─────────┐                            │
│                    │   WAL   │  ← Persistência            │
│                    │(Registra│    "O QUE ACONTECEU"       │
│                    │ + handoff│    + "COMO RETOMAR"       │
│                    └─────────┘                            │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

**Fluxo de dados entre eles:**

```
DTP → dispatch → MODUS OPERANDI/CHECK-MATE → resultado → DTP (re-avalia)
                                                ↓
                                            WAL (registra)
                                                ↓
                                      [próxima sessão: WAL → DTP (restaura)]
```

---

## 4. WAL-HANDOFF: Como o DTP persiste entre sessões

Quando sessão encerra (ou risco de encerrar):

```
WAL-HANDOFF deve incluir:

┌─ DTP SNAPSHOT ────────────────────────────────────────┐
│                                                       │
│  OBJETIVO GLOBAL: [copiar seção A]                    │
│  ESTADO ATUAL: [N] [copiar seção B mais recente]      │
│  PROGRESSO: [X%]                                      │
│                                                       │
│  DECISÕES PENDENTES (da fila):                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │ D-003 │ Score 6.9 │ CRIAÇÃO │ deps: D-001(done) │ │
│  │ D-005 │ Score 5.2 │ CORR.   │ deps: D-003(pend) │ │
│  └──────────────────────────────────────────────────┘ │
│                                                       │
│  DECISÕES CONCLUÍDAS (resumo):                        │
│  D-001: done, D-002: done, D-004: invalidated         │
│                                                       │
│  PRÓXIMA AÇÃO RECOMENDADA: D-003                      │
│  GATE: dependências ok, score válido                  │
│  DISPATCH: MODUS OPERANDI                             │
│                                                       │
│  ⚠️ ALERTAS:                                          │
│  [qualquer anomalia ou risco identificado]            │
│                                                       │
└───────────────────────────────────────────────────────┘
```

---

## 5. PSEUDOCÓDIGO COMPLETO (Computacional)

```python
class DecisionNode:
    id: str
    description: str
    type: Enum[CREATION, CORRECTION, REFACTORING, INVESTIGATION]
    value_to_goal: float       # 0-10
    execution_cost: float      # 0-10
    risk_if_delayed: float     # 0-10
    dependents_count: int
    irreversibility: float     # 0-10
    state_alignment: float     # 0-10
    depends_on: List[str]      # IDs
    blocks: List[str]          # IDs
    status: Enum[PENDING, ACTIVE, DONE, INVALIDATED, ABSORBED]
    
    def score(self) -> float:
        weights = {
            'value': 0.25,
            'cost': 0.15,       # invertido
            'risk': 0.20,
            'dependents': 0.15,
            'irreversibility': 0.15,
            'alignment': 0.10
        }
        return (
            weights['value'] * self.value_to_goal +
            weights['cost'] * (10 - self.execution_cost) +
            weights['risk'] * self.risk_if_delayed +
            weights['dependents'] * min(self.dependents_count, 10) +
            weights['irreversibility'] * self.irreversibility +
            weights['alignment'] * self.state_alignment
        )

class DTP:
    objective: str                    # Imutável
    acceptance_criteria: List[str]    # Mensuráveis
    state: StateSnapshot              # Versão N
    dag: DirectedAcyclicGraph         # Recomputável
    queue: List[DecisionNode]         # Derivada do DAG
    log: List[LogEntry]               # Append-only
    
    def run_cycle(self):
        """Ciclo principal DTP"""
        
        # FASE 0: Captura de estado
        self.state = self.capture_current_state()
        
        # FASE 1: Enumerar candidatos
        candidates = self.enumerate_candidates(self.state)
        
        # FASE 2: Construir DAG
        self.dag = self.build_dag(candidates)
        assert self.dag.is_acyclic(), "Ciclo detectado → decompor"
        
        # FASE 3: Scoring
        for node in self.dag.nodes:
            node.compute_score()
        
        # FASE 4: Ordenação
        self.queue = self.topological_sort_weighted(self.dag)
        
        # FASE 5: Executar próximo
        while self.queue and not self.is_complete():
            next_decision = self.queue[0]
            
            # Gate de pré-execução
            if not self.pre_execution_gate(next_decision):
                # Premissa inválida → recomputar
                return self.run_cycle()  # recursão controlada
            
            # Fast-track check
            if next_decision.execution_cost <= 2 and \
               next_decision.is_reversible:
                result = self.execute_fast_track(next_decision)
            else:
                result = self.dispatch(next_decision)
            
            # FASE 6: Pós-execução
            self.post_execution(next_decision, result)
            
            # Re-avaliar antes de continuar
            self.revalidate_pending()
            self.queue = self.topological_sort_weighted(self.dag)
    
    def dispatch(self, decision: DecisionNode):
        """Fase 5: Despachar para protocolo correto"""
        match decision.type:
            case CREATION:
                return ModusOperandi.execute(decision)
            case CORRECTION:
                return CheckMate.execute(decision)
            case REFACTORING:
                CheckMate.create_branch(decision)
                return ModusOperandi.rebuild(decision)
            case INVESTIGATION:
                return self.investigate_inline(decision)
    
    def post_execution(self, decision, result):
        """Fase 6: Re-avaliação mandatória"""
        # 6.1 Atualizar estado
        self.state = self.state.apply_delta(result.delta)
        
        # 6.2 Verificar progresso
        progress = self.compute_progress()
        if progress.regressed:
            self.alert("REGRESSÃO DETECTADA", decision, result)
        
        # 6.3 Revalidar pendentes
        for node in self.dag.pending_nodes():
            if not node.premises_still_valid(self.state):
                node.status = INVALIDATED
            elif node.score_changed_significantly(self.state):
                node.recompute_score()
                node.status = RESCORED
        
        # 6.4 Detectar emergentes
        new_candidates = self.detect_emergent_decisions(result)
        for nc in new_candidates:
            self.dag.add_node(nc)
        
        # 6.5 Log
        self.log.append(LogEntry(
            from_state=self.state.version - 1,
            to_state=self.state.version,
            decision=decision.id,
            result=result.status,
            progress=progress.percentage,
            invalidated=[n.id for n in self.dag.invalidated()],
            emergent=[n.id for n in new_candidates]
        ))
    
    def pre_execution_gate(self, decision) -> bool:
        """Gate: todas as condições devem ser True"""
        deps_done = all(
            self.dag.get(d).status == DONE 
            for d in decision.depends_on
        )
        state_supports = decision.premises_valid(self.state)
        score_valid = not decision.score_changed_significantly(self.state)
        
        return deps_done and state_supports and score_valid
    
    def is_complete(self) -> bool:
        """Fase 7: Critério de parada"""
        progress = self.compute_progress()
        
        # Condição 1: Objetivo atingido
        if progress.percentage >= 100:
            return True
        
        # Condição 2: Diminishing returns
        if self.queue:
            next_value = self.queue[0].marginal_value()
            next_cost = self.queue[0].marginal_cost()
            if next_cost > next_value:
                self.log.append("PARADA: custo marginal > valor marginal")
                return True
        
        # Condição 3: Bloqueio externo
        if all(n.status in [DONE, INVALIDATED, ABSORBED] 
               or n.is_externally_blocked 
               for n in self.dag.nodes):
            self.generate_wal_handoff()
            return True
        
        return False
```

---

## 6. TEMPLATE DE USO PRÁTICO

Ao iniciar qualquer trabalho, preencher:

```
═══════════════════════════════════════════════════════
DTP INSTANCE: [nome do projeto/objetivo]
═══════════════════════════════════════════════════════

A. OBJETIVO GLOBAL:
   [Descrever em 1-2 frases]
   
   Critérios de aceitação:
   □ [critério mensurável 1]
   □ [critério mensurável 2]
   □ [critério mensurável N]

B. ESTADO ATUAL [0]:
   [O que existe agora]
   [O que não existe]
   [Restrições conhecidas]

C. CANDIDATOS:
   ┌──────┬──────────────┬──────────┬───────┬──────────┐
   │ ID   │ Descrição    │ Tipo     │ Score │ Deps     │
   ├──────┼──────────────┼──────────┼───────┼──────────┤
   │ D-001│              │          │       │          │
   │ D-002│              │          │       │          │
   └──────┴──────────────┴──────────┴───────┴──────────┘

D. FILA:
   1. [ID] → [protocolo]
   2. [ID] → [protocolo]
   
E. LOG:
   [vazio — início]

═══════════════════════════════════════════════════════
```

````