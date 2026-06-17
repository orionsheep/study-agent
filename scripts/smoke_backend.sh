#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://127.0.0.1:8000}"
CONNECT_TIMEOUT_SECONDS="${CONNECT_TIMEOUT_SECONDS:-10}"
SMOKE_TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-30}"
LIVE_SMOKE_TIMEOUT_SECONDS="${LIVE_SMOKE_TIMEOUT_SECONDS:-180}"
curl -fsS --connect-timeout "$CONNECT_TIMEOUT_SECONDS" --max-time "$SMOKE_TIMEOUT_SECONDS" "$BASE/health" >/tmp/learnforge_health.json
curl -fsS --connect-timeout "$CONNECT_TIMEOUT_SECONDS" --max-time "$SMOKE_TIMEOUT_SECONDS" "$BASE/api/system/status" >/tmp/learnforge_status.json
python3 scripts/validate_artifact_boundaries.py
curl -fsS --connect-timeout "$CONNECT_TIMEOUT_SECONDS" --max-time "$SMOKE_TIMEOUT_SECONDS" \
  "$BASE/api/chat/messages?student_id=demo-student&course_id=ai-course&conversation_id=smoke" >/tmp/learnforge_history.json
if [ "${LEARNFORGE_LIVE_SMOKE:-0}" = "1" ]; then
  for payload in \
    '{"student_id":"demo-student","course_id":"ai-course","conversation_id":"smoke","message":"生成动能定理演示"}' \
    '{"student_id":"demo-student","course_id":"ai-course","conversation_id":"smoke-ppt","message":"请把伯努利定律总结成PPT"}' \
    '{"student_id":"demo-student","course_id":"ai-course","conversation_id":"smoke-interactive","message":"生成一个伯努利定律的可交互模型"}' \
    '{"student_id":"demo-student","course_id":"ai-course","conversation_id":"smoke-image","message":"生成一张人船模型的教学图"}' \
    '{"student_id":"demo-student","course_id":"ai-course","conversation_id":"smoke-video","message":"找一下机械振动相关物理题目相关的视频"}'; do
    curl -fsS --connect-timeout "$CONNECT_TIMEOUT_SECONDS" --max-time "$LIVE_SMOKE_TIMEOUT_SECONDS" \
      -X POST "$BASE/api/chat/message" -H 'Content-Type: application/json' -d "$payload" >/tmp/learnforge_live_smoke.json || {
      echo "Live smoke failed for payload: $payload" >&2
      exit 1
    }
  done
  curl -fsS --connect-timeout "$CONNECT_TIMEOUT_SECONDS" --max-time "$SMOKE_TIMEOUT_SECONDS" \
    "$BASE/api/chat/messages?student_id=demo-student&course_id=ai-course&conversation_id=smoke-video" >/tmp/learnforge_history.json
fi
python3 - <<'PY'
import json
for path in ['/tmp/learnforge_health.json', '/tmp/learnforge_history.json']:
    data = json.load(open(path))
    assert data is not None
print('Backend smoke passed')
PY
