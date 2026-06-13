#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
if grep -RInE --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=dist --exclude-dir=build --exclude-dir=.git \
  --exclude-dir=.data --exclude-dir=.runtime \
  --exclude='package-lock.json' --exclude='.env' --exclude='.env.*' \
  '(sk-[A-Za-z0-9_-]{20,}|Bearer [A-Za-z0-9._-]{24,}|api[_-]?key[[:space:]]*=[[:space:]]*["'\''][^"'\'']{12,})' "$ROOT" >/tmp/learnforge_secrets.txt 2>/dev/null; then
  echo "Potential secret found"
  sed -E \
    -e 's/sk-[A-Za-z0-9_-]{20,}/sk-<redacted>/g' \
    -e 's/Bearer [A-Za-z0-9._-]{24,}/Bearer <redacted>/g' \
    -e 's/(api[_-]?key[[:space:]]*=[[:space:]]*["'\''])[^\'''\"']{12,}(["'\''])/\1<redacted>\2/g' \
    /tmp/learnforge_secrets.txt
  exit 1
fi
echo "Secret scan passed"
