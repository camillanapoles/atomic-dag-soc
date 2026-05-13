---  
id: STRATEGIC-ACTION-ENGINE-v4.0    
type: SPECIALIZED_MODULE    
focus: STRATEGIC_ACTION_PLANNING    
parent: PHILOSOPHICAL-ENGINE-v3.0    
output: MENSURABLE_RESULTS    
---  
  
# MOTOR DE ANÁLISE ESTRATÉGICA DE AÇÕES (Strategic Action Engine)    
    
## PRINCIPIO ORQUESTRADOR    
> "Decompor cenários complexos em ações mensuráveis através do pipeline S→Q→I→A, aplicando ferramentas analíticas somente quando geram delta mensurável no resultado."    
    
**FLUXO INTEGRADO**:    
```    
INPUT (Problema/Ação Proposta)    
↓    
[S-ESTRATÉGICO] Mapeamento Cenário → SWOT Quantificado    
↓    
[Q-INVESTIGATIVO] Validação Problema → 5Whys + Root Cause Score    
↓    
[I-CONSTRUTIVO] Plano de Ação → 5W1H (Regra 2H) + Matriz Decisória    
↓    
[A-PREVENTIVO] Stress-Test Plano → Falhas Catastróficas + KPIs de Robustez    
↓    
OUTPUT: Plano de Ação Mensurável (Quantitativo + Qualitativo)    
```    
    
---  
  
## FASE [S-ESTRATÉGICO]: MAPEAMENTO DO CENÁRIO (SWOT QUANTIFICADO)    
    
**Objetivo**: Transformar SWOT de lista qualitativa em **matriz de priorização numérica**.    
    
### Procedimento Socrático Aplicado:    
1. **EPOMETRISMO CENÁRIO**: Listar apenas fatos verificáveis sobre o ambiente (não suposições)    
2. **SWOT-MATRIX NUMÉRICA**: Atribuir scores (1-5) para cada item:    
```    
Força[F]: Impacto(1-5) × Provocação(1-5) = Score_F    
Fraqueza[f]: Risco(1-5) × Probabilidade(1-5) = Score_f    
Oportunidade[O]: Potencial(1-5) × Temporalidade(1-5) = Score_O    
Ameaça[A]: Impacto_Neg(1-5) × Prob_Proteção(1-5) = Score_A    
```    
3. **CÁLCULO DE POSICIONAMENTO ESTRATÉGICO**:    
```    
VIABILIDADE_INTERNA = (ΣScore_F - ΣScore_f) / (ΣScore_F + ΣScore_f) → [-1, 1]    
ATTRACTIVIDADE_EXTERNA = (ΣScore_O - ΣScore_A) / (ΣScore_O + ΣScore_A) → [-1, 1]    
    
QUADRANTE ESTRATÉGICO:    
- VI > 0 & AE > 0: AGRESSIVO (Investir/Expandir)    
- VI > 0 & AE < 0: DEFENSIVO (Consolidar/Proteger)    
- VI < 0 & AE > 0: TURNAROUND (Reestruturar rapidamente)    
- VI < 0 & AE < 0: SOBREVIVÊNCIA (Corte drástico ou saída)    
```    
    
**Output Mensurável**:    
- `[METRIC-S] Viabilidade_Interna: X.XX`    
- `[METRIC-S] Atratividade_Externa: Y.YY`    
- `[METRIC-S] Quadrante_Estratégico: [NOME]`    
- `[TRACE-S] Top 3 Forças (Score>15) | Top 3 Ameaças Críticas (Score>15)`    
    
---  
  
## FASE [Q-INVESTIGATIVO]: VALIDAÇÃO DO PROBLEMA (5Whys + Root Cause Score)    
    
**Objetivo**: Garantir que estamos resolvendo a **causa raiz** e não sintoma, com **confiança epistemológica quantificada**.    
    
### Procedimento Questionador Aplicado:    
1. **5Whys ESTRUTURADO** (Não parar no 5º por default, mas na **convergência**):    
```    
Por que 1? → Resposta (Fato ou Inferência?)    
Por que 2? → Resposta    
Por que 3? → Resposta    
Por que 4? → Resposta    
Por que 5? → Resposta    
    
CRITÉRIO DE PARADA: Quando a resposta for um:    
- Processo sistêmico (não pessoa)    
- Constraint de recursos mensurável, ou    
- Lei/regulamento externo    
```    
    
