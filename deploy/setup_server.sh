#!/bin/bash
# ============================================================
# 易会办 · 云服务器一键部署脚本
# 在阿里云 Linux 3 上执行：bash setup_server.sh
# ============================================================
set -e

APP_DIR="/opt/yihuiban"
VENV_DIR="$APP_DIR/data-sim/.venv"
LOG_DIR="/var/log/yihuiban"

echo "========================================="
echo "  易会办 · 云服务器部署"
echo "========================================="

# ---- 1. 安装系统依赖 ----
echo "[1/6] 安装系统依赖..."
dnf install -y python3.11 python3.11-pip python3.11-devel nginx git 2>&1 | tail -3

# ---- 2. 创建目录结构 ----
echo "[2/6] 创建目录..."
mkdir -p $APP_DIR $LOG_DIR

# ---- 3. 配置 Python 虚拟环境 ----
echo "[3/6] 配置 Python 虚拟环境..."
mkdir -p $APP_DIR/data-sim
cd $APP_DIR/data-sim
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install fastapi uvicorn aiosqlite apscheduler -q
pip install httpx python-dotenv openai dashscope -q
pip install chromadb -q
echo "  Python: $(.venv/bin/python --version)"

# ---- 4. 配置 Nginx ----
echo "[4/6] 配置 Nginx..."
cat > /etc/nginx/conf.d/yihuiban.conf << 'NGINX_EOF'
server {
    listen 80;
    server_name _;

    # 前端静态文件（SPA）
    root /opt/yihuiban/frontend/dist;
    index index.html;

    # API 代理到后端
    location /api/ {
        proxy_pass http://127.0.0.1:8008;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }

    # SPA 路由回退：非 API 请求都返回 index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINX_EOF

# 确保 nginx 主配置引入我们的配置
grep -q "conf.d/\*.conf" /etc/nginx/nginx.conf || sed -i '/http {/a\    include /etc/nginx/conf.d/*.conf;' /etc/nginx/nginx.conf

# ---- 5. 配置 systemd 服务 ----
echo "[5/6] 配置 systemd 后端服务..."
cat > /etc/systemd/system/yihuiban.service << 'SYSTEMD_EOF'
[Unit]
Description=易会办后端 API 服务
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/yihuiban/data-sim
Environment="PATH=/opt/yihuiban/data-sim/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/yihuiban/data-sim/.venv/bin/python app.py
Restart=always
RestartSec=5
StandardOutput=append:/var/log/yihuiban/backend.log
StandardError=append:/var/log/yihuiban/backend.log

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF

systemctl daemon-reload

# ---- 6. 配置 .env（如不存在） ----
echo "[6/6] 检查环境变量..."
if [ ! -f "$APP_DIR/data-sim/.env" ]; then
    echo "# 易会办环境配置" > $APP_DIR/data-sim/.env
    echo "DASHSCOPE_API_KEY=sk-your-key-here" >> $APP_DIR/data-sim/.env
    echo "⚠ 请在 $APP_DIR/data-sim/.env 中配置 DASHSCOPE_API_KEY"
fi

echo ""
echo "========================================="
echo "  安装完成！后续操作："
echo "========================================="
echo ""
echo "  1. 配置 API Key:"
echo "     vi $APP_DIR/data-sim/.env"
echo ""
echo "  2. 启动服务:"
echo "     systemctl start yihuiban"
echo "     systemctl start nginx"
echo ""
echo "  3. 设置开机自启:"
echo "     systemctl enable yihuiban nginx"
echo ""
echo "  4. 查看日志:"
echo "     journalctl -u yihuiban -f"
echo "     tail -f $LOG_DIR/backend.log"
echo ""
echo "  访问地址: http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_IP')"
echo "========================================="
