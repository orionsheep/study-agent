#!/usr/bin/env bash
#
# LearnForge 一键启动：
#   - Open Notebook sidecar (Docker Compose profile: notebooklm)
#   - english-word-fission sidecar (repo-local Next service, port 3011)
#   - LearnForge API (8011)
#   - LearnForge web (5173)
#
# 用法:
#   ./scripts/dev.sh
#
# 可配置:
#   LEARNFORGE_START_SIDECARS=0  跳过 sidecar 启动，只启动 API/web
#   LEARNFORGE_REQUIRE_SIDECARS=0 sidecar 不健康时仅警告，不中断启动
#   EFW_BASE_URL=http://localhost:3011
#   EFW_START_COMMAND="npm run start"
#
# 说明:
#   sidecar 源码/compose 均在当前 repo 内。不要依赖 Desktop 等外部项目路径。

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/services/api"
WEB_DIR="$ROOT/apps/web"
EFW_DIR="$ROOT/services/english-word-fission"
API_LOG="${API_LOG:-/tmp/learnforge_api.log}"
EFW_LOG="${EFW_LOG:-/tmp/learnforge_english_word_fission.log}"
API_PORT="${API_PORT:-8011}"
WEB_PORT="${WEB_PORT:-5173}"
OPEN_NOTEBOOK_API_URL="${OPEN_NOTEBOOK_API_URL:-http://localhost:5055}"
OPEN_NOTEBOOK_WEB_URL="${OPEN_NOTEBOOK_WEB_URL:-http://localhost:8502}"
EFW_BASE_URL="${EFW_BASE_URL:-http://localhost:3011}"
EFW_DATABASE_URL="${EFW_DATABASE_URL:-postgresql://learnforge:learnforge@localhost:5432/learnforge?schema=LPT_english}"
EFW_START_COMMAND="${EFW_START_COMMAND:-npm run dev -- --port 3011}"
LEARNFORGE_START_SIDECARS="${LEARNFORGE_START_SIDECARS:-1}"
LEARNFORGE_REQUIRE_SIDECARS="${LEARNFORGE_REQUIRE_SIDECARS:-1}"

API_PID=""
EFW_PID=""
CLEANED=0

port_from_url() {
  local url="$1"
  local rest="${url#*://}"
  local hostport="${rest%%/*}"
  if [[ "$hostport" == *:* ]]; then
    echo "${hostport##*:}"
  elif [[ "$url" == https:* ]]; then
    echo "443"
  else
    echo "80"
  fi
}

OPEN_NOTEBOOK_API_PORT="$(port_from_url "$OPEN_NOTEBOOK_API_URL")"
OPEN_NOTEBOOK_WEB_PORT="$(port_from_url "$OPEN_NOTEBOOK_WEB_URL")"
EFW_PORT="$(port_from_url "$EFW_BASE_URL")"

cleanup() {
  [ "$CLEANED" -eq 1 ] && return
  CLEANED=1
  echo
  echo "→ 正在停止 LearnForge 前后端..."
  [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null || true
  if [ -n "$EFW_PID" ]; then
    echo "→ 正在停止本脚本启动的 english-word-fission..."
    kill "$EFW_PID" 2>/dev/null || true
    lsof -ti:"$EFW_PORT" 2>/dev/null | xargs kill 2>/dev/null || true
  fi
  lsof -ti:"$API_PORT" 2>/dev/null | xargs kill 2>/dev/null || true
  lsof -ti:"$WEB_PORT" 2>/dev/null | xargs kill 2>/dev/null || true
  echo "✓ 已停止 LearnForge 前后端；Docker sidecar 保持运行以便下次秒开"
}
trap cleanup EXIT INT TERM

fail_or_warn() {
  local message="$1"
  if [ "$LEARNFORGE_REQUIRE_SIDECARS" = "1" ]; then
    echo "✗ $message"
    exit 1
  fi
  echo "⚠ $message"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || { echo "✗ 找不到 $1"; exit 1; }
}

open_notebook_ready() {
  curl -fsS -m 5 "$OPEN_NOTEBOOK_API_URL/health" >/dev/null 2>&1 ||
    curl -fsS -m 5 "$OPEN_NOTEBOOK_API_URL/api/health" >/dev/null 2>&1
}

english_ready() {
  curl -fsS -m 8 -H "X-User-Id: health-check" "$EFW_BASE_URL/api/libraries" >/dev/null 2>&1
}

english_owned_by_repo() {
  local pid cwd
  for pid in $(lsof -ti:"$EFW_PORT" 2>/dev/null); do
    cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)"
    [ "$cwd" = "$EFW_DIR" ] && return 0
  done
  return 1
}