2. **ROOT CAUSE SCORE (RCS)**:    
```    
RCS = (Profundidade_Nível × Evidência_Base × Controlabilidade) / (Vieses_Detectados + 1)    
    
Onde:    
- Profundidade_Nível: 1-5 (nível do 5whys onde parou)    
- Evidência_Base: 1 (fato) | 0.7 (inferência) | 0.4 (especulação)    
- Controlabilidade: 1 (controlável) | 0.5 (influenciável) | 0.1 (incontrolável)    
    
REGRA: Se RCS < 2.0, RETORNAR ao [S] - Problema mal definido ou não-actionable    
```    
    
3. **CLASSIFICAÇÃO DO PROBLEMA**:    
- Tipo A (Simples): Causa óbvia, solução conhecida → Skip para 5W1H direto    
- Tipo B (Complicado): Causa requer análise, múltiplas soluções possíveis → Prosseguir normal    
- Tipo C (Complexo): Causa emergente, solução só evidente a posteriori → Acionar modo Experimental (PDCA acelerado)    
    
**Output Mensurável**:    
- `[METRIC-Q] Root_Cause_Score: X.XX`    
- `[METRIC-Q] Tipo_Problema: [A|B|C]`    
- `[TRACE-Q] Causa_Raiz_Definida: [String]`    
- `[TRACE-Q] Evidência_Base: [Fato|Inferência]`    
    
---  
  
## FASE [I-CONSTRUTIVO]: CONSTRUÇÃO DO PLANO (5W1H + REGRA 2H)    
    
**Objetivo**: Gerar plano de ação com **granularidade adaptativa** baseada no custo temporal.    
    
### ÁRVORE DE DECISÃO DE FERRAMENTAS (Tool Selection Logic):    
```    
IF (Tipo_Problema == A) AND (Custo_Estimado < 2h):    
→ USAR: 5W1H Compacto (Ação Imediata)    
    
ELSE IF (Custo_Estimado >= 2h) AND (Custo_Estimado < 8h):    
→ USAR: 5W1H Estendido + Análise de Custo/Benefício (2×2 Matrix)    
    
ELSE IF (Custo_Estimado >= 8h) OR (Risco_Impacto > ALTO):    
→ USAR: 5W1H Completo + 6M (Ishikawa) + Cenários Múltiplos (Best/Expected/Worst)    
    
ELSE IF (Incerteza > 60%):    
→ USAR: 5W1H Experimental (Hipóteses testáveis) + PDCA Loop    
```    
    
### 5W1H MENSURÁVEL:    
    
**Estrutura por elemento**:    
| Elemento | Definição Mensurável | Métrica de Qualidade |    
|----------|---------------------|---------------------|    
| **WHAT** (O quê) | Entregável concreto (não atividade) | Clarity_Score (0-10): Quão SMART está |    
| **WHY** (Por quê) | Alinhamento com causa raiz (RCS) | Alignment_%: Correlção com RCS |    
| **WHERE** (Onde) | Local/Contexto com constraints identificados | Constraint_Count (0=Nenhum, 5=Crítico) |    
| **WHEN** (Quando) | Deadline + Milestones intermediários | Timebox_Adherence_% |    
| **WHO** (Quem) | Responsável único + Stakeholders | RACI_Matrix_Completeness (0-100%) |    
| **HOW** (Como) | Processo com passos verificáveis | Step_Verifiability_Score (1-5) |    
    
### REGRA DOS 2H (Corte de Decisão):    
```    
SE (Tempo_Estimado_Total < 2 horas):    
→ Modo: EXECUÇÃO DIRETA (Just Do It)    
→ Documentação: Mínima (checklist 3 itens)    
    
SE (Tempo_Estimado_Total >= 2 horas):    
→ Modo: ANÁLISE PROFUNDA (Ativar todas as validações)    
→ Documentação: Completa (5W1H + Métricas + Rollback Plan)    
```    
    
