---
Id: DAW-OS-ARCH-003
Filename: WINDOW_PROTOCOL_SPEC_V1.md
Created: 2026-03-05
Version: 1.0.0
Tag: window-protocol, llm-runtime, format-spec, container
Status: EMITIDO
PMQ: 9.8/10
WAL_Checkpoint: ARCH-003
Depends: DAW-OS-ARCH-002 (LLM-PVM)
---

# WINDOW PROTOCOL v1.0
## O Container Nativo do LLM-as-PVM

---

## 1. A DECISÃO ARQUITETURAL

```
YAML frontmatter + Markdown  →  excelente para ÁTOMOS (dados)
XML                          →  excelente para BPMN (schema)
HTMX                         →  excelente para browser (partial DOM)

WINDOW PROTOCOL              →  necessário para LLM-as-PVM (runtime)
```

Nenhum formato existente resolve o problema completo porque nenhum
foi projetado para um runtime que **lê e reescreve texto como execução**.

O Window Protocol é um **superconjunto estruturado** de Markdown que
adiciona semântica de seções com roles funcionais — análogo ao HTML
`<head>/<body>/<script>`, mas em texto puro que o LLM processa nativamente.

---

## 2. ANATOMIA DE UMA WINDOW

```
┌─────────────────────────────────────────────────────────────────┐
│  WINDOW: auth-security-001                                      │
├─────────────────────────────────────────────────────────────────┤
│  ██ SEÇÃO 1: CONTRACT (análogo ao <head>)                       │
│     └─ YAML frontmatter: identidade, estado FSM, qualidade      │
│     └─ Lido pelo LLM PRIMEIRO — define o contrato da Window     │
├─────────────────────────────────────────────────────────────────┤
│  ██ SEÇÃO 2: CONTENT (análogo ao <body>)                        │
│     └─ Markdown: o trabalho visível da Lane                     │
│     └─ O que o LLM produz como resultado da execução            │
├─────────────────────────────────────────────────────────────────┤
│  ██ SEÇÃO 3: PROTOCOL (análogo ao <script>)                     │
│     └─ Regras explícitas que o LLM DEVE seguir                  │
│     └─ Transições válidas, gates, ações permitidas              │
├─────────────────────────────────────────────────────────────────┤
│  ██ SEÇÃO 4: MEMORY (análogo ao localStorage)                   │
│     └─ Estado persistente entre interações                      │
│     └─ Nunca apagado — acumulativo append-only                  │
├─────────────────────────────────────────────────────────────────┤
│  ██ SEÇÃO 5: CURSOR (análogo ao event listener ativo)           │
│     └─ Aponta exatamente ONDE o LLM deve agir agora            │
│     └─ Atualizado pelo DTP após cada transição                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. ESPECIFICAÇÃO FORMAL DO FORMATO

````markdown
---
# ══════════════════════════════════════════════
# SEÇÃO 1: CONTRACT  (LLM lê isto PRIMEIRO)
# ══════════════════════════════════════════════
window_id: auth-security-001
atomic_id: auth-sec-001
version: 1.0.0

# Identidade do átomo
lane:
  id: "MO[SECURITY.VALIDATE][0]"
  role: validate
  action: verificar
  domain: segurança
  executor: llm

# Estado FSM atual
cursor_state:
  FROM: "MO[KDI][0]"           # de onde veio
  THIS: "MO[SECURITY][0]"      # onde está agora
  GOTO: "MO[EXEC][0]"          # para onde vai SE aprovado

# Gate de qualidade
quality_gate:
  pmq_threshold: 9.5
  dimensions: [CE, PI, CC, PRI, RA, EIC, OVA]
  current_pmq: null             # preenchido pelo LLM ao finalizar

# Transições FSM válidas
fsm:
  current_state: active
  valid_transitions:
    active → complete: "pmq >= 9.5 AND all_checks_passed"
    active → blocked:  "blocker_detected == true"
    active → retry:    "pmq < 9.5 AND iterations < 5"
  blocked_transitions:
    - "complete → active"       # não pode regredir
    - "blocked → complete"      # deve passar por active
---

# ══════════════════════════════════════════════
# SEÇÃO 2: CONTENT  (o trabalho da Lane)
# ══════════════════════════════════════════════

## Validação de Segurança

> [!note] CURSOR ATIVO: Executar validação dos itens abaixo

### Checklist de Verificação

- [x] SSL/TLS configurado (verificado: cert válido até 2027-01)
- [ ] Rate limiting implementado
- [ ] Audit logs ativos
- [ ] Input sanitization em todos os endpoints

### Análise de Risco

<!-- LLM preenche esta subseção ao executar a Lane -->
[AGUARDANDO EXECUÇÃO]

# ══════════════════════════════════════════════
# SEÇÃO 3: PROTOCOL  (regras que o LLM segue)
# ══════════════════════════════════════════════

> [!protocol] REGRAS DE EXECUÇÃO — MANDATÓRIO SEGUIR
>
> **ENTRADA (FROM)**: Verificar que MO[KDI][0] está `complete`
> antes de qualquer ação nesta Window.
>
> **EXECUÇÃO (THIS)**:
> 1. Preencher cada item do checklist com evidência real
> 2. Completar a subseção "Análise de Risco" com dados concretos
> 3. Calcular PMQ ao finalizar (7 dimensões, pesos padrão)
>
> **GATE**: SE pmq < 9.5 → ATUALIZAR cursor_state.THIS para `retry`
>           SE pmq >= 9.5 → ATUALIZAR cursor_state.THIS para `complete`
>
> **SAÍDA (GOTO)**: Emitir para MO[EXEC][0] somente se `complete`
>
> **PROIBIDO**: Avançar para GOTO sem PMQ calculado e registrado

# ══════════════════════════════════════════════
# SEÇÃO 4: MEMORY  (estado persistente — NUNCA APAGAR)
# ══════════════════════════════════════════════

> [!memory] LOG IMUTÁVEL DE INTERAÇÕES
>
> ```
> [2026-03-05T14:00:00Z] | FROM: MO[KDI][0] → THIS: MO[SECURITY][0]
>                          | task=validate_security | iter=0
>                          | context_loaded: ssl_cert, nginx_config
>
> [PRÓXIMAS ENTRADAS AQUI — APPEND ONLY]
> ```

# ══════════════════════════════════════════════
# SEÇÃO 5: CURSOR  (onde agir AGORA)
# ══════════════════════════════════════════════

> [!cursor] AÇÃO IMEDIATA REQUERIDA
>
> **VOCÊ ESTÁ EM**: `MO[SECURITY.VALIDATE][0]` — estado `active`
>
> **PRÓXIMA AÇÃO**:
> └─ Preencher checklist (itens ☐) com evidência real
> └─ Completar "Análise de Risco"
> └─ Calcular PMQ e registrar em `quality_gate.current_pmq`
> └─ Atualizar `cursor_state.THIS` conforme gate
> └─ Registrar em MEMORY (append)
>
> **NÃO FAZER**: modificar CONTRACT sem gate aprovado
````

---

## 4. COMO O LLM PROCESSA A WINDOW

```
CICLO DE VIDA DE UMA WINDOW (o LLM como engine):

