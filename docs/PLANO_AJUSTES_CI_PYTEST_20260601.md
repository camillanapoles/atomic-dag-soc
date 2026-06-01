# Plano de Ajustes — CI/CD + Pytest Config

> Branch: `feature/ci-pytest-fix`  
> Autor: Auditor externo (Kimi Code CLI)  
> Mandato: corrigir gaps C1 (CI ausente) e C2 (pytest config quebra slow tests)  
> Regra: NUNCA mergear sem autorização explícita de @cnmfs

---

## 1. Diagnóstico dos Gaps

### Gap C1 — CI/CD ausente
**Sintoma:** README afirma "CI runs the same triad on Python 3.11/3.12/3.13 on every push and pull request", mas `.github/workflows/` não existe no repo.  
**Causa:** Workflow foi referenciado em commits antigos (`e37bf56`) mas não está presente no `main` atual. Dívidas D1 e D2 no STATUS.md indicam problemas históricos com o CI.  
**Risco:** Sem pipeline automatizada, regressões só detectadas manualmente. Contradiz mandato D2 e propósito central do projeto (falsificações baratas e rotineiras).

### Gap C2 — Pytest config quebra testes slow
**Sintoma:** `pytest -m slow` resulta em `FAIL — coverage 56.60% < 95%` mesmo com 102 testes passando.  
**Causa:** `pyproject.toml` define `addopts = "... --cov-fail-under=95"` globalmente. Testes slow usam `subprocess.Popen` e `multiprocessing.Pool`; `pytest-cov` não rastreia código em subprocessos por padrão.  
**Risco:** Falso-falha em toda execução de testes slow. Desenvolvedor perde tempo debugando coverage em vez de código.

---

## 2. Estratégia de Correção

### 2.1 Pyproject.toml — desacoplar coverage gate dos testes slow

**Abordagem:** Remover `--cov-fail-under=95` do `addopts` global. O gate de cobertura passa a ser responsabilidade do caller (CI ou desenvolvedor), não do pytest default.

```toml
# ANTES
addopts = "-ra --cov=atomic_dag --cov-report=term-missing --cov-fail-under=95"

# DEPOIS
addopts = "-ra --cov=atomic_dag --cov-report=term-missing"
```

**Justificativa:** O `addopts` é aplicado em TODAS as invocações do pytest. Queremos:
- `pytest -m "not slow" --cov-fail-under=95` → gate ativo nos testes rápidos
- `pytest -m slow --no-cov` → sem coverage nos testes slow (evita falso-falha)
- `pytest` (sem args) → coverage reportado mas sem fail-under (conveniente para desenvolvimento)

Esta abordagem é minimalista e não quebra nenhum workflow existente.

### 2.2 GitHub Actions workflow — 3 jobs, matriz 3.11/3.12/3.13

**Job `lint`:** Ruff + MyPy strict  
**Job `test-fast`:** pytest -m "not slow" com coverage e fail-under 95  
**Job `test-slow`:** pytest -m slow sem coverage  

**Justificativa para separar fast/slow:**
- Testes rápidos: 2.55s → rodam em todo push/PR como gate rápido
- Testes slow: 4.15s (SIGKILL fuzzer) → rodam em PR e push, mas são mais pesados; separação permite diagnóstico claro se falha é em lógica (fast) ou em adversarial (slow)
- MyPy e ruff são rápidos (<5s) → podem rodar em job separado para feedback imediato

**Concurrency:** Cancelar runs redundantes do mesmo branch/PR.

### 2.3 Script de conveniência local

`scripts/run-tests.sh` replica a tríade canônica localmente, documentando os comandos corretos pós-fix.

---

## 3. Checklist de Implementação

- [ ] Criar branch `feature/ci-pytest-fix` a partir de `main`
- [ ] Editar `pyproject.toml`: remover `--cov-fail-under=95` do `addopts`
- [ ] Criar `.github/workflows/ci.yml` com 3 jobs + matriz
- [ ] Criar `scripts/run-tests.sh`
- [ ] Verificar localmente: `pytest -m "not slow" --cov-fail-under=95` → PASS
- [ ] Verificar localmente: `pytest -m slow --no-cov` → PASS
- [ ] Verificar localmente: `ruff check src tests` → PASS
- [ ] Verificar localmente: `mypy src` → PASS
- [ ] Commit com cursor FROM/THIS/GOTO
- [ ] Push para origin `feature/ci-pytest-fix`
- [ ] NÃO mergear — aguardar `go merge` de @cnmfs

---

## 4. Critérios de Aceitação

1. `pytest -m "not slow" --cov-fail-under=95` passa com cobertura ≥ 95%
2. `pytest -m slow --no-cov` passa com 102 testes verdes
3. `pytest` (sem args) roda todos os 337 testes e reporta coverage sem falhar
4. CI executa em 3 versões de Python (3.11, 3.12, 3.13)
5. CI separa lint, testes rápidos e testes slow em jobs distintos
6. Zero alterações em código funcional (src/atomic_dag/*.py) — só config e infra
