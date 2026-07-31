#!/bin/bash
# ============================================================
# 易会办 · 代码上传脚本（本地执行）
# 用法：bash deploy/upload.sh
# ============================================================
set -e

SERVER="root@39.107.68.177"
PASS="TianSha9527"
APP_DIR="/opt/yihuiban"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "========================================="
echo "  易会办 · 上传代码到服务器"
echo "========================================="

# ---- 1. 构建前端 ----
echo "[1/4] 构建前端..."
cd "$SCRIPT_DIR/frontend"
npx vite build 2>&1 | tail -3

# ---- 2. 上传后端代码（排除 venv、__pycache__、.db 文件）----
echo "[2/4] 上传后端代码..."
sshpass -p "$PASS" rsync -avz --delete \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '*.db-shm' \
    --exclude '*.db-wal' \
    --exclude '.DS_Store' \
    --exclude 'yihuiban_sim.db' \
    "$SCRIPT_DIR/data-sim/" \
    "$SERVER:$APP_DIR/data-sim/" 2>&1 | tail -5

# ---- 3. 上传前端构建产物 ----
echo "[3/4] 上传前端静态文件..."
sshpass -p "$PASS" ssh $SERVER "mkdir -p $APP_DIR/frontend/dist"
sshpass -p "$PASS" rsync -avz --delete \
    "$SCRIPT_DIR/frontend/dist/" \
    "$SERVER:$APP_DIR/frontend/dist/" 2>&1 | tail -3

# ---- 4. 上传并执行服务端安装脚本 ----
echo "[4/4] 执行服务端安装..."
sshpass -p "$PASS" scp "$SCRIPT_DIR/deploy/setup_server.sh" "$SERVER:/tmp/"
sshpass -p "$PASS" ssh $SERVER "bash /tmp/setup_server.sh"

echo ""
echo "========================================="
echo "  上传完成！"
echo "========================================="
