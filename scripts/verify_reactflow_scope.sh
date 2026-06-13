#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
if grep -RIn --include='*.tsx' --include='*.ts' 'ReactFlow' "$ROOT/apps/web/src/features/app-canvas" >/tmp/learnforge_reactflow.txt 2>/dev/null; then
  echo "React Flow appears in main canvas scope"
  cat /tmp/learnforge_reactflow.txt
  exit 1
fi
echo "React Flow scope verified"