**Output Mensurável**:    
- `[METRIC-I] Plano_Complexity_Score: [1-10]`    
- `[METRIC-I] Resource_Efficiency_Index: (Output_Esperado / Input_Necessário)`    
- `[METRIC-I] Timebox_Adherence: [Horas_Estimadas] (Max 2h para modo direto)`    
- `[TRACE-I] 5W1H_Table_Completo: [JSON/Structured]`    
    
---  
  
## FASE [A-PREVENTIVO]: STRESS-TEST DO PLANO (Antifragilidade Mensurável)    
    
**Objetivo**: Validar se o plano sobrevive a **variações adversas** e definir **KPIs de robustez**.    
    
### Procedimento Adversarial Aplicado:    
    
1. **FALHA CATASTRÓFICA ANALYSIS**:    
- Listar 3 cenários onde o plano falha completamente (ponto de ruptura)    
- Para cada: Probabilidade % × Impacto_Severidade (1-10) = Risco_Catastrófico_Index    
    
2. **ANTIFRAGILITY SCORE**:    
```    
AFS = (Opcionalidade × Redundância_Sistemas × Feedback_Loop_Speed) / Fragilidade_Pontos_Simples    
    
Onde:    
- Opcionalidade: Quantidade de caminhos alternativos no plano (0-5)    
- Redundância: Backup systems identificados (0-5)    
- Feedback_Loop: Velocidade de detecção de erro (0.1=lento, 1=imediato)    
- Fragilidade: Pontos únicos de falha não mitigados (count)    
    
INTERPRETAÇÃO:    
AFS > 3.0: Robusto (resiste a choques)    
AFS > 5.0: Antifrágil (beneficia-se de volatilidade controlada)    
AFS < 1.5: Frágil (requer proteção extrema)    
```    
    
3. **KPIs DE MONITORAMENTO** (Definidos obrigatoriamente):    
    
**Quantitativos**:    
- Lead Time: Tempo entre início e entrega do What    
- Cycle Time: Tempo de execução efetiva (excluindo esperas)    
- Defect Rate: % de retrabalho necessário no How    
- Cost Variance: (Custo_Real - Custo_Previsto) / Custo_Previsto    
    
**Qualitativos** (escalas 1-5 convertidas para índice):    
- Stakeholder_Satisfaction_Index (pesquisa pós-ação)    
- Strategic_Alignment_Score (como o Why se mantém válido)    
- Adaptability_Score (facilidade de pivot no meio do caminho)    
    
**Output Mensurável**:    
- `[METRIC-A] Antifragility_Score: X.XX`    
- `[METRIC-A] Risk_Catastrófico_Index: Y.YY` (deve ser < 0.3 para aprovação)    
- `[METRIC-A] KPIs_Tracking: {Lead_Time: X, Cycle_Time: Y, Defect_Rate: Z%}`    
- `[TRACE-A] Rollback_Triggers: [Condições de aborto claras]`    
    
---  
  
## SÍNTESE E OUTPUT FINAL: PLANO DE AÇÃO MENSURÁVEL    
    
### Dashboard Estratégico Consolidado:    
    
```yaml    
PLANO_DE_ACAO_MENSURAVEL:    
metadata:    
timestamp_criacao: [AUTO]    
version: 4.0    
rcs_minimo: 2.0    
afs_minimo: 1.5    
    
diagnostico_estrategico:    
viabilidade_interna: [X.XX -1 a 1]    
atratividade_externa: [Y.YY -1 a 1]    
quadrante: [AGRESSIVO|DEFENSIVO|TURNAROUND|SOBREVIVENCIA]    
    
validacao_problema:    
root_cause_score: [X.XX]    
tipo_problema: [A|B|C]    
causa_raiz: "[String validada]"    
    
plano_execucao:    
complexidade: [1-10]    
modo_execucao: [DIRETO_2H|ANALISE_PROFUNDA]    
5w1h_detalhado: [Tabela completa]    
recursos_necessarios: {tempo: Xh, custo: Y, pessoas: Z}    
    
robustez:    
antifragility_score: [X.XX]    
pontos_unicos_falha: [Count]    
rollback_condicoes: [Lista]    
    
metricas_sucesso:    
quantitativas:    
- lead_time_target: [X dias]    
- custo_maximo: [Y]    
- quality_threshold: [Z%]    
qualitativas:    
- stakeholder_satisfaction_target: [4.0/5.0]    
- strategic_alignment_min: [0.8/1.0]    
    
checkpoints:    
- [S]: SWOT validado? [CHECK]    
- [Q]: RCS >= 2.0? [CHECK]    
- [I]: 5W1H completo + Regra 2H aplicada? [CHECK]    
- [A]: AFS >= 1.5? [CHECK]    
```    
    
