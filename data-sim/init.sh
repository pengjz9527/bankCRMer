#!/bin/bash
# 易会办 客户洞察模拟数据集 — 初始化脚本
# 用法: bash init.sh

set -e

echo "=== 易会办 客户洞察模拟数据集 初始化 ==="

# Step 1: 启动 PostgreSQL
echo "[1/4] 启动 PostgreSQL Docker 容器..."
docker compose up -d postgres

echo "等待 PostgreSQL 就绪..."
until docker compose exec -T postgres pg_isready -U yihuiban -d yihuiban_sim 2>/dev/null; do
  sleep 2
done
echo "PostgreSQL 已就绪。"

# Step 2: 安装 Python 依赖
echo "[2/4] 安装 Python 依赖..."
pip install psycopg2-binary 2>/dev/null || echo "psycopg2-binary already installed"

# Step 3: 生成并写入数据
echo "[3/4] 生成模拟数据并写入数据库..."
python generate_data.py

# Step 4: 验证行数
echo "[4/4] 验证数据行数..."
docker compose exec -T postgres psql -U yihuiban -d yihuiban_sim -c "
SELECT 'customers' as tbl, count(*) FROM customers
UNION ALL SELECT 'family_info', count(*) FROM family_info
UNION ALL SELECT 'business_info', count(*) FROM business_info
UNION ALL SELECT 'employment_status', count(*) FROM employment_status
UNION ALL SELECT 'holdings', count(*) FROM holdings
UNION ALL SELECT 'transactions', count(*) FROM transactions
UNION ALL SELECT 'loans', count(*) FROM loans
UNION ALL SELECT 'behavior_logs', count(*) FROM behavior_logs
UNION ALL SELECT 'customer_relations', count(*) FROM customer_relations
UNION ALL SELECT 'communications', count(*) FROM communications
UNION ALL SELECT 'risk_assessments', count(*) FROM risk_assessments
UNION ALL SELECT 'customer_benefits', count(*) FROM customer_benefits
UNION ALL SELECT 'available_activities', count(*) FROM available_activities
UNION ALL SELECT 'customer_activity_participation', count(*) FROM customer_activity_participation
UNION ALL SELECT 'battle_packages', count(*) FROM battle_packages
UNION ALL SELECT 'battle_package_clues', count(*) FROM battle_package_clues
ORDER BY tbl;
"

echo ""
echo "=== 初始化完成 ==="
echo "数据库: yihuiban_sim"
echo "用户: yihuiban"
echo "端口: localhost:5432"
echo ""
echo "启动 API 服务: python api_server.py"
