#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DATABASE_URL="${DATABASE_URL:-postgresql://learnforge:learnforge@127.0.0.1:5432/learnforge}"
PYTEST_BIN="${PYTEST_BIN:-$ROOT/.venv/bin/pytest}"
if [[ ! -x "$PYTEST_BIN" ]]; then
  PYTEST_BIN="pytest"
fi

docker compose up -d postgres redis

for _ in {1..40}; do
  if docker compose exec -T postgres pg_isready -U learnforge -d learnforge >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker compose exec -T postgres pg_isready -U learnforge -d learnforge >/dev/null

LEARNFORGE_POSTGRES_INTEGRATION=1 \
LEARNFORGE_TEST_DATABASE_URL="$DATABASE_URL" \
DATABASE_URL="$DATABASE_URL" \
"$PYTEST_BIN" services/api/tests/test_postgres_store_core.py -q
