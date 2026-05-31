# WAL Humano — Sprint 3 do `atomic-dag-soc`

> Continuação do WAL_HUMANO.md (Sprint 2). Mesma convenção: cronológico,
> narrativo, decisões com justificativa, correções com a lição extraída.
> Sem amenizar, sem inflar. Quando conflitar com ADR/spec, o ADR/spec vence.

## 0. Estado herdado de Sprint 2

Branch `main` em `da46621` (depois estendido por 2.H-2.M docs sync até
`a943e90`). Tag `v0.3.0-sprint2`. 9 módulos, 256 testes, cov 98.54%.
Sprint 3 endereça FM-10 (RPN=162, TD-003): `tick_streaming` não acopla
`advance_cursor` → cursor stale → continuidade cross-session quebra.

## 1. Fases 3.A–3.B — spec antes de código

- **3.A (ADR-007, PR #11/#12, merge `486f766`):** ADR-007 com §0 nota
  terminológica Popperiana (fecha D13 durável), D1-D8, DA-1/2/3, e D7 como
  critério Popperiano-mestre (par red→green de test_fm10_regression).
- **3.B (api/streaming.md, merge `ecd86c2`):** contrato observável de
  tick_streaming + advance_cursor + StreamEvent + TickResult + exit codes.

## 2. Incidente do autogate (entre 3.B e 3.C)

Durante operação autônoma, o executor passou a auto-avançar fase→fase ao ver
CI verde, e um mandato 3.A→3.G "de uma vez" foi emitido. Isso quebrou o
protocolo "uma fase, um go". Detectado e retificado:

- **Autogate ERRADICADO** → invariante **I8-ext** gravado no CLAUDE.md (3.C):
  "CI verde é pré-condição, nunca gatilho; após reportar → IDLE".
- Mandato monolítico cancelado; retomado um-mandato-por-fase.
- Branch de 3.C feita sob autogate (com CI vermelho por furo de cobertura)
  abandonada; refeita limpa.

**Lição L-orq-autogate:** velocidade sem checkpoint reintroduz o risco que o
projeto existe para impedir. O `go` humano por fase é o gate de continuidade.

## 3. Furo do ADR-007 D7 (corrigido em 3.C)

O D7 original prescrevia "skeleton sem teste (RED) → coupling (GREEN)" em dois
commits — incompatível com `cov-fail-under=95` global (todo push abaixo de 95%
→ CI vermelho). Contradizia o precedente real 2.C.2 (`1d5f18f`: transitions.py
100% no próprio skeleton). Decidido via FDC-U (S-A, Σ 7.50): módulo + testes
JUNTOS num PR; o red→green é do test_fm10_regression especificamente, não da
cobertura do módulo. **L-orq-14** registrado: mandato não decompõe código em
commits sem cobertura sob gate global.

## 4. Fase 3.C — streaming.py + FM-10 closure (PR #14, merge `83d9a17`)

`streaming.py` implementado; `tick_streaming` invoca `advance_cursor` (ordem
D1/D11: advance + write_atomic(state.json) ANTES do WAL). Par Popperiano:
`1049649` (RED local, sem coupling) → `64c3f5e` (GREEN). test_fm10_regression
com dois mecanismos: comportamental (cursor no disco) + estrutural (spy).
20 testes, streaming.py 100%, global 98.70%.

Dois incidentes de honestidade (I1), detectados e corrigidos pelo executor:
(1) superdeclaração de 8 arquivos quando commit tinha 6 (CLAUDE.md+STATUS não
persistiram por tooling; fix-forward `b47f779`); (2) SHAs placeholder no [COMS]
de merge antes do retorno real (corrigido com SHA medido). Ambos reportados com
transparência. **Lição:** `git show --stat HEAD` antes de declarar contagem;
nunca escrever SHA antes do resultado real chegar.

## 5. Fase 3.D — bateria adversarial (PR #15, merge `d5bdf2d`)

Três arquivos espelhando 2.D: test_streaming_sigkill (α.3 determinístico, 50×),
concurrency (4-proc), performance (p99). **50/50 in_critical_window**, zero
violação WAL-ahead-of-disk. Perf p99 2.72ms. Confirmado em CI que os testes
slow rodaram (327 passed, não 225) — D7 provado em CI, não só local.

## 6. Fase 3.E — CLI stream (PR #16, merge `2a1f8b2`)

Subcommand `atomic-dag stream` (DA-3: separado de transition). JSONL de
--events-file/stdin; exit 0/1/2. Fase dedicada I4 (cli.py): só ADICIONA stream,
funções existentes intactas (zero deleção no diff). cli.py 100%, 10 testes.

## 7. Fase 3.F — TD-003 Resolved (PR #17, merge `c324e58`)

Docs-only. TD-003 (FM-10) movida de Active para Resolved no TECHNICAL_DEBT.md,
com verificação prévia (cov 98.78% + test_fm10_regression 3/3) colada ANTES de
declarar — "a fact, not an aspiration".

## 8. Fase 3.G — fechamento (este documento + tag v0.4.0-sprint3)

Sprint 3 fechado. Tag ANNOTATED v0.4.0-sprint3 (lição D8 do Sprint 2: a tag
anterior ficou lightweight via UI; esta nasce annotated).

## 9. Padrões que emergiram no Sprint 3

- **Protocolo restaurado funciona:** após erradicar o autogate, as fases
  3.C→3.G correram sob "uma fase, um go, validação na fonte" sem incidente
  de processo. O custo de um `go` por fase é o que garante a confiabilidade.
- **Furos de mandato pegos cedo:** o D7 incompatível foi pego pelo CI vermelho
  na primeira tentativa de 3.C; corrigido antes de qualquer merge. Captura
  precoce, custo barato (padrão 6.2 do WAL Sprint 2 confirmado).
- **Honestidade do executor:** três autocorreções (superdeclaração ×2 +
  placeholder) reportadas, não escondidas. I1 em ação.

## 10. Sprint 3 estatística final

- 7 fases (3.A-3.G), 7 PRs (#11-#17), todos CI 3-matriz verde (D2)
- FM-10 (RPN=162) FECHADO — maior risco aberto do FMEA neutralizado
- streaming.py 100%, global ~98.78%, suite 337 testes
- Prova adversarial: 50/50 SIGKILL α.3 in_critical_window
- Critério Popperiano-mestre satisfeito: par red→green em main, regressão
  ativa em todo push
- Dívidas: TD-003 fechada; D13 fechada durável (ADR-007 §0); I8-ext inaugurado
- Tag v0.4.0-sprint3 (annotated)

## 11. Onde estamos, em uma frase

Sprint 3 fechado: FM-10 neutralizado com prova adversarial em CI, streaming
operacional via CLI, continuidade cross-session falsificável e testada.
Próximo: Sprint 4 (Hello SOC + arXiv + DOI).
