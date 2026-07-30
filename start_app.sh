#!/bin/bash
kill $(lsof -ti :8008) 2>/dev/null
sleep 2
cd /Users/pengjizhou/Documents/yihuiban-app/data-sim
.venv/bin/python app.py > /tmp/yh_server.log 2>&1 &
echo "PID=$!"
sleep 15
echo "=== openapi.json ==="
curl -s --max-time 5 http://localhost:8008/openapi.json | head -c 200
echo ""
echo "=== /docs status ==="
curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://localhost:8008/docs
echo ""
