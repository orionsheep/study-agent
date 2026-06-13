#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://127.0.0.1:3000}"
curl -fsS "$BASE" | grep -q "LearnForge V2"
echo "Web smoke passed"
