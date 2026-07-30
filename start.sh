#!/bin/bash
# ============================================================
# 易会办 一键启动脚本
# 启动后端 API (8008) + 前端工作台 (8080)
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="/tmp/yihuiban_logs"
mkdir -p "$LOG_DIR"

echo "========================================="
echo "  易会办 · 启动中..."
echo "========================================="

# ---- 1. 清理旧进程 ----
echo "[1/3] 清理旧进程..."
kill $(lsof -ti :8008) 2>/dev/null || true
kill $(lsof -ti :8080) 2>/dev/null || true
sleep 1

# ---- 2. 启动后端 API (端口 8008) ----
echo "[2/3] 启动后端 API (端口 8008)..."
cd "$SCRIPT_DIR/data-sim"
nohup .venv/bin/python app.py > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "  后端 PID: $BACKEND_PID"

# 等待后端就绪
echo -n "  等待后端就绪"
for i in $(seq 1 30); do
  if curl -s --max-time 1 http://localhost:8008/api/ai/agent/health > /dev/null 2>&1; then
    echo " ✓"
    break
  fi
  echo -n "."
  sleep 1
done

# ---- 3. 启动前端 Vue 开发服务器 (端口 8080) ----
echo "[3/3] 启动前端 Vue 应用 (端口 8080)..."
cd "$SCRIPT_DIR/frontend"
nohup npx vite --host 0.0.0.0 --port 8080 > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "  前端 PID: $FRONTEND_PID"

# 等待前端就绪
echo -n "  等待前端就绪"
for i in $(seq 1 30); do
  if curl -s --max-time 1 -o /dev/null -w "%{http_code}" http://localhost:8080/ | grep -q 200; then
    echo " ✓"
    break
  fi
  echo -n "."
  sleep 1
done

# ---- 验证 ----
echo ""
echo "========================================="
echo "  启动完成！"
echo "========================================="
echo "  后端 API:    http://localhost:8008"
echo "  API 文档:    http://localhost:8008/docs"
echo "  前端工作台:  http://localhost:8080"
echo "  管理后台:    http://localhost:8080/admin"
echo ""
echo "  日志目录: $LOG_DIR"
echo "  停止服务:   kill \$(lsof -ti :8008) \$(lsof -ti :8080)"
echo "========================================"
