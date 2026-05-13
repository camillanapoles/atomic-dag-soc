┌─────────────────────────────────────────────────────────┐
│  🎯 DECISION TOPOLOGY PROTOCOL (DTP)                    │
│  ➞ Camada ACIMA de MODUS OPERANDI e CHECK-MATE          │
│  ➞ Orquestrador de decisões contínuas                   │
└─────────────────────────────────────────────────────────┘



🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻🔺🔻


TRIGGER: Sempre que existirem ≥ 2 caminhos possíveis
         OU incerteza sobre ordem de execução
         OU risco de retrabalho

├➞ [0] ENUMERAÇÃO DE CANDIDATOS
│       ➞ Listar TODAS as ações/decisões possíveis
│       ➞ Classificar cada uma: CRIAÇÃO | CORREÇÃO | REFATORAÇÃO
│       ➞ Para cada candidato, responder:
│         • O que entrega? (valor tangível)
│         • O que consome? (custo real)
│         • O que bloqueia se não feito? (dependentes)
│         • O que precisa estar pronto antes? (dependências)
│         • É reversível? (custo de desfazer)
│
├➞ [1] GRAFO DE DEPENDÊNCIAS (DAG)
│       ➞ Mapear: "X depende de Y" para todo par
│       ➞ Detectar ciclos (dependência circular)
│         └─ Se ciclo: decompor até eliminar
│       ➞ Identificar NÓS RAIZ (sem dependências = podem começar)
│       ➞ Identificar CAMINHO CRÍTICO (sequência mais longa)
│
├➞ [2] MATRIZ DE IMPACTO (por candidato)
│       ┌──────────────────────────────────────────┐
│       │ Dimensão        │ Peso    │ Score [0-10] │
│       ├──────────────────────────────────────────┤
│       │ Valor entregue   │ 0.30   │              │
│       │ Custo execução   │ 0.20   │ (invertido)  │
│       │ Risco se adiado  │ 0.20   │              │
│       │ Nº dependentes   │ 0.15   │              │
│       │ Irreversibilidade│ 0.15   │              │
│       └──────────────────────────────────────────┘
│       
│       Score(n) = Σ (peso_i × score_i)
│       
│       ➞ REGRA: Decisões IRREVERSÍVEIS + ALTO IMPACTO
│         são analisadas com profundidade 2x
│
├➞ [3] ORDENAÇÃO TOPOLÓGICA PONDERADA
│       ➞ Topological sort do DAG
│       ➞ Dentro do mesmo nível (sem dependência mútua):
│         ordenar por Score(n) decrescente
│       ➞ Resultado: FILA DE EXECUÇÃO ORDENADA
│       
│       Pseudocódigo:
│       ┌─────────────────────────────────────────┐
│       │ function order(candidates):              │
│       │   dag = build_dag(candidates)            │
│       │   assert no_cycles(dag)                  │
│       │   levels = topological_levels(dag)       │
│       │   for level in levels:                   │
│       │     level.sort_by(score, descending)     │
│       │   return flatten(levels)                 │
│       └─────────────────────────────────────────┘
│
├➞ [4] DECISÃO + DISPATCH
│       Para cada item na fila ordenada:
│       ┌─────────────────────────────────────────┐
│       │ IF tipo == CRIAÇÃO:                      │
│       │   ➞ DISPATCH → MODUS OPERANDI           │
│       │ ELIF tipo == CORREÇÃO:                   │
│       │   ➞ DISPATCH → CHECK-MATE               │
│       │ ELIF tipo == REFATORAÇÃO:                │
│       │   ➞ DISPATCH → CHECK-MATE (branch)      │
│       │     + MODUS OPERANDI (rebuild)           │
│       └─────────────────────────────────────────┘
│
├➞ [5] RE-AVALIAÇÃO PÓS-EXECUÇÃO (CONTÍNUO)
│       Após cada decisão executada:
│       ➞ Estado mudou? SIM (sempre muda)
│       ➞ Recomputar: 
│         • Dependências restantes ainda válidas?
│         • Scores mudaram com novo contexto?
│         • Surgiram novos candidatos?
│       ➞ VOLTAR A [1] com candidatos restantes
│       
│       ⚠️  Isso é O PONTO CHAVE:
│       Decisão NÃO é one-shot. É REATIVA.
│       Cada execução altera o campo de jogo.
│
└➞ [6] CRITÉRIO DE PARADA
        ➞ Fila vazia E objetivo global atingido
        ➞ OU: custo marginal > valor marginal
           (não vale mais a pena continuar)