"""
易会办 客户洞察 — 全内置运行脚本 (SQLite + FastAPI)
一键启动: .venv/bin/python app.py
"""

import sys

# ═══════════════════════════════════════════════════════════════
# Python 版本与运行环境校验
# ═══════════════════════════════════════════════════════════════
_MIN_PY = (3, 11)
_MAX_PY = (3, 14)  # Python 3.14+ 部分原生依赖(chromadb)不兼容
_cur_ver = (sys.version_info.major, sys.version_info.minor)

if _cur_ver < _MIN_PY:
    sys.exit(
        f"\n{'='*60}\n"
        f"  ❌ Python 版本过低: {sys.version.split()[0]}\n"
        f"  项目需要 Python >= 3.11\n"
        f"  请使用虚拟环境: .venv/bin/python app.py\n"
        f"{'='*60}\n"
    )

if _cur_ver >= _MAX_PY:
    sys.exit(
        f"\n{'='*60}\n"
        f"  ❌ Python {sys.version_info.major}.{sys.version_info.minor} 不兼容\n"
        f"  部分原生依赖(如 chromadb)不支持 Python 3.14+\n"
        f"  请使用虚拟环境: cd data-sim && .venv/bin/python app.py\n"
        f"{'='*60}\n"
    )

# 检测是否在虚拟环境中运行
_in_venv = (
    hasattr(sys, "real_prefix")
    or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
)
if not _in_venv:
    print(
        f"\n{'='*60}\n"
        f"  ⚠️  建议在虚拟环境中运行\n"
        f"  当前解释器: {sys.executable}\n"
        f"  正确启动: cd data-sim && .venv/bin/python app.py\n"
        f"{'='*60}\n",
        file=sys.stderr,
    )

# 解决旧版 SQLite 兼容问题：ChromaDB 需要 sqlite3 >= 3.35
try:
    __import__('pysqlite3')
    import sys as _sys
    _sys.modules['sqlite3'] = _sys.modules.pop('pysqlite3')
except ImportError:
    pass

import json, random, sqlite3, os, sys
from datetime import date, timedelta, datetime
from pathlib import Path

# 添加当前目录到 path 以导入 templates 和 agentos
sys.path.insert(0, str(Path(__file__).parent))

# AgentOS 导入
from agentos.agents.opportunity_mining import create_opp_mining_agent
from agentos.agents.battle_package import create_battle_pkg_agent
from agentos.agents.customer_insight import create_customer_insight_agent
from agentos.agents.scheduler import create_scheduler_agent
from agentos.agents.qa_assistant import create_qa_agent
from agentos.agents.content_agent import create_content_agent
from agentos.agents.router import create_router_agent
from agentos.harness import AgentContext
from agentos.skills import query_customer_insight, query_customer_insights_by_manager, query_customers_by_insight_filter, query_tasks_for_schedule
from agentos.news_fetcher import fetch_daily_news
from data_engine import daily_tick
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
log = logging.getLogger("app")

# ============================================================
# 配置
# ============================================================
DB_PATH = str(Path(__file__).parent / "yihuiban_sim.db")
TODAY = date.today()
random.seed(42)

# ============================================================
# SQLite Schema
# ============================================================
SCHEMA = """
CREATE TABLE IF NOT EXISTS processing_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    cust_id INTEGER REFERENCES customers(id),
    cust_name TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('电话联系','微信联系','跳过')),
    notes TEXT DEFAULT '',
    processed_at TEXT NOT NULL,
    card_id TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pr_cust ON processing_records(cust_id);
CREATE INDEX IF NOT EXISTS idx_pr_card ON processing_records(card_id);

PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_no TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL CHECK(gender IN ('M','F')),
    occupation TEXT,
    industry TEXT,
    city TEXT,
    education TEXT,
    phone_masked TEXT,
    tier TEXT NOT NULL,
    total_aum REAL NOT NULL DEFAULT 0,
    employment_status TEXT DEFAULT '在职',
    contact_prefer TEXT DEFAULT '不限定'
);

CREATE TABLE IF NOT EXISTS family_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER UNIQUE REFERENCES customers(id),
    marriage INTEGER DEFAULT 0, children INTEGER DEFAULT 0,
    child_count INTEGER DEFAULT 0, child_age INTEGER,
    child_education TEXT,
    study_abroad_intent TEXT DEFAULT '无',
    study_abroad_target_country TEXT,
    spouse_has_income INTEGER,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS business_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER UNIQUE REFERENCES customers(id),
    business_name TEXT, duration_years INTEGER,
    share_ratio REAL, reg_capital REAL,
    address TEXT, scope TEXT, continuity INTEGER,
    verified INTEGER DEFAULT 1, verified_source TEXT
);

CREATE TABLE IF NOT EXISTS employment_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER UNIQUE REFERENCES customers(id),
    status TEXT NOT NULL,
    unemployment_benefits INTEGER DEFAULT 0,
    benefit_amount REAL, benefit_start_date TEXT,
    benefit_end_date TEXT,
    verified INTEGER DEFAULT 1, last_verified_date TEXT
);

CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER REFERENCES customers(id),
    product_type TEXT NOT NULL, product_name TEXT NOT NULL,
    product_code TEXT, amount REAL NOT NULL,
    yield_rate REAL, risk_level TEXT,
    maturity_date TEXT, purchase_date TEXT, status TEXT DEFAULT '持有中'
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER REFERENCES customers(id),
    txn_date TEXT NOT NULL, txn_type TEXT NOT NULL CHECK(txn_type IN ('in','out')),
    amount REAL NOT NULL, counterparty TEXT, summary TEXT, channel TEXT,
    counterparty_cust_id INTEGER REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER REFERENCES customers(id),
    product_name TEXT NOT NULL,
    credit_line REAL NOT NULL, used_amount REAL NOT NULL DEFAULT 0,
    remaining REAL NOT NULL DEFAULT 0,
    overdue_count INTEGER DEFAULT 0, interest_rate REAL,
    start_date TEXT, maturity_date TEXT
);

CREATE TABLE IF NOT EXISTS loan_rejections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER REFERENCES customers(id),
    product_name TEXT NOT NULL, reject_reason TEXT, rejected_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS behavior_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER REFERENCES customers(id),
    event_date TEXT NOT NULL, event_time TEXT,
    channel TEXT NOT NULL, page_type TEXT NOT NULL,
    action TEXT NOT NULL, duration_sec INTEGER DEFAULT 0,
    product_code TEXT, product_type TEXT
);

CREATE TABLE IF NOT EXISTS customer_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id_a INTEGER REFERENCES customers(id),
    cust_id_b INTEGER REFERENCES customers(id),
    relation_type TEXT NOT NULL, evidence TEXT, evidence_field TEXT
);

-- 管户关系：客户经理与客户的归属关系
CREATE TABLE IF NOT EXISTS cust_manager_rel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER NOT NULL REFERENCES customers(id),
    manager_id TEXT NOT NULL,
    manager_name TEXT NOT NULL,
    assigned_date TEXT NOT NULL DEFAULT (date('now')),
    is_primary INTEGER DEFAULT 1,
    UNIQUE(cust_id, manager_id)
);

CREATE INDEX IF NOT EXISTS idx_cmr_cust ON cust_manager_rel(cust_id);
CREATE INDEX IF NOT EXISTS idx_cmr_mgr ON cust_manager_rel(manager_id);

CREATE TABLE IF NOT EXISTS communications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER REFERENCES customers(id),
    comm_date TEXT NOT NULL, comm_time TEXT,
    channel TEXT NOT NULL, duration_min INTEGER,
    summary TEXT NOT NULL, key_topics TEXT
);

CREATE TABLE IF NOT EXISTS risk_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER UNIQUE REFERENCES customers(id),
    test_result TEXT NOT NULL, valid_until TEXT, tested_date TEXT NOT NULL,
    wealth_score INTEGER, score_time TEXT,
    dimension_asset REAL, dimension_income REAL, dimension_social REAL
);

CREATE TABLE IF NOT EXISTS risk_assessment_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER REFERENCES customers(id),
    test_result TEXT NOT NULL,
    tested_date TEXT NOT NULL,
    wealth_score INTEGER,
    dimension_asset REAL, dimension_income REAL, dimension_social REAL
);

CREATE TABLE IF NOT EXISTS product_catalog (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id          TEXT NOT NULL UNIQUE,
    product_code        TEXT,
    product_name        TEXT NOT NULL,
    short_name          TEXT,
    bank_name           TEXT,
    issuer              TEXT,
    category            TEXT NOT NULL,
    sub_category        TEXT,
    risk_level          TEXT,
    risk_name           TEXT,
    term_days           INTEGER,
    term_desc           TEXT,
    min_amount          REAL DEFAULT 1,
    min_amount_desc     TEXT,
    expected_return_min REAL,
    expected_return_max REAL,
    yield_rate          REAL,
    return_type         TEXT,
    return_benchmark    TEXT,
    currency            TEXT DEFAULT 'CNY',
    invest_direction    TEXT,
    subscription_fee    TEXT,
    redemption_fee      TEXT,
    redemption_days     TEXT,
    selling_points      TEXT,
    scenario_tags       TEXT,
    applicable_customer TEXT,
    source_url          TEXT,
    data_source         TEXT,
    data_date           TEXT,
    manager             TEXT,
    status              TEXT DEFAULT '在售'
);

CREATE TABLE IF NOT EXISTS customer_benefits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER REFERENCES customers(id),
    benefit_name TEXT NOT NULL, benefit_type TEXT NOT NULL,
    description TEXT, tier_requirement TEXT,
    rarity TEXT DEFAULT '普通', acquired_date TEXT NOT NULL,
    expiry_date TEXT, status TEXT DEFAULT '有效'
);

CREATE TABLE IF NOT EXISTS available_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
    type TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
    description TEXT, target_tier TEXT, reward_desc TEXT
);

CREATE TABLE IF NOT EXISTS customer_activity_participation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER REFERENCES customers(id),
    activity_id TEXT REFERENCES available_activities(activity_id),
    participated_date TEXT NOT NULL,
    status TEXT DEFAULT '已参与', result_note TEXT
);

CREATE TABLE IF NOT EXISTS battle_packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bp_id TEXT NOT NULL UNIQUE, opp_id TEXT NOT NULL,
    cust_id INTEGER REFERENCES customers(id),
    mode TEXT NOT NULL, status TEXT DEFAULT '未使用',
    task_id TEXT DEFAULT '',              -- Phase3: 关联的客户聚合待办ID
    customer_overview TEXT NOT NULL,  -- JSON
    agenda TEXT, risk_warnings TEXT NOT NULL DEFAULT '[]',
    care_items TEXT NOT NULL DEFAULT '[]', -- Phase3: 非商机关怀事项 JSON
    post_visit_actions TEXT NOT NULL DEFAULT '[]',
    generated_at TEXT NOT NULL, expires_at TEXT NOT NULL, used_at TEXT
);

CREATE TABLE IF NOT EXISTS battle_package_clues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clue_id TEXT NOT NULL UNIQUE, bp_id TEXT REFERENCES battle_packages(bp_id),
    opp_id TEXT DEFAULT '',             -- Phase3: 该线索关联的商机ID
    priority TEXT NOT NULL, title TEXT NOT NULL,
    discovery_basis TEXT NOT NULL, strategy TEXT NOT NULL,
    opening_script TEXT NOT NULL, products TEXT NOT NULL DEFAULT '[]',
    deviation_branches TEXT
);

CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opp_id TEXT NOT NULL UNIQUE,
    cust_id INTEGER REFERENCES customers(id),
    cust_name TEXT NOT NULL,
    opportunity_type TEXT NOT NULL,
    title TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0,
    estimated_value REAL NOT NULL DEFAULT 0,
    reasoning TEXT NOT NULL,
    suggested_action TEXT,
    priority TEXT DEFAULT '常规',
    source TEXT NOT NULL DEFAULT 'AI-opp_mining',
    source_method TEXT,
    trigger_signals TEXT,
    status TEXT DEFAULT '待跟进',
    generated_at TEXT NOT NULL,
    manager_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_opp_cust ON opportunities(cust_id);
CREATE INDEX IF NOT EXISTS idx_opp_gen ON opportunities(generated_at);

-- 客户信号表（统一收集所有客户事件/信号，作为商机挖掘的输入源）
CREATE TABLE IF NOT EXISTS customer_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT NOT NULL UNIQUE,
    cust_id INTEGER NOT NULL REFERENCES customers(id),
    signal_type TEXT NOT NULL,
    signal_data TEXT NOT NULL DEFAULT '{}',
    strategy_tags TEXT NOT NULL DEFAULT '[]',
    priority_weight INTEGER NOT NULL DEFAULT 50,
    valid_from TEXT NOT NULL,
    valid_until TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    consumed_by_opp TEXT,
    consumed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sig_cust ON customer_signals(cust_id);
CREATE INDEX IF NOT EXISTS idx_sig_type ON customer_signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_sig_status ON customer_signals(status);
CREATE INDEX IF NOT EXISTS idx_sig_valid ON customer_signals(valid_from, valid_until);

-- 商机-面谈关联表（一个商机可关联多次面谈）
CREATE TABLE IF NOT EXISTS opp_meeting_rel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opp_id TEXT NOT NULL,
    meeting_id INTEGER NOT NULL REFERENCES meeting_records(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(opp_id, meeting_id)
);
CREATE INDEX IF NOT EXISTS idx_omr_opp ON opp_meeting_rel(opp_id);
CREATE INDEX IF NOT EXISTS idx_omr_meeting ON opp_meeting_rel(meeting_id);

CREATE INDEX IF NOT EXISTS idx_cust_tier ON customers(tier);
CREATE INDEX IF NOT EXISTS idx_h_cust ON holdings(cust_id);
CREATE INDEX IF NOT EXISTS idx_t_cust ON transactions(cust_id);
CREATE INDEX IF NOT EXISTS idx_b_cust ON behavior_logs(cust_id);
CREATE INDEX IF NOT EXISTS idx_comm_cust ON communications(cust_id);
CREATE INDEX IF NOT EXISTS idx_bp_cust ON battle_packages(cust_id);
CREATE INDEX IF NOT EXISTS idx_bpc_bpid ON battle_package_clues(bp_id);

CREATE TABLE IF NOT EXISTS customer_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER NOT NULL REFERENCES customers(id),
    manager_id TEXT NOT NULL,
    overview_json TEXT NOT NULL,
    change_signals_json TEXT NOT NULL DEFAULT '[]',
    risk_signals_json TEXT NOT NULL DEFAULT '[]',
    risk_level TEXT NOT NULL DEFAULT 'green',
    generated_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    UNIQUE(cust_id, generated_at)
);

CREATE INDEX IF NOT EXISTS idx_ci_cust ON customer_insights(cust_id);
CREATE INDEX IF NOT EXISTS idx_ci_mgr ON customer_insights(manager_id);
CREATE INDEX IF NOT EXISTS idx_ci_risk ON customer_insights(risk_level);

CREATE TABLE IF NOT EXISTS daily_schedules (
    schedule_date TEXT NOT NULL,
    manager_id TEXT NOT NULL,
    morning_json TEXT NOT NULL DEFAULT '[]',
    afternoon_json TEXT NOT NULL DEFAULT '[]',
    total_minutes INTEGER NOT NULL DEFAULT 0,
    generated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'rule',
    PRIMARY KEY (schedule_date, manager_id)
);

CREATE INDEX IF NOT EXISTS idx_ds_date ON daily_schedules(schedule_date);
CREATE INDEX IF NOT EXISTS idx_ds_mgr ON daily_schedules(manager_id);

-- KPI 指标定义表（管理后台可 CRUD，动态驱动前端）
CREATE TABLE IF NOT EXISTS kpi_definitions (
    kpi_code TEXT PRIMARY KEY,
    kpi_name TEXT NOT NULL,
    unit TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 0,
    category TEXT NOT NULL DEFAULT 'core',
    sort_order INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    icon TEXT DEFAULT '📊',
    description TEXT,
    trend_direction TEXT DEFAULT 'up',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- KPI 目标值表（按机构/客户经理 + 时间维度）
CREATE TABLE IF NOT EXISTS kpi_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kpi_code TEXT NOT NULL REFERENCES kpi_definitions(kpi_code),
    org_id TEXT,
    manager_id TEXT,
    year INTEGER NOT NULL,
    quarter INTEGER,
    month INTEGER,
    target_value REAL NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(kpi_code, org_id, manager_id, year, quarter, month)
);

-- KPI 完成数据快照表（T+1 汇总）
CREATE TABLE IF NOT EXISTS kpi_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kpi_code TEXT NOT NULL REFERENCES kpi_definitions(kpi_code),
    org_id TEXT,
    manager_id TEXT NOT NULL DEFAULT '',
    snap_date TEXT NOT NULL,
    actual_value REAL NOT NULL DEFAULT 0,
    yoy_value REAL,
    period_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(kpi_code, manager_id, snap_date, period_type)
);

CREATE INDEX IF NOT EXISTS idx_kpi_snap_mgr ON kpi_snapshots(manager_id, snap_date);
CREATE INDEX IF NOT EXISTS idx_kpi_snap_org ON kpi_snapshots(org_id, snap_date);
CREATE INDEX IF NOT EXISTS idx_kpi_target_mgr ON kpi_targets(manager_id, year);

-- 数据日推进标记（幂等保障）
CREATE TABLE IF NOT EXISTS data_ticks (
    tick_date TEXT PRIMARY KEY,
    stats_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

-- ============================================================
-- Admin 管理后台专用表
-- ============================================================

-- 智能体运行日志
CREATE TABLE IF NOT EXISTS agent_run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_role TEXT NOT NULL,
    method TEXT NOT NULL,
    manager_id TEXT DEFAULT '',
    status TEXT NOT NULL CHECK(status IN ('pending','success','error')),
    input_summary TEXT DEFAULT '',
    output_summary TEXT DEFAULT '',
    error_msg TEXT DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    duration_ms INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_arl_role ON agent_run_logs(agent_role);
CREATE INDEX IF NOT EXISTS idx_arl_status ON agent_run_logs(status);
CREATE INDEX IF NOT EXISTS idx_arl_started ON agent_run_logs(started_at);

-- Token 消耗记录
CREATE TABLE IF NOT EXISTS agent_token_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_role TEXT NOT NULL,
    run_log_id INTEGER REFERENCES agent_run_logs(id),
    model_name TEXT NOT NULL DEFAULT '',
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_atu_role ON agent_token_usage(agent_role);
CREATE INDEX IF NOT EXISTS idx_atu_run ON agent_token_usage(run_log_id);
CREATE INDEX IF NOT EXISTS idx_atu_date ON agent_token_usage(recorded_at);

-- 大模型配置
CREATE TABLE IF NOT EXISTS model_configs (
    config_key TEXT PRIMARY KEY,
    provider TEXT NOT NULL DEFAULT 'deepseek',
    model_name TEXT NOT NULL,
    api_base TEXT NOT NULL DEFAULT '',
    api_key TEXT NOT NULL DEFAULT '',
    is_active INTEGER DEFAULT 0,
    purpose TEXT DEFAULT 'general',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 智能体可配置参数
CREATE TABLE IF NOT EXISTS agent_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_role TEXT NOT NULL,
    param_key TEXT NOT NULL,
    param_value TEXT NOT NULL DEFAULT '',
    param_type TEXT DEFAULT 'string',
    description TEXT DEFAULT '',
    updated_at TEXT NOT NULL,
    UNIQUE(agent_role, param_key)
);
CREATE INDEX IF NOT EXISTS idx_ac_role ON agent_configs(agent_role);

-- 审计日志
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT DEFAULT '',
    customer_id TEXT DEFAULT '',
    operator TEXT DEFAULT 'admin',
    manager_name TEXT DEFAULT '',
    detail TEXT DEFAULT '',
    endpoint TEXT DEFAULT '',
    result_count INTEGER DEFAULT 0,
    sensitive_level TEXT DEFAULT '',
    ip_address TEXT DEFAULT '',
    user_agent TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_al_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_al_created ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_al_operator ON audit_logs(operator);
-- idx_al_customer 由迁移脚本在确保列存在后创建

-- 平台环境配置（可视化管理 .env 中的可变配置项）
CREATE TABLE IF NOT EXISTS platform_configs (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'general',
    description TEXT DEFAULT '',
    updated_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- 定时任务执行历史
CREATE TABLE IF NOT EXISTS task_execution_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    job_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK(status IN ('success','error','skipped')),
    result_summary TEXT DEFAULT '',
    result_detail TEXT DEFAULT '',
    error_msg TEXT DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    duration_ms INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_teh_job ON task_execution_history(job_id);
CREATE INDEX IF NOT EXISTS idx_teh_started ON task_execution_history(started_at);

-- ============================================================
-- ContentAgent 数据基础设施
-- ============================================================

-- 昨日回顾存储
CREATE TABLE IF NOT EXISTS daily_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    manager_id TEXT NOT NULL,
    review_date TEXT NOT NULL,
    content TEXT NOT NULL,
    generated_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_read INTEGER DEFAULT 0,
    UNIQUE(manager_id, review_date)
);
CREATE INDEX IF NOT EXISTS idx_dr_mgr ON daily_reviews(manager_id, review_date);

-- 金融资讯缓存
CREATE TABLE IF NOT EXISTS daily_news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT,
    source TEXT NOT NULL DEFAULT 'tushare',
    category TEXT NOT NULL DEFAULT 'finance',
    news_url TEXT,
    fetched_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_dn_date ON daily_news(fetched_at);
CREATE INDEX IF NOT EXISTS idx_dn_category ON daily_news(category);

-- 数据导出审批记录
CREATE TABLE IF NOT EXISTS data_export_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id TEXT NOT NULL,
    requester_name TEXT DEFAULT '',
    export_type TEXT NOT NULL DEFAULT 'customers',
    export_scope TEXT DEFAULT '',
    reason TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected','executed')),
    approver_id TEXT DEFAULT '',
    approved_at TEXT,
    file_path TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ea_status ON data_export_approvals(status);
CREATE INDEX IF NOT EXISTS idx_ea_requester ON data_export_approvals(requester_id);

-- 面谈记录 + PDCA（v2：支持追加口述、摘要合并、状态流转）
CREATE TABLE IF NOT EXISTS meeting_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER NOT NULL REFERENCES customers(id),
    cust_name TEXT DEFAULT '',
    bp_id TEXT,
    opp_id TEXT,
    manager_id TEXT NOT NULL,
    meeting_date TEXT NOT NULL,
    plan_result TEXT,
    deviation_note TEXT,
    customer_feedback TEXT,
    action_items TEXT,
    dictation_raw TEXT DEFAULT '[]',
    summary TEXT DEFAULT '',
    meeting_status TEXT DEFAULT 'drafting',
    profile_changes_json TEXT DEFAULT '[]',
    todos_json TEXT DEFAULT '[]',
    generated_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_mr_cust ON meeting_records(cust_id);
CREATE INDEX IF NOT EXISTS idx_mr_mgr ON meeting_records(manager_id, meeting_date);
CREATE INDEX IF NOT EXISTS idx_mr_cust_date ON meeting_records(cust_id, meeting_date DESC);

-- 画像变更追踪
CREATE TABLE IF NOT EXISTS profile_change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id INTEGER NOT NULL REFERENCES customers(id),
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    source TEXT DEFAULT 'dictation',
    meeting_id INTEGER REFERENCES meeting_records(id),
    changed_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_pcl_cust ON profile_change_log(cust_id, changed_at);

-- 行内公告
CREATE TABLE IF NOT EXISTS internal_announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT,
    ann_type TEXT NOT NULL,
    priority TEXT DEFAULT 'normal',
    published_at TEXT NOT NULL,
    expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ia_date ON internal_announcements(published_at);

-- 产品变更日志
CREATE TABLE IF NOT EXISTS product_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL,
    change_type TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pu_date ON product_updates(changed_at);
"""

