#!/bin/bash
# run-tests.sh — Tríade canônica local + testes slow
# Uso: ./scripts/run-tests.sh

set -euo pipefail

echo "=========================================="
echo "== atomic-dag-soc — Tríade Canônica    =="
echo "=========================================="

echo ""
echo "==> 1. Ruff check..."
python -m ruff check src tests

echo ""
echo "==> 2. MyPy strict..."
python -m mypy src

echo ""
echo "==> 3. Fast tests + coverage (fail-under 95)..."
python -m pytest -m "not slow" \
  --cov=atomic_dag \
  --cov-report=term-missing \
  --cov-fail-under=95

echo ""
echo "==> 4. Slow tests (SIGKILL fuzzer, perf, concurrency)..."
python -m pytest -m slow --no-cov -v

echo ""
echo "=========================================="
echo "== TODOS OS TESTES PASSARAM ✅          =="
echo "=========================================="
