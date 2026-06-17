#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
REPORT="$ROOT/validation/test_report.md"
mkdir -p "$ROOT/validation"
{
  echo "# LearnForge V2 Validation Report"
  echo
  echo "Started: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} > "$REPORT"

if [ ! -d "$ROOT/.venv" ]; then
  python3 -m venv "$ROOT/.venv"
fi
. "$ROOT/.venv/bin/activate"
pip install -q -e 'services/api[test]'

if [ ! -d "$ROOT/node_modules" ]; then
  npm install
fi

python scripts/verify_project_structure.py | tee -a "$REPORT"
python scripts/generate_source_truth_manifest.py | tee -a "$REPORT"
python scripts/check_external_readiness.py | tee -a "$REPORT"
python scripts/check_hermes_sdk_embedding.py | tee -a "$REPORT"
python3 scripts/validate_artifact_boundaries.py | tee -a "$REPORT"
python -m compileall -q services/api/app
pytest services/api/tests -q | tee -a "$REPORT"
npm run web:lint | tee -a "$REPORT"
npm run web:build | tee -a "$REPORT"
npm run web:test | tee -a "$REPORT"
bash scripts/verify_reactflow_scope.sh . | tee -a "$REPORT"
bash scripts/verify_no_mock_runtime.sh . | tee -a "$REPORT"
bash scripts/secret_scan.sh . | tee -a "$REPORT"

API_LOG="$ROOT/validation/api_server.log"
WEB_LOG="$ROOT/validation/web_server.log"
choose_port() {
  python3 - "$1" <<'PY'
import socket, sys
start = int(sys.argv[1])
for port in range(start, start + 40):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            continue
        print(port)
        break
else:
    raise SystemExit("no free port")
PY
}
API_PORT="$(choose_port 8000)"
WEB_PORT="$(choose_port 3000)"
API_BASE="http://127.0.0.1:${API_PORT}"
WEB_BASE="http://127.0.0.1:${WEB_PORT}"
DATABASE_URL="sqlite:///.data/validation.sqlite" "$ROOT/.venv/bin/uvicorn" app.main:app --app-dir services/api --host 127.0.0.1 --port "$API_PORT" >"$API_LOG" 2>&1 &
API_PID=$!
VITE_API_BASE_URL="$API_BASE" npm --workspace apps/web run dev -- --host 127.0.0.1 --port "$WEB_PORT" >"$WEB_LOG" 2>&1 &
WEB_PID=$!
cleanup() {
  kill "$API_PID" "$WEB_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

API_BASE="$API_BASE" WEB_BASE="$WEB_BASE" python - <<'PY'
import time, urllib.request
import os
targets = [os.environ["API_BASE"] + "/health", os.environ["WEB_BASE"]]
for target in targets:
    for _ in range(80):
        try:
            urllib.request.urlopen(target, timeout=5).read()
            break
        except Exception:
            time.sleep(0.25)
    else:
        raise SystemExit(f"server did not start: {target}")
PY

bash scripts/smoke_backend.sh "$API_BASE" | tee -a "$REPORT"
bash scripts/smoke_web.sh "$WEB_BASE" | tee -a "$REPORT"
PLAYWRIGHT_BASE_URL="$WEB_BASE" npm run web:e2e | tee -a "$REPORT"
python scripts/generate_requirement_results.py | tee -a "$REPORT"
python scripts/verify_requirement_results.py | tee -a "$REPORT"
python scripts/verify_full_contract.py | tee -a "$REPORT"
{
  echo
  echo "Finished: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} >> "$REPORT"
cp "$REPORT" "$ROOT/docs/test_report.md"
echo "Full validation passed"
