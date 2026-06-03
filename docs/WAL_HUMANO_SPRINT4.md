# WAL Humano — Sprint 4 do `atomic-dag-soc`

> Continuação de WAL_HUMANO.md (S2) e WAL_HUMANO_SPRINT3.md (S3). Mesma
> convenção: cronológico, narrativo, decisões com justificativa, correções com
> a lição. Sem amenizar, sem inflar. Quando conflitar com ADR/spec, o ADR/spec vence.

## 0. Estado herdado de Sprint 3

Branch `main` em `6818856` (Sprint 3 fechado). Tag `v0.4.0-sprint3`
(lightweight — D8: o GitHub UI não cria tags annotated; corrigido o registro
em 4.E, que dizia "annotated" por engano). 12 módulos, 337 testes, cov 98.78%.
FM-10 neutralizado. Sprint 4 sai da arquitetura interna para a entrega externa:
demonstrar o sistema rodando ponta-a-ponta com um runtime LLM.

## 1. Resequenciamento (decisão do operador, antes de 4.A)

Antes de abrir o Sprint 4, o operador reavaliou a sequência de publicação. Via
FDC-U, decidiu-se separar arXiv (retratável) de DOI (permanente) por
permanência, e introduziu-se "otimização-antes-de-publicação". Resultado: arXiv
→ S7, DOI → S8 (gate isolado, último ato). Formalizado em ADR-008. Isto herda o
princípio do ADR-003 Lesson 2 (replanejar a cada sprint = VVV aplicado ao plano).
**Lição L-plan-1/2/3:** a retratabilidade do arXiv é rede de segurança, não
licença para publicar imaturo; o DOI permanente merece gate isolado; a regra de
ordenação é fixa mas as datas são recalibráveis.

## 2. Fase 4.A — ADR-008 (PR #19, merge `8e1bea3`)

Regra de ordenação de publicação por permanência + otimização-antes-de-publicação
+ replan contínuo. Supersede parcialmente ADR-005 (timing; mecanismo "Zenodo
requires public" retido). docs-only.

## 3. Fase 4.B — ADR-009 + api/llm-bridge.md (PR #20, merge `90f1d8c`)

Decisão + contrato fundidos num PR. ADR-009: escopo minimalista da ponte
(chamada API + parse + injeção; Provider Protocol + mock; LLM_PVM_FRAMEWORK
fora de escopo). api/llm-bridge.md: contrato observável. docs-only. Padrão
ADR→api→code preservado.

## 4. Fase 4.C — llm_bridge.py (PR #21, merge `ce309c3`)

Primeiro código que cruza a fronteira LLM↔Python operacionalmente (ADR-001
materializado). bridge_transition/bridge_stream + LLMProvider Protocol +
AnthropicProvider (lazy import) + BridgeAPIError/BridgeParseError. A ponte
escreve só o BODY (frontmatter byte-preservado); todo estado é delegado a
execute_transition/tick_streaming (D-bridge-3). 60 stmts, 100% cov, 16 testes
mock (zero LLM real). Modo S-A.

Três decisões honestas do executor, todas ancoradas na fonte: (1) FSM real não
tem "draft" — usou pending+do→in-progress; (2) pyproject [llm] já existia
(no-op); (3) removeu uma branch defensiva morta do esqueleto do orquestrador
(cov 98.78→98.90; M3 + regra "no error handling for impossible scenarios").

## 5. Fase 4.D — Hello SOC (PR #22, merge `bb54224`)

Primeiro USO real da ponte: 3 átomos reais (HELLO-001/002/003) percorrem o ciclo
FSM completo (pending→in-progress→checked→verified→completed→closed) com body
gerado pela ponte. **Tensão resolvida:** o ROADMAP pede "átomos reais" e o
D-bridge-5 pede "zero LLM real na suite" — resolvido distinguindo átomo (real)
de provider (gravado em CI via RecordedProvider; AnthropicProvider real só
manual com --real). 5 testes end-to-end, `['closed','closed','closed']`.

Decisão ancorada: só `do` usa bridge_transition (regenera body); check/next/last
usam execute_transition direto. **UX fix descoberto no teste (I1):** rodar da
raiz mutava os átomos in-repo; corrigido para copiar a tmp dir por padrão
(--in-place opcional). O exemplo não corrompe o repo.

## 6. Fase 4.E — build_dashboard.py / I-DASH N2 (PR #23, merge `33bd7dd`)

Mecaniza o I-DASH: a seção `meta` do dashboard (HEAD/tag/fase — a que defasa em
TODA fase) passa a ser regenerada de STATUS.md, com gate `--check` enforçado na
3-matriz CI via subprocess (sem tocar ci.yml). **Escopo cirúrgico:** só `meta`
religada; timeline/debts têm parsers prontos e testados mas NÃO religados —
carregam prosa curada que divergiria das tabelas. Decisão escalada e aprovada
(normalização STATUS→dashboard fica para o Sprint 6/meta-uso).

Dois achados de honestidade (I1): (1) bug de regex (named group interno
deslocou índices; group(3) era o body, não o END marker → corrompeu a região na
1ª run) — diagnosticado em isolamento, corrigido com named groups, dashboard
restaurado do HEAD e refeito limpo; (2) fix pré-existente em verify_setup.py
(F541 + reuso de var), surfado ao incluir scripts/ no lint scope.

## 7. Fase 4.F — fechamento (este documento + tag v0.5.0-sprint4)

Sprint 4 fechado. Esta é a PRIMEIRA fase a usar o I-DASH mecanizado: a meta do
dashboard foi regenerada rodando build_dashboard.py, não à mão.

## 8. Padrões do Sprint 4

- **Sprint sem incidente de processo:** ao contrário do S3 (autogate), o S4
  correu 4.A→4.F sob "uma fase, um go, validação na fonte" sem nenhuma quebra de
  protocolo. O protocolo restaurado provou-se estável por um sprint inteiro.
- **Resolução de tensões na fonte:** 4.D (átomos reais vs zero-LLM-real) e a
  ambiguidade do contrato §4 em 4.C (bridge escreve vs delega) foram resolvidas
  lendo a fonte, não chutando — e escaladas quando genuinamente ambíguas.
- **Honestidade sustentada:** cada fase trouxe autocorreções reportadas
  (3 em 4.C, UX fix em 4.D, bug de regex + fix pré-existente em 4.E). I1 vivo.
- **Marco arquitetural:** ADR-001 (dual-layer LLM⊥Python), descrito desde o
  Sprint 0, tornou-se operacional em 4.C e demonstrado em 4.D.

## 9. Sprint 4 estatística final

- 6 fases (4.A-4.F), 6 PRs (#19-#23 + close), CI 3-matriz verde em cada (D2)
- ADR-001 materializado: fronteira LLM↔Python operacional
- Hello SOC end-to-end com átomos reais (critério Popperiano-mestre do sprint)
- I-DASH mecanizado N2 (build_dashboard.py + gate --check em CI)
- llm_bridge.py 100%, suite ~368 testes, cov global 98.90%, 13 módulos
- Sem publicação (arXiv/DOI resequenciados para S7/S8 por ADR-008)
- Correção factual: tag v0.4.0-sprint3 é lightweight, não annotated (D8)
- Tag v0.5.0-sprint4

## 10. Onde estamos, em uma frase

Sprint 4 fechado: o framework saiu de "implementado e testado" para
"demonstrado" — a ponte LLM↔Python opera, o Hello SOC roda ponta-a-ponta com
átomos reais, e o status se auto-atualiza. Próximo: Sprint 5 (robustez —
writer fix → reconcile → per-atom locking).