┌─────────────────────────────────────────────────────────┐
│  1. LLM LÊ CONTRACT                                     │
│     → entende identidade, estado FSM, transições válidas│
│     → carrega regras do PROTOCOL                        │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│  2. LLM LÊ CURSOR                                       │
│     → sabe EXATAMENTE onde agir                         │
│     → não precisa inferir — está explícito              │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│  3. LLM EXECUTA A LANE no CONTENT                       │
│     → reescreve APENAS a seção de CONTENT               │
│     → mantém CONTRACT, PROTOCOL, MEMORY intactos        │
│     → não toca no que não é sua responsabilidade        │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│  4. LLM AVALIA PMQ                                      │
│     → calcula as 7 dimensões internamente               │
│     → registra em quality_gate.current_pmq              │
└─────────────────────┬───────────────────────────────────┘
                      │
              PMQ ≥ 9.5?
            ┌────┴────┐
           SIM       NÃO
            │         │
┌───────────▼──┐  ┌───▼──────────────────────────────┐
│ ATUALIZA     │  │ ATUALIZA cursor_state.THIS=retry  │
│ THIS=complete│  │ ATUALIZA CURSOR (nova instrução)  │
│ EMITE GOTO   │  │ REGISTRA em MEMORY                │
│ REGISTRA WAL │  │ LOOP (máx 5 iterações)            │
└──────────────┘  └───────────────────────────────────┘
```

### O Delta Update — equivalente ao HTMX partial render

```
O LLM não reescreve a Window inteira a cada interação.
Reescreve APENAS a seção responsável:

INTERAÇÃO 1: executa Lane → reescreve CONTENT + CURSOR + MEMORY
INTERAÇÃO 2: refina → reescreve CONTENT + quality_gate.pmq + MEMORY  
INTERAÇÃO 3: conclui → reescreve CONTRACT.cursor_state + CURSOR + MEMORY

