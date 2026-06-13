#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://127.0.0.1:8000}"
curl -fsS "$BASE/health" >/tmp/learnforge_health.json
curl -fsS "$BASE/api/system/status" >/tmp/learnforge_status.json
curl -fsS -X POST "$BASE/api/chat/message" \
  -H 'Content-Type: application/json' \
  -d '{"student_id":"demo-student","course_id":"ai-course","conversation_id":"smoke","message":"生成动能定理演示"}' >/tmp/learnforge_chat.json
python3 - <<'PY'
import json
for path in ['/tmp/learnforge_health.json', '/tmp/learnforge_chat.json']:
    data = json.load(open(path))
    assert data
print('Backend smoke passed')
PY