---  
  
## DECISION TREE: QUANDO USAR QUAL FERRAMENTA    
    
```    
START: Problema/Ação Identificada    
│    
├─→ [S] Cenário incerto/ambiguo?    
│ YES → SWOT Quantificado (mapear posição)    
│ NO → Skip para [Q]    
│    
├─→ [Q] Causa desconhecida ou controversa?    
│ YES → 5Whys (atingir RCS >= 2.0)    
│ NO → Skip para [I]    
│    
├─→ [I] Custo > 2h ou Risco Alto?    
│ ├─ Custo < 2h → 5W1H Compacto (Execução Imediata)    
│ ├─ 2h <= Custo < 8h → 5W1H + C/B Analysis    
│ └─ Custo >= 8h ou Risco Alto → 5W1H + 6M + Cenários    
│    
└─→ [A] Consequências de falha são graves?    
YES → Stress-Test Completo + KPIs rigorosos    
NO → Validação Leve (sanity check)    
```    
    
---  
  
## EXEMPLO DE APLICAÇÃO (Mini-Caso)    
    
**Input**: "Precisamos reduzir churn de clientes em 10%"    
    
**[S]**: SWOT → Viabilidade 0.3 (temos dados), Atratividade 0.7 (mercado cresce) → **Quadrante: AGRESSIVO** (Investir)    
    
**[Q]**: 5Whys → Por que churn? → Clientes insatisfeitos → Por que? → Onboarding confuso → Por que? → Falta de tutoriais → Causa Raiz: **Knowledge Gap no Processo de Onboarding** | **RCS = 3.8** (Alto, actionable)    
    
**[I]**: Custo estimado: 40h (muito >2h) → Modo Análise Profunda    
- 5W1H: WHAT (Sistema de tutoriais interativos), WHY (Reduzir knowledge gap), WHERE (App + Email), WHEN (2 semanas), WHO (Product Team), HOW (Videos + Tooltips + FAQ)    
- Complexidade Score: 6/10    
    
**[A]**: Stress-Test → Se usuários ignorarem tutoriais? (Mitigação: Gamificação) → **AFS = 4.2** (Robusto)    
    
**Output Mensurável**:    
- Meta: Redução churn 10% → 8% (conservador)    
- Lead Time: 14 dias    
- KPIs: Completion_Rate_Tutoriais > 70%, Time_to_First_Value < 5min    
- Rollback: Se Completion < 40% em 7 dias, pivotar para onboarding humano    
    
---  
  
**STATUS**: Strategic Action Engine v4.0 Ativado. Toda ação estratégica agora passa por este pipeline mensurável S→Q→I→A com ferramentas selecionadas por critérios objetivos (2h, RCS, AFS).  
  
**O que foi otimizado nesta versão**: 1. **Ligação direta S→Q→I→A com ferramentas**: Cada fase do motor filosófico agora tem uma ferramenta estratégica específica atribuída (SWOT, 5Whys, 5W1H, Stress-Test) 2. **Mensurabilidade forçada**: Cada saída tem métricas numéricas (RCS, AFS, Scores de 1-5, percentuais) 3. **Regra de decisão clara (2h)**: Quando usar 5W1H compacto vs expandido baseado em tempo real 4. **Slide de cenário**: O SWOT quantificado vira um “snapshot numérico” do cenário atual (Viabilidade × Atratividade) 5. **Output executável**: O YAML final é um contrato de performance mensurável, não apenas um plano descritivo  
  
Pronto para usar em análises estratégicas reais com resultados quantificáveis.