#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d "$ROOT/.venv" ]; then
  python3 -m venv "$ROOT/.venv"
fi

. "$ROOT/.venv/bin/activate"
pip install -q -e 'services/api[test]'

python -m compileall -q services/api/app
pytest \
  services/api/tests/test_memory_closed_loop.py \
  services/api/tests/test_edumem0_policies.py \
  services/api/tests/test_memory_end_to_end.py \
  services/api/tests/test_agents_and_skills.py \
  -q

npm run web:lint
npm run web:test -- --run tests/renderers.test.tsx
npm run web:build