wait_for() {
  local label="$1"
  local timeout="$2"
  local check_fn="$3"
  for _ in $(seq 1 "$timeout"); do
    if "$check_fn"; then
      echo "✓ $label 就绪"
      return 0
    fi
    sleep 1
  done
  return 1
}

ensure_docker() {
  if docker info >/dev/null 2>&1; then
    return 0
  fi
  if [[ "$(uname -s)" == "Darwin" ]]; then
    echo "→ Docker daemon 未就绪，尝试启动 Docker Desktop..."
    open -a Docker >/dev/null 2>&1 || true
  fi
  echo "→ 等待 Docker daemon..."
  for _ in $(seq 1 90); do
    docker info >/dev/null 2>&1 && return 0
    sleep 2
  done
  return 1
}

ensure_postgres() {
  echo "→ 启动共享 Postgres/Redis（英语 sidecar 使用同一个本地 Postgres）"
  docker compose up -d postgres redis >/dev/null
  for _ in $(seq 1 60); do
    if docker compose exec -T postgres pg_isready -U learnforge -d learnforge >/dev/null 2>&1; then
      echo "✓ Postgres 就绪"
      return 0
    fi
    sleep 1
  done
  return 1
}

ensure_open_notebook() {
  if [ "$LEARNFORGE_START_SIDECARS" != "1" ]; then
    if open_notebook_ready; then
      echo "✓ Open Notebook 已就绪 → $OPEN_NOTEBOOK_API_URL"
    else
      fail_or_warn "Open Notebook 未就绪，且 LEARNFORGE_START_SIDECARS=0"
    fi
    return 0
  fi
  ensure_docker || { fail_or_warn "Docker daemon 不可用，无法启动 Open Notebook"; return 0; }
  local compose_container
  compose_container="$(docker compose --profile notebooklm ps -q open_notebook 2>/dev/null || true)"
  if open_notebook_ready; then
    if [ -n "$compose_container" ] && [ "$(docker inspect -f '{{.State.Running}}' "$compose_container" 2>/dev/null || true)" = "true" ]; then
      echo "✓ Open Notebook 已就绪 → $OPEN_NOTEBOOK_API_URL"
      return 0
    fi
    fail_or_warn "Open Notebook 端口已有健康服务，但不是当前 repo 的 compose 容器。请停止外部 open-notebook 容器后重试。"
    return 0
  fi

  echo "→ 启动当前 repo 的 Open Notebook sidecar → $OPEN_NOTEBOOK_WEB_URL / $OPEN_NOTEBOOK_API_URL"
  if ! OPEN_NOTEBOOK_ENCRYPTION_KEY="${OPEN_NOTEBOOK_ENCRYPTION_KEY:-learnforgeopennotebooksecret0000}" \
      OPEN_NOTEBOOK_PASSWORD="${OPEN_NOTEBOOK_PASSWORD:-}" \
      docker compose --profile notebooklm up -d open_notebook_surrealdb open_notebook; then
    if open_notebook_ready; then
      echo "✓ Open Notebook 已由现有端口服务提供"
      return 0
    fi
    echo "最近容器状态："
    docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E 'open_notebook|8502|5055' || true
    fail_or_warn "Open Notebook 启动失败。请检查 $OPEN_NOTEBOOK_API_PORT/$OPEN_NOTEBOOK_WEB_PORT 是否被非本项目服务占用。"
    return 0
  fi
  wait_for "Open Notebook" 120 open_notebook_ready || fail_or_warn "Open Notebook 未在 120 秒内就绪"
}

ensure_english_word_fission() {
  if english_ready; then
    if english_owned_by_repo; then
      echo "✓ english-word-fission 已就绪 → $EFW_BASE_URL"
      return 0
    fi
    fail_or_warn "english-word-fission 端口已有健康服务，但不是当前 repo 的 $EFW_DIR。请停止外部英语服务后重试。"
    return 0
  fi
  [ "$LEARNFORGE_START_SIDECARS" = "1" ] || { fail_or_warn "english-word-fission 未就绪，且 LEARNFORGE_START_SIDECARS=0"; return 0; }
  [ -d "$EFW_DIR" ] || { fail_or_warn "找不到当前 repo 内的英语服务目录：$EFW_DIR"; return 0; }
  [ -f "$EFW_DIR/package.json" ] || { fail_or_warn "英语服务缺少 package.json：$EFW_DIR"; return 0; }
  if lsof -ti:"$EFW_PORT" >/dev/null 2>&1; then
    fail_or_warn "端口 $EFW_PORT 已被占用，但 $EFW_BASE_URL/api/libraries 不健康。请停止占用进程后重试。"
    return 0
  fi

  if [ ! -d "$EFW_DIR/node_modules" ]; then
    echo "→ 安装 english-word-fission 依赖（首次启动会稍久）"
    ( cd "$EFW_DIR" && npm install )
  fi

  echo "→ 初始化 english-word-fission Prisma schema"
  (
    cd "$EFW_DIR" &&
    DATABASE_URL="$EFW_DATABASE_URL" npx prisma generate &&
    DATABASE_URL="$EFW_DATABASE_URL" npx prisma db push --accept-data-loss
  ) >>"$EFW_LOG" 2>&1 || {
    echo "✗ Prisma 初始化失败，最近日志："
    tail -40 "$EFW_LOG" || true
    exit 1
  }

  echo "→ 启动当前 repo 的 english-word-fission → $EFW_BASE_URL   (日志: $EFW_LOG)"
  (
    cd "$EFW_DIR" &&
    DATABASE_URL="$EFW_DATABASE_URL" AUTH_API_BASE="${AUTH_API_BASE:-}" exec bash -lc "$EFW_START_COMMAND"
  ) >"$EFW_LOG" 2>&1 &
  EFW_PID=$!
  if ! wait_for "english-word-fission" 90 english_ready; then
    echo "✗ english-word-fission 启动失败，最近日志："
    tail -50 "$EFW_LOG" || true
    exit 1
  fi
}

check_api_sidecars() {
  local notebook_status english_status
  notebook_status="$(curl -fsS -m 8 "http://127.0.0.1:$API_PORT/api/notebooklm/status" 2>/dev/null || true)"
  english_status="$(curl -fsS -m 8 "http://127.0.0.1:$API_PORT/api/english/health" 2>/dev/null || true)"
  echo "$notebook_status" | grep -q '"status":"ready"\|"status": "ready"' || fail_or_warn "LearnForge API 看到的 NotebookLM 仍未 ready：$notebook_status"
  echo "$english_status" | grep -q '"reachable":true\|"reachable": true' || fail_or_warn "LearnForge API 看到的英语服务仍未 reachable：$english_status"
}

# ── 0. 依赖检查 ──
if [ ! -x "$API_DIR/.venv/bin/python" ]; then
  echo "✗ 找不到 $API_DIR/.venv/bin/python —— 请先创建后端虚拟环境"
  exit 1
fi
require_command npm
require_command lsof
require_command curl

# ── 1. 启动 sidecars ──
if [ "$LEARNFORGE_START_SIDECARS" = "1" ]; then
  require_command docker
  ensure_docker || { fail_or_warn "Docker daemon 不可用，无法启动本地 sidecars"; }
  ensure_postgres || fail_or_warn "Postgres 未就绪"
  ensure_open_notebook
  ensure_english_word_fission
else
  echo "→ 跳过 sidecar 启动（LEARNFORGE_START_SIDECARS=0）"
fi

# ── 2. 启动后端（后台）──
if lsof -ti:"$API_PORT" >/dev/null 2>&1; then
  echo "→ 端口 $API_PORT 已被占用，跳过后端启动（当作它就是 LearnForge API）"
else
  echo "→ 启动后端 API  →  http://127.0.0.1:$API_PORT   (日志: $API_LOG)"
  (
    cd "$API_DIR" &&
    OPEN_NOTEBOOK_API_URL="$OPEN_NOTEBOOK_API_URL" \
    OPEN_NOTEBOOK_WEB_URL="$OPEN_NOTEBOOK_WEB_URL" \
    EFW_BASE_URL="$EFW_BASE_URL" \
    exec ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "$API_PORT"
  ) >"$API_LOG" 2>&1 &
  API_PID=$!
  echo "→ 等待后端就绪..."
  for _ in $(seq 1 60); do
    if curl -sf "http://127.0.0.1:$API_PORT/openapi.json" >/dev/null 2>&1; then
      echo "✓ 后端就绪"
      break
    fi
    if ! kill -0 "$API_PID" 2>/dev/null; then
      echo "✗ 后端启动失败，最近日志："
      tail -25 "$API_LOG" || true
      exit 1
    fi
    sleep 0.5
  done
fi

check_api_sidecars

# ── 3. 启动前端（前台）──
echo "→ 启动前端 web  →  http://localhost:$WEB_PORT"
echo "  （Ctrl+C 停止 API/web 和本脚本启动的英语 sidecar；Docker sidecar 保持运行）"
echo
cd "$WEB_DIR"
npm run dev -- --port "$WEB_PORT" --strictPort
