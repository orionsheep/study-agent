#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
FORBIDDEN=(
  "mock tutor response"
  "boundary_mock_adapter"
  "fake provider"
  "simulated MiMo"
  "simulated Hermes"
  "placeholder response"
  "TODO real integration"
  "in-memory only"
  "frontend-only fake stream"
)
for term in "${FORBIDDEN[@]}"; do
  if grep -RIn --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.runtime --exclude-dir=.data --exclude-dir=validation --exclude-dir=dist --exclude-dir=build --exclude='*.md' --exclude='*test*' --exclude='*spec*' --exclude='verify_no_mock_runtime.sh' "$term" "$ROOT" >/tmp/learnforge_forbidden.txt 2>/dev/null; then
    echo "Forbidden runtime term found: $term"
    cat /tmp/learnforge_forbidden.txt
    exit 1
  fi
done
if grep -RIn --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=build --include='*.py' --include='*.ts' --include='*.tsx' "mock" "$ROOT/services" "$ROOT/apps" 2>/dev/null | grep -Ev '/tests/|/fixtures/|test_provider|mocking|unmock' >/tmp/learnforge_mock.txt; then
  echo "Potential mock outside tests/fixtures found"
  cat /tmp/learnforge_mock.txt
  exit 1
fi
echo "No forbidden mock runtime patterns found"