# ============================================================
# 数据生成 (复用 templates.py 的逻辑, 但内联写入 SQLite)
# ============================================================
def gen_all(db):
    """生成全部数据到 SQLite"""
    print("生成100人模拟数据集...")

    # 导入模板
    from templates import (
        ALL_TEMPLATES, TIER_AUM_RANGE, PRODUCTS, RISK_LEVELS, RISK_RESULTS,
        CITIES, INDUSTRIES, EDUCATIONS, COMPANY_PREFIX,
        weighted_choice, generate_name, child_education_from_age
    )

    cur = db.cursor()
    cust_id = 1

    # 全局产品目录 — 从 product_database.json 导入真实数据（仅首次，幂等）
    if cur.execute("SELECT COUNT(*) FROM product_catalog").fetchone()[0] > 0:
        print(f"  产品目录: 已有数据，跳过导入 ({cur.execute('SELECT COUNT(*) FROM product_catalog').fetchone()[0]} 款)")
    else:
        import json as _json
        from pathlib import Path as _Path
        json_path = _Path(__file__).parent / "data" / "product_database.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                prod_db = _json.load(f)
            products = prod_db.get("products", [])
            insert_sql = """
                INSERT INTO product_catalog (
                    product_id, product_code, product_name, short_name,
                    bank_name, issuer, category, sub_category,
                    risk_level, risk_name, term_days, term_desc,
                    min_amount, min_amount_desc,
                    expected_return_min, expected_return_max,
                    yield_rate, return_type, return_benchmark,
                    currency, invest_direction, subscription_fee,
                    redemption_fee, redemption_days,
                    selling_points, scenario_tags, applicable_customer,
                    source_url, data_source, data_date, manager, status
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?
                )
            """
            for p in products:
                cur.execute(insert_sql, (
                    p.get("product_id", ""),
                    p.get("product_code", ""),
                    p.get("product_name", ""),
                    p.get("short_name", ""),
                    p.get("bank_name", ""),
                    p.get("issuer", ""),
                    p.get("category", ""),
                    p.get("sub_category", ""),
                    p.get("risk_level", ""),
                    p.get("risk_name", ""),
                    p.get("term_days"),
                    p.get("term_desc", ""),
                    p.get("min_amount", 1),
                    p.get("min_amount_desc", ""),
                    p.get("expected_return_min"),
                    p.get("expected_return_max"),
                    p.get("expected_return_max"),
                    p.get("return_type", ""),
                    p.get("return_benchmark", ""),
                    p.get("currency", "CNY"),
                    p.get("invest_direction", ""),
                    p.get("subscription_fee", ""),
                    p.get("redemption_fee", ""),
                    p.get("redemption_days", ""),
                    _json.dumps(p.get("selling_points", []), ensure_ascii=False),
                    _json.dumps(p.get("scenario_tags", []), ensure_ascii=False),
                    _json.dumps(p.get("applicable_customer", {}), ensure_ascii=False),
                    p.get("source_url", ""),
                    p.get("data_source", ""),
                    p.get("data_date", ""),
                    p.get("issuer", ""),
                    p.get("status", "在售"),
                ))
            print(f"  产品目录: 从 JSON 导入 {len(products)} 款")
        else:
            print("  ⚠ product_database.json 未找到，产品表为空")

    occupations_map = {
        "在职": ["工程师","教师","公务员","销售经理","会计","IT项目经理","医生","护士","企业中层","银行职员"],
        "自由职业": ["自媒体","设计师","咨询顾问","自由撰稿人","摄影师"],
        "无业": ["暂无"], "待业": ["暂无"], "不确定": ["待确认"],
    }

    for tmpl in ALL_TEMPLATES:
        for _ in range(tmpl["count"]):
            cust_no = f"C{datetime.now().strftime('%y%m')}{cust_id:04d}"
            gender = weighted_choice(tmpl["gender_ratio"])
            age = random.randint(*tmpl["age_range"])
            tier = weighted_choice(tmpl["tier_weights"])
            city = weighted_choice(tmpl["city_weights"])
            if city == "其他":
                city = random.choice([c for c in CITIES if c not in tmpl.get("city_weights", {})])
            education = weighted_choice(tmpl["education_weights"])
            emp_status = weighted_choice(tmpl["employment"]["status_weights"])
            occ = random.choice(occupations_map.get(emp_status, ["待确认"]))
            ind = random.choice(INDUSTRIES) if emp_status in ("在职","自由职业") else None
            aum = int(random.uniform(*tmpl["tier_specifics"][tier]["aum_range"]))
            phone = f"1{random.randint(30,99)}{random.randint(1000,9999)}{random.randint(1000,9999)}"
            phone_m = phone[:3] + "****" + phone[-4:]
            name = generate_name(gender)

            # contact_prefer: ~30% 客户有明确联系时段偏好，与职业关联
            morning_occ = ["销售经理", "企业中层", "自媒体", "咨询顾问"]  # 管理层/自主安排 → 上午
            afternoon_occ = ["工程师", "教师", "公务员", "会计", "IT项目经理", "医生", "护士", "银行职员"]  # 上班族 → 下午
            if occ in morning_occ:
                contact_prefer = "上午优先" if random.random() < 0.7 else "不限定"
            elif occ in afternoon_occ:
                contact_prefer = "下午优先" if random.random() < 0.6 else "不限定"
            elif emp_status == "自由职业":
                contact_prefer = random.choice(["上午优先", "下午优先", "不限定"])
            else:
                contact_prefer = "不限定"

            cur.execute(
                "INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cust_id, cust_no, name, age, gender, occ, ind, city, education, phone_m, tier, aum, emp_status, contact_prefer))

            # family_info
            fam = tmpl.get("family", {})
            married = random.random() < fam.get("married_prob", 0.5)
            children = married and random.random() < fam.get("children_prob", 0.5)
            child_count, child_age, child_edu, study_i, country = 0, None, None, "无", None
            if children:
                child_count = random.randint(*fam.get("child_count_range", (1, 1)))
                child_age = random.randint(*fam.get("child_age_range", (0, 18)))
                child_edu = child_education_from_age(child_age)
                study_i = "已留学" if child_edu == "留学中" else ("有" if random.random() < fam.get("study_abroad_intent_prob", 0.1) else "无")
                country = random.choice(["美国","英国","澳大利亚","加拿大","新加坡"]) if study_i in ("有","已留学") else None
            spouse_inc = random.random() < fam.get("spouse_has_income_prob", 0.5) if married else None
            cur.execute("INSERT INTO family_info VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (cust_id, cust_id, int(married), int(children), child_count, child_age, child_edu, study_i, country, int(spouse_inc) if spouse_inc is not None else None, TODAY.isoformat()))

            # business_info
            if random.random() < tmpl.get("has_business_info_probt", 0):
                verified = random.random() < tmpl.get("business_verified_prob", 0.7)
                source = "客户经理确认" if verified else random.choice(["交易流水推断","待面谈确认"])
                prefix = random.choice(COMPANY_PREFIX)
                biz_name = f"{prefix}{random.choice(['贸易','科技','实业','商贸','电子','建材'])}有限公司"
                cur.execute("INSERT INTO business_info VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (cust_id, cust_id, biz_name, random.randint(2, 15),
                             round(random.uniform(30, 100), 2), random.choice([50,100,200,500,1000])*10000,
                             f"合肥市{random.choice(['蜀山','庐阳','包河','瑶海'])}区",
                             random.choice(["日用百货批发零售","电子产品销售","建筑装饰工程","餐饮管理"]),
                             1, int(verified), source))

            # employment_status
            ben = False; ben_amt = None; ben_s = None; ben_e = None
            v_emp = emp_status != "不确定"
            lv = TODAY.isoformat() if v_emp else (TODAY - timedelta(days=random.randint(30,90))).isoformat()
            if emp_status in ("无业","待业"):
                ben = random.random() < tmpl["employment"].get("unemployment_benefits_prob", 0.5)
                if ben:
                    ben_amt = round(random.uniform(1500, 4000), 2)
                    ben_s = (TODAY - timedelta(days=random.randint(60,180))).isoformat()
                    ben_e = (TODAY + timedelta(days=random.randint(90,365))).isoformat()
            cur.execute("INSERT INTO employment_status VALUES (?,?,?,?,?,?,?,?,?)",
                        (cust_id, cust_id, emp_status, int(ben), ben_amt, ben_s, ben_e, int(v_emp), lv))

            # holdings
            ht = tmpl["holdings_template"]
            remaining = aum
            for ptype, cfg in ht.items():
                if random.random() > cfg["prob"]: continue
                cnt = random.randint(*cfg.get("count_range", (1, 1)))
                for _ in range(cnt):
                    amt = int(random.uniform(*cfg["amount_range"]))
                    amt = min(amt, int(remaining * 0.7))
                    if amt <= 0: continue
                    remaining -= amt
                    prod_pool = PRODUCTS.get(ptype, [("未知产品","X000")])
                    pn, pc = random.choice(prod_pool)
                    yld = round(random.uniform(1.5, 4.5), 4) if ptype != "贵金属" else None
                    risk = random.choice(RISK_LEVELS[:3]) if ptype != "存款" else "R1"
                    mat = None
                    if ptype in ("存款","理财"):
                        mat = (TODAY + timedelta(days=random.choice([-5,-1,3,7,15,30,60,90,180]))).isoformat()
                    pur = (TODAY - timedelta(days=random.randint(30,365))).isoformat()
                    cur.execute("INSERT INTO holdings VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                                (None, cust_id, ptype, pn, pc, amt, yld, risk, mat, pur, "持有中"))
            # 活期存款: 剩余AUM中至少有活期余额
            current_amt = max(0, int(remaining * random.uniform(0.5, 1.0)))
            if current_amt > 0:
                cur.execute("INSERT INTO holdings VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (None, cust_id, "存款", "活期存款", "CURRENT001", current_amt, 0.35, "R1", None, (TODAY - timedelta(days=random.randint(90,730))).isoformat(), "持有中"))

            # loans
            if random.random() < tmpl.get("loan_prob", 0.1):
                ltw = tmpl.get("loan_type_weights", {"房贷": 1.0})
                ltype = weighted_choice(ltw)
                if ltype == "房贷": prod = f"{random.choice(['首套','二套'])}住房贷款"; credit = int(random.uniform(300000,1500000))
                elif ltype == "经营贷": prod = "个人经营性贷款"; credit = int(random.uniform(200000,1000000))
                else: prod = "个人消费贷款"; credit = int(random.uniform(50000,300000))
                used = int(credit * random.uniform(0.3, 0.95))
                overdue = random.randint(0, 5) if random.random() < tmpl.get("loan_overdue_prob", 0.2) else 0
                rate = round(random.uniform(3.5, 6.5), 4)
                start = (TODAY - timedelta(days=random.randint(180,1825))).isoformat()
                mat = (TODAY + timedelta(days=random.randint(1825,7300))).isoformat()
                cur.execute("INSERT INTO loans VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (None, cust_id, prod, credit, used, credit - used, overdue, rate, start, mat))
                if random.random() < tmpl.get("loan_rejection_prob", 0.1):
                    cur.execute("INSERT INTO loan_rejections VALUES (?,?,?,?,?)",
                                (None, cust_id, random.choice(["XX信用贷款","ZZ经营贷"]),
                                 random.choice(["征信记录不良","收入证明不足","负债率过高"]),
                                 (TODAY - timedelta(days=random.randint(90,365))).isoformat()))

            # behavior_logs
            bias = tmpl["behavior_bias"]
            daily_prob = tmpl.get("behavior_daily_prob", 0.05) * tmpl["tier_specifics"][tier]["active_prob"]
            d = TODAY - timedelta(days=90)
            while d <= TODAY:
                if random.random() < daily_prob:
                    for _ in range(random.randint(1, 3)):
                        page = weighted_choice(bias)
                        action = random.choice(["浏览","搜索","点击详情","收藏","对比"])
                        dur = random.randint(10, 300)
                        prod_code = random.choice(PRODUCTS.get(page, [("","X000")]))[1]
                        t = f"{random.randint(8,22):02d}:{random.randint(0,59):02d}:00"
                        ch = random.choice(["手机银行","网银","微信"])
                        cur.execute("INSERT INTO behavior_logs VALUES (?,?,?,?,?,?,?,?,?,?)",
                                    (None, cust_id, d.isoformat(), t, ch, page, action, dur, prod_code, page))
                d += timedelta(days=1)

            # transactions
            freq = 3 if aum > 1000000 else (5 if aum > 200000 else (8 if aum > 50000 else 12))
            d = TODAY - timedelta(days=180)
            while d <= TODAY:
                for _ in range(max(1, int(random.uniform(0, freq / 30.0 * 2)))):
                    is_in = random.random() < 0.55
                    amt = round(random.uniform(100, aum * 0.02) if is_in else random.uniform(50, aum * 0.03), 2)
                    cp = random.choice(["支付宝","微信","他行账户","本行账户","公司","个人"])
                    s = random.choice(["工资","奖金","报销","退款","转账","理财赎回"]) if is_in else random.choice(["消费","转账","取现","还款","缴费","理财购买"])
                    cur.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
                                (None, cust_id, d.isoformat(), "in" if is_in else "out", amt, cp, s, random.choice(["手机银行","网银","柜台","ATM"]), None))
                d += timedelta(days=1)

            # signal injection
            if random.random() < 0.08:
                cur.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
                            (None, cust_id, (TODAY-timedelta(days=1)).isoformat(), "out",
                             round(random.uniform(50000,300000),2), "他行账户", "大额转出", "手机银行", None))
            if tmpl.get("salary_disbursement", False):
                for off in range(1, 8):
                    if random.random() < 0.5:
                        cur.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
                                    (None, cust_id, (TODAY-timedelta(days=off)).isoformat(), "in",
                                     round(random.uniform(3000,20000),2), "公司", "工资", "手机银行", None))
            if emp_status in ("无业","待业"):
                for m in range(1, 7):
                    if random.random() < 0.5:
                        cur.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
                                    (None, cust_id, (TODAY-timedelta(days=30*m)).isoformat(), "in",
                                     round(random.uniform(1500,3500),2), "社保局", "失业金", "手机银行", None))
            if tmpl.get("type_name") == "F·小微企业主":
                for m in range(1, 4):
                    cur.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
                                (None, cust_id, (TODAY-timedelta(days=15*m)).isoformat(), "in",
                                 round(random.uniform(5000,80000),2), "企业账户",
                                 random.choice(["货款","采购款","结算款","预付款","服务费"]), "网银", None))
            if tmpl.get("other_bank_transfer_prob", 0) > 0 and random.random() < tmpl["other_bank_transfer_prob"]:
                cur.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)",
                            (None, cust_id, (TODAY-timedelta(days=random.randint(1,30))).isoformat(), "out",
                             round(random.uniform(10000,200000),2), "他行账户", "他行转账", "手机银行", None))

            cust_id += 1

    # relations
    all_custs = [i+1 for i in range(cust_id-1)]
    biz_custs = list(cur.execute("SELECT cust_id FROM business_info").fetchall())
    biz_custs = [r[0] for r in biz_custs]
    for i in range(len(biz_custs)):
        for j in range(i+1, min(i+3, len(biz_custs))):
            if random.random() < 0.4:
                cur.execute("INSERT INTO customer_relations VALUES (?,?,?,?,?,?)",
                            (None, biz_custs[i], biz_custs[j], "同企业代发",
                             f"同一企业代发: 徽商集团", "transactions.summary"))
    # 亲属
    for i in range(len(all_custs)):
        for j in range(i+1, len(all_custs)):
            ci = cur.execute("SELECT city,name FROM customers WHERE id=?", (all_custs[i],)).fetchone()
            cj = cur.execute("SELECT city,name FROM customers WHERE id=?", (all_custs[j],)).fetchone()
            if ci and cj and ci[0] == cj[0] and ci[1][:1] == cj[1][:1] and random.random() < 0.05:
                cur.execute("INSERT INTO customer_relations VALUES (?,?,?,?,?,?)",
                            (None, all_custs[i], all_custs[j], "亲属", "同姓氏同城市", "customers.city"))

    # communications
    for tmpl in ALL_TEMPLATES:
        freq = tmpl.get("communications_per_month", 0.3)
        for cid in all_custs:
            for m in range(1, 7):
                if random.random() < freq / 4:
                    topics = random.choice(["日常问候","产品咨询","账户服务","定存到期","子女教育","资金规划"])
                    cur.execute("INSERT INTO communications VALUES (?,?,?,?,?,?,?,?)",
                                (None, cid, (TODAY-timedelta(days=30*m)).isoformat(),
                                 f"{random.randint(9,17):02d}:00:00", random.choice(["电话","面谈","微信"]),
                                 random.randint(5,45), f"客户经理致电客户沟通{topics}", topics))

    # risk_assessments
    for cid in all_custs:
        if random.random() < 0.65:
            # 生成 1-3 条历史快照
            hist_count = random.randint(1, 3)
            for h in range(hist_count):
                hist_date = (TODAY - timedelta(days=random.randint(365, 1095))).isoformat()
                cur.execute("INSERT INTO risk_assessment_history VALUES (?,?,?,?,?,?,?,?)",
                            (None, cid,
                             random.choice(RISK_RESULTS[:3]),
                             hist_date,
                             int(random.uniform(20, 95)),
                             round(random.uniform(10, 40), 2),
                             round(random.uniform(10, 35), 2),
                             round(random.uniform(5, 25), 2)))
            # 当前风测结果
            tested = (TODAY - timedelta(days=random.randint(30, 365))).isoformat()
            cur.execute("INSERT INTO risk_assessments VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (None, cid, random.choice(RISK_RESULTS[:3]),
                         (TODAY+timedelta(days=365)).isoformat(),
                         tested,
                         int(random.uniform(20,95)), TODAY.isoformat(),
                         round(random.uniform(10,40),2), round(random.uniform(10,35),2), round(random.uniform(5,25),2)))

    # counterparty_cust_id 后处理: 为 counterparty="本行账户" 的流水随机匹配行内客户
    other_custs = all_custs.copy()
    txn_rows = cur.execute("SELECT id, cust_id FROM transactions WHERE counterparty = '本行账户'").fetchall()
    for tid, from_cust in txn_rows:
        # 从其他客户中随机选一个(排除自己)
        pool = [c for c in other_custs if c != from_cust]
        if pool:
            cur.execute("UPDATE transactions SET counterparty_cust_id = ? WHERE id = ?",
                        (random.choice(pool), tid))

    # benefits
    bp = [("机场贵宾厅","出行","每年6次免费使用","财富","稀有"),
          ("三甲医院体检","健康","每年1次VIP体检套餐","高净值","稀有"),
          ("商超满减券","购物","满200减50","优质","普通"),
          ("子女教育咨询","教育","专业教育规划师1对1咨询","财富","限时"),
          ("留学规划服务","教育","免费留学规划1次","私钻","稀有"),
          ("代驾服务","出行","每年12次免费代驾","高净值","限时"),
          ("生日礼遇","购物","生日当月专属礼品","优质","普通"),
          ("高尔夫练习场","健康","每月2次免费","私钻","稀有"),
          ("法律咨询服务","其他","免费法律咨询1次","私行","限时")]
    tord = ["千元以下","千元户","万元户","优质","财富","高净值","私钻","私行"]
    for cid in all_custs:
        tier = cur.execute("SELECT tier FROM customers WHERE id=?", (cid,)).fetchone()[0]
        ti = tord.index(tier) if tier in tord else 3
        eligible = [b for b in bp if tord.index(b[3]) <= ti]
        n = random.randint(0, 4)
        if n > 0 and eligible:
            for _ in range(n):
                bn, bt, desc, treq, rar = random.choice(eligible)
                acq = (TODAY-timedelta(days=random.randint(1,180))).isoformat()
                exp = (TODAY+timedelta(days=random.randint(180,365))).isoformat()
                cur.execute("INSERT INTO customer_benefits VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (None, cid, bn, bt, desc, treq, rar, acq, exp, "有效"))

    # activities
    acts = [
        ("ACT001","新客理财专享","理财",(TODAY-timedelta(days=30)).isoformat(),(TODAY+timedelta(days=60)).isoformat(),"首次购买理财享额外收益加成","优质","年化+0.5%"),
        ("ACT002","基金定投大赛","基金",(TODAY-timedelta(days=15)).isoformat(),(TODAY+timedelta(days=90)).isoformat(),"参与定投赢取大奖","千元户","最高500元红包"),
        ("ACT003","保险保障月","保险",(TODAY-timedelta(days=5)).isoformat(),(TODAY+timedelta(days=55)).isoformat(),"指定保险产品首年保费9折","财富","保费折扣"),
        ("ACT004","大额存单抢购","存款",(TODAY+timedelta(days=1)).isoformat(),(TODAY+timedelta(days=30)).isoformat(),"限量大额存单年化3.5%","优质","高利率锁定"),
        ("ACT005","信用卡推荐有礼","信用卡",(TODAY-timedelta(days=60)).isoformat(),(TODAY+timedelta(days=30)).isoformat(),"推荐好友办卡双方各得100元","千元以下","现金奖励"),
        ("ACT006","贵金属投资讲座","贵金属",(TODAY+timedelta(days=10)).isoformat(),(TODAY+timedelta(days=40)).isoformat(),"专家解读贵金属市场走势","高净值","精美伴手礼"),
        ("ACT007","暑期亲子财商营","综合",(TODAY+timedelta(days=5)).isoformat(),(TODAY+timedelta(days=35)).isoformat(),"带孩子学习理财知识","财富","亲子互动礼盒"),
        ("ACT008","留学金融一站式","综合",(TODAY-timedelta(days=10)).isoformat(),(TODAY+timedelta(days=80)).isoformat(),"留学贷款+外汇+保险组合方案","高净值","手续费减免"),
        ("ACT009","代发薪客户权益升级","综合",(TODAY-timedelta(days=20)).isoformat(),(TODAY+timedelta(days=40)).isoformat(),"代发客户专享理财额度提升","千元户","专享额度"),
        ("ACT010","年终回馈抽奖","综合",(TODAY+timedelta(days=30)).isoformat(),(TODAY+timedelta(days=90)).isoformat(),"消费满额参与抽奖","优质","最高8888元"),
    ]
    for act in acts:
        cur.execute("INSERT INTO available_activities VALUES (?,?,?,?,?,?,?,?,?)", (None,)+act)

    for cid in all_custs:
        n = random.randint(0, 3)
        if n > 0:
            chosen = random.sample(acts, min(n, len(acts)))
            for act in chosen:
                pd = (TODAY-timedelta(days=random.randint(1,30))).isoformat()
                cur.execute("INSERT INTO customer_activity_participation VALUES (?,?,?,?,?,?)",
                            (None, cid, act[0], pd, random.choice(["已参与","已完成"]), random.choice(["客户反馈积极","","待跟进"])))

    # === 管户关系分配 ===
    # 定义 3 位客户经理
    managers = [
        ("M001", "李建国"),
        ("M002", "王芳"),
        ("M003", "张伟"),
    ]
    for mid, mname in managers:
        cur.execute("INSERT OR IGNORE INTO cust_manager_rel (cust_id, manager_id, manager_name, assigned_date, is_primary) VALUES (?,?,?,?,?)",
                    (0, mid, mname, TODAY.isoformat(), 1))  # dummy row to init
    # 按客户 tier 分配管户（高价值客户优先分配给资深经理 M001）
    tier_order = ["私行", "高净值", "财富", "优质", "万元户", "千元户", "千元以下"]
    cust_rows = cur.execute("SELECT id, tier, total_aum FROM customers ORDER BY total_aum DESC").fetchall()
    primary_done = set()
    for cid, tier, aum in cust_rows:
        # 主客户经理：高价值 → M001, 中等 → M002, 低价值 → M003
        if aum and aum >= 200000:
            primary_mgr = "M001"
        elif aum and aum >= 50000:
            primary_mgr = "M002"
        else:
            primary_mgr = "M003"
        primary_name = dict(managers)[primary_mgr]
        cur.execute("INSERT OR IGNORE INTO cust_manager_rel (cust_id, manager_id, manager_name, assigned_date, is_primary) VALUES (?,?,?,?,?)",
                    (cid, primary_mgr, primary_name, (TODAY - timedelta(days=random.randint(30,365))).isoformat(), 1))
        primary_done.add(cid)

    # 部分高价值客户增加协办经理
    for cid in primary_done:
        c = cur.execute("SELECT total_aum FROM customers WHERE id=?", (cid,)).fetchone()
        if c and (c[0] or 0) >= 50000 and random.random() < 0.3:
            # 选一个不同于主经理的协办经理
            other_mgrs = [m for m in managers if m[0] != primary_mgr]
            co_mgr = random.choice(other_mgrs)
            cur.execute("INSERT OR IGNORE INTO cust_manager_rel (cust_id, manager_id, manager_name, assigned_date, is_primary) VALUES (?,?,?,?,?)",
                        (cid, co_mgr[0], co_mgr[1], (TODAY - timedelta(days=random.randint(7,90))).isoformat(), 0))

    print(f"  管户关系: {len(primary_done)} 客户分配完成")

    # battle_packages
    opp_types = ["产品到期承接","代发到账配置","流失预警挽回","基金挖掘","教育金规划","经营贷续贷"]
    candidates = random.sample(all_custs, min(15, len(all_custs)))
    for i, cid in enumerate(candidates):
        bpid = f"BP{i+1:03d}"
        oppid = f"OPP{i+1:03d}"
        mode = "面谈版" if random.random() < 0.6 else "电话版"
        c = cur.execute("SELECT name,age,gender,tier,total_aum FROM customers WHERE id=?", (cid,)).fetchone()
        overview = json.dumps({"name":c[0],"age":c[1],"gender":"男" if c[2]=="M" else "女","tier":c[3],"total_aum":c[4],"visit_purpose":random.choice(opp_types)}, ensure_ascii=False)
        agenda = None
        if mode == "面谈版":
            agenda = json.dumps([{"step":1,"topic":"开场寒暄","duration":"2-3分钟"},{"step":2,"topic":"核心议题","duration":"10-15分钟"},{"step":3,"topic":"延伸议题","duration":"5-10分钟"},{"step":4,"topic":"收尾确认","duration":"3-5分钟"}], ensure_ascii=False)
        rw = json.dumps(["不得承诺收益","不得误导风险等级","基金产品须说明过往业绩不代表未来表现"], ensure_ascii=False)
        pa = json.dumps(["录入本次沟通记录","标记客户意向产品","创建跟进任务"], ensure_ascii=False)
        ga = (TODAY - timedelta(days=random.randint(0,10))).isoformat()
        ea = (TODAY + timedelta(days=7 - random.randint(0,10))).isoformat()
        st = "已过期" if (TODAY - timedelta(days=random.randint(0,10))).isoformat() > ea else ("已使用" if random.random() < 0.2 else "未使用")
        ua = (TODAY - timedelta(days=random.randint(1,5))).isoformat() if st == "已使用" else None
        cur.execute("INSERT INTO battle_packages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (None, bpid, oppid, cid, mode, st, overview, agenda, rw, pa, ga, ea, ua))

        n_clues = 1 if mode == "电话版" else random.randint(2, 3)
        for j in range(n_clues):
            clid = f"CL{bpid}{j+1:02d}"
            pr = random.choice(["高","中","常规"])
            title = f"线索#{j+1}: {random.choice(opp_types)}"
            basis = f"系统检测到客户{random.choice(['产品即将到期','近期高频浏览理财','代发工资稳定流入'])}"
            strategy = f"以到期提醒为切入点"
            script = f"{c[0]}您好……"
            prods = json.dumps([{"name":"XX稳健理财","type":"理财","risk":"R2","yield":3.5,"reason":"符合风测","script":"这款产品最大特点是稳健……"}], ensure_ascii=False)
            dev = None
            if mode == "面谈版":
                dev = json.dumps([{"scenario":"客户表示不需要","response":"了解真实需求","suggested_products":[]}], ensure_ascii=False)
            cur.execute("INSERT INTO battle_package_clues VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (None, clid, bpid, pr, title, basis, strategy, script, prods, dev))

    db.commit()

    # ---- KPI 种子数据 ----
    gen_kpi_data(db)

    # stats
    tables = ["customers","family_info","business_info","employment_status","holdings","transactions","loans",
              "loan_rejections","behavior_logs","customer_relations","communications","risk_assessments",
              "risk_assessment_history",
              "product_catalog","customer_benefits","available_activities","customer_activity_participation",
              "battle_packages","battle_package_clues",
              "kpi_definitions","kpi_targets","kpi_snapshots"]
    for t in tables:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n}")
    print(f"Done! {cust_id-1} customers generated.")

def gen_kpi_data(db):
    """生成 KPI 种子数据（可独立调用，用于已有 DB 补充）"""
    import random as _rnd
    from calendar import monthrange
    cur = db.cursor()

    print("生成 KPI 指标体系...")
    now_ts = datetime.now().isoformat()
    kpi_defs = [
        ("aum",      "AUM 净增",      "万元", 0.30, "core", 1, "active", "📊", "管户客户总资产期末−期初净增量",       "up"),
        ("finance",  "理财产品销量",  "万元", 0.20, "core", 2, "active", "💰", "新申购理财产品金额（不含到期续作）",   "up"),
        ("fund",     "基金销量",      "万元", 0.15, "core", 3, "active", "📈", "基金申购金额（含定投新增）",             "up"),
        ("insurance","保险销量",      "万元", 0.10, "core", 4, "active", "🛡️", "保险首年保费",                           "up"),
        ("deposit",  "存款净增",      "万元", 0.10, "aux",  5, "active", "🏦", "管户客户存款期末−期初",                 "up"),
        ("vip",      "贵宾客户新增",   "户",  0.10, "aux",  6, "active", "👑", "财富/私行等级客户期末−期初数",          "up"),
        ("active",   "有效户转化",     "户",  0.05, "aux",  7, "active", "🔄", "沉默户→活跃户转化数量",                  "up"),
    ]
    for d in kpi_defs:
        cur.execute(
            "INSERT OR REPLACE INTO kpi_definitions (kpi_code,kpi_name,unit,weight,category,sort_order,status,icon,description,trend_direction,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (*d, now_ts, now_ts))

    print("生成 KPI 目标值...")
    mgr_targets = {
        "M001": {"aum":1200,"finance":720,"fund":480,"insurance":240,"deposit":600,"vip":40,"active":80},
        "M002": {"aum":1000,"finance":600,"fund":400,"insurance":200,"deposit":500,"vip":35,"active":70},
        "M003": {"aum":900,"finance":540,"fund":360,"insurance":180,"deposit":450,"vip":30,"active":60},
    }
    q_weights = [0.22, 0.25, 0.25, 0.28]
    for mgr_id, targets in mgr_targets.items():
        for q_idx in range(4):
            q_num = q_idx + 1
            for kpi_code, year_val in targets.items():
                q_target = round(year_val * q_weights[q_idx], 1)
                cur.execute(
                    "INSERT OR REPLACE INTO kpi_targets (kpi_code,org_id,manager_id,year,quarter,month,target_value,created_by,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (kpi_code, "BR001", mgr_id, 2026, q_num, None, q_target, "system", now_ts))

    print("生成 KPI 完成快照...")
    _rnd.seed(42)
    # 三个客户经理梯度差异
    mgr_mult = {"M001": 0.85, "M002": 0.60, "M003": 0.40}       # 当前季度完成率系数
    mgr_prev = {"M001": 0.93, "M002": 0.85, "M003": 0.78}        # 已结束季度完成率
    for mgr_id, year_targets in mgr_targets.items():
        mult = mgr_mult.get(mgr_id, 0.6)
        prev_rate = mgr_prev.get(mgr_id, 0.85)
        for m_idx in range(7):
            m_num = m_idx + 1
            q_num = (m_num - 1) // 3 + 1   # 当前月份所属季度 1/2/3
            q_idx = q_num - 1
            month_in_q = m_num - q_idx * 3  # 季度内第几个月 1/2/3
            month_end = monthrange(2026, m_num)[1]
            snap_date = f"2026-{m_num:02d}-{month_end:02d}"
            is_q_end = (m_num % 3 == 0)
            for kpi_code, year_val in year_targets.items():
                # YTD 累计：已完成季度 + 当前季度部分
                ytd_actual = 0.0
                for pq in range(q_idx):
                    ytd_actual += year_val * q_weights[pq] * prev_rate
                cur_target = year_val * q_weights[q_idx]
                base_rate = [0.35, 0.68, 0.95][month_in_q - 1]
                rate = base_rate * mult + _rnd.uniform(-0.05, 0.05)
                rate = max(0.06, min(0.98, rate))
                ytd_actual += cur_target * rate
                actual = round(ytd_actual, 1)
                yoy = round(actual * _rnd.uniform(0.85, 0.98), 1) if m_idx < 3 else None
                cur.execute(
                    "INSERT OR REPLACE INTO kpi_snapshots (kpi_code,org_id,manager_id,snap_date,actual_value,yoy_value,period_type,created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (kpi_code, "BR001", mgr_id, snap_date, actual, yoy, "quarter" if is_q_end else "month", now_ts))

    db.commit()
    print("KPI 数据生成完成")

# ============================================================
# 启动
# ============================================================
def main():
    # 创建数据库并生成数据（如果不存在）
    need_gen = not os.path.exists(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    # 迁移：确保 contact_prefer 列存在（向后兼容旧数据库）
    try:
        db.execute("ALTER TABLE customers ADD COLUMN contact_prefer TEXT DEFAULT '不限定'")
        db.commit()
        print("迁移: 已添加 customers.contact_prefer 列")
    except sqlite3.OperationalError:
        pass  # 列已存在
    # 迁移：opportunities 表新增字段（新架构）
    try:
        db.execute("ALTER TABLE opportunities ADD COLUMN updated_at TEXT")
        db.commit()
        print("迁移: 已添加 opportunities.updated_at 列")
    except sqlite3.OperationalError:
        pass  # 列已存在
    try:
        db.execute("ALTER TABLE opportunities ADD COLUMN status_history TEXT DEFAULT '[]'")
        db.commit()
        print("迁移: 已添加 opportunities.status_history 列")
    except sqlite3.OperationalError:
        pass  # 列已存在
    # 迁移：确保 task_execution_history.result_detail 列存在
    try:
        db.execute("ALTER TABLE task_execution_history ADD COLUMN result_detail TEXT DEFAULT ''")
        db.commit()
        print("迁移: 已添加 task_execution_history.result_detail 列")
    except sqlite3.OperationalError:
        pass  # 列已存在
    # 迁移：审计日志表扩展字段（客户隐私保护方案）
    audit_new_cols = [
        ("customer_id", "TEXT DEFAULT ''"),
        ("manager_name", "TEXT DEFAULT ''"),
        ("endpoint", "TEXT DEFAULT ''"),
        ("result_count", "INTEGER DEFAULT 0"),
        ("sensitive_level", "TEXT DEFAULT ''"),
        ("user_agent", "TEXT DEFAULT ''"),
    ]
    for col_name, col_def in audit_new_cols:
        try:
            db.execute(f"ALTER TABLE audit_logs ADD COLUMN {col_name} {col_def}")
            db.commit()
            print(f"迁移: 已添加 audit_logs.{col_name} 列")
        except sqlite3.OperationalError:
            pass  # 列已存在
    # 确保新增索引存在
    try:
        db.execute("CREATE INDEX IF NOT EXISTS idx_al_operator ON audit_logs(operator)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_al_customer ON audit_logs(customer_id)")
        db.commit()
    except Exception:
        pass
    # 迁移：客户表增加数据保留截止日期（数据生命周期管理）
    try:
        db.execute("ALTER TABLE customers ADD COLUMN data_retain_until TEXT DEFAULT ''")
        db.commit()
        print("迁移: 已添加 customers.data_retain_until 列")
    except sqlite3.OperationalError:
        pass
    # 迁移：管户关系表增加解绑日期（客户经理离职/调岗）
    try:
        db.execute("ALTER TABLE cust_manager_rel ADD COLUMN unassigned_date TEXT DEFAULT ''")
        db.commit()
        print("迁移: 已添加 cust_manager_rel.unassigned_date 列")
    except sqlite3.OperationalError:
        pass
    # 迁移：确保 task_execution_history.status CHECK 约束包含 'skipped'
    try:
        # SQLite 不支持直接修改 CHECK 约束，通过重建表实现
        db.execute(
            "CREATE TABLE IF NOT EXISTS task_execution_history_v2 "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, job_name TEXT NOT NULL DEFAULT '', "
            "status TEXT NOT NULL CHECK(status IN ('success','error','skipped')), result_summary TEXT DEFAULT '', "
            "result_detail TEXT DEFAULT '', error_msg TEXT DEFAULT '', started_at TEXT NOT NULL, "
            "finished_at TEXT, duration_ms INTEGER DEFAULT 0)"
        )
        db.execute(
            "INSERT INTO task_execution_history_v2 SELECT * FROM task_execution_history"
        )
        db.execute("DROP TABLE task_execution_history")
        db.execute("ALTER TABLE task_execution_history_v2 RENAME TO task_execution_history")
        db.execute("CREATE INDEX IF NOT EXISTS idx_teh_job ON task_execution_history(job_id)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_teh_started ON task_execution_history(started_at)")
        db.commit()
        print("迁移: 已更新 task_execution_history 状态约束（新增 skipped）")
    except Exception as e:
        print(f"迁移: task_execution_history status 约束可能已是最新 ({e})")
    # 迁移：重建 meeting_records 表（v2：支持追加口述、摘要合并）
    try:
        cur_cols = [r[1] for r in db.execute("PRAGMA table_info(meeting_records)").fetchall()]
        if 'summary' not in cur_cols or 'meeting_status' not in cur_cols:
            db.execute("DROP TABLE IF EXISTS meeting_records")
            db.execute("DROP TABLE IF EXISTS profile_change_log")
            db.execute("""
                CREATE TABLE meeting_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cust_id INTEGER NOT NULL REFERENCES customers(id),
                    cust_name TEXT DEFAULT '',
                    bp_id TEXT, opp_id TEXT,
                    manager_id TEXT NOT NULL,
                    meeting_date TEXT NOT NULL,
                    plan_result TEXT, deviation_note TEXT,
                    customer_feedback TEXT, action_items TEXT,
                    dictation_raw TEXT DEFAULT '[]',
                    summary TEXT DEFAULT '',
                    meeting_status TEXT DEFAULT 'drafting',
                    profile_changes_json TEXT DEFAULT '[]',
                    todos_json TEXT DEFAULT '[]',
                    generated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_mr_cust ON meeting_records(cust_id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_mr_mgr ON meeting_records(manager_id, meeting_date)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_mr_cust_date ON meeting_records(cust_id, meeting_date DESC)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_mr_status ON meeting_records(meeting_status)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_mr_opp ON meeting_records(opp_id)")
            db.execute("""
                CREATE TABLE IF NOT EXISTS profile_change_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cust_id INTEGER NOT NULL REFERENCES customers(id),
                    field_name TEXT NOT NULL,
                    old_value TEXT, new_value TEXT,
                    source TEXT DEFAULT 'dictation',
                    meeting_id INTEGER REFERENCES meeting_records(id),
                    changed_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_pcl_cust ON profile_change_log(cust_id, changed_at)")
            db.commit()
            print("迁移: 已重建 meeting_records 表（v2 新增 summary/meeting_status/dictation JSON）")
    except Exception as e:
        print(f"迁移: meeting_records 重建跳过 ({e})")
    db.commit()

    # 迁移：给 opportunities 表移除 meeting_status/meeting_id（改用 opp_meeting_rel 关联表）
    try:
        opp_cols = [r[1] for r in db.execute("PRAGMA table_info(opportunities)").fetchall()]
        if 'meeting_status' in opp_cols or 'meeting_id' in opp_cols:
            # 创建 opp_meeting_rel 关联表
            db.execute("""
                CREATE TABLE IF NOT EXISTS opp_meeting_rel (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opp_id TEXT NOT NULL,
                    meeting_id INTEGER NOT NULL REFERENCES meeting_records(id),
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(opp_id, meeting_id)
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_omr_opp ON opp_meeting_rel(opp_id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_omr_meeting ON opp_meeting_rel(meeting_id)")
            # 重建 opportunities 表，移除多余字段
            db.execute("""
                CREATE TABLE opportunities_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opp_id TEXT NOT NULL UNIQUE,
                    cust_id INTEGER REFERENCES customers(id),
                    cust_name TEXT NOT NULL,
                    opportunity_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    estimated_value REAL NOT NULL DEFAULT 0,
                    reasoning TEXT NOT NULL,
                    suggested_action TEXT,
                    priority TEXT DEFAULT '常规',
                    source TEXT NOT NULL DEFAULT 'AI-opp_mining',
                    source_method TEXT,
                    trigger_signals TEXT,
                    status TEXT DEFAULT '待跟进',
                    generated_at TEXT NOT NULL,
                    manager_id TEXT
                )
            """)
            db.execute("""
                INSERT INTO opportunities_new
                (id,opp_id,cust_id,cust_name,opportunity_type,title,confidence,estimated_value,
                 reasoning,suggested_action,priority,source,source_method,trigger_signals,
                 status,generated_at,manager_id)
                SELECT id,opp_id,cust_id,cust_name,opportunity_type,title,confidence,estimated_value,
                       reasoning,suggested_action,priority,source,source_method,trigger_signals,
                       status,generated_at,manager_id
                FROM opportunities
            """)
            db.execute("DROP TABLE opportunities")
            db.execute("ALTER TABLE opportunities_new RENAME TO opportunities")
            db.execute("CREATE INDEX IF NOT EXISTS idx_opp_cust ON opportunities(cust_id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_opp_gen ON opportunities(generated_at)")
            db.commit()
            print("迁移: 已重建 opportunities 表（移除 meeting_status/meeting_id，新增 opp_meeting_rel 关联表）")
    except Exception as e:
        print(f"迁移: opportunities 重建跳过 ({e})")

    if need_gen:
        gen_all(db)
    else:
        print(f"数据库已存在: {DB_PATH} ({db.execute('SELECT COUNT(*) FROM customers').fetchone()[0]} 人)")
        # 补充 KPI 种子数据（如果不存在）
        if db.execute("SELECT COUNT(*) FROM kpi_definitions").fetchone()[0] == 0:
            print("KPI 数据为空，补充生成...")
            gen_kpi_data(db)

    # 启动 FastAPI
    print("\n启动 API 服务: http://localhost:8008")
    print("API 文档: http://localhost:8008/docs\n")

    import uvicorn
    from fastapi import FastAPI, Query, HTTPException, Body, Request, UploadFile, File, Form
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    app = FastAPI(title="易会办 客户洞察 API", version="1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    pool = ThreadPoolExecutor(max_workers=4)

    def get_db():
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def q(sql, params=(), one=False):
        conn = get_db()
        try:
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
            conn.close()
            if one: return dict(rows[0]) if rows else None
            return [dict(r) for r in rows]
        except Exception as e:
            conn.close()
            raise

    def ex(sql, params=()):
        conn = get_db()
        try:
            conn.execute(sql, params)
            conn.commit()
            conn.close()
        except Exception as e:
            conn.close()
            raise

    async def aq(sql, params=(), one=False):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(pool, lambda: q(sql, params, one))

    async def ae(sql, params=()):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(pool, lambda: ex(sql, params))

    def _has_common_substring(a: str, b: str, min_len: int = 10) -> bool:
        """检查两个字符串是否有长度 ≥ min_len 的公共子串（中文按字符计）"""
        if not a or not b:
            return False
        shorter = a if len(a) <= len(b) else b
        longer = b if len(a) <= len(b) else a
        for i in range(len(shorter) - min_len + 1):
            if shorter[i:i + min_len] in longer:
                return True
        return False

    async def _check_dup_opp(cust_id: int, opportunity_type: str, title: str) -> bool:
        """检查同一客户是否已有相似待跟进商机（类型匹配 或 标题子串重叠≥10字）"""
        # 1. 精确类型匹配
        dup = await aq(
            "SELECT 1 FROM opportunities WHERE cust_id=? AND status='待跟进' AND opportunity_type=?",
            (cust_id, opportunity_type), one=True
        )
        if dup:
            return True
        # 2. 标题子串重叠检查（防御 LLM 类型名/措辞漂移）
        existing = await aq(
            "SELECT title FROM opportunities WHERE cust_id=? AND status='待跟进'",
            (cust_id,)
        )
        for row in (existing or []):
            if _has_common_substring(title, row['title'] or '', 10):
                return True
        return False

    def ok(data=None, message="ok"):
        return {"code": 0, "data": data, "message": message}

    def _d(d):
        return d if d is None else (d.isoformat() if isinstance(d, (date,datetime)) else str(d))

    def _n(row):
        return None if row is None or all(v is None for v in row.values()) else row

    def _signal_type_label(stype: str) -> str:
        """信号类型的中文标签"""
        labels = {
            "due": "产品到期",
            "overdue": "产品逾期",
            "fund_browse": "浏览基金产品",
            "insurance_browse": "浏览保险产品",
            "loan_browse": "浏览贷款产品",
            "high_aum_idle": "大额资金闲置",
            "insight_change": "客户画像变更",
            "insight_risk": "风险信号预警",
        }
        return labels.get(stype, stype)

    # ================================================================
    # 审计日志工具函数（含实时异常检测）
    # ================================================================

    # 高频/IP跟踪内存字典（重启后重置）
    _operator_query_log: dict = {}  # operator -> [(timestamp, cust_id), ...]
    _operator_ip_log: dict = {}     # operator -> [(timestamp, ip), ...]
    # 高频阈值（可通过管理后台修改 platform_configs 调整）
    _high_freq_window_min = 5   # 时间窗口（分钟）
    _high_freq_max_queries = 30  # 最大查询不同客户数

    def _get_thresholds():
        """从 platform_configs 读取高频阈值配置"""
        nonlocal _high_freq_window_min, _high_freq_max_queries
        try:
            conn = get_db()
            for key, default in [('audit_high_freq_window', 5), ('audit_high_freq_max', 30)]:
                row = conn.execute(
                    "SELECT config_value FROM platform_configs WHERE config_key=?", (key,)
                ).fetchone()
                if row and row[0]:
                    val = int(row[0])
                    if key == 'audit_high_freq_window':
                        _high_freq_window_min = val
                    else:
                        _high_freq_max_queries = val
            conn.close()
        except Exception:
            pass  # 表不存在时忽略，使用默认值

    def reload_audit_thresholds():
        """热加载审计高频阈值（供 admin API 调用的同步版本）"""
        _get_thresholds()
        return {"window_min": _high_freq_window_min, "max_queries": _high_freq_max_queries}

    def get_audit_thresholds():
        """获取当前审计高频阈值"""
        return {"window_min": _high_freq_window_min, "max_queries": _high_freq_max_queries}

    # 启动时加载阈值
    _get_thresholds()

    def log_asset_access(action, manager_id, manager_name, cust_id, endpoint,
                         result_count=0, sensitive_level='', detail='', request=None):
        """记录客户资产查询审计日志（含实时异常检测）"""
        import datetime as _dt
        now_dt = _dt.datetime.now()
        now = now_dt.strftime('%Y-%m-%d %H:%M:%S')

        # 提取 IP 和 User-Agent
        ip = ''
        ua = ''
        if request:
            try:
                ip = request.client.host if request.client else ''
                ua = request.headers.get('user-agent', '')[:500]
            except Exception:
                pass

        # --- 实时异常检测 ---

        # 规则1：管户关系校验
        if cust_id and manager_id:
            try:
                conn = get_db()
                row = conn.execute(
                    "SELECT 1 FROM cust_manager_rel WHERE cust_id=? AND manager_id=?",
                    (int(cust_id), manager_id)
                ).fetchone()
                conn.close()
                if not row:
                    detail = f"[⚠ 非管户] {detail}".strip()
            except Exception:
                pass

        # 规则2：高频查询检测
        if manager_id and cust_id:
            ts = now_dt.timestamp()
            if manager_id not in _operator_query_log:
                _operator_query_log[manager_id] = []
            # 清理过期记录
            cutoff = ts - _high_freq_window_min * 60
            _operator_query_log[manager_id] = [
                (t, c) for t, c in _operator_query_log[manager_id] if t > cutoff
            ]
            # 记录本次查询
            _operator_query_log[manager_id].append((ts, str(cust_id)))
            # 统计窗口内不同客户数
            unique_custs = set(c for _, c in _operator_query_log[manager_id])
            if len(unique_custs) > _high_freq_max_queries:
                if '⚠ 高频' not in detail:
                    detail = f"{detail} [⚠ 高频]"

        # 规则3：深夜查询（00:00-06:00 + C2）
        hour = now_dt.hour
        if 0 <= hour < 6 and sensitive_level == 'C2':
            if '⚠ 深夜' not in detail:
                detail = f"[⚠ 深夜] {detail}".strip()

        # 规则4：IP突变检测（同一operator 10分钟内≥2个不同城市级IP）
        if manager_id and ip:
            ts = now_dt.timestamp()
            if manager_id not in _operator_ip_log:
                _operator_ip_log[manager_id] = []
            # 清理10分钟前的记录
            ip_cutoff = ts - 600
            _operator_ip_log[manager_id] = [
                (t, i) for t, i in _operator_ip_log[manager_id] if t > ip_cutoff
            ]
            _operator_ip_log[manager_id].append((ts, ip))
            unique_ips = set(i for _, i in _operator_ip_log[manager_id])
            if len(unique_ips) >= 2:
                if '⚠ IP异常' not in detail:
                    detail = f"{detail} [⚠ IP异常]"

        # --- 写入审计日志 ---
        try:
            conn = get_db()
            conn.execute(
                """INSERT INTO audit_logs
                   (action, target_type, target_id, customer_id, operator, manager_name,
                    detail, endpoint, result_count, sensitive_level,
                    ip_address, user_agent, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (action, 'customer', str(cust_id) if cust_id else '', str(cust_id) if cust_id else '',
                 manager_id, manager_name, detail, endpoint,
                 result_count, sensitive_level, ip, ua, now)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[审计日志写入失败] {e}")

    # ---- 26 API endpoints ----
    @app.get("/api/customers")
    async def cust_list(keyword: str = Query(None), tier: str = Query(None), manager_id: str = Query(None), page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), request: Request = None):
        w, p = ["1=1"], []
        from_clause = "FROM customers"
        if manager_id:
            from_clause = "FROM customers c INNER JOIN cust_manager_rel cmr ON c.id = cmr.cust_id"
            w[0] = "cmr.manager_id = ?"
            p = [manager_id]
        if keyword: w.append("(name LIKE ? OR phone_masked LIKE ?)"); p.extend([f"%{keyword}%", f"%{keyword}%"])
        if tier: w.append("tier IN (" + ",".join(["?"]*len(tier.split(","))) + ")"); p.extend([t.strip() for t in tier.split(",")])
        where = " AND ".join(w)
        total = (await aq(f"SELECT COUNT(*) as cnt {from_clause} WHERE {where}", p, True))["cnt"]
        select_fields = "c.id,c.cust_no,c.name,c.age,c.gender,c.occupation,c.city,c.tier,c.total_aum,c.employment_status" if manager_id else "id,cust_no,name,age,gender,occupation,city,tier,total_aum,employment_status"
        rows = await aq(f"SELECT {select_fields} {from_clause} WHERE {where} ORDER BY total_aum DESC LIMIT ? OFFSET ?", p + [size, (page-1)*size])
        items = [{"id":r["id"],"cust_no":r["cust_no"],"name":r["name"],"age":r["age"],"gender":"男" if r["gender"]=="M" else "女","city":r["city"],"tier":r["tier"],"total_aum":r["total_aum"],"employment_status":r["employment_status"]} for r in (rows or [])]
        # 审计日志
        log_asset_access('list_customers', manager_id or '', '', '', '/api/customers',
                         len(items), 'C3', f'查询客户列表,返回{len(items)}条', request)
        return ok({"customers":items,"total":total,"page":page,"size":size})

    @app.get("/api/customers/{cid}/profile")
    async def profile(cid: int, request: Request = None):
        basic, fam, biz, wth, credit, beh, emp = await asyncio.gather(
            aq("SELECT * FROM customers WHERE id=?", (cid,), True),
            aq("SELECT * FROM family_info WHERE cust_id=?", (cid,), True),
            aq("SELECT * FROM business_info WHERE cust_id=?", (cid,), True),
            aq("SELECT total_aum,tier FROM customers WHERE id=?", (cid,), True),
            aq("SELECT COUNT(*) as cnt FROM loans WHERE cust_id=?", (cid,), True),
            aq("SELECT COUNT(*) as cnt FROM behavior_logs WHERE cust_id=?", (cid,), True),
            aq("SELECT * FROM employment_status WHERE cust_id=?", (cid,), True))
        if not basic: raise HTTPException(404)
        loaded = ["basic"]
        risk_r = await aq("SELECT test_result FROM risk_assessments WHERE cust_id=?", (cid,), True)
        # 审计日志
        log_asset_access('view_profile', '', '', str(cid), f'/api/customers/{cid}/profile',
                         1, 'C2', f'查看客户{basic["name"]}({cid})完整画像', request)
        return ok({"loaded_modules":loaded, "basic":{"name":basic["name"],"age":basic["age"],"gender":"男" if basic["gender"]=="M" else "女","tier":basic["tier"],"employment_status":basic["employment_status"],"occupation":basic["occupation"],"city":basic["city"],"education":basic.get("education", "—")},
            "family":{k:fam[k] for k in ["marriage","children","child_count","child_age","child_education","study_abroad_intent","study_abroad_target_country"]} if fam else None,
            "business":{k:biz[k] for k in ["business_name","duration_years","share_ratio","reg_capital","address","scope","verified","verified_source"]} if biz else None,
            "wealth_summary":{"total_aum":wth["total_aum"],"tier":wth["tier"],"wealth_score":None,"yoy_return":None},
            "credit_summary":{"loan_count":credit["cnt"],"overdue_count":0,"rejection_count":0},
            "behavior_summary":{"fin_prefs":[],"risk_result":risk_r["test_result"] if risk_r else None,"liquidity":None},
            "employment_detail":{k:emp[k] for k in ["status","unemployment_benefits","benefit_amount","verified"]} if emp else None})

    @app.get("/api/customers/{cid}/basic")
    async def basic(cid: int, request: Request = None):
        r = await aq("SELECT * FROM customers WHERE id=?", (cid,), True)
        if not r: raise HTTPException(404)
        # 审计日志
        log_asset_access('view_basic', '', '', str(cid), f'/api/customers/{cid}/basic',
                         1, 'C3', f'查看客户{r["name"]}({cid})基本信息', request)
        return ok({"id":r["id"],"name":r["name"],"age":r["age"],"gender":"男" if r["gender"]=="M" else "女","tier":r["tier"],"total_aum":r["total_aum"],"phone_masked":r["phone_masked"],"employment_status":r["employment_status"],"occupation":r["occupation"],"industry":r["industry"],"city":r["city"],"education":r["education"]})

    @app.get("/api/customers/{cid}/family")
    async def family(cid: int): r = await aq("SELECT marriage,children,child_count,child_age,child_education,study_abroad_intent,study_abroad_target_country,spouse_has_income FROM family_info WHERE cust_id=?", (cid,), True); return ok(_n(r))
    @app.get("/api/customers/{cid}/employment")
    async def employment(cid: int): r = await aq("SELECT status,unemployment_benefits,benefit_amount,benefit_start_date,benefit_end_date,verified,last_verified_date FROM employment_status WHERE cust_id=?", (cid,), True); return ok(_n(r))
    @app.get("/api/customers/{cid}/business")
    async def business(cid: int): r = await aq("SELECT business_name,duration_years,share_ratio,reg_capital,address,scope,verified,verified_source FROM business_info WHERE cust_id=?", (cid,), True); return ok(_n(r))

    @app.get("/api/customers/{cid}/wealth/summary")
    async def w_summary(cid: int, request: Request = None):
        r = await aq("SELECT total_aum,tier FROM customers WHERE id=?", (cid,), True)
        if not r: raise HTTPException(404)
        risk = await aq("SELECT wealth_score,score_time,dimension_asset,dimension_income,dimension_social FROM risk_assessments WHERE cust_id=?", (cid,), True)
        tags = []; hc = (await aq("SELECT COUNT(*) as cnt FROM holdings WHERE cust_id=?", (cid,), True))["cnt"]
        if hc >= 5: tags.append("多元配置")
        if risk and risk.get("wealth_score"):
            tags.append("优质客户" if risk["wealth_score"]>=70 else ("成长客户" if risk["wealth_score"]>=40 else "待培养"))
        # 审计日志
        log_asset_access('view_wealth_summary', '', '', str(cid), f'/api/customers/{cid}/wealth/summary',
                         1, 'C2', f'查看客户{cid}财富摘要(total_aum={r["total_aum"]})', request)
        return ok({"total_aum":r["total_aum"],"tier":r["tier"],"tier_label":r["tier"],"tags":tags,"wealth_score":risk["wealth_score"] if risk else None,"score_time":_d(risk["score_time"]) if risk else None,"score_dimensions":None})

    @app.get("/api/customers/{cid}/wealth/holdings")
    async def w_holdings(cid: int, request: Request = None):
        rows = await aq("SELECT * FROM holdings WHERE cust_id=? ORDER BY amount DESC", (cid,))
        if not rows: return ok(None)
        dist, total = {}, 0; details = []
        for r in rows:
            a = r["amount"]; total += a; dist[r["product_type"]] = dist.get(r["product_type"],0)+a
            details.append({"product_name":r["product_name"],"product_type":r["product_type"],"amount":a,"yield_rate":r["yield_rate"],"risk_level":r["risk_level"],"maturity_date":_d(r["maturity_date"]),"status":r["status"]})
        # 审计日志
        log_asset_access('view_holdings', '', '', str(cid), f'/api/customers/{cid}/wealth/holdings',
                         len(details), 'C2', f'查看客户{cid}持仓明细,{len(details)}条产品', request)
        return ok({"total_scale":total,"distribution":{"deposit":dist.get("存款",0),"wealth_mgmt":dist.get("理财",0),"fund":dist.get("基金",0),"precious_metal":dist.get("贵金属",0)},"details":details})

    @app.get("/api/customers/{cid}/wealth/fund-flow")
    async def w_fundflow(cid: int, months: int = Query(12), request: Request = None):
        since = (TODAY - timedelta(days=months*30)).isoformat()
        rows = await aq("SELECT txn_type,amount,summary FROM transactions WHERE cust_id=? AND txn_date>=?", (cid, since))
        if not rows: return ok(None)
        inflow = sum(r["amount"] for r in rows if r["txn_type"]=="in")
        outflow = sum(r["amount"] for r in rows if r["txn_type"]=="out")
        # 审计日志
        log_asset_access('view_fund_flow', '', '', str(cid), f'/api/customers/{cid}/wealth/fund-flow',
                         len(rows), 'C2', f'查看客户{cid}资金流水,{len(rows)}条', request)
        return ok({"yearly_inflow":round(inflow,2),"yearly_outflow":round(outflow,2),"retention_desc":"资金留存率较高" if inflow>outflow*0.8 else "资金流出现象需关注"})

    @app.get("/api/customers/{cid}/wealth/salary")
    async def w_salary(cid: int, request: Request = None):
        since = (TODAY - timedelta(days=210)).isoformat()
        rows = await aq("SELECT txn_date,amount FROM transactions WHERE cust_id=? AND summary='工资' AND txn_date>=? ORDER BY txn_date DESC", (cid, since))
        if not rows: return ok(None)
        amts = [r["amount"] for r in rows]; avg6 = round(sum(amts[:6])/min(6,len(amts)),2)
        # 审计日志
        log_asset_access('view_salary', '', '', str(cid), f'/api/customers/{cid}/wealth/salary',
                         1, 'C2', f'查看客户{cid}代发薪资', request)
        return ok({"current_month_amount":amts[0],"avg_6m":avg6,"salary_level":"高收入" if avg6>15000 else ("中等收入" if avg6>8000 else "入门收入")})

    @app.get("/api/customers/{cid}/credit/loans")
    async def c_loans(cid: int):
        rows = await aq("SELECT product_name,credit_line,used_amount,(credit_line-used_amount) as remaining,overdue_count,interest_rate,start_date,maturity_date FROM loans WHERE cust_id=?", (cid,))
        if not rows: return ok(None)
        items = [{"product_name":r["product_name"],"credit_line":r["credit_line"],"used":r["used_amount"],"remaining":r["remaining"],"overdue_count":r["overdue_count"]} for r in rows]
        return ok({"loans":items,"total_count":len(items)})

    @app.get("/api/customers/{cid}/credit/rejections")
    async def c_rej(cid: int):
        rows = await aq("SELECT product_name,reject_reason,rejected_date FROM loan_rejections WHERE cust_id=?", (cid,))
        return ok(None) if not rows else ok({"rejections":[dict(r) for r in rows],"total_count":len(rows)})

    @app.get("/api/customers/{cid}/credit/social-security")
    async def c_ss(cid: int):
        r = await aq("SELECT COUNT(*) as cnt FROM transactions WHERE cust_id=? AND summary='工资'", (cid,), True)
        return ok({"housing_fund_base":5000,"housing_fund_period":"5年","social_security_base":6000,"social_security_period":"5年"}) if r and r["cnt"]>0 else ok(None)

    @app.get("/api/customers/{cid}/behavior/preferences")
    async def b_prefs(cid: int):
        rows = await aq("SELECT page_type,COUNT(*) as cnt FROM behavior_logs WHERE cust_id=? GROUP BY page_type ORDER BY cnt DESC", (cid,))
        if not rows: return ok(None)
        total = sum(r["cnt"] for r in rows)
        prefs = [{"label":f"{r['page_type']}偏好","basis":f"近3月浏览{r['cnt']}次,占比{r['cnt']*100//total}%"} for r in rows if r["cnt"]>=3]
        risk = await aq("SELECT test_result FROM risk_assessments WHERE cust_id=?", (cid,), True)
        return ok({"fin_prefs":prefs,"liquidity":"高" if total>80 else ("中" if total>30 else "低"),"risk":{"test_result":risk["test_result"] if risk else None}})

    @app.get("/api/customers/{cid}/behavior/logs")
    async def b_logs(cid: int, days: int = Query(90), page: int = Query(1), size: int = Query(50)):
        since = (TODAY - timedelta(days=days)).isoformat()
        total = (await aq("SELECT COUNT(*) as cnt FROM behavior_logs WHERE cust_id=? AND event_date>=?", (cid, since), True))["cnt"]
        rows = await aq("SELECT * FROM behavior_logs WHERE cust_id=? AND event_date>=? ORDER BY event_date DESC LIMIT ? OFFSET ?", (cid, since, size, (page-1)*size))
        return ok({"logs":[{"date":r["event_date"],"channel":r["channel"],"page_type":r["page_type"],"action":r["action"],"duration_sec":r["duration_sec"]} for r in (rows or [])],"total":total,"page":page})

    @app.get("/api/customers/{cid}/relations")
    async def relations(cid: int):
        rows = await aq("SELECT cr.*,c1.name as na,c1.tier as ta,c1.total_aum as aa,c2.name as nb,c2.tier as tb,c2.total_aum as ab FROM customer_relations cr JOIN customers c1 ON cr.cust_id_a=c1.id JOIN customers c2 ON cr.cust_id_b=c2.id WHERE cr.cust_id_a=? OR cr.cust_id_b=?", (cid, cid))
        items = []
        for r in (rows or []):
            is_a = r["cust_id_a"]==cid
            items.append({"target_cust_id":r["cust_id_b"] if is_a else r["cust_id_a"],"target_name":r["nb"] if is_a else r["na"],"relation_type":r["relation_type"],"evidence":r["evidence"],"target_tier":r["tb"] if is_a else r["ta"],"target_aum":r["ab"] if is_a else r["aa"]})
        return ok({"relations":items,"count":len(items)})

    @app.get("/api/customers/{cid}/benefits")
    async def benefits(cid: int):
        rows = await aq("SELECT * FROM customer_benefits WHERE cust_id=?", (cid,))
        return ok({"benefits":[{"benefit_name":r["benefit_name"],"type":r["benefit_type"],"rarity":r["rarity"],"status":r["status"],"acquired_date":r["acquired_date"]} for r in (rows or [])],"eligible_count":0})

    @app.get("/api/customers/{cid}/activities")
    async def cust_acts(cid: int):
        parts = await aq("SELECT cap.*,aa.title,aa.type FROM customer_activity_participation cap JOIN available_activities aa ON cap.activity_id=aa.activity_id WHERE cap.cust_id=?", (cid,))
        avail = await aq("SELECT * FROM available_activities WHERE end_date>=? ORDER BY start_date LIMIT 5", (TODAY.isoformat(),))
        return ok({"participated":[{"activity_id":p["activity_id"],"title":p["title"],"type":p["type"],"status":p["status"]} for p in (parts or [])],"available":[{"activity_id":a["activity_id"],"title":a["title"],"type":a["type"],"description":a["description"],"reward_desc":a["reward_desc"]} for a in (avail or [])]})

    @app.get("/api/activities")
    async def acts_list(type: str = Query(None, alias="type"), tier: str = Query(None)):
        w, p = ["end_date>=?"], [TODAY.isoformat()]
        if type: w.append("type=?"); p.append(type)
        if tier: w.append("target_tier=?"); p.append(tier)
        rows = await aq(f"SELECT * FROM available_activities WHERE {' AND '.join(w)} ORDER BY start_date", p)
        return ok({"activities":[{"activity_id":r["activity_id"],"title":r["title"],"type":r["type"],"target_tier":r["target_tier"],"reward_desc":r["reward_desc"]} for r in (rows or [])]})

    @app.get("/api/products")
    async def products_list(
        type_: str = Query(None, alias="type"),
        risk: str = Query(None),
        keyword: str = Query(None),
    ):
        """
        获取产品列表（从 product_catalog 表读取）
        支持按类型、风险等级、关键词筛选
        """
        import json as _json

        # 从数据库查询在售产品
        rows = await aq(
            "SELECT * FROM product_catalog WHERE status = '在售' ORDER BY category, product_id"
        )

        # 转换为前端预期格式
        def map_product(p: dict) -> dict:
            cat = p.get("category", "")
            icon_map = {"理财": "📊", "基金": "📈", "存款": "🏦", "保险": "🛡️"}
            risk_label_map = {"R1": "低风险", "R2": "中低风险", "R3": "中风险", "R4": "中高风险", "R5": "高风险"}

            # 解析 JSON 序列化字段（DB 存储为 TEXT）
            def _parse_json(val, default):
                if isinstance(val, str):
                    try:
                        return _json.loads(val)
                    except Exception:
                        return default
                return val if val else default

            selling_points = _parse_json(p.get("selling_points"), [])
            scenario_tags = _parse_json(p.get("scenario_tags"), [])

            # 构建 benchmark/收益文本
            er_min = p.get("expected_return_min", "")
            er_max = p.get("expected_return_max", "")
            return_type = p.get("return_type", "")
            if er_min and er_max:
                benchmark = f"{return_type} {er_min}%-{er_max}%"
                hist_yield = f"近1年 ~{er_max}%"
            elif er_max:
                benchmark = f"{return_type} {er_max}%"
                hist_yield = f"近1年 ~{er_max}%"
            else:
                benchmark = return_type or ""
                hist_yield = ""

            # 构建亮点文本
            highlights = " · ".join(selling_points[:3]) if selling_points else ""

            # min_amount 格式
            min_amt = p.get("min_amount", 1) or 1
            if min_amt >= 10000:
                min_unit = "万"
                min_val = min_amt / 10000
            else:
                min_unit = "元"
                min_val = min_amt

            # 解析适用客群
            applicable_customer = _parse_json(p.get("applicable_customer"), {})

            return {
                "id": p.get("product_id", ""),
                "type": cat,
                "name": p.get("short_name", p.get("product_name", "")),
                "full_name": p.get("product_name", ""),
                "icon": icon_map.get(cat, "📋"),
                "risk": p.get("risk_level", "R2"),
                "riskLabel": risk_label_map.get(p.get("risk_level", "R2"), "中低风险"),
                "riskName": p.get("risk_name", ""),
                "min": min_val,
                "minUnit": min_unit,
                "minAmountDesc": p.get("min_amount_desc", ""),
                "term": p.get("term_desc", ""),
                "termType": p.get("sub_category", ""),
                "termDays": p.get("term_days"),
                "benchmark": benchmark,
                "histYield": hist_yield,
                "expectedReturnMin": er_min,
                "expectedReturnMax": er_max,
                "returnType": return_type,
                "returnBenchmark": p.get("return_benchmark", ""),
                "manager": p.get("issuer", p.get("bank_name", "")),
                "issuer": p.get("issuer", ""),
                "scale": "",
                "investScope": p.get("invest_direction", ""),
                "redeem": p.get("redemption_days", ""),
                "fee": p.get("subscription_fee", "") or "无",
                "redemptionFee": p.get("redemption_fee", ""),
                "highlights": highlights,
                "sellingPoints": selling_points,
                "scenario_tags": scenario_tags,
                "applicableCustomer": applicable_customer,
                "aiFit": 5,  # 默认 AI 推荐分
                "aiReason": "",
                "bank_name": p.get("bank_name", ""),
                "currency": p.get("currency", "CNY"),
                "productCode": p.get("product_code", ""),
                "dataDate": p.get("data_date", ""),
                "dataSource": p.get("data_source", ""),
                "sourceUrl": p.get("source_url", ""),
                "status": p.get("status", "在售"),
            }

        products = [map_product(dict(r)) for r in (rows or [])]

        # 筛选
        if type_:
            products = [p for p in products if p["type"] == type_]
        if risk:
            products = [p for p in products if p["risk"] == risk]
        if keyword:
            kw = keyword.lower()
            products = [p for p in products if
                        kw in p["name"].lower() or kw in p.get("full_name", "").lower()]

        return ok({"products": products, "total": len(products)})

    # ============================================================
    # 昨日回顾 API
    # ============================================================

    @app.get("/api/daily-review")
    async def daily_review(manager_id: str = Query("")):
        """
        获取客户经理最近一日回顾数据。
        返回最近一条回顾的完整内容（含 sections），以及统计数据摘要。
        """
        if not manager_id:
            return err("缺少 manager_id 参数")

        row = await aq(
            "SELECT * FROM daily_reviews WHERE manager_id = ? ORDER BY review_date DESC LIMIT 1",
            [manager_id]
        )
        if not row:
            return ok({"has_review": False, "message": "暂无昨日回顾数据"})

        r = dict(row[0])
        # 解析 content JSON
        content = {}
        try:
            content = json.loads(r.get("content", "{}"))
        except Exception:
            content = {"sections": [{"title": "回顾内容", "content": r.get("content", "")}]}

        # 提取统计数据
        sections = content.get("sections", [])
        summary_text = ""
        stats = []
        for sec in sections:
            title = sec.get("title", "")
            text = sec.get("content", "")
            if "概要" in title or "概览" in title:
                summary_text = text
            elif title:
                stats.append({"title": title, "content": text})

        return ok({
            "has_review": True,
            "review_date": r["review_date"],
            "generated_at": r["generated_at"],
            "is_read": bool(r["is_read"]),
            "summary": summary_text,
            "sections": sections,
            "stats": stats,
        })

    @app.get("/api/daily-digest")
    async def daily_digest():
        """
        获取最近一次资讯摘要（从定时任务执行历史中读取）。
        返回 AI 提炼的要闻列表和综合解读。
        """
        row = await aq(
            "SELECT * FROM task_execution_history WHERE job_id = 'daily_digest_gen' AND status = 'success' ORDER BY started_at DESC LIMIT 1"
        )
        if not row:
            return ok({"has_digest": False, "message": "暂无资讯摘要数据"})

        r = dict(row[0])
        detail = {}
        try:
            detail = json.loads(r.get("result_detail", "{}"))
        except Exception:
            detail = {}

        headlines = detail.get("headlines", [])
        briefing = detail.get("briefing", "")
        digest_date = detail.get("date", "")

        return ok({
            "has_digest": True,
            "date": digest_date,
            "generated_at": r["finished_at"] or r["started_at"],
            "headline_count": len(headlines),
            "headlines": headlines,
            "briefing": briefing,
        })

    # ============================================================
    # KPI 业绩看板 API
    # ============================================================

    @app.get("/api/kpi/definitions")
    async def kpi_definitions_list():
        """返回所有 active KPI 定义（含权重分配）"""
        rows = await aq("SELECT * FROM kpi_definitions WHERE status='active' ORDER BY sort_order")
        defs = [{"kpi_code":r["kpi_code"],"kpi_name":r["kpi_name"],"unit":r["unit"],
                  "weight":r["weight"],"category":r["category"],"sort_order":r["sort_order"],
                  "icon":r["icon"],"description":r["description"],"trend_direction":r["trend_direction"]}
                 for r in (rows or [])]
        total_weight = round(sum(d["weight"] for d in defs), 4)
        return ok({"definitions": defs, "total_weight": total_weight, "valid": abs(total_weight - 1.0) < 0.01})

    @app.post("/api/kpi/definitions")
    async def kpi_definition_create(body: dict = Body(...)):
        """新增 KPI（管理后台）"""
        now_ts = datetime.now().isoformat()
        await ae("INSERT INTO kpi_definitions (kpi_code,kpi_name,unit,weight,category,sort_order,status,icon,description,trend_direction,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                 (body["kpi_code"], body["kpi_name"], body["unit"], body["weight"],
                  body.get("category","aux"), body.get("sort_order",99), "active",
                  body.get("icon","📋"), body.get("description",""),
                  body.get("trend_direction","up"), now_ts, now_ts))
        return ok({"kpi_code": body["kpi_code"]}, "KPI 创建成功")

    @app.put("/api/kpi/definitions/{kpi_code}")
    async def kpi_definition_update(kpi_code: str, body: dict = Body(...)):
        """修改 KPI（名称/权重/状态等）"""
        now_ts = datetime.now().isoformat()
        fields = []
        params = []
        for key in ["kpi_name","unit","weight","category","sort_order","status","icon","description","trend_direction"]:
            if key in body:
                fields.append(f"{key}=?")
                params.append(body[key])
        if not fields:
            return err("无变更字段")
        params.append(now_ts)
        params.append(kpi_code)
        await ae(f"UPDATE kpi_definitions SET {', '.join(fields)}, updated_at=? WHERE kpi_code=?", params)
        return ok({}, "KPI 更新成功")

    @app.delete("/api/kpi/definitions/{kpi_code}")
    async def kpi_definition_delete(kpi_code: str):
        """软删除 KPI（status='inactive'），不可物理删除"""
        now_ts = datetime.now().isoformat()
        await ae("UPDATE kpi_definitions SET status='inactive', updated_at=? WHERE kpi_code=?", (now_ts, kpi_code))
        return ok({}, "KPI 已停用")

    @app.get("/api/kpi/snapshot")
    async def kpi_snapshot(
        manager_id: str = Query(None),
        org_id: str = Query(None),
        period: str = Query("month", description="month/quarter/half_year/year"),
        date: str = Query(None, description="快照日期或季度key如2026-Q3"),
    ):
        """查询 KPI 完成数据快照"""
        w, p = [], []
        if manager_id:
            w.append("s.manager_id=?"); p.append(manager_id)
        if org_id:
            w.append("s.org_id=?"); p.append(org_id)
        if period:
            w.append("s.period_type=?"); p.append(period)
        if date:
            w.append("s.snap_date like ?"); p.append(date + "%")

        where = f"WHERE {' AND '.join(w)}" if w else ""
        rows = await aq(
            f"SELECT s.*, d.kpi_name, d.unit, d.weight, d.icon, d.category, d.sort_order "
            f"FROM kpi_snapshots s JOIN kpi_definitions d ON s.kpi_code=d.kpi_code "
            f"{where} ORDER BY s.snap_date DESC, d.sort_order", p)

        # 按 KPI 分组
        by_kpi = {}
        for r in (rows or []):
            kc = r["kpi_code"]
            if kc not in by_kpi:
                by_kpi[kc] = {"kpi_code":kc,"kpi_name":r["kpi_name"],"unit":r["unit"],
                               "weight":r["weight"],"icon":r["icon"],"category":r["category"],
                               "snapshots":[]}
            by_kpi[kc]["snapshots"].append({
                "snap_date":r["snap_date"],"actual_value":r["actual_value"],
                "yoy_value":r["yoy_value"],"period_type":r["period_type"]})
        return ok({"by_kpi": list(by_kpi.values()), "snap_count": len(rows or [])})

    @app.get("/api/kpi/targets")
    async def kpi_targets(
        manager_id: str = Query(None),
        org_id: str = Query(None),
        year: int = Query(2026),
        quarter: int = Query(None),
    ):
        """查询 KPI 目标值（默认 YTD 累计至当前季度）"""
        w, p = ["t.year=?"], [year]
        if manager_id:
            w.append("t.manager_id=?"); p.append(manager_id)
        if org_id:
            w.append("t.org_id=?"); p.append(org_id)
        if quarter is not None:
            # 显式指定季度：返回单季度目标
            w.append("t.quarter=?"); p.append(quarter)
            rows = await aq(
                f"SELECT t.*, d.kpi_name, d.unit, d.weight, d.icon, d.category, d.sort_order "
                f"FROM kpi_targets t JOIN kpi_definitions d ON t.kpi_code=d.kpi_code "
                f"WHERE {' AND '.join(w)} ORDER BY d.sort_order", p)
        else:
            # 默认：YTD 累计至当前季度
            cur_q = (date.today().month - 1) // 3 + 1
            w.append("t.quarter<=?"); p.append(cur_q)
            rows = await aq(
                f"SELECT t.kpi_code, SUM(t.target_value) as target_value, "
                f"d.kpi_name, d.unit, d.weight, d.icon, d.category, d.sort_order "
                f"FROM kpi_targets t JOIN kpi_definitions d ON t.kpi_code=d.kpi_code "
                f"WHERE {' AND '.join(w)} GROUP BY t.kpi_code ORDER BY d.sort_order", p)
        return ok({"targets": [dict(r) for r in (rows or [])], "count": len(rows or [])})

    @app.get("/api/kpi/ranking")
    async def kpi_ranking(
        manager_id: str = Query(None),
        period: str = Query("quarter", description="month/quarter/year"),
        key: str = Query(None, description="如 2026-07 或 2026-Q3"),
        limit: int = Query(20),
    ):
        """
        KPI 完成排名（动态按 active KPI + weight 计算综合得分）
        支持客户经理排名（manager_id 指定时返回该经理在全体中的排名）
        """
        # 获取 active KPI 定义
        kpi_rows = await aq("SELECT * FROM kpi_definitions WHERE status='active' AND weight>0 ORDER BY sort_order")
        if not kpi_rows:
            return ok({"rankings": [], "my_rank": None})

        # 获取指定时间段内各经理的快照数据（始终查全部，用于排名计算）
        snap_key = key or (datetime.now().strftime("%Y-%m"))
        w, p = ["s.snap_date like ?"], [snap_key + "%"]

        snap_rows = await aq(
            f"SELECT s.manager_id, s.kpi_code, MAX(s.actual_value) as actual "
            f"FROM kpi_snapshots s WHERE {' AND '.join(w)} GROUP BY s.manager_id, s.kpi_code", p)

        # 获取目标值
        target_rows = await aq(
            f"SELECT manager_id, kpi_code, target_value FROM kpi_targets WHERE year=?", (2026,))

        # 构建: {manager_id: {kpi_code: actual}}
        snap_by_mgr = {}
        for r in (snap_rows or []):
            mid = r["manager_id"]
            if mid not in snap_by_mgr:
                snap_by_mgr[mid] = {}
            snap_by_mgr[mid][r["kpi_code"]] = r["actual"]

        # 构建: {manager_id: {kpi_code: target}}
        tgt_by_mgr = {}
        for r in (target_rows or []):
            mid = r["manager_id"]
            if mid not in tgt_by_mgr:
                tgt_by_mgr[mid] = {}
            tgt_by_mgr[mid][r["kpi_code"]] = r["target_value"]

        # 计算综合得分
        rankings = []
        for mid, snap in snap_by_mgr.items():
            total_weight = 0
            weighted_score = 0
            details = []
            for kpi in kpi_rows:
                kc = kpi["kpi_code"]
                wgt = kpi["weight"]
                actual = snap.get(kc, 0)
                target = (tgt_by_mgr.get(mid, {}).get(kc, 1) or 1)
                rate = min(1.2, actual / max(target, 0.01))
                weighted_score += rate * wgt
                total_weight += wgt
                details.append({"kpi_code":kc,"kpi_name":kpi["kpi_name"],"actual":actual,"target":target,"rate":round(rate,4)})

            score = round(weighted_score / max(total_weight, 0.01) * 100, 1)
            rankings.append({"manager_id":mid,"composite_score":score,"details":details})

        rankings.sort(key=lambda x: x["composite_score"], reverse=True)
        my_rank = next((i+1 for i, r in enumerate(rankings) if r["manager_id"] == manager_id), None) if manager_id else None

        return ok({"rankings": rankings[:limit], "my_rank": my_rank, "total": len(rankings)})

    @app.get("/api/kpi/trend")
    async def kpi_trend(
        manager_id: str = Query(None),
        kpi: str = Query("aum", description="kpi_code"),
        months: int = Query(12),
    ):
        """KPI 趋势数据（折线图用）"""
        from datetime import timedelta
        start = (datetime.now() - timedelta(days=months * 31)).strftime("%Y-%m")
        w, p = ["s.snap_date >= ?", "s.period_type='month'"], [start]
        if manager_id:
            w.append("s.manager_id=?"); p.append(manager_id)
        if kpi:
            w.append("s.kpi_code=?"); p.append(kpi)

        rows = await aq(
            f"SELECT s.snap_date, s.actual_value, s.yoy_value, d.kpi_name, d.unit "
            f"FROM kpi_snapshots s JOIN kpi_definitions d ON s.kpi_code=d.kpi_code "
            f"WHERE {' AND '.join(w)} ORDER BY s.snap_date", p)
        return ok({"trend": [dict(r) for r in (rows or [])], "kpi": kpi, "months": months})

    @app.get("/api/tasks")
    async def tasks(date_: str = Query(None, alias="date"), manager_id: str = Query(None)):
        td = date.fromisoformat(date_) if date_ else TODAY
        # 获取经理管户ID列表
        mgr_cust_ids = None
        if manager_id:
            mgr_rows = await aq("SELECT cust_id FROM cust_manager_rel WHERE manager_id = ?", (manager_id,))
            mgr_cust_ids = set(r["cust_id"] for r in (mgr_rows or []))
        tasks = []
        # 1. 产品到期
        due = await aq("SELECT h.cust_id,c.name,COUNT(*) as cnt,MIN(h.maturity_date) as nearest,SUM(h.amount) as total FROM holdings h JOIN customers c ON h.cust_id=c.id WHERE h.maturity_date BETWEEN ? AND ? GROUP BY h.cust_id,c.name", (td.isoformat(), (td+timedelta(days=7)).isoformat()))
        for r in (due or []):
            if mgr_cust_ids and r['cust_id'] not in mgr_cust_ids: continue
            tasks.append({"task_id":f"TK_DUE_{r['cust_id']}","type":"产品到期","cust_id":r["cust_id"],"cust_name":r["name"],"summary":f"{r['cnt']}笔产品即将到期, 合计{float(r['total'])/10000:.0f}万","priority":"高"})
        # 2. 贷款逾期
        overdue = await aq("SELECT l.cust_id,c.name,l.overdue_count FROM loans l JOIN customers c ON l.cust_id=c.id WHERE l.overdue_count>0")
        for r in (overdue or []):
            if mgr_cust_ids and r['cust_id'] not in mgr_cust_ids: continue
            tasks.append({"task_id":f"TK_OD_{r['cust_id']}","type":"贷款逾期","cust_id":r["cust_id"],"cust_name":r["name"],"summary":f"贷款逾期{r['overdue_count']}期, 需跟进","priority":"高"})
        # 3. 大额异动(昨日)
        big = await aq("SELECT t.cust_id,c.name,t.amount FROM transactions t JOIN customers c ON t.cust_id=c.id WHERE t.txn_date=? AND t.amount>30000 AND t.txn_type='out' ORDER BY t.amount DESC LIMIT 3", (td.isoformat(),))
        for r in (big or []):
            if mgr_cust_ids and r['cust_id'] not in mgr_cust_ids: continue
            tasks.append({"task_id":f"TK_BIG_{r['cust_id']}","type":"大额异动","cust_id":r["cust_id"],"cust_name":r["name"],"summary":f"昨日大额转出{float(r['amount'])/10000:.1f}万","priority":"高"})
        # 4. 联络超期(>14天未联系)
        old = await aq("SELECT c.id,c.name,MAX(cm.comm_date) as last_date FROM customers c LEFT JOIN communications cm ON c.id=cm.cust_id GROUP BY c.id HAVING MAX(cm.comm_date) IS NULL OR MAX(cm.comm_date) < ? LIMIT 8", ((td-timedelta(days=14)).isoformat(),))
        for r in (old or []):
            if mgr_cust_ids and r['id'] not in mgr_cust_ids: continue
            days = '从未联络' if not r['last_date'] else f"超期{(td - date.fromisoformat(r['last_date'])).days}天"
            tasks.append({"task_id":f"TK_CT_{r['id']}","type":"联络超期","cust_id":r["id"],"cust_name":r["name"],"summary":days,"priority":"中"})
        return ok({"tasks":tasks,"total":len(tasks)})

    @app.post("/api/tasks/processing-records")
    async def save_processing_record(body: dict):
        """保存客户处理记录"""
        task_type = body.get("task_type", "")
        cust_id = body.get("cust_id", 0)
        cust_name = body.get("cust_name", "")
        action = body.get("action", "")
        notes = body.get("notes", "")
        card_id = body.get("card_id", "")
        processed_at = datetime.now().isoformat()
        await ae(
            "INSERT INTO processing_records (task_type, cust_id, cust_name, action, notes, processed_at, card_id) VALUES (?,?,?,?,?,?,?)",
            (task_type, cust_id, cust_name, action, notes, processed_at, card_id))
        return ok({"record_id": None, "processed_at": processed_at}, "处理记录已保存")

    @app.get("/api/opportunities")
    async def opps(manager_id: str = Query(None)):
        # 从 opportunities 表读取已入库商机（规则引擎在日程排程时生成）
        ai_opps = await aq(
            "SELECT * FROM opportunities WHERE source IN ('AI-opp_mining','规则挖掘') ORDER BY confidence DESC, generated_at DESC"
        )
        opps = []
        for r in (ai_opps or []):
            opps.append({
                "opp_id": r["opp_id"],
                "source": "AI挖掘" if r["source"] == "AI-opp_mining" else "规则挖掘",
                "cust_id": r["cust_id"],
                "cust_name": r["cust_name"],
                "type": r["opportunity_type"],
                "estimated_value": r["estimated_value"],
                "confidence": r["confidence"],
                "reasoning": r["reasoning"],
                "status": r["status"],
                "suggested_action": r.get("suggested_action", ""),
                "source_method": r.get("source_method", ""),
                "generated_at": r.get("generated_at", ""),
            })

        # 按客户经理过滤
        if manager_id:
            mgr_cust_ids = set(r["cust_id"] for r in (await aq(
                "SELECT cust_id FROM cust_manager_rel WHERE manager_id = ?", (manager_id,)
            ) or []))
            opps = [o for o in opps if o["cust_id"] in mgr_cust_ids]

        # Phase3: 查询已有的作战包，通过 clues 表建立 opp_id -> bp_id 映射（一个商机可能对应多个作战包，取最新）
        bp_rows = await aq("SELECT bpc.opp_id, bp.bp_id FROM battle_package_clues bpc JOIN battle_packages bp ON bpc.bp_id = bp.bp_id ORDER BY bp.generated_at DESC")
        opp_bp_map = {}
        for r in (bp_rows or []):
            if r["opp_id"] and r["opp_id"] not in opp_bp_map:
                opp_bp_map[r["opp_id"]] = r["bp_id"]
        for o in opps:
            if o["opp_id"] in opp_bp_map:
                o["bp_id"] = opp_bp_map[o["opp_id"]]

        return ok({"opportunities":opps,"summary":{"total_count":len(opps),"total_value":sum(o["estimated_value"] for o in opps),"ai_mined_count":sum(1 for o in opps if o["source"]=="AI挖掘"),"rule_mined_count":sum(1 for o in opps if o["source"]=="规则挖掘")}})

    @app.get("/api/battle-packages")
    async def bp_list(cust_id: int = Query(None), opp_id: str = Query(None), status: str = Query(None)):
        w, p = ["1=1"], []
        if cust_id: w.append("bp.cust_id=?"); p.append(cust_id)
        if opp_id: w.append("bp.opp_id=?"); p.append(opp_id)
        if status: w.append("bp.status=?"); p.append(status)
        rows = await aq(f"SELECT bp.bp_id,bp.opp_id,bp.cust_id,c.name as cn,bp.mode,bp.status,bp.generated_at,bp.expires_at FROM battle_packages bp JOIN customers c ON bp.cust_id=c.id WHERE {' AND '.join(w)} ORDER BY bp.generated_at DESC", p)
        return ok({"packages":[{"bp_id":r["bp_id"],"opp_id":r["opp_id"],"cust_id":r["cust_id"],"cust_name":r["cn"],"mode":r["mode"],"status":r["status"],"generated_at":r["generated_at"],"expires_at":r["expires_at"]} for r in (rows or [])],"total":len(rows or [])})

    @app.get("/api/battle-packages/{bpid}")
    async def bp_detail(bpid: str):
        row = await aq("SELECT bp.*,c.name as cn FROM battle_packages bp JOIN customers c ON bp.cust_id=c.id WHERE bp.bp_id=?", (bpid,), True)
        if not row: raise HTTPException(404)
        clues = await aq("SELECT * FROM battle_package_clues WHERE bp_id=? ORDER BY CASE priority WHEN '高' THEN 1 WHEN '中' THEN 2 ELSE 3 END", (bpid,))
        ov = json.loads(row["customer_overview"]) if isinstance(row["customer_overview"],str) else row["customer_overview"]
        ag = json.loads(row["agenda"]) if row["agenda"] and isinstance(row["agenda"],str) else row["agenda"]
        rw = json.loads(row["risk_warnings"]) if isinstance(row["risk_warnings"],str) else row["risk_warnings"]
        pa = json.loads(row["post_visit_actions"]) if isinstance(row["post_visit_actions"],str) else row["post_visit_actions"]
        # Phase3: care_items / opening_speech (兼容新旧格式)
        care_items_val = row.get("care_items", "[]")
        if isinstance(care_items_val, str):
            try:
                parsed = json.loads(care_items_val)
            except Exception:
                parsed = care_items_val
        else:
            parsed = care_items_val or []
        # 新格式：opening_speech 为字符串；旧格式：care_items 为数组
        if isinstance(parsed, str):
            opening_speech = parsed
            cis = []
        elif isinstance(parsed, list):
            opening_speech = ""
            cis = parsed
        else:
            opening_speech = ""
            cis = []
        ci = []
        for cl in (clues or []):
            p = json.loads(cl["products"]) if isinstance(cl["products"],str) else cl["products"]
            d = json.loads(cl["deviation_branches"]) if cl["deviation_branches"] and isinstance(cl["deviation_branches"],str) else cl["deviation_branches"]
            ci.append({"clue_id":cl["clue_id"],"opp_id":cl.get("opp_id",""),"priority":cl["priority"],"title":cl["title"],"discovery_basis":cl["discovery_basis"],"strategy":cl["strategy"],"opening_script":cl["opening_script"],"products":p,"deviation_branches":d})
        return ok({"bp_id":row["bp_id"],"opp_id":row["opp_id"],"cust_id":row["cust_id"],"cust_name":row["cn"],"mode":row["mode"],"status":row["status"],"task_id":row.get("task_id",""),"customer_overview":ov,"agenda":ag,"care_items":cis,"opening_speech":opening_speech,"clues":ci,"risk_warnings":rw,"post_visit_actions":pa,"generated_at":row["generated_at"],"expires_at":row["expires_at"],"used_at":row.get("used_at")})

    @app.get("/api/battle-packages/{bpid}/clues")
    async def bp_clues(bpid: str):
        rows = await aq("SELECT * FROM battle_package_clues WHERE bp_id=? ORDER BY CASE priority WHEN '高' THEN 1 WHEN '中' THEN 2 ELSE 3 END", (bpid,))
        items = []
        for cl in (rows or []):
            p = json.loads(cl["products"]) if isinstance(cl["products"],str) else cl["products"]
            d = json.loads(cl["deviation_branches"]) if cl["deviation_branches"] and isinstance(cl["deviation_branches"],str) else cl["deviation_branches"]
            items.append({"clue_id":cl["clue_id"],"priority":cl["priority"],"title":cl["title"],"opening_script":cl["opening_script"],"products":p,"deviation_branches":d})
        return ok({"clues":items})

    @app.post("/api/battle-packages/{bpid}/use")
    async def bp_use(bpid: str):
        await ae("UPDATE battle_packages SET status='已使用',used_at=? WHERE bp_id=?", (datetime.now().isoformat(), bpid))
        return ok(message="作战包已标记为使用中")

    @app.get("/api/battle-packages/linked")
    async def bp_linked(opp_ids: str = Query("")):
        """
        Phase3: 查询关联到指定商机的作战包
        GET /api/battle-packages/linked?opp_ids=OPP_001,OPP_002
        Returns: { packages: [{bp_id, opp_id, cust_id, cust_name, status, generated_at}] }
        """
        if not opp_ids.strip():
            return ok({"packages": [], "total": 0})
        ids = [o.strip() for o in opp_ids.split(",") if o.strip()]
        if not ids:
            return ok({"packages": [], "total": 0})
        # 通过 clues 表的 opp_id 字段查询关联作战包
        placeholders = ",".join(["?" for _ in ids])
        rows = await aq(
            f"SELECT DISTINCT bp.bp_id, bp.opp_id, bp.cust_id, c.name as cust_name, bp.mode, bp.status, bp.generated_at "
            f"FROM battle_packages bp "
            f"JOIN battle_package_clues bpc ON bp.bp_id = bpc.bp_id "
            f"JOIN customers c ON bp.cust_id = c.id "
            f"WHERE bpc.opp_id IN ({placeholders}) "
            f"ORDER BY bp.generated_at DESC",
            ids
        )
        return ok({"packages": [dict(r) for r in (rows or [])], "total": len(rows or [])})

    @app.post("/api/battle-packages/generate")
    async def bp_gen(body: dict):
        opp_id = body.get("opp_id",""); parts = opp_id.rsplit("_",1); cid = int(parts[-1]) if parts[-1].isdigit() else 1
        cust = await aq("SELECT name,age,gender,tier,total_aum FROM customers WHERE id=?", (cid,), True)
        if not cust: raise HTTPException(400)
        bpid = f"BP_GEN_{int(datetime.now().timestamp())}"
        ov = json.dumps({"name":cust["name"],"age":cust["age"],"gender":"男" if cust["gender"]=="M" else "女","tier":cust["tier"],"total_aum":cust["total_aum"],"visit_purpose":"商机跟进"}, ensure_ascii=False)
        await ae("INSERT INTO battle_packages (bp_id,opp_id,cust_id,mode,status,customer_overview,risk_warnings,post_visit_actions,generated_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (bpid,opp_id,cid,"面谈版","未使用",ov,'["不得承诺收益"]','["录入沟通记录"]',datetime.now().isoformat(),(TODAY+timedelta(days=7)).isoformat()))
        await ae("INSERT INTO battle_package_clues (clue_id,bp_id,priority,title,discovery_basis,strategy,opening_script,products) VALUES (?,?,?,?,?,?,?,?)",
                  (f"CL{bpid}01",bpid,"中","商机跟进","系统生成","以商机为切入",f"{cust['name']}您好……",'[{"name":"XX稳健理财","type":"理财","risk":"R2","yield":3.5}]'))
        return ok({"bp_id":bpid,"mode":"面谈版","generated_at":datetime.now().isoformat(),"expires_at":(TODAY+timedelta(days=7)).isoformat()})

    # ================================================================
    # 从 DB 初始化全局 ModelAdapter（首次启动从 .env seed 到 model_configs 表）
    # ================================================================
    from agentos.model_adapter import init_adapter_from_db
    adapter = init_adapter_from_db(ae, aq)
    print(f"模型适配器已就绪: provider={adapter.config.provider}, model={adapter.config.model_name}")

    # ================================================================
    # 平台配置：从 DB 加载并覆盖 os.environ（首次从 .env seed）
    # ================================================================
    async def seed_platform_configs():
        """首次启动时将 .env 关键配置写入 DB，之后从 DB 加载覆盖 os.environ"""
        import os as _os
        existing = await aq("SELECT COUNT(*) as cnt FROM platform_configs", one=True)
        if not existing or existing.get("cnt", 0) == 0:
            now = datetime.now().isoformat()
            defaults = [
                ("TUSHARE_TOKEN", _os.getenv("TUSHARE_TOKEN", ""), "金融数据", "Tushare 数据源 Token，用于抓取金融资讯"),
                ("DASHSCOPE_API_KEY", _os.getenv("DASHSCOPE_API_KEY", ""), "向量嵌入", "DashScope 百炼 API Key，用于知识库向量化"),
                ("DASHSCOPE_EMBEDDING_BASE_URL", _os.getenv("DASHSCOPE_EMBEDDING_BASE_URL", ""), "向量嵌入", "DashScope 嵌入服务端点"),
                ("DASHSCOPE_EMBEDDING_MODEL", _os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v3"), "向量嵌入", "嵌入模型名称"),
                ("DASHSCOPE_EMBEDDING_DIM", _os.getenv("DASHSCOPE_EMBEDDING_DIM", "1024"), "向量嵌入", "向量维度"),
                ("CHROMA_PERSIST_DIR", _os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"), "向量存储", "ChromaDB 本地持久化路径"),
                ("ALIBABA_ACCESS_KEY_ID", _os.getenv("ALIBABA_ACCESS_KEY_ID", ""), "语音识别", "阿里云 AccessKey ID"),
                ("ALIBABA_ACCESS_KEY_SECRET", _os.getenv("ALIBABA_ACCESS_KEY_SECRET", ""), "语音识别", "阿里云 AccessKey Secret"),
                ("ALIBABA_NLS_APP_KEY", _os.getenv("ALIBABA_NLS_APP_KEY", ""), "语音识别", "阿里云智能语音交互 AppKey"),
            ]
            for key, val, cat, desc in defaults:
                await ae(
                    "INSERT OR REPLACE INTO platform_configs (config_key, config_value, category, description, updated_at, created_at) VALUES (?,?,?,?,?,?)",
                    (key, val, cat, desc, now, now))
            print(f"Platform configs: 已从 .env seed {len(defaults)} 条配置")

        # 从 DB 加载所有配置并覆盖 os.environ
        rows = await aq("SELECT config_key, config_value FROM platform_configs")
        for r in (rows or []):
            _os.environ[r["config_key"]] = r.get("config_value", "")
        print(f"Platform configs: 已从 DB 加载 {len(rows or [])} 条配置到环境变量")

    # 同步执行
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(seed_platform_configs())
    except RuntimeError:
        asyncio.run(seed_platform_configs())

    def reload_platform_configs_sync():
        """热加载：从 DB 重新读取配置并覆盖 os.environ（供 admin API 调用的同步版本）"""
        import os as _os, sqlite3 as _sq
        db = _sq.connect(DB_PATH)
        db.row_factory = _sq.Row
        rows = db.execute("SELECT config_key, config_value FROM platform_configs").fetchall()
        for r in rows:
            _os.environ[r["config_key"]] = r["config_value"]
        db.close()
        print(f"Platform configs: 热加载 {len(rows)} 条配置")

    # 引入全局 harness（用于 invoke 调用，自动记录运行日志和 token 消耗）
    from agentos.harness import harness as h
    # 设置 DB 回调（同步 ex，用于 _log_run / _log_token）
    h.set_db_callback(ex)
    # 设置技能审计日志回调（客户隐私保护）
    h.set_skill_audit_callback(log_asset_access)
    # 同步 harness 的 adapter 为 DB 初始化后的实例（否则 last_usage 取不到 token）
    h.adapter = adapter

    # ================================================================
    # AI Agent API
    # ================================================================

    # 初始化 OppMiningAgent
    opp_mining_agent = create_opp_mining_agent()
    print(f"AI Agent loaded: {opp_mining_agent.meta.name} (model={opp_mining_agent.adapter.config.model_name})")

    # 初始化 BattlePkgAgent
    battle_pkg_agent = create_battle_pkg_agent()
    print(f"AI Agent loaded: {battle_pkg_agent.meta.name} (model={battle_pkg_agent.adapter.config.model_name})")

    # 初始化 CustomerInsightAgent
    insight_agent = create_customer_insight_agent()
    print(f"AI Agent loaded: {insight_agent.meta.name} (model={insight_agent.adapter.config.model_name})")

    # 初始化 SchedulerAgent
    scheduler_agent = create_scheduler_agent()
    print(f"AI Agent loaded: {scheduler_agent.meta.name} (model={scheduler_agent.adapter.config.model_name})")

    # 初始化 QAAgent
    qa_agent = create_qa_agent()
    print(f"AI Agent loaded: {qa_agent.meta.name} (model={qa_agent.adapter.config.model_name})")

    # 初始化 ContentAgent
    content_agent = create_content_agent()
    print(f"AI Agent loaded: {content_agent.meta.name} (model={content_agent.adapter.config.model_name})")

    # 初始化 RouterAgent（AI 对话路由）
    router_agent = create_router_agent()
    router_agent.set_db_callbacks(aq, ae)
    print(f"AI Agent loaded: {router_agent.meta.name} (model={router_agent.adapter.config.model_name})")

    @app.post("/api/ai/opportunity/mining")
    async def ai_opportunity_mining(body: dict):
        """
        手动触发商机挖掘（客户经理在 APP 点击"AI 挖掘"）

        Request:
          { "manager_id": "M001" }

        Response:
          { "status": "completed"|"no_new_data", "signals": N, "highlights": [...], "message": "..." }
        """
        manager_id = body.get("manager_id", "default")
        ctx = AgentContext(manager_id=manager_id, scope="on_demand")

        # 异步执行挖掘（通过 harness.invoke 自动记录运行日志和 token）
        result = await h.invoke("opportunity_miner", "mine_on_demand", ctx, manager_id=manager_id)

        # 入库商机信号（去重：同一客户同一类型只保留一条活跃商机）
        if result.get("all_signals"):
            now = datetime.now().isoformat()
            ts = int(datetime.now().timestamp())
            inserted = 0
            skipped = 0
            for i, s in enumerate(result["all_signals"]):
                # 去重：类型匹配 或 标题子串重叠≥15字 → 视为重复商机
                if await _check_dup_opp(s["customer_id"], s["opportunity_type"], s.get("title", "")):
                    skipped += 1
                    continue
                opp_id = f"OPP_AI_{s['customer_id']}_{ts}_{i}"
                await ae(
                    """INSERT OR IGNORE INTO opportunities
                       (opp_id, cust_id, cust_name, opportunity_type, title, confidence,
                        estimated_value, reasoning, suggested_action, priority, source,
                        source_method, trigger_signals, generated_at, manager_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (opp_id, s["customer_id"], s["customer_name"], s["opportunity_type"],
                     s["title"], s["confidence"], s["estimated_value"], s["reasoning"],
                     s.get("suggested_action", ""), s["priority"], s["source"],
                     s.get("source_method", ""), json.dumps(s.get("trigger_signals", []), ensure_ascii=False),
                     now, manager_id),
                )
                inserted += 1

            return ok({
                "status": result["status"],
                "total_customers": result["total_customers"],
                "skipped": result.get("skipped", 0) + skipped,
                "signals": inserted,
                "high_confidence": result.get("high_confidence", 0),
                "highlights": result.get("highlights", []),
            })
        else:
            return ok({
                "status": result["status"],
                "message": result.get("message", "未发现新商机"),
                "signals": 0,
            })

    @app.post("/api/ai/opportunity/mining/stream")
    async def ai_opportunity_mining_stream(body: dict):
        """
        SSE 流式商机挖掘：实时推送进度事件

        Request: { "manager_id": "M001" }
        SSE Events:
          event: phase      → {"phase":"start",...}
          event: batch_progress → {"batch":1,"customers":[...],"batch_signals":3,...}
          event: done       → {"status":"completed"|"no_new_data",...}
          event: error      → {"message":"..."}
        """
        manager_id = body.get("manager_id", "default")
        ctx = AgentContext(manager_id=manager_id, scope="on_demand")
        start_ts = int(datetime.now().timestamp())

        async def event_stream():
            queue = asyncio.Queue()

            async def push_event(event_type: str, data: dict):
                await queue.put((event_type, data))

            async def run_mining():
                try:
                    result = await h.invoke(
                        "opportunity_miner", "mine_on_demand",
                        ctx, manager_id=manager_id,
                        progress_callback=push_event,
                    )
                    # 入库商机信号（去重：类型匹配 + 标题前缀匹配）
                    if result.get("all_signals"):
                        now = datetime.now().isoformat()
                        inserted = 0
                        skipped = 0
                        for i, s in enumerate(result["all_signals"]):
                            # 去重：类型匹配 或 标题子串重叠≥15字
                            if await _check_dup_opp(s["customer_id"], s["opportunity_type"], s.get("title", "")):
                                skipped += 1
                                continue
                            opp_id = f"OPP_AI_{s['customer_id']}_{start_ts}_{i}"
                            await ae(
                                """INSERT OR IGNORE INTO opportunities
                                   (opp_id, cust_id, cust_name, opportunity_type, title, confidence,
                                    estimated_value, reasoning, suggested_action, priority, source,
                                    source_method, trigger_signals, generated_at, manager_id)
                                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                                (opp_id, s["customer_id"], s["customer_name"], s["opportunity_type"],
                                 s["title"], s["confidence"], s["estimated_value"], s["reasoning"],
                                 s.get("suggested_action", ""), s["priority"], s["source"],
                                 s.get("source_method", ""), json.dumps(s.get("trigger_signals", []), ensure_ascii=False),
                                 now, manager_id),
                            )
                            inserted += 1
                        log.info(f"SSE mining: inserted={inserted}, skipped={skipped}")
                except Exception as e:
                    log.error(f"SSE mining error: {e}")
                    await queue.put(("error", {"message": f"挖掘异常: {str(e)}"}))

            # 启动后台挖掘任务
            asyncio.create_task(run_mining())

            # 主循环：从队列读取并推送 SSE
            while True:
                try:
                    event_type, data = await asyncio.wait_for(queue.get(), timeout=300)
                    payload = json.dumps(data, ensure_ascii=False)
                    yield f"event: {event_type}\ndata: {payload}\n\n"
                    if event_type in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    yield f"event: error\ndata: {{\"message\":\"挖掘超时，请重试\"}}\n\n"
                    break

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    @app.get("/api/ai/opportunity/list")
    async def ai_opportunity_list(
        manager_id: str = Query(None),
        cust_id: int = Query(None),
        status: str = Query(None),
        limit: int = Query(50),
    ):
        """
        查询已生成的商机列表
        """
        w, p = ["1=1"], []
        if manager_id: w.append("manager_id=?"); p.append(manager_id)
        if cust_id: w.append("cust_id=?"); p.append(cust_id)
        if status: w.append("status=?"); p.append(status)
        p.append(limit)
        rows = await aq(
            f"SELECT * FROM opportunities WHERE {' AND '.join(w)} ORDER BY confidence DESC, generated_at DESC LIMIT ?", p
        )
        items = []
        for r in (rows or []):
            ts = json.loads(r["trigger_signals"]) if r["trigger_signals"] and isinstance(r["trigger_signals"], str) else r["trigger_signals"]
            items.append({
                "opp_id": r["opp_id"], "cust_id": r["cust_id"], "cust_name": r["cust_name"],
                "opportunity_type": r["opportunity_type"], "title": r["title"],
                "confidence": r["confidence"], "estimated_value": r["estimated_value"],
                "reasoning": r["reasoning"], "suggested_action": r["suggested_action"],
                "priority": r["priority"], "source": r["source"], "source_method": r["source_method"],
                "trigger_signals": ts, "status": r["status"], "generated_at": r["generated_at"],
            })
        return ok({"opportunities": items, "total": len(items)})

    @app.get("/api/opportunity/{opp_id}")
    async def opportunity_detail(opp_id: str):
        """
        获取单个商机详情（按 opp_id 精确查询）
        用于日程卡片点击"详情"时展示完整商机信息
        """
        rows = await aq("SELECT * FROM opportunities WHERE opp_id = ?", (opp_id,))
        if not rows:
            return {"code": 404, "data": None, "message": "商机不存在"}
        r = rows[0]
        ts = json.loads(r["trigger_signals"]) if r.get("trigger_signals") and isinstance(r["trigger_signals"], str) else r.get("trigger_signals")
        # Phase3: 查询关联的作战包（通过 battle_package_clues 表）
        bp_row = await aq(
            "SELECT bpc.bp_id FROM battle_package_clues bpc "
            "JOIN battle_packages bp ON bpc.bp_id = bp.bp_id "
            "WHERE bpc.opp_id = ? ORDER BY bp.generated_at DESC LIMIT 1",
            (opp_id,)
        )
        bp_id = bp_row[0]["bp_id"] if bp_row else None
        # 查询关联的面谈记录
        meeting_rows = await aq(
            "SELECT m.id, m.meeting_date, m.meeting_status, m.summary, m.dictation_raw "
            "FROM opp_meeting_rel r JOIN meeting_records m ON r.meeting_id=m.id "
            "WHERE r.opp_id=? ORDER BY m.meeting_date DESC",
            (opp_id,)
        )
        meetings = []
        for m in (meeting_rows or []):
            try:
                d_raw = json.loads(m.get("dictation_raw", "[]") or "[]") if m.get("dictation_raw") else []
            except (json.JSONDecodeError, TypeError):
                d_raw = []
            meetings.append({
                "meeting_id": m["id"],
                "meeting_date": m["meeting_date"],
                "meeting_status": m.get("meeting_status", ""),
                "summary": m.get("summary", "") or "",
                "dictation_count": len(d_raw) if isinstance(d_raw, list) else 0,
            })
        # 查询关联的信号详情（从 customer_signals 表中）
        signal_rows = await aq(
            "SELECT signal_id, signal_type, strategy_tags, priority_weight, signal_data, valid_from, valid_until, consumed_at "
            "FROM customer_signals WHERE consumed_by_opp = ? ORDER BY priority_weight DESC",
            (opp_id,)
        )
        signals = []
        for s in (signal_rows or []):
            try:
                stags = json.loads(s["strategy_tags"]) if isinstance(s["strategy_tags"], str) else (s["strategy_tags"] or [])
            except (json.JSONDecodeError, TypeError):
                stags = []
            try:
                sdata = json.loads(s["signal_data"]) if isinstance(s["signal_data"], str) else (s["signal_data"] or {})
            except (json.JSONDecodeError, TypeError):
                sdata = {}
            signals.append({
                "signal_id": s["signal_id"],
                "signal_type": s["signal_type"],
                "signal_type_label": _signal_type_label(s["signal_type"]),
                "strategy_tags": stags,
                "priority_weight": s["priority_weight"],
                "signal_data": sdata,
                "valid_from": s.get("valid_from", ""),
                "valid_until": s.get("valid_until", ""),
                "consumed_at": s.get("consumed_at", ""),
            })
        return ok({
            "opp_id": r["opp_id"], "cust_id": r["cust_id"], "cust_name": r["cust_name"],
            "opportunity_type": r["opportunity_type"], "title": r["title"],
            "confidence": r["confidence"], "estimated_value": r["estimated_value"],
            "reasoning": r["reasoning"], "suggested_action": r.get("suggested_action", ""),
            "priority": r["priority"], "source": r["source"], "source_method": r.get("source_method", ""),
            "trigger_signals": ts, "status": r["status"],
            "bp_id": bp_id,
            "meetings": meetings,
            "signals": signals,
            "generated_at": r["generated_at"],
        })

    @app.put("/api/opportunity/{opp_id}/status")
    async def opportunity_update_status(opp_id: str, body: dict):
        """
        更新商机状态（含状态流转历史）

        状态流转规则：
          待跟进 → 处理中
          处理中 → 处理中（可多次，表示持续跟进）
          处理中 → 已转化
          处理中 → 已关闭
          已关闭 → 处理中（重新打开）

        Request: { "status": "处理中" | "已转化" | "已关闭" }
        """
        new_status = (body.get("status") or "").strip()
        valid_statuses = ["待跟进", "处理中", "已转化", "已关闭"]
        if new_status not in valid_statuses:
            return {"code": 400, "data": None, "message": f"无效状态，允许: {', '.join(valid_statuses)}"}

        row = await aq("SELECT opp_id, status, status_history FROM opportunities WHERE opp_id = ?", (opp_id,), one=True)
        if not row:
            return {"code": 404, "data": None, "message": "商机不存在"}

        old_status = row.get("status") or "待跟进"

        # 校验状态流转合法性
        allowed_transitions = {
            "待跟进": ["处理中"],
            "处理中": ["处理中", "已转化", "已关闭"],
            "已关闭": ["处理中"],
            "已转化": [],  # 终态，不可再流转
        }
        if new_status not in allowed_transitions.get(old_status, []):
            return {"code": 400, "data": None,
                    "message": f"不允许从「{old_status}」直接流转到「{new_status}」"}

        # 更新状态历史
        try:
            history = json.loads(row.get("status_history") or "[]")
        except (json.JSONDecodeError, TypeError):
            history = []
        history.append({
            "from": old_status,
            "to": new_status,
            "at": datetime.now().isoformat(),
        })

        now = datetime.now().isoformat()
        await ae(
            "UPDATE opportunities SET status = ?, status_history = ?, updated_at = ? WHERE opp_id = ?",
            (new_status, json.dumps(history, ensure_ascii=False), now, opp_id)
        )

        return ok({
            "opp_id": opp_id,
            "old_status": old_status,
            "new_status": new_status,
            "updated_at": now,
        }, f"商机状态已从「{old_status}」更新为「{new_status}」")

    @app.get("/api/ai/agent/health")
    async def ai_agent_health():
        """Agent 健康检查"""
        from agentos.harness import harness
        agents = harness.registry.list_agents()
        return ok({
            "status": "healthy",
            "model": opp_mining_agent.adapter.config.model_name,
            "provider": opp_mining_agent.adapter.config.provider,
            "agents": agents,
        })

    # ================================================================
    # 客户洞察 API
    # ================================================================

    @app.get("/api/customer-insights")
    async def customer_insights_list(
        manager_id: str = Query(None),
        insight_filter: str = Query(None),
    ):
        """
        查询客户洞察列表
        - manager_id: 按客户经理筛选
        - insight_filter: 'change'=有变化信号, 'risk'=有预警信号, 不传=全部
        """
        if insight_filter in ('change', 'risk') and manager_id:
            customers = query_customers_by_insight_filter(manager_id, insight_filter)
            return ok({"customers": customers, "total": len(customers)})
        elif manager_id:
            insights = query_customer_insights_by_manager(manager_id)
            return ok({"insights": insights, "total": len(insights)})
        else:
            return ok({"insights": [], "total": 0})

    @app.get("/api/customer-insights/{cust_id}")
    async def customer_insight_detail(cust_id: int):
        """获取单个客户的最新洞察快照"""
        insight = query_customer_insight(cust_id)
        if not insight:
            return {"code": 404, "data": None, "message": "该客户暂无洞察快照"}
        return ok(insight)

    @app.post("/api/ai/customer-insight/generate")
    async def ai_customer_insight_generate(body: dict):
        """
        手动触发客户洞察生成（按需/批量）

        Request:
          { "cust_id": 1 }      // 单客户生成
          { "scope": "all" }     // 全量生成（管理员操作）
        """
        cust_id = body.get("cust_id")
        scope = body.get("scope", "single")
        manager_id = body.get("manager_id", "")

        ctx = AgentContext(manager_id=manager_id, scope="on_demand")

        if cust_id:
            # 单客户生成（通过 harness.invoke 自动记录运行日志和 token）
            result = await h.invoke("customer_insight", "generate_single", ctx, cust_id=cust_id)
            if result.get("error"):
                return {"code": 500, "data": None, "message": result["error"]}
            # 保存
            insight_agent._save_insight(result, manager_id)
            return ok({
                "cust_id": cust_id,
                "risk_level": result.get("risk_level", "green"),
                "change_count": len(result.get("change_signals", [])),
                "risk_count": len(result.get("risk_signals", [])),
                "overview": result.get("overview"),
            })
        elif scope == "all":
            # 全量批量生成（通过 harness.invoke 自动记录运行日志和 token）
            result = await h.invoke("customer_insight", "batch_generate_all", ctx)
            return ok(result)
        else:
            raise HTTPException(400, "请提供 cust_id 或 scope=all")

    # ================================================================
    # 作战包生成 API
    # ================================================================

    # Phase3: 作战包去重检查（同一客户+任务，7天内已有一个未使用的作战包）
    def check_existing_bp(cust_id: int, task_id: str = "") -> dict | None:
        db = get_db()
        try:
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            if task_id:
                row = db.execute(
                    "SELECT bp_id, status, generated_at FROM battle_packages WHERE cust_id=? AND task_id=? AND status='未使用' AND generated_at>=? ORDER BY generated_at DESC LIMIT 1",
                    (cust_id, task_id, cutoff)
                ).fetchone()
            else:
                row = db.execute(
                    "SELECT bp_id, status, generated_at FROM battle_packages WHERE cust_id=? AND status='未使用' AND generated_at>=? ORDER BY generated_at DESC LIMIT 1",
                    (cust_id, cutoff)
                ).fetchone()
            if row:
                return {"bp_id": row["bp_id"], "status": row["status"], "generated_at": row["generated_at"]}
            return None
        finally:
            db.close()

    @app.post("/api/ai/battle-package/generate")
    async def ai_battle_package_generate(body: dict):
        """
        生成作战包（同步，Phase3：支持多商机+关怀事项）

        Request:
          {
            "cust_id": 1,
            "mode": "标准版",
            "visit_context": {          // 拜访上下文
              "task_id": "TASK_...",     // 客户聚合待办ID
              "opp_ids": ["OPP_..."],    // 待推进商机列表
              "care_items": [{           // 非商机关怀事项
                "type_code": "birthday",
                "type_name": "客户生日",
                "summary": "3天后生日"
              }]
            },
            "force": false               // 是否强制重新生成（跳过去重检查）
          }

        Response:
          {
            "code": 0,
            "data": {
              "bp_id": "BP_AI_...",
              "cust_id": 1,
              "cust_name": "王建国",
              "mode": "标准版",
              "status": "未使用",
              "bp_data": { ... },
              "generated_at": "...",
              "expires_at": "..."
            }
          }
        """
        cust_id = body.get("cust_id")
        mode = body.get("mode", "标准版")
        visit_context = body.get("visit_context") or {}
        force = body.get("force", False)
        task_id = visit_context.get("task_id", "")
        opp_ids = visit_context.get("opp_ids", []) or []

        if not cust_id:
            raise HTTPException(400, "缺少 cust_id")
        if mode != "标准版":
            raise HTTPException(400, "mode 必须为'标准版'")

        # Phase3: 去重检查（非 force 模式下）
        if not force:
            existing = check_existing_bp(cust_id, task_id)
            if existing:
                return {"code": 409, "data": existing, "message": "该客户/任务在7天内已有未使用的作战包，请使用 force=true 强制重新生成"}

        ctx = AgentContext(scope="on_demand")

        # 检查是否有洞察快照，有则注入到作战包中
        insight_data = query_customer_insight(cust_id)
        if insight_data:
            print(f"[BP] 使用已有洞察快照: cust_id={cust_id}, risk={insight_data.get('risk_level', 'green')}")

        # 生成作战包（通过 harness.invoke 自动记录运行日志和 token）
        bp_result = await h.invoke(
            "battle_package_maker", "generate_battle_package",
            ctx, cust_id=cust_id, mode=mode, visit_context=visit_context,
            insight_data=insight_data
        )

        if bp_result.get("status") == "failed":
            return {"code": 500, "data": None, "message": bp_result.get("error", "生成失败")}

        # 保存到数据库（含异常保护：写入失败不应让整个请求 500）
        try:
            saved = battle_pkg_agent.save_battle_package(bp_result, get_db(), task_id=task_id, opp_ids=opp_ids)
        except Exception as save_err:
            import traceback
            print(f"[BP] 保存作战包失败: {save_err}")
            traceback.print_exc()
            return {"code": 500, "data": None, "message": f"作战包已生成但保存失败: {str(save_err)}"}

        return ok({
            **saved,
            "bp_data": bp_result.get("bp_data"),
            "elapsed_s": bp_result.get("elapsed_s"),
        })

    @app.post("/api/ai/battle-package/generate/stream")
    async def ai_battle_package_generate_stream(body: dict):
        """
        SSE 流式生成作战包：实时推送进度事件（Phase3）

        Request: { "cust_id": 1, "mode": "标准版", "visit_context": {...}, "force": false }
        SSE Events:
          event: phase       → {"phase":"loading_data","message":"..."}
          event: phase       → {"phase":"matching_products","customer_name":"..."}
          event: phase       → {"phase":"generating","message":"..."}
          event: done        → {"status":"completed",...}
          event: error       → {"message":"..."}
        """
        cust_id = body.get("cust_id")
        mode = body.get("mode", "标准版")
        visit_context = body.get("visit_context") or {}
        force = body.get("force", False)
        task_id = visit_context.get("task_id", "")
        opp_ids = visit_context.get("opp_ids", []) or []

        if not cust_id:
            raise HTTPException(400, "缺少 cust_id")
        if mode != "标准版":
            raise HTTPException(400, "mode 必须为'标准版'")

        # Phase3: 去重检查（非 force 模式下）
        if not force:
            existing = check_existing_bp(cust_id, task_id)
            if existing:
                async def conflict_stream():
                    yield f"event: error\ndata: {json.dumps({'code': 409, 'message': '该客户/任务在7天内已有未使用的作战包', 'existing': existing}, ensure_ascii=False)}\n\n"
                return StreamingResponse(conflict_stream(), media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})

        ctx = AgentContext(scope="on_demand")

        # 检查是否有洞察快照
        stream_insight_data = query_customer_insight(cust_id)

        async def event_stream():
            queue = asyncio.Queue()

            async def push_event(event_type: str, data: dict):
                await queue.put((event_type, data))

            async def run_generation():
                try:
                    result = await h.invoke(
                        "battle_package_maker", "generate_battle_package",
                        ctx, cust_id=cust_id, mode=mode,
                        visit_context=visit_context,
                        insight_data=stream_insight_data,
                        progress_callback=push_event,
                    )

                    if result.get("status") == "completed":
                        # 保存到数据库（含异常保护）
                        try:
                            saved = battle_pkg_agent.save_battle_package(result, get_db(), task_id=task_id, opp_ids=opp_ids)
                        except Exception as save_err:
                            print(f"[BP-Stream] 保存作战包失败: {save_err}")
                            await queue.put(("error", {"message": f"保存失败: {str(save_err)}"}))
                            return
                        await queue.put(("done", {
                            **saved,
                            "generate_status": "completed",
                            "bp_data": result.get("bp_data"),
                            "elapsed_s": result.get("elapsed_s"),
                        }))
                    else:
                        await queue.put(("error", {
                            "message": result.get("error", "生成失败"),
                        }))
                except Exception as e:
                    log.error(f"SSE battle_package error: {e}")
                    await queue.put(("error", {"message": f"生成异常: {str(e)}"}))

            asyncio.create_task(run_generation())

            while True:
                try:
                    event_type, data = await asyncio.wait_for(queue.get(), timeout=300)
                    payload = json.dumps(data, ensure_ascii=False)
                    yield f"event: {event_type}\ndata: {payload}\n\n"
                    if event_type in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    yield f"event: error\ndata: {{\"message\":\"生成超时，请重试\"}}\n\n"
                    break

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    # ================================================================
    # 智能问答 API (QAAgent)
    # ================================================================

    @app.post("/api/ai/qa/ask")
    async def ai_qa_ask(body: dict):
        """
        智能问答：客户经理在 AI 对话面板输入问题，QAAgent 基于 RAG 知识库检索并解答

        Request:
          { "question": "为什么不能提前还贷款？", "manager_id": "M001" }

        Response:
          { "code": 0, "data": { "answer": "...", "intent": "...", "sources": [...], "matched_rules": [...] } }
        """
        question = body.get("question", "").strip()
        if not question:
            return {"code": 1, "data": None, "message": "请输入您的提问"}

        manager_id = body.get("manager_id", "")
        ctx = AgentContext(manager_id=manager_id, scope="on_demand")

        try:
            result = await h.invoke(
                "qa_assistant", "ask", ctx,
                params={
                    "question": question,
                    "manager_id": manager_id,
                }
            )
            return ok({
                "summary": result.get("summary", ""),
                "answer": result.get("answer", ""),
                "intent": result.get("intent", ""),
                "sources": result.get("sources", []),
                "matched_rules": result.get("matched_rules", []),
                "knowledge_count": result.get("knowledge_count", 0),
                "rules_count": result.get("rules_count", 0),
            })
        except Exception as e:
            log.error(f"QAAgent error: {e}")
            return {"code": 500, "data": None, "message": f"问答处理失败: {str(e)}"}

    # ================================================================
    # 面谈口述转写 API (ContentAgent.transcribe_dictation) v2
    # 支持：首次录音创建记录、追加录音合并摘要
    # ================================================================

    @app.post("/api/ai/dictation/transcribe")
    async def ai_dictation_transcribe(
        audio: UploadFile = File(..., description="语音录音文件 (wav/mp3/m4a)"),
        manager_id: str = Form("M001"),
        cust_name: str = Form(""),
        cust_id: str = Form(""),
        bp_id: str = Form(""),
        opp_id: str = Form(""),
        meeting_id: str = Form(""),
    ):
        """
        面谈口述转写 v2：客户经理面访结束后口述 1-2 分钟，AI 转写提取
        PDCA 结构化信息、客户画像变更、待办事项。

        支持追加录音：传入 meeting_id 后，新转写内容将与已有摘要合并。

        Request: multipart/form-data
          - audio: 音频文件 (必填)
          - manager_id: 客户经理 ID
          - cust_name: 客户姓名
          - cust_id: 客户 ID（可选）
          - bp_id: 关联作战包 ID（可选）
          - opp_id: 关联商机 ID（可选）
          - meeting_id: 已有面谈记录 ID（追加录音时传入）
        """
        # 验证文件类型
        allowed_types = ["audio/wav", "audio/mpeg", "audio/mp4", "audio/x-m4a", "audio/webm",
                         "audio/ogg", "audio/x-wav", "audio/wave"]
        if audio.content_type and audio.content_type not in allowed_types:
            if not audio.content_type.startswith("audio/"):
                return {"code": 1, "data": None, "message": f"不支持的音频格式: {audio.content_type}"}

        # 检查文件大小
        audio_bytes = await audio.read()
        max_size = 10 * 1024 * 1024
        if len(audio_bytes) > max_size:
            return {"code": 1, "data": None, "message": f"音频文件过大（{len(audio_bytes)//1024}KB）"}
        if len(audio_bytes) < 1024:
            return {"code": 1, "data": None, "message": "音频文件过小，可能没有有效录音内容"}

        is_append = bool(meeting_id)
        log.info(f"dictation transcribe: mgr={manager_id}, cust={cust_name or '未知'}, "
                 f"size={len(audio_bytes)//1024}KB, append={is_append}, meeting_id={meeting_id}")

        # 解析 cust_id（追加模式从已有记录获取，首次录音从参数获取）
        cust_id_int = 0
        if cust_id:
            try:
                cust_id_int = int(cust_id)
            except ValueError:
                pass
        if not cust_id_int and cust_name:
            c_row = await aq(
                "SELECT id FROM customers WHERE name=? LIMIT 1", (cust_name,), one=True
            )
            if c_row:
                cust_id_int = c_row["id"]

        ctx = AgentContext(manager_id=manager_id, scope="event")

        # 追加模式：加载已有面谈记录
        existing_summary = ""
        existing_pdc = None
        existing_dictations = []
        if is_append:
            row = await aq("SELECT * FROM meeting_records WHERE id=?", (int(meeting_id),), one=True)
            if not row:
                return {"code": 404, "data": None, "message": f"面谈记录不存在: {meeting_id}"}
            existing_summary = row.get("summary", "") or ""
            existing_pdc = {
                "plan": row.get("plan_result", "") or "",
                "do": row.get("deviation_note", "") or "",
                "check": row.get("customer_feedback", "") or "",
                "act": row.get("action_items", "") or "",
            }
            try:
                existing_dictations = json.loads(row.get("dictation_raw", "[]") or "[]")
            except (json.JSONDecodeError, TypeError):
                existing_dictations = []

        # 查询该客户活跃商机，构建客户级 PDCA 上下文
        cust_context = ""
        if cust_id_int:
            opp_rows = await aq(
                "SELECT opp_id, opportunity_type, title, estimated_value, priority, status "
                "FROM opportunities WHERE cust_id=? AND status IN ('待跟进','已生成作战包') "
                "ORDER BY priority DESC LIMIT 10",
                (cust_id_int,),
            )
            if opp_rows:
                lines = []
                for o in opp_rows:
                    lines.append(
                        f"- [{o['priority']}] {o['opportunity_type']}: {o['title']} "
                        f"(价值≈{o.get('estimated_value', 0)}万, opp_id={o['opp_id']})"
                    )
                cust_context = "\n".join(lines)
                log.info(f"dictation customer context: {len(opp_rows)} active opps for cust_id={cust_id_int}")

        try:
            result = await h.invoke(
                "content_gen", "transcribe_dictation", ctx,
                audio_path="",
                audio_bytes=audio_bytes,
                existing_summary=existing_summary,
                existing_pdc=existing_pdc,
                cust_context=cust_context,
            )

            if result.get("error"):
                return {"code": 500, "data": result, "message": result["error"]}

            transcript = result.get("transcript", "")
            pdc = result.get("pdc", {})
            summary = result.get("summary", "")
            profile_changes = result.get("profile_changes", [])
            todos = result.get("todos", [])
            now_str = datetime.now().isoformat()
            today_str = date.today().isoformat()

            # 构建口述记录条目
            new_dictation = {
                "seq": len(existing_dictations) + 1,
                "transcript": transcript,
                "recorded_at": now_str,
            }
            all_dictations = existing_dictations + [new_dictation]
            dictation_json = json.dumps(all_dictations, ensure_ascii=False)

            if is_append:
                # 追加模式：更新已有记录
                await ae(
                    "UPDATE meeting_records SET "
                    "plan_result=?, deviation_note=?, customer_feedback=?, action_items=?, "
                    "dictation_raw=?, summary=?, profile_changes_json=?, todos_json=?, "
                    "updated_at=? WHERE id=?",
                    (pdc.get("plan", ""), pdc.get("do", ""), pdc.get("check", ""), pdc.get("act", ""),
                     dictation_json, summary, json.dumps(profile_changes, ensure_ascii=False),
                     json.dumps(todos, ensure_ascii=False), now_str, int(meeting_id))
                )
                mid = int(meeting_id)
                log.info(f"Meeting record updated: id={mid}, dictations={len(all_dictations)}")
            else:
                # 首次录音：创建新记录
                db = sqlite3.connect(DB_PATH)
                cursor = db.cursor()
                cursor.execute(
                    "INSERT INTO meeting_records "
                    "(cust_id, cust_name, bp_id, opp_id, manager_id, meeting_date, "
                    "plan_result, deviation_note, customer_feedback, action_items, "
                    "dictation_raw, summary, meeting_status, profile_changes_json, todos_json, "
                    "generated_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (cust_id_int, cust_name, bp_id, opp_id, manager_id, today_str,
                     pdc.get("plan", ""), pdc.get("do", ""), pdc.get("check", ""), pdc.get("act", ""),
                     dictation_json, summary, "completed",
                     json.dumps(profile_changes, ensure_ascii=False),
                     json.dumps(todos, ensure_ascii=False),
                     now_str, now_str)
                )
                mid = cursor.lastrowid
                db.commit()
                db.close()

                # 关联商机：如果提供了 opp_id，写入关联表
                if opp_id:
                    try:
                        db2 = sqlite3.connect(DB_PATH)
                        db2.execute(
                            "INSERT OR IGNORE INTO opp_meeting_rel (opp_id, meeting_id) VALUES (?,?)",
                            (opp_id, mid)
                        )
                        db2.commit()
                        db2.close()
                        log.info(f"Opportunity {opp_id} linked to meeting {mid}")
                    except Exception as e:
                        log.warning(f"Failed to link opportunity to meeting: {e}")

                log.info(f"Meeting record created: id={mid}, cust={cust_name}")

            return ok({
                "meeting_id": mid,
                "transcript": transcript,
                "pdc": pdc,
                "summary": summary,
                "profile_changes": profile_changes,
                "todos": todos,
                "dictation_count": len(all_dictations),
                "is_append": is_append,
            })
        except Exception as e:
            log.error(f"Dictation transcribe error: {e}")
            import traceback
            traceback.print_exc()
            return {"code": 500, "data": None, "message": f"口述转写失败: {str(e)}"}

    # ================================================================
    # 面谈记录查询 API
    # ================================================================

    @app.post("/api/meeting/records")
    async def create_meeting_record(
        manager_id: str = Form("M001"),
        cust_name: str = Form(""),
        cust_id: str = Form(""),
        bp_id: str = Form(""),
        opp_id: str = Form(""),
        opp_ids: str = Form(""),
    ):
        """
        创建待办处理记录（面谈/电话/微信结束时调用）。
        口述转写可后续通过 dictation/transcribe 追加。
        opp_ids 支持逗号分隔的多商机关联（opp_meeting_rel）。
        """
        cust_id_int = 0
        if cust_id:
            try:
                cust_id_int = int(cust_id)
            except ValueError:
                pass
        if not cust_id_int and cust_name:
            c_row = await aq(
                "SELECT id FROM customers WHERE name=? LIMIT 1", (cust_name,), one=True
            )
            if c_row:
                cust_id_int = c_row["id"]

        today_str = date.today().isoformat()
        now_str = datetime.now().isoformat()

        db = sqlite3.connect(DB_PATH)
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO meeting_records "
            "(cust_id, cust_name, bp_id, opp_id, manager_id, meeting_date, "
            "plan_result, deviation_note, customer_feedback, action_items, "
            "dictation_raw, summary, meeting_status, profile_changes_json, todos_json, "
            "generated_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (cust_id_int, cust_name, bp_id, opp_id, manager_id, today_str,
             "", "", "", "",
             "[]", "", "drafting",
             "[]", "[]",
             now_str, now_str)
        )
        mid = cursor.lastrowid
        db.commit()
        db.close()

        # 关联商机（支持单个 opp_id 和逗号分隔的 opp_ids）
        all_opp_ids = []
        if opp_id:
            all_opp_ids.append(opp_id.strip())
        if opp_ids:
            all_opp_ids.extend([oid.strip() for oid in opp_ids.split(",") if oid.strip()])
        # 去重
        all_opp_ids = list(dict.fromkeys(all_opp_ids))

        if all_opp_ids:
            try:
                db2 = sqlite3.connect(DB_PATH)
                for oid in all_opp_ids:
                    db2.execute(
                        "INSERT OR IGNORE INTO opp_meeting_rel (opp_id, meeting_id) VALUES (?,?)",
                        (oid, mid)
                    )
                db2.commit()
                db2.close()
                log.info(f"Meeting {mid} linked to opportunities: {all_opp_ids}")
            except Exception as e:
                log.warning(f"Failed to link meeting to opportunities: {e}")

        log.info(f"Processing record created: id={mid}, cust={cust_name}, opps={all_opp_ids}")
        return ok({"meeting_id": mid, "meeting_status": "drafting", "opp_ids": all_opp_ids})

    @app.get("/api/meeting/records")
    async def get_meeting_records(
        manager_id: str = Query(""),
        cust_name: str = Query(""),
        cust_id: int = Query(0),
        status: str = Query(""),
        page: int = Query(1),
        page_size: int = Query(20),
    ):
        """
        查询面谈记录列表。
        可按客户经理、客户姓名/ID、状态筛选。
        """
        where = []
        params = []
        if manager_id:
            where.append("manager_id=?")
            params.append(manager_id)
        if cust_id:
            where.append("cust_id=?")
            params.append(cust_id)
        if cust_name:
            where.append("cust_name LIKE ?")
            params.append(f"%{cust_name}%")
        if status:
            where.append("meeting_status=?")
            params.append(status)

        where_clause = " AND ".join(where) if where else "1=1"
        offset = (page - 1) * page_size

        rows = await aq(
            f"SELECT id, cust_name, manager_id, meeting_date, meeting_status, "
            f"summary, dictation_raw, generated_at "
            f"FROM meeting_records WHERE {where_clause} "
            f"ORDER BY generated_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        total_row = await aq(
            f"SELECT COUNT(*) as cnt FROM meeting_records WHERE {where_clause}",
            params, one=True
        )
        total = total_row["cnt"] if total_row else 0

        items = []
        for r in rows:
            try:
                d = json.loads(r.get("dictation_raw", "[]") or "[]")
            except (json.JSONDecodeError, TypeError):
                d = []
            items.append({
                "id": r["id"],
                "cust_name": r.get("cust_name", ""),
                "manager_id": r["manager_id"],
                "meeting_date": r["meeting_date"],
                "meeting_status": r.get("meeting_status", "drafting"),
                "summary": r.get("summary", "") or "",
                "dictation_count": len(d),
                "generated_at": r["generated_at"],
            })

        return ok({"items": items, "total": total, "page": page, "page_size": page_size})

    @app.get("/api/meeting/records/{record_id}")
    async def get_meeting_record_detail(record_id: int):
        """
        获取单条面谈记录详情，包含所有口述转写历史。
        """
        row = await aq("SELECT * FROM meeting_records WHERE id=?", (record_id,), one=True)
        if not row:
            return {"code": 404, "data": None, "message": f"面谈记录不存在: {record_id}"}

        try:
            dictations = json.loads(row.get("dictation_raw", "[]") or "[]")
        except (json.JSONDecodeError, TypeError):
            dictations = []
        try:
            profile_changes = json.loads(row.get("profile_changes_json", "[]") or "[]")
        except (json.JSONDecodeError, TypeError):
            profile_changes = []
        try:
            todos = json.loads(row.get("todos_json", "[]") or "[]")
        except (json.JSONDecodeError, TypeError):
            todos = []

        return ok({
            "id": row["id"],
            "cust_id": row["cust_id"],
            "cust_name": row.get("cust_name", ""),
            "bp_id": row.get("bp_id", ""),
            "opp_id": row.get("opp_id", ""),
            "manager_id": row["manager_id"],
            "meeting_date": row["meeting_date"],
            "meeting_status": row.get("meeting_status", "drafting"),
            "pdc": {
                "plan": row.get("plan_result", "") or "",
                "do": row.get("deviation_note", "") or "",
                "check": row.get("customer_feedback", "") or "",
                "act": row.get("action_items", "") or "",
            },
            "summary": row.get("summary", "") or "",
            "profile_changes": profile_changes,
            "todos": todos,
            "dictations": dictations,
            "generated_at": row["generated_at"],
            "updated_at": row.get("updated_at", ""),
        })

    # ================================================================
    # AI 对话路由 API (RouterAgent) — 统一对话入口
    # ================================================================

    @app.post("/api/ai/chat")
    async def ai_chat(body: dict):
        """
        AI 对话统一入口：RouterAgent 意图识别 → 分发 → 响应 + 建议

        Request:
          { "question": "王建国最近怎么样", "manager_id": "M001", "channel": "home" }

        Response:
          { "code": 0, "data": { "type": "...", "content": {...}, "suggestions": [...], "meta": {...} } }
        """
        question = body.get("question", "").strip()
        if not question:
            return {"code": 1, "data": None, "message": "请输入您的问题"}

        manager_id = body.get("manager_id", "")
        channel = body.get("channel", "home")
        history = body.get("history", [])

        ctx = AgentContext(manager_id=manager_id, scope="on_demand")

        try:
            result = await h.invoke(
                "router", "chat", ctx,
                params={
                    "question": question,
                    "manager_id": manager_id,
                    "channel": channel,
                    "history": history,
                }
            )
            return ok(result)
        except Exception as e:
            log.error(f"RouterAgent error: {e}")
            return {"code": 500, "data": None, "message": f"对话处理失败: {str(e)}"}

    # ================================================================
    # 日程管理 API
    # ================================================================

    @app.get("/api/schedule-types")
    async def schedule_types_list():
        """获取工作分类目录"""
        catalog = scheduler_agent.get_catalog()
        return ok({"types": catalog, "total": len(catalog)})

    @app.get("/api/schedule/week")
    async def schedule_week_get(start_date: str = Query(None), manager_id: str = Query(None)):
        """
        获取/生成 7 日周计划

        Query:
            start_date: 周起始日期（YYYY-MM-DD），默认今天
            manager_id: 客户经理 ID，默认 M001
        """
        mid = manager_id or "M001"
        sd = start_date or TODAY.isoformat()

        # 收集全部待办任务
        tasks = query_tasks_for_schedule(mid, sd)

        # 生成 7 日周计划
        weekly = scheduler_agent.generate_weekly_plan(
            tasks, manager_id=mid, start_date=sd
        )

        # 保存 7 天排程到 DB
        for day_schedule in weekly.days:
            scheduler_agent.save_schedule(day_schedule, get_db())

        return ok(weekly.to_dict())

    @app.post("/api/schedule/adjust")
    async def schedule_batch_adjust(body: dict):
        """跨天批量调整（已废弃，请使用 /api/schedule/{date}/adjust）"""
        return {"code": 410, "data": None, "message": "批量调整已下线，请使用单日调整接口"}

    @app.get("/api/schedule/{schedule_date}")
    async def schedule_get(schedule_date: str, manager_id: str = Query(None)):
        """
        获取指定日期的日程排程
        如果 DB 中不存在，则触发规则引擎实时生成
        """
        mid = manager_id or "M001"

        # 尝试从 DB 加载
        schedule = scheduler_agent.load_schedule(mid, schedule_date, get_db())
        if schedule:
            return ok(schedule.to_dict())

        # 不存在则实时生成
        td = date.fromisoformat(schedule_date) if schedule_date else TODAY
        
        # 使用 skill 函数收集全部待办任务（基础待办 + 商机 + 洞察）
        tasks = query_tasks_for_schedule(mid, schedule_date)

        # 构建排程
        schedule = scheduler_agent.generate_daily_schedule(
            tasks, manager_id=mid, schedule_date=schedule_date
        )

        # 保存到 DB
        scheduler_agent.save_schedule(schedule, get_db())

        return ok(schedule.to_dict())

    @app.post("/api/schedule/{schedule_date}/regenerate")
    async def schedule_regenerate(schedule_date: str, body: dict):
        """
        触发 AI 重新排程（LLM 微调）
        """
        mid = body.get("manager_id", "M001")
        use_llm = body.get("use_llm", True)

        # 先确保有基准排程
        schedule = scheduler_agent.load_schedule(mid, schedule_date, get_db())
        if not schedule:
            return {"code": 404, "data": None, "message": "请先生成当日排程"}

        if use_llm:
            ctx = AgentContext(scope="on_demand", manager_id=mid)
            refined = await h.invoke("scheduler", "ai_refine_schedule", ctx, base_schedule=schedule)
            scheduler_agent.save_schedule(refined, get_db())
            return ok(refined.to_dict())
        else:
            # 仅规则引擎重排
            # 需要重新获取任务...此处简化：返回现有排程
            return ok(schedule.to_dict())

    @app.post("/api/schedule/{schedule_date}/adjust")
    async def schedule_adjust(schedule_date: str, body: dict):
        """
        手动调整日程（保存调整后的三卡片结构）

        Request:
          { "manager_id": "M001", "cards": [...] }
        """
        mid = body.get("manager_id", "M001")
        cards_data = body.get("cards", [])

        # 重建三卡片
        from agentos.agents.scheduler import ScheduleCard, DailySchedule
        cards = []
        for cd in cards_data:
            card = ScheduleCard(
                card_type=cd.get("card_type", "customer"),
                card_name=cd.get("card_name", ""),
                morning=scheduler_agent._parse_tasks_from_list(cd.get("morning", [])),
                afternoon=scheduler_agent._parse_tasks_from_list(cd.get("afternoon", [])),
            )
            cards.append(card)

        schedule = DailySchedule(
            date=schedule_date,
            manager_id=mid,
            cards=cards,
            generated_at=datetime.now().isoformat(),
            version=0,
            source="manual",
        )
        scheduler_agent.save_schedule(schedule, get_db())

        return ok(schedule.to_dict())

    @app.get("/api/schedule/{schedule_date}/pending")
    async def schedule_pending(schedule_date: str, manager_id: str = Query(None)):
        """
        获取当日未安排待办列表（deferred + 溢出任务）
        """
        mid = manager_id or "M001"

        schedule = scheduler_agent.load_schedule(mid, schedule_date, get_db())
        if not schedule:
            return ok({"pending": [], "cards_status": []})

        # 返回 deferred_tasks + 各卡片容量状态
        cards_status = []
        for card in schedule.cards:
            cards_status.append({
                "card_type": card.card_type,
                "card_name": card.card_name,
                "total_count": card.total_count,
                "max_capacity": card.max_capacity,
                "can_add": card.total_count < card.max_capacity,
            })

        return ok({
            "pending": [t.to_dict() for t in schedule.deferred_tasks],
            "cards_status": cards_status,
        })

    @app.post("/api/schedule/{schedule_date}/add-task")
    async def schedule_add_task(schedule_date: str, body: dict):
        """
        从未安排待办池手动添加任务到指定卡片（带容量校验）

        Request:
          { "manager_id": "M001", "task_id": "TK_DUE_14", "card_type": "customer" }
        """
        mid = body.get("manager_id", "M001")
        task_id = body.get("task_id", "")
        card_type = body.get("card_type", "customer")

        if not task_id:
            return {"code": 400, "data": None, "message": "缺少 task_id"}

        schedule = scheduler_agent.load_schedule(mid, schedule_date, get_db())
        if not schedule:
            return {"code": 404, "data": None, "message": "未找到当日排程"}

        success, msg = scheduler_agent.add_task_to_card(
            schedule, task_id, card_type, schedule.deferred_tasks
        )

        if success:
            scheduler_agent.save_schedule(schedule, get_db())
            return ok({"message": msg, "schedule": schedule.to_dict()})
        else:
            return {"code": 400, "data": None, "message": msg}

    @app.post("/api/schedule/{schedule_date}/complete")
    async def schedule_complete(schedule_date: str, body: dict):
        """
        标记任务为已完成。完成后不计入容量统计。

        Request:
          { "manager_id": "M001", "task_id": "TK_DUE_14" }
        """
        mid = body.get("manager_id", "M001")
        task_id = body.get("task_id", "")

        if not task_id:
            return {"code": 400, "data": None, "message": "缺少 task_id"}

        schedule = scheduler_agent.load_schedule(mid, schedule_date, get_db())
        if not schedule:
            return {"code": 404, "data": None, "message": "未找到当日排程"}

        found = scheduler_agent.mark_task_complete(schedule, task_id)
        if not found:
            return {"code": 404, "data": None, "message": f"未找到任务: {task_id}"}

        scheduler_agent.save_schedule(schedule, get_db())
        return ok({"message": f"任务 {task_id} 已标记完成", "schedule": schedule.to_dict()})

    @app.post("/api/schedule/{schedule_date}/process-task")
    async def schedule_process_task(schedule_date: str, body: dict):
        """
        记录单个客户的处理方式（电话/微信）。
        不修改日程状态，仅写入 processing_records 表。

        Request:
          { "manager_id": "M001", "task_id": "TK_DUE_14",
            "cust_id": 1, "cust_name": "王建国", "action": "电话联系" }
        """
        mid = body.get("manager_id", "M001")
        task_id = body.get("task_id", "")
        cust_id = body.get("cust_id", 0)
        cust_name = body.get("cust_name", "")
        action = body.get("action", "")

        if not task_id:
            return {"code": 400, "data": None, "message": "缺少 task_id"}
        if action not in ("电话联系", "微信联系", "跳过"):
            return {"code": 400, "data": None, "message": "action 必须为 电话联系/微信联系/跳过"}

        schedule = scheduler_agent.load_schedule(mid, schedule_date, get_db())
        if not schedule:
            return {"code": 404, "data": None, "message": "未找到当日排程"}

        ok_flag = scheduler_agent.process_customer_task(
            schedule, task_id, cust_id, cust_name, action, get_db()
        )
        if not ok_flag:
            return {"code": 404, "data": None, "message": f"未找到任务: {task_id}"}

        return ok({"message": f"已记录 {cust_name} 的处理方式: {action}"})

    @app.post("/api/schedule/{schedule_date}/confirm-complete")
    async def schedule_confirm_complete(schedule_date: str, body: dict):
        """
        确认完成客户综合待办。
        检查待办关联客户是否有面谈记录，如有则标记完成。

        Request:
          { "manager_id": "M001", "task_id": "TK_xxx", "cust_id": 66,
            "cust_name": "曹辉" }

        Response:
          { "completed": true/false, "meeting_records": [...], "message": "..." }
        """
        mid = body.get("manager_id", "M001")
        task_id = body.get("task_id", "")
        cust_id = body.get("cust_id", 0)
        cust_name = body.get("cust_name", "")

        if not task_id:
            return {"code": 400, "data": None, "message": "缺少 task_id"}

        # 检查面谈记录
        db = get_db()
        cur = db.cursor()
        mr_rows = cur.execute(
            "SELECT id, cust_name, meeting_date, meeting_status, summary, dictation_raw, generated_at "
            "FROM meeting_records WHERE cust_id = ? ORDER BY generated_at DESC",
            (cust_id,),
        ).fetchall()

        meeting_records = []
        for r in mr_rows:
            try:
                d = json.loads(r["dictation_raw"] or "[]")
            except (json.JSONDecodeError, TypeError):
                d = []
            meeting_records.append({
                "id": r["id"],
                "cust_name": r["cust_name"],
                "meeting_date": r["meeting_date"],
                "meeting_status": r["meeting_status"],
                "summary": (r["summary"] or "")[:100],
                "dictation_count": len(d),
                "generated_at": r["generated_at"],
            })

        if not meeting_records:
            return {"code": 400, "data": {"completed": False, "meeting_records": []},
                    "message": "该客户暂无面谈记录，无法确认完成。请先进行面谈并记录。"}

        # 标记任务完成
        schedule = scheduler_agent.load_schedule(mid, schedule_date, get_db())
        if not schedule:
            return {"code": 404, "data": None, "message": "未找到当日排程"}

        found = scheduler_agent.mark_task_complete(schedule, task_id)
        if not found:
            return {"code": 404, "data": None, "message": f"未找到任务: {task_id}"}

        scheduler_agent.save_schedule(schedule, get_db())
        return ok({"completed": True, "meeting_records": meeting_records,
                    "message": f"待办已完成", "schedule": schedule.to_dict()})

    @app.post("/api/schedule/{schedule_date}/return-to-pool")
    async def schedule_return_to_pool(schedule_date: str, body: dict):
        """
        将日程卡片上的待办放回未安排待办池。

        Request:
          { "manager_id": "M001", "task_id": "TK_DUE_14" }
        """
        mid = body.get("manager_id", "M001")
        task_id = body.get("task_id", "")

        if not task_id:
            return {"code": 400, "data": None, "message": "缺少 task_id"}

        schedule = scheduler_agent.load_schedule(mid, schedule_date, get_db())
        if not schedule:
            return {"code": 404, "data": None, "message": "未找到当日排程"}

        found = scheduler_agent.return_task_to_pool(schedule, task_id)
        if not found:
            return {"code": 404, "data": None, "message": f"未找到任务: {task_id}"}

        scheduler_agent.save_schedule(schedule, get_db())
        return ok({"message": f"任务 {task_id} 已放回待办池", "schedule": schedule.to_dict()})

    @app.get("/api/schedule/{year}/{month}/events")
    async def schedule_events(year: int, month: int, manager_id: str = Query(None)):
        """
        获取指定月份的日历事件标记
        用于日历视图显示哪些天有待办/商机/报告/会议
        """
        mid = manager_id or "M001"
        events = scheduler_agent.get_month_events(mid, year, month, get_db())
        return ok({"events": events, "year": year, "month": month})

    # ================================================================
    # 定时任务：每日凌晨 0:00 全量日程生成
    # ================================================================

    async def scheduled_data_tick():
        """定时数据日推进（每日 07:30）— 注入当日交易/行为/沟通数据
        
        同一天多次触发时自动跳过（幂等保护），避免重复插入数据。"""
        job_id = "daily_data_tick"
        job_name = "数据日推进"
        started_at = datetime.now().isoformat()
        start_ts = datetime.now()
        today_str = date.today().isoformat()
        print(f"\n[Scheduler] {job_name}启动 @ {started_at}")
        try:
            result = daily_tick(today_str, DB_PATH)
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            tick_status = result.get("status", "error") if isinstance(result, dict) else "error"

            if tick_status == "skipped":
                reason = result.get("reason", "") if isinstance(result, dict) else ""
                summary = f"今天已完成数据推进，无需重复执行"
                detail = json.dumps({
                    "date": today_str,
                    "status": "skipped",
                    "reason": reason,
                    "hint": "每日 07:30 定时自动执行，手动触发前若当天已执行则跳过",
                }, ensure_ascii=False)
                print(f"[Scheduler] {job_name}跳过: {reason}")
                await ae(
                    "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (job_id, job_name, "skipped", summary, detail, "", started_at, datetime.now().isoformat(), duration_ms)
                )
            else:
                stats = result.get("stats", {}) if isinstance(result, dict) else {}
                summary = (
                    f"交易 {stats.get('transactions', 0)} 笔, "
                    f"行为 {stats.get('behaviors', 0)} 条, "
                    f"沟通 {stats.get('communications', 0)} 次, "
                    f"持仓 {stats.get('holding_updates', 0)} 项, "
                    f"事件 {stats.get('events', 0)} 个, "
                    f"产品 {stats.get('product_updates', 0)} 项, "
                    f"公告 {stats.get('announcements', 0)} 条"
                )
                detail = json.dumps({
                    "date": today_str,
                    "transactions": stats.get("transactions", 0),
                    "behaviors": stats.get("behaviors", 0),
                    "communications": stats.get("communications", 0),
                    "holding_updates": stats.get("holding_updates", 0),
                    "events": stats.get("events", 0),
                    "product_updates": stats.get("product_updates", 0),
                    "announcements": stats.get("announcements", 0),
                }, ensure_ascii=False)
                print(f"[Scheduler] {job_name}完成: {summary}")
                await ae(
                    "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (job_id, job_name, "success", summary, detail, "", started_at, datetime.now().isoformat(), duration_ms)
                )
        except Exception as e:
            import traceback
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}失败: {e}")
            traceback.print_exc()
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "error", "", json.dumps({"error": str(e)}, ensure_ascii=False), str(e), started_at, datetime.now().isoformat(), duration_ms)
            )

    async def scheduled_schedule_gen():
        """定时批量日程排程（每日 08:00）— 生成 7 日周计划"""
        job_id = "daily_schedule_gen"
        job_name = "日程排程"
        started_at = datetime.now().isoformat()
        start_ts = datetime.now()
        print(f"\n[Scheduler] {job_name}启动 @ {started_at}")
        sd = date.today().isoformat()
        mgr_count = 0
        mgr_details = []  # 记录每位经理的详情
        try:
            # 获取所有客户经理
            mgr_rows = await aq("SELECT DISTINCT manager_id FROM cust_manager_rel")
            managers = [r["manager_id"] for r in (mgr_rows or [])]
            if not managers:
                managers = ["M001"]
            mgr_count = len(managers)

            for mid in managers:
                # 使用 skill 函数收集全部待办任务
                tasks = query_tasks_for_schedule(mid, sd)
                task_count = len(tasks) if tasks else 0

                if tasks:
                    # 生成 7 日周计划（含 7 天日排程数据）
                    weekly = scheduler_agent.generate_weekly_plan(
                        tasks, manager_id=mid, start_date=sd
                    )
                    # 保存 7 天排程
                    slot_count = 0
                    for day_schedule in weekly.days:
                        scheduler_agent.save_schedule(day_schedule, get_db())
                        slot_count += len(day_schedule.slots) if hasattr(day_schedule, 'slots') else 0
                    mgr_details.append({"manager_id": mid, "task_count": task_count, "slot_count": slot_count})
                else:
                    mgr_details.append({"manager_id": mid, "task_count": 0, "slot_count": 0})

            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            detail = json.dumps({"date": sd, "managers": mgr_details, "manager_count": mgr_count}, ensure_ascii=False)
            print(f"[Scheduler] {job_name}完成: {mgr_count} 位经理")
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "success", f"已为 {mgr_count} 位经理生成日程", detail, "", started_at, datetime.now().isoformat(), duration_ms)
            )
        except Exception as e:
            import traceback
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}失败: {e}")
            traceback.print_exc()
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "error", "", json.dumps({"error": str(e)}, ensure_ascii=False), str(e), started_at, datetime.now().isoformat(), duration_ms)
            )

    async def scheduled_news_fetch():
        """定时金融资讯抓取（每日 08:30）— Tushare/新浪/东方财富"""
        job_id = "daily_news_fetch"
        job_name = "金融资讯抓取"
        started_at = datetime.now().isoformat()
        start_ts = datetime.now()
        today_date = date.today()
        print(f"\n[Scheduler] {job_name}启动 @ {started_at}")
        try:
            result = fetch_daily_news(today_date, DB_PATH)
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            summary = f"抓取 {result['count']} 条资讯 (来源: {result.get('sources', {})})"
            # 查询本次抓取的资讯标题作为详情
            headline_rows = await aq(
                "SELECT title, source, category FROM daily_news WHERE fetched_at=? ORDER BY id DESC LIMIT 50",
                (today_date.isoformat(),)
            )
            headlines = [{"title": r["title"], "source": r["source"], "category": r["category"]} for r in (headline_rows or [])]
            detail = json.dumps({
                "date": today_date.isoformat(),
                "count": result["count"],
                "sources": result.get("sources", {}),
                "headlines": headlines,
            }, ensure_ascii=False)
            print(f"[Scheduler] {job_name}完成: {result['status']}, {result['count']} 条")
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "success" if result["status"] != "error" else "error", summary, detail, "", started_at, datetime.now().isoformat(), duration_ms)
            )
        except Exception as e:
            import traceback
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}失败: {e}")
            traceback.print_exc()
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "error", "", json.dumps({"error": str(e)}, ensure_ascii=False), str(e), started_at, datetime.now().isoformat(), duration_ms)
            )

    async def scheduled_review_gen():
        """定时昨日回顾生成（每日 20:00）— 为全行客户经理生成昨日工作总结"""
        job_id = "daily_review_gen"
        job_name = "昨日回顾生成"
        started_at = datetime.now().isoformat()
        start_ts = datetime.now()
        print(f"\n[Scheduler] {job_name}启动 @ {started_at}")
        try:
            ctx = AgentContext(scope="scheduled")
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            results = await h.invoke("content_gen", "batch_gen_review", ctx, target_date=yesterday)
            success_count = sum(1 for r in results if r.get("saved"))
            mgr_list = []
            for r in results:
                mgr_list.append({
                    "manager_id": r.get("manager_id", ""),
                    "saved": r.get("saved", False),
                    "error": r.get("error", ""),
                })
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            summary = f"已为 {success_count}/{len(results)} 位经理生成昨日回顾"
            detail = json.dumps({
                "date": yesterday,
                "success_count": success_count,
                "total_count": len(results),
                "managers": mgr_list,
            }, ensure_ascii=False)
            print(f"[Scheduler] {job_name}完成: {summary}")
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "success", summary, detail, "", started_at, datetime.now().isoformat(), duration_ms)
            )
        except Exception as e:
            import traceback
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}失败: {e}")
            traceback.print_exc()
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "error", "", json.dumps({"error": str(e)}, ensure_ascii=False), str(e), started_at, datetime.now().isoformat(), duration_ms)
            )

    async def scheduled_digest_gen():
        """定时资讯摘要生成（每日 08:35）— 在新闻抓取后提炼要闻
        若当天无新闻数据，自动先执行一次新闻抓取，确保手动触发时也能产出结果。"""
        job_id = "daily_digest_gen"
        job_name = "资讯摘要生成"
        started_at = datetime.now().isoformat()
        start_ts = datetime.now()
        print(f"\n[Scheduler] {job_name}启动 @ {started_at}")
        try:
            target_date = date.today().isoformat()

            # 检查当天是否有新闻数据，没有则先抓取
            existing = await aq(
                "SELECT COUNT(*) as cnt FROM daily_news WHERE date(fetched_at) = ?",
                (target_date,), one=True
            )
            news_prefetched = False
            if not existing or existing.get("cnt", 0) == 0:
                print(f"[Scheduler] {job_name}: 当天无新闻数据，自动补抓...")
                fetch_daily_news(date.today(), DB_PATH)
                news_prefetched = True

            ctx = AgentContext(scope="scheduled")
            result = await h.invoke("content_gen", "gen_digest", ctx, target_date=target_date)
            headlines = result.get("headlines", [])
            headline_count = len(headlines)
            empty = result.get("empty", False)
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            summary = f"提炼 {headline_count} 条要闻" + ("(数据为空)" if empty else "")
            detail = json.dumps({
                "date": target_date,
                "headline_count": headline_count,
                "headlines": headlines,
                "briefing": result.get("briefing", ""),
                "empty": empty,
                "news_prefetched": news_prefetched,
            }, ensure_ascii=False)
            print(f"[Scheduler] {job_name}完成: {summary}")
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "success", summary, detail, "", started_at, datetime.now().isoformat(), duration_ms)
            )
        except Exception as e:
            import traceback
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}失败: {e}")
            traceback.print_exc()
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "error", "", json.dumps({"error": str(e)}, ensure_ascii=False), str(e), started_at, datetime.now().isoformat(), duration_ms)
            )

    # ================================================================
    # 定时任务配置
    # 注：v2.0 起商机挖掘改为按需触发（经理在商机看板点击"AI 挖掘"），不再定时执行
    # ================================================================
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    scheduler = AsyncIOScheduler()

    async def scheduled_insight_generation():
        """定时批量客户洞察快照生成（每周日 03:00）"""
        job_id = "weekly_insight_gen"
        job_name = "客户洞察刷新"
        started_at = datetime.now().isoformat()
        start_ts = datetime.now()
        print(f"\n[Scheduler] {job_name}启动 @ {started_at}")
        ctx = AgentContext(scope="scheduled")
        try:
            result = await h.invoke("customer_insight", "batch_generate_all", ctx)
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            result_dict = result if isinstance(result, dict) else {}
            summary = f"批量洞察完成" if isinstance(result, dict) else str(result)
            detail = json.dumps({
                "date": date.today().isoformat(),
                "generated_count": result_dict.get("generated", result_dict.get("count", 0)),
                "customers": result_dict.get("customers", []),
            }, ensure_ascii=False)
            print(f"[Scheduler] {job_name}完成: {result}")
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "success", summary, detail, "", started_at, datetime.now().isoformat(), duration_ms)
            )
        except Exception as e:
            import traceback
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}失败: {e}")
            traceback.print_exc()
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "error", "", json.dumps({"error": str(e)}, ensure_ascii=False), str(e), started_at, datetime.now().isoformat(), duration_ms)
            )

    async def audit_daily_report():
        """审计日志日报（每日 08:00）— 统计昨日审计日志概要"""
        job_id = "audit_daily_report"
        job_name = "审计日志日报"
        started_at = datetime.now().isoformat()
        start_ts = datetime.now()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        print(f"\n[Scheduler] {job_name}启动 @ {started_at}")
        try:
            conn = get_db()
            # 昨日总查询次数
            total_row = conn.execute(
                "SELECT COUNT(*) as cnt FROM audit_logs WHERE created_at >= ? AND created_at < ?",
                (yesterday, date.today().isoformat())
            ).fetchone()
            total = total_row[0] if total_row else 0
            # 异常数
            anomaly_row = conn.execute(
                "SELECT COUNT(*) as cnt FROM audit_logs WHERE created_at >= ? AND created_at < ? AND detail LIKE '%⚠%'",
                (yesterday, date.today().isoformat())
            ).fetchone()
            anomaly_count = anomaly_row[0] if anomaly_row else 0
            # 人均查询数
            avg_row = conn.execute(
                "SELECT COUNT(*) as cnt FROM audit_logs WHERE created_at >= ? AND created_at < ? AND operator != ''",
                (yesterday, date.today().isoformat())
            ).fetchone()
            total_with_op = avg_row[0] if avg_row else 0
            op_count_row = conn.execute(
                "SELECT COUNT(DISTINCT operator) as cnt FROM audit_logs WHERE created_at >= ? AND created_at < ? AND operator != ''",
                (yesterday, date.today().isoformat())
            ).fetchone()
            op_count = op_count_row[0] if op_count_row else 1
            avg_per_person = round(total_with_op / op_count, 1) if op_count > 0 else 0
            # 最常被查的 Top 10 客户
            top_custs = conn.execute(
                "SELECT customer_id, COUNT(*) as cnt FROM audit_logs WHERE created_at >= ? AND created_at < ? AND customer_id != '' GROUP BY customer_id ORDER BY cnt DESC LIMIT 10",
                (yesterday, date.today().isoformat())
            ).fetchall()
            top_list = [{"customer_id": r[0], "query_count": r[1]} for r in top_custs]
            conn.close()

            summary = f"昨日查询 {total} 次, 异常 {anomaly_count} 次, 人均 {avg_per_person} 次"
            detail = json.dumps({
                "date": yesterday,
                "total_queries": total,
                "anomaly_count": anomaly_count,
                "avg_per_person": avg_per_person,
                "operator_count": op_count,
                "top_queried_customers": top_list,
            }, ensure_ascii=False)
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}完成: {summary}")
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "success", summary, detail, "", started_at, datetime.now().isoformat(), duration_ms)
            )
        except Exception as e:
            import traceback
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}失败: {e}")
            traceback.print_exc()
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "error", "", json.dumps({"error": str(e)}, ensure_ascii=False), str(e), started_at, datetime.now().isoformat(), duration_ms)
            )

    async def audit_weekly_cleanup():
        """审计日志周清理（每周一 08:00）— 删除6个月前的日志"""
        job_id = "audit_weekly_cleanup"
        job_name = "审计日志周清理"
        started_at = datetime.now().isoformat()
        start_ts = datetime.now()
        print(f"\n[Scheduler] {job_name}启动 @ {started_at}")
        try:
            conn = get_db()
            # 检查总行数
            total_row = conn.execute("SELECT COUNT(*) as cnt FROM audit_logs").fetchone()
            total_rows = total_row[0] if total_row else 0
            # 6 个月前的截止日期
            cutoff_date = (date.today() - timedelta(days=183)).isoformat()
            # 删除 6 个月前的日志
            deleted = conn.execute(
                "DELETE FROM audit_logs WHERE created_at < ?", (cutoff_date,)
            ).rowcount
            conn.commit()
            conn.close()

            alerts = []
            if total_rows > 1000000:
                alerts.append(f"⚠ 审计日志表超过 100 万行（当前 {total_rows:,} 行）")
            summary = f"删除 {deleted} 条6个月前日志, 当前 {total_rows - deleted:,} 行" + (f", {'; '.join(alerts)}" if alerts else "")
            detail = json.dumps({
                "cutoff_date": cutoff_date,
                "total_before": total_rows,
                "deleted": deleted,
                "total_after": total_rows - deleted,
                "alerts": alerts,
            }, ensure_ascii=False)
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}完成: {summary}")
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "success", summary, detail, "", started_at, datetime.now().isoformat(), duration_ms)
            )
        except Exception as e:
            import traceback
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}失败: {e}")
            traceback.print_exc()
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "error", "", json.dumps({"error": str(e)}, ensure_ascii=False), str(e), started_at, datetime.now().isoformat(), duration_ms)
            )

    async def data_anonymization_task():
        """数据匿名化任务（每日 03:00）— 到期客户数据自动匿名化"""
        job_id = "data_anonymization"
        job_name = "到期数据匿名化"
        started_at = datetime.now().isoformat()
        start_ts = datetime.now()
        today_str = date.today().isoformat()
        print(f"\n[Scheduler] {job_name}启动 @ {started_at}")
        try:
            conn = get_db()
            # 查找 data_retain_until 已过期的客户
            expired = conn.execute(
                "SELECT id, name FROM customers WHERE data_retain_until != '' AND data_retain_until < ?",
                (today_str,)
            ).fetchall()
            count = 0
            for row in expired:
                conn.execute(
                    "UPDATE customers SET name='已注销', phone_masked='', id_card_masked='', data_retain_until='' WHERE id=?",
                    (row[0],)
                )
                count += 1
            conn.commit()
            conn.close()
            summary = f"匿名化 {count} 名到期客户数据"
            detail = json.dumps({
                "date": today_str,
                "anonymized_count": count,
                "expired_customers": [{"id": r[0], "name": r[1]} for r in expired],
            }, ensure_ascii=False)
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}完成: {summary}")
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "success", summary, detail, "", started_at, datetime.now().isoformat(), duration_ms)
            )
        except Exception as e:
            import traceback
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}失败: {e}")
            traceback.print_exc()
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, result_detail, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, job_name, "error", "", json.dumps({"error": str(e)}, ensure_ascii=False), str(e), started_at, datetime.now().isoformat(), duration_ms)
            )

    @app.on_event("startup")
    async def start_scheduler():
        scheduler.add_job(scheduled_data_tick, "cron", hour=7, minute=30, id="daily_data_tick")
        scheduler.add_job(scheduled_schedule_gen, "cron", hour=8, minute=0, id="daily_schedule_gen")
        scheduler.add_job(audit_daily_report, "cron", hour=8, minute=0, id="audit_daily_report")
        scheduler.add_job(scheduled_news_fetch, "cron", hour=8, minute=30, id="daily_news_fetch")
        scheduler.add_job(scheduled_digest_gen, "cron", hour=8, minute=35, id="daily_digest_gen")
        scheduler.add_job(scheduled_review_gen, "cron", hour=20, minute=0, id="daily_review_gen")
        scheduler.add_job(scheduled_insight_generation, "cron", day_of_week="sun", hour=3, minute=0, id="weekly_insight_gen")
        scheduler.add_job(audit_weekly_cleanup, "cron", day_of_week="mon", hour=8, minute=0, id="audit_weekly_cleanup")
        scheduler.add_job(data_anonymization_task, "cron", hour=3, minute=0, id="data_anonymization")
        scheduler.start()
        print(f"Scheduler started: data tick @ 07:30, schedule gen @ 08:00, news fetch @ 08:30, digest gen @ 08:35, review gen @ 20:00, insight gen @ Sun 03:00, audit report @ 08:00, audit cleanup @ Mon 08:00, anonymization @ 03:00")

    # ---- Admin API 注册 ----
    from admin_api import register_admin_routes
    # h 已在前面设置为 harness 全局单例，DB 回调已设置
    register_admin_routes(app, scheduler, get_db, aq, ae, h, reload_platform_configs_sync, get_audit_thresholds, reload_audit_thresholds)

    uvicorn.run(app, host="0.0.0.0", port=8008, log_level="info")

if __name__ == "__main__":
    main()