MANTÉM INTACTO: PROTOCOL (nunca muda), estrutura do CONTRACT
ACUMULA: MEMORY (append-only, análogo ao WAL)
ATUALIZA: CONTENT (trabalho), CURSOR (próxima ação), PMQ
```

---

## 5. COMPARAÇÃO DECISIVA: POR QUE NÃO XML, HTMX OU YAML PURO

```
┌──────────────┬─────────────────────────────┬──────────────────────────────┐
│ FORMATO      │ PROBLEMA CRÍTICO            │ POR QUÊ NÃO RESOLVE          │
├──────────────┼─────────────────────────────┼──────────────────────────────┤
│ YAML puro    │ Sem seções de conteúdo      │ Ótimo para CONTRACT,         │
│              │ Sem protocolo embutido      │ insuficiente como Window     │
│              │ Sem memória persistente     │ completa. É UMA PEÇA, não    │
│              │                             │ o container inteiro.         │
├──────────────┼─────────────────────────────┼──────────────────────────────┤
│ XML          │ Verboso para geração LLM    │ LLM gera XML mal-formado     │
│              │ Encoding overhead           │ com frequência. Dificulta    │
│              │ Não é formato de trabalho   │ leitura do CONTENT pelo LLM. │
│              │                             │ Bom para BPMN, não para      │
│              │                             │ Window de trabalho.          │
├──────────────┼─────────────────────────────┼──────────────────────────────┤
│ HTMX         │ Requer HTTP server          │ Runtime externo obrigatório. │
│              │ Requer browser              │ Viola o princípio LLM-as-PVM.│
│              │ Não é text-native           │ Útil para a camada de VIEW   │
│              │                             │ (humano), não para execução  │
│              │                             │ pelo LLM.                    │
├──────────────┼─────────────────────────────┼──────────────────────────────┤
│ WINDOW       │ Enforcement convencional    │ O enforcement É convencional │
│ PROTOCOL     │ (não compilado)             │ — o LLM segue o PROTOCOL     │
│ (este)       │                             │ por design, não por          │
│              │                             │ compilação. Mitigação:       │
│              │                             │ PMQ gate é o verificador     │
│              │                             │ externo. DTP valida output   │
│              │                             │ antes de aceitar GOTO.       │
└──────────────┴─────────────────────────────┴──────────────────────────────┘
```

### Resposta à Dúvida do Documento Original

> *"precisamos de por analogia modularizar todo um contexto em única window onde análogo a webpage container fica explícito conforme a engine"*

```
WEBPAGE:  browser carrega HTML → DOM representa estado → JS atualiza parcialmente
WINDOW:   LLM carrega .md     → CONTRACT representa estado → LLM atualiza seção-alvo

A JANELA É O DOCUMENTO INTEIRO.
Não é um arquivo de dados (como atom.md).
É o AMBIENTE DE EXECUÇÃO completo de uma Lane:
contrato + trabalho + regras + memória + cursor = tudo num só lugar.

