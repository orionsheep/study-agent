#!/usr/bin/env bash
#
# LearnForge 一键启动：后端 API (8011) + 前端 web (5173)
#
#   用法:  ./scripts/dev.sh
#
#   - 后端跑在后台，日志写到 /tmp/learnforge_api.log（可用 API_LOG 环境变量覆盖）
#   - 前端跑在前台，Vite 输出直接显示在终端
#   - Ctrl+C 会同时停掉前后端
#   - 如果某端口已被占用，会跳过对应服务的启动（假设那就是 LearnForge）

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/services/api"
WEB_DIR="$ROOT/apps/web"
API_LOG="${API_LOG:-/tmp/learnforge_api.log}"
API_PORT=8011
WEB_PORT=5173

API_PID=""
CLEANED=0

cleanup() {
  [ "$CLEANED" -eq 1 ] && return
  CLEANED=1
  echo
  echo "→ 正在停止服务..."
  # 停后端进程（若本脚本启动了它）
  [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null
  # 兜底：按端口清理，确保不留僵尸进程
  lsof -ti:"$API_PORT" 2>/dev/null | xargs kill 2>/dev/null
  lsof -ti:"$WEB_PORT" 2>/dev/null | xargs kill 2>/dev/null
  echo "✓ 已停止"
}
trap cleanup EXIT INT TERM

# ── 0. 依赖检查 ──
if [ ! -x "$API_DIR/.venv/bin/python" ]; then
  echo "✗ 找不到 $API_DIR/.venv/bin/python —— 请先创建后端虚拟环境"
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "✗ 找不到 npm"
  exit 1
fi
command -v lsof >/dev/null 2>&1 || { echo "✗ 找不到 lsof"; exit 1; }

# ── 1. 启动后端（后台）──
if lsof -ti:"$API_PORT" >/dev/null 2>&1; then
  echo "→ 端口 $API_PORT 已被占用，跳过后端启动（当作它就是 LearnForge API）"
else
  echo "→ 启动后端 API  →  http://127.0.0.1:$API_PORT   (日志: $API_LOG)"
  ( cd "$API_DIR" && exec ./.venv/bin/python -m uvicorn app.main:app \
        --host 0.0.0.0 --port "$API_PORT" ) >"$API_LOG" 2>&1 &
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

# ── 2. 启动前端（前台）──
echo "→ 启动前端 web  →  http://localhost:$WEB_PORT"
echo "  （Ctrl+C 同时停止前后端）"
echo
cd "$WEB_DIR"
npm run dev -- --port "$WEB_PORT" --strictPort