"a cada caso a janela é atualizada"
→ o LLM faz delta-update da seção correta
→ mantém o resto intacto (como innerHTML parcial)
→ a Window nunca é destruída e recriada — é MUTÁVEL in-place
```

---

## 6. DISTINÇÃO CRÍTICA: ÁTOMO vs WINDOW

```
ÁTOMO (atom.md)                      WINDOW (.window.md)
──────────────────────────────────   ──────────────────────────────────
Unidade de DADO                      Ambiente de EXECUÇÃO
Frontmatter = metadado estático      CONTRACT = estado FSM dinâmico
Conteúdo = documentação              CONTENT = trabalho em progresso
Lido por humanos e LLMs              Processado pelo LLM como runtime
Versionado no Git                    Mutável durante a sessão
Imutável após publicação             Acumula MEMORY a cada interação
```

**Um átomo GERA uma Window quando o DTP o despacha para execução.**
Após execução, o resultado do CONTENT volta para o átomo.
A Window é efêmera — existe durante a Lane. O átomo é permanente.

```python
# Ciclo de vida completo
atom = Atom.load("atoms/auth-sec-001.md")          # carrega dado permanente
window = Window.from_atom(atom, cursor, context)    # cria ambiente de execução
result = LLM.execute(window)                        # LLM processa como runtime
atom.update_from_window(result)                     # resultado volta ao átomo
WAL.log(window.memory)                              # memória persiste no WAL
GitOps.commit(atom, session_id)                     # átomo versionado
window.dispose()                                    # window descartada
```

---

## 7. TEMPLATE CANÔNICO DA WINDOW

Este é o template que o sistema gera automaticamente quando
o DTP despacha um átomo para execução:

````markdown
---
window_id: {atom_id}-{session_id}-{timestamp}
atomic_id: {atom_id}
version: "1.0.0"
lane:
  id: "{lane_id}"
  role: {role}
  action: {action}
  domain: {domain}
  executor: llm
cursor_state:
  FROM: "{previous_lane}"
  THIS: "{current_lane}"
  GOTO: "{next_lane}"
quality_gate:
  pmq_threshold: 9.5
  current_pmq: null
fsm:
  current_state: active
  valid_transitions:
    "active → complete": "pmq >= 9.5"
    "active → retry": "pmq < 9.5 AND iterations < 5"
    "active → blocked": "blocker == true"
---

# ── CONTENT ──────────────────────────────────────────────

{atom_content_injected_here}

# ── PROTOCOL ─────────────────────────────────────────────

> [!protocol] REGRAS DE EXECUÇÃO
>
> **FROM**: Verificar pré-condições: {pre_conditions}
> **THIS**: Executar lane {lane_id} com payload do CONTENT
> **GATE**: PMQ ≥ {pmq_threshold} → complete | < threshold → retry
> **GOTO**: Emitir para {next_lane} somente se complete
> **PROIBIDO**: Modificar PROTOCOL. Pular MEMORY.

# ── MEMORY ───────────────────────────────────────────────

> [!memory] APPEND-ONLY
>
> ```
> {previous_memory_from_wal}
> ```

# ── CURSOR ───────────────────────────────────────────────

> [!cursor] AÇÃO REQUERIDA AGORA
>
> Lane: {lane_id} | Estado: active | Iter: {iteration}
>
> {cursor_instructions_from_dtp}
````

---

## 8. INTEGRAÇÃO NA ARQUITETURA DAW-OS

```
DTP.dispatch(best_lane)
  → Window.from_atom(atom, cursor, context)   ← gera a Window
  → LLM.execute(window)                        ← LLM processa como runtime
    ├─ Lê CONTRACT → entende estado
    ├─ Lê CURSOR   → sabe onde agir
    ├─ Executa Lane em CONTENT (delta)
    ├─ Calcula PMQ → registra em CONTRACT
    ├─ Atualiza CURSOR conforme gate
    └─ Registra em MEMORY (append)
  → PMQGate.validate(window.pmq)              ← gate externo confirma
  → atom.update_from_window(window.content)   ← resultado volta ao átomo
  → WAL.log(window.memory)                    ← memória no event store
  → GitOps.commit(atom)                       ← versionamento
  → DTP.evaluate_best(updated_context)        ← próxima decisão
```

---

## 9. WAL — HANDOFF SESSION-001

```python
WAL_HANDOFF = {
    "session_id"      : "SESSION-001",
    "atoms_completed" : [
        "DAW_OS_ARCHITECTURE_V1",
        "LLM_PVM_FRAMEWORK_V1",
        "WINDOW_PROTOCOL_SPEC_V1"
    ],
    "pmq_avg"         : 9.77,
    "decisao_formato" : "Window Protocol = Markdown estruturado com 5 seções semânticas",
    "insight_chave"   : "Window ≠ arquivo. Window = ambiente de execução efêmero do LLM",
    "distincao_critica": "Átomo = dado permanente. Window = runtime temporário da Lane.",
    "next_atoms"      : [
        {
            "id"     : "ATOM-004",
            "name"   : "FPG_CANONICAL_SCHEMA_V1",
            "reason" : "Schema formal do Functional Process Graph — input universal do DTP"
        },
        {
            "id"     : "ATOM-005",
            "name"   : "PATTERN_DETECTOR_SPEC_V1",
            "reason" : "Especificar como qualquer input → FPG → Lanes detectadas"
        }
    ],
    "session_export"  : "SESSION-001.zip com 3 átomos, PMQ_avg=9.77, pronto para SESSION-002"
}
```

---

**PMQ: 9.8/10**
```
CE  (Completude):    9.9 — responde YAML vs XML vs HTMX + especifica protocolo completo
PI  (Precisão):      9.8 — template canônico, ciclo de vida, distinção átomo vs window
CC  (Clareza):       9.8 — tabela comparativa, analogia webpage, diagrama ciclo de vida
PRI (Profundidade):  9.8 — delta-update concept, Window efêmera vs átomo permanente
RA  (Relevância):    9.9 — responde exatamente a dúvida levantada no documento
EIC (Estrutura):     9.7 — 9 seções + template canônico + WAL
OVA (Originalidade): 9.7 — Window Protocol como superconjunto de Markdown é genuinamente novo
```