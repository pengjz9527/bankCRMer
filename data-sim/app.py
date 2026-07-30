"""
易会办 客户洞察 — 全内置运行脚本 (SQLite + FastAPI)
一键启动: python3 app.py
"""
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
from agentos.harness import AgentContext
from agentos.skills import query_customer_insight, query_customer_insights_by_manager, query_customers_by_insight_filter, query_tasks_for_schedule
from data_engine import daily_tick
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')

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
    remaining REAL GENERATED ALWAYS AS (credit_line - used_amount) VIRTUAL,
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
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT NOT NULL UNIQUE, product_name TEXT NOT NULL,
    product_type TEXT NOT NULL, risk_level TEXT,
    yield_rate REAL, min_amount REAL DEFAULT 1,
    manager TEXT, status TEXT DEFAULT '在售'
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
    customer_overview TEXT NOT NULL,  -- JSON
    agenda TEXT, risk_warnings TEXT NOT NULL DEFAULT '[]',
    post_visit_actions TEXT NOT NULL DEFAULT '[]',
    generated_at TEXT NOT NULL, expires_at TEXT NOT NULL, used_at TEXT
);

CREATE TABLE IF NOT EXISTS battle_package_clues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clue_id TEXT NOT NULL UNIQUE, bp_id TEXT REFERENCES battle_packages(bp_id),
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
    operator TEXT DEFAULT 'admin',
    detail TEXT DEFAULT '',
    ip_address TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_al_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_al_created ON audit_logs(created_at);

-- 定时任务执行历史
CREATE TABLE IF NOT EXISTS task_execution_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    job_name TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK(status IN ('success','error')),
    result_summary TEXT DEFAULT '',
    error_msg TEXT DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    duration_ms INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_teh_job ON task_execution_history(job_id);
CREATE INDEX IF NOT EXISTS idx_teh_started ON task_execution_history(started_at);
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

    # 全局产品目录
    pid = 1
    for ptype, items in PRODUCTS.items():
        for name, code in items:
            cur.execute(
                "INSERT INTO product_catalog VALUES (?,?,?,?,?,?,?,?,?)",
                (pid, code, name, ptype,
                 random.choice(RISK_LEVELS[:2]) if ptype in ("存款","保险") else random.choice(RISK_LEVELS[1:4]),
                 round(random.uniform(0.5, 5.5), 4),
                 random.choice([1, 1000, 10000]),
                 random.choice(["徽银","兴银","杭银","南银","平安","博时","易方达"]),
                 "在售"))
            pid += 1

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
                cur.execute("INSERT INTO loans VALUES (?,?,?,?,?,?,?,?,?)",
                            (None, cust_id, prod, credit, used, overdue, rate, start, mat))
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
    for mgr_id, year_targets in mgr_targets.items():
        seasonal = [0.06, 0.07, 0.08, 0.07, 0.08, 0.09, 0.10]
        for m_idx in range(7):
            m_num = m_idx + 1
            month_end = monthrange(2026, m_num)[1]
            snap_date = f"2026-{m_num:02d}-{month_end:02d}"
            is_q_end = (m_num % 3 == 0)
            for kpi_code, year_val in year_targets.items():
                progress = max(0, min(1.1, sum(seasonal[:m_idx+1]) + _rnd.uniform(-0.04, 0.06)))
                actual = round(year_val * progress, 1)
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
    db.commit()

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
    from fastapi import FastAPI, Query, HTTPException, Body
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    app = FastAPI(title="易会办 客户洞察 API", version="1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    pool = ThreadPoolExecutor(max_workers=4)

    def get_db():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
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

    def ok(data=None, message="ok"):
        return {"code": 0, "data": data, "message": message}

    def _d(d):
        return d if d is None else (d.isoformat() if isinstance(d, (date,datetime)) else str(d))

    def _n(row):
        return None if row is None or all(v is None for v in row.values()) else row

    # ---- 26 API endpoints ----
    @app.get("/api/customers")
    async def cust_list(keyword: str = Query(None), tier: str = Query(None), manager_id: str = Query(None), page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)):
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
        return ok({"customers":items,"total":total,"page":page,"size":size})

    @app.get("/api/customers/{cid}/profile")
    async def profile(cid: int):
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
        return ok({"loaded_modules":loaded, "basic":{"name":basic["name"],"age":basic["age"],"gender":"男" if basic["gender"]=="M" else "女","tier":basic["tier"],"employment_status":basic["employment_status"],"occupation":basic["occupation"],"city":basic["city"]},
            "family":{k:fam[k] for k in ["marriage","children","child_count","child_age","child_education","study_abroad_intent","study_abroad_target_country"]} if fam else None,
            "business":{k:biz[k] for k in ["business_name","duration_years","share_ratio","reg_capital","address","scope","verified","verified_source"]} if biz else None,
            "wealth_summary":{"total_aum":wth["total_aum"],"tier":wth["tier"],"wealth_score":None,"yoy_return":None},
            "credit_summary":{"loan_count":credit["cnt"],"overdue_count":0,"rejection_count":0},
            "behavior_summary":{"fin_prefs":[],"risk_result":risk_r["test_result"] if risk_r else None,"liquidity":None},
            "employment_detail":{k:emp[k] for k in ["status","unemployment_benefits","benefit_amount","verified"]} if emp else None})

    @app.get("/api/customers/{cid}/basic")
    async def basic(cid: int):
        r = await aq("SELECT * FROM customers WHERE id=?", (cid,), True)
        if not r: raise HTTPException(404)
        return ok({"id":r["id"],"name":r["name"],"age":r["age"],"gender":"男" if r["gender"]=="M" else "女","tier":r["tier"],"total_aum":r["total_aum"],"phone_masked":r["phone_masked"],"employment_status":r["employment_status"],"occupation":r["occupation"],"industry":r["industry"],"city":r["city"],"education":r["education"]})

    @app.get("/api/customers/{cid}/family")
    async def family(cid: int): r = await aq("SELECT marriage,children,child_count,child_age,child_education,study_abroad_intent,study_abroad_target_country,spouse_has_income FROM family_info WHERE cust_id=?", (cid,), True); return ok(_n(r))
    @app.get("/api/customers/{cid}/employment")
    async def employment(cid: int): r = await aq("SELECT status,unemployment_benefits,benefit_amount,benefit_start_date,benefit_end_date,verified,last_verified_date FROM employment_status WHERE cust_id=?", (cid,), True); return ok(_n(r))
    @app.get("/api/customers/{cid}/business")
    async def business(cid: int): r = await aq("SELECT business_name,duration_years,share_ratio,reg_capital,address,scope,verified,verified_source FROM business_info WHERE cust_id=?", (cid,), True); return ok(_n(r))

    @app.get("/api/customers/{cid}/wealth/summary")
    async def w_summary(cid: int):
        r = await aq("SELECT total_aum,tier FROM customers WHERE id=?", (cid,), True)
        if not r: raise HTTPException(404)
        risk = await aq("SELECT wealth_score,score_time,dimension_asset,dimension_income,dimension_social FROM risk_assessments WHERE cust_id=?", (cid,), True)
        tags = []; hc = (await aq("SELECT COUNT(*) as cnt FROM holdings WHERE cust_id=?", (cid,), True))["cnt"]
        if hc >= 5: tags.append("多元配置")
        if risk and risk.get("wealth_score"):
            tags.append("优质客户" if risk["wealth_score"]>=70 else ("成长客户" if risk["wealth_score"]>=40 else "待培养"))
        return ok({"total_aum":r["total_aum"],"tier":r["tier"],"tier_label":r["tier"],"tags":tags,"wealth_score":risk["wealth_score"] if risk else None,"score_time":_d(risk["score_time"]) if risk else None,"score_dimensions":None})

    @app.get("/api/customers/{cid}/wealth/holdings")
    async def w_holdings(cid: int):
        rows = await aq("SELECT * FROM holdings WHERE cust_id=? ORDER BY amount DESC", (cid,))
        if not rows: return ok(None)
        dist, total = {}, 0; details = []
        for r in rows:
            a = r["amount"]; total += a; dist[r["product_type"]] = dist.get(r["product_type"],0)+a
            details.append({"product_name":r["product_name"],"product_type":r["product_type"],"amount":a,"yield_rate":r["yield_rate"],"risk_level":r["risk_level"],"maturity_date":_d(r["maturity_date"]),"status":r["status"]})
        return ok({"total_scale":total,"distribution":{"deposit":dist.get("存款",0),"wealth_mgmt":dist.get("理财",0),"fund":dist.get("基金",0),"precious_metal":dist.get("贵金属",0)},"details":details})

    @app.get("/api/customers/{cid}/wealth/fund-flow")
    async def w_fundflow(cid: int, months: int = Query(12)):
        since = (TODAY - timedelta(days=months*30)).isoformat()
        rows = await aq("SELECT txn_type,amount,summary FROM transactions WHERE cust_id=? AND txn_date>=?", (cid, since))
        if not rows: return ok(None)
        inflow = sum(r["amount"] for r in rows if r["txn_type"]=="in")
        outflow = sum(r["amount"] for r in rows if r["txn_type"]=="out")
        return ok({"yearly_inflow":round(inflow,2),"yearly_outflow":round(outflow,2),"retention_desc":"资金留存率较高" if inflow>outflow*0.8 else "资金流出现象需关注"})

    @app.get("/api/customers/{cid}/wealth/salary")
    async def w_salary(cid: int):
        since = (TODAY - timedelta(days=210)).isoformat()
        rows = await aq("SELECT txn_date,amount FROM transactions WHERE cust_id=? AND summary='工资' AND txn_date>=? ORDER BY txn_date DESC", (cid, since))
        if not rows: return ok(None)
        amts = [r["amount"] for r in rows]; avg6 = round(sum(amts[:6])/min(6,len(amts)),2)
        return ok({"current_month_amount":amts[0],"avg_6m":avg6,"salary_level":"高收入" if avg6>15000 else ("中等收入" if avg6>8000 else "入门收入")})

    @app.get("/api/customers/{cid}/credit/loans")
    async def c_loans(cid: int):
        rows = await aq("SELECT product_name,credit_line,used_amount,remaining,overdue_count,interest_rate,start_date,maturity_date FROM loans WHERE cust_id=?", (cid,))
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
        获取产品列表（从 product_database.json 读取）
        支持按类型、风险等级、关键词筛选
        """
        # 读取产品数据库
        import json as _json
        prod_db_path = Path(__file__).parent.parent / "prototype" / "data" / "product_database.json"
        if not prod_db_path.exists():
            return ok({"products": [], "total": 0})

        with open(prod_db_path, "r", encoding="utf-8") as f:
            prod_db = _json.load(f)

        all_products = prod_db.get("products", [])

        # 转换为前端预期格式
        def map_product(p: dict) -> dict:
            cat = p.get("category", "")
            icon_map = {"理财": "📊", "基金": "📈", "存款": "🏦", "保险": "🛡️"}
            risk_label_map = {"R1": "低风险", "R2": "中低风险", "R3": "中风险", "R4": "中高风险", "R5": "高风险"}

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
            selling_points = p.get("selling_points", [])
            highlights = " · ".join(selling_points[:3]) if selling_points else ""

            # min_amount 格式
            min_amt = p.get("min_amount", 1) or 1
            if min_amt >= 10000:
                min_unit = "万"
                min_val = min_amt / 10000
            else:
                min_unit = "元"
                min_val = min_amt

            return {
                "id": p.get("product_id", ""),
                "type": cat,
                "name": p.get("short_name", p.get("product_name", "")),
                "full_name": p.get("product_name", ""),
                "icon": icon_map.get(cat, "📋"),
                "risk": p.get("risk_level", "R2"),
                "riskLabel": risk_label_map.get(p.get("risk_level", "R2"), "中低风险"),
                "min": min_val,
                "minUnit": min_unit,
                "term": p.get("term_desc", ""),
                "termType": p.get("sub_category", ""),
                "benchmark": benchmark,
                "histYield": hist_yield,
                "manager": p.get("issuer", p.get("bank_name", "")),
                "scale": "",  # product_database 无此字段
                "investScope": p.get("invest_direction", ""),
                "redeem": p.get("redemption_days", ""),
                "fee": p.get("subscription_fee", "") or "无",
                "highlights": highlights,
                "scenario_tags": p.get("scenario_tags", []),
                "aiFit": 5,  # 默认 AI 推荐分
                "aiReason": "",
                "bank_name": p.get("bank_name", ""),
                "status": p.get("status", "在售"),
            }

        products = [map_product(p) for p in all_products if p.get("status") == "在售"]

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
        """查询 KPI 目标值"""
        w, p = ["t.year=?"], [year]
        if manager_id:
            w.append("t.manager_id=?"); p.append(manager_id)
        if org_id:
            w.append("t.org_id=?"); p.append(org_id)
        if quarter:
            w.append("t.quarter=?"); p.append(quarter)

        rows = await aq(
            f"SELECT t.*, d.kpi_name, d.unit, d.weight, d.icon, d.category, d.sort_order "
            f"FROM kpi_targets t JOIN kpi_definitions d ON t.kpi_code=d.kpi_code "
            f"WHERE {' AND '.join(w)} ORDER BY d.sort_order", p)
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
            tasks.append({"task_id":f"TK_DUE_{r['cust_id']}","type":"产品到期","cust_id":r["cust_id"],"cust_name":r["name"],"summary":f"{r['cnt']}笔产品即将到期, 合计{float(r['total'])/10000:.0f}万","priority":"高","is_opportunity_task":True})
        # 2. 贷款逾期
        overdue = await aq("SELECT l.cust_id,c.name,l.overdue_count FROM loans l JOIN customers c ON l.cust_id=c.id WHERE l.overdue_count>0")
        for r in (overdue or []):
            if mgr_cust_ids and r['cust_id'] not in mgr_cust_ids: continue
            tasks.append({"task_id":f"TK_OD_{r['cust_id']}","type":"贷款逾期","cust_id":r["cust_id"],"cust_name":r["name"],"summary":f"贷款逾期{r['overdue_count']}期, 需跟进","priority":"高","is_opportunity_task":False})
        # 3. 大额异动(昨日)
        big = await aq("SELECT t.cust_id,c.name,t.amount FROM transactions t JOIN customers c ON t.cust_id=c.id WHERE t.txn_date=? AND t.amount>30000 AND t.txn_type='out' ORDER BY t.amount DESC LIMIT 3", (td.isoformat(),))
        for r in (big or []):
            if mgr_cust_ids and r['cust_id'] not in mgr_cust_ids: continue
            tasks.append({"task_id":f"TK_BIG_{r['cust_id']}","type":"大额异动","cust_id":r["cust_id"],"cust_name":r["name"],"summary":f"昨日大额转出{float(r['amount'])/10000:.1f}万","priority":"高","is_opportunity_task":True})
        # 4. 联络超期(>14天未联系)
        old = await aq("SELECT c.id,c.name,MAX(cm.comm_date) as last_date FROM customers c LEFT JOIN communications cm ON c.id=cm.cust_id GROUP BY c.id HAVING MAX(cm.comm_date) IS NULL OR MAX(cm.comm_date) < ? LIMIT 8", ((td-timedelta(days=14)).isoformat(),))
        for r in (old or []):
            if mgr_cust_ids and r['id'] not in mgr_cust_ids: continue
            days = '从未联络' if not r['last_date'] else f"超期{(td - date.fromisoformat(r['last_date'])).days}天"
            tasks.append({"task_id":f"TK_CT_{r['id']}","type":"联络超期","cust_id":r["id"],"cust_name":r["name"],"summary":days,"priority":"中","is_opportunity_task":True})
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
        opps = []
        # 规则匹配: 代发到账
        sal = await aq("SELECT DISTINCT t.cust_id,c.name FROM transactions t JOIN customers c ON t.cust_id=c.id WHERE t.summary='工资' AND t.txn_date>=?", ((TODAY-timedelta(days=7)).isoformat(),))
        for r in (sal or []):
            opps.append({"opp_id":f"OPP_SAL_{r['cust_id']}","source":"规则匹配","cust_id":r["cust_id"],"cust_name":r["name"],"type":"代发到账配置","estimated_value":20000,"confidence":0.75,"reasoning":"近7天有代发工资到账, 可推荐工资理财配置","status":"待跟进"})
        # 规则匹配: 产品到期
        due = await aq("SELECT h.cust_id,c.name,SUM(h.amount) as total FROM holdings h JOIN customers c ON h.cust_id=c.id WHERE h.maturity_date BETWEEN ? AND ? GROUP BY h.cust_id,c.name", (TODAY.isoformat(), (TODAY+timedelta(days=30)).isoformat()))
        for r in (due or []):
            opps.append({"opp_id":f"OPP_DUE_{r['cust_id']}","source":"规则匹配","cust_id":r["cust_id"],"cust_name":r["name"],"type":"产品到期承接","estimated_value":float(r["total"]),"confidence":0.85,"reasoning":f"30天内{float(r['total'])/10000:.0f}万产品到期, 建议提前联系客户做好承接方案","status":"待跟进"})
        # 流失预警: AUM<5万 且 tier 较低
        decline = await aq("SELECT c.id,c.name,c.total_aum FROM customers c WHERE c.total_aum<50000 AND c.tier IN ('千元以下','千元户') ORDER BY c.total_aum ASC LIMIT 5")
        for r in (decline or []):
            opps.append({"opp_id":f"OPP_DEC_{r['id']}","source":"AI挖掘","cust_id":r["id"],"cust_name":r["name"],"type":"流失预警挽回","estimated_value":5000,"confidence":0.55,"reasoning":f"AUM仅{float(r['total_aum'])/10000:.1f}万且持续走低, 近2月无交易, 建议联系了解资金去向","status":"待跟进"})
        # AI挖掘: 有基金浏览行为但无基金持仓
        ai_rows = await aq("SELECT b.cust_id,c.name,COUNT(*) as cnt FROM behavior_logs b JOIN customers c ON b.cust_id=c.id WHERE b.page_type='基金' AND c.id NOT IN (SELECT cust_id FROM holdings WHERE product_type='基金') GROUP BY b.cust_id HAVING COUNT(*)>=5 LIMIT 4")
        for r in (ai_rows or []):
            opps.append({"opp_id":f"OPP_AI_{r['cust_id']}","source":"AI挖掘","cust_id":r["cust_id"],"cust_name":r["name"],"type":"基金购买意向","estimated_value":30000,"confidence":0.65,"reasoning":f"近3月浏览基金{r['cnt']}次但无持仓, 判断有基金配置需求","status":"待跟进"})
        # 手动创建: 模拟客户经理标记的商机
        manual_pool = await aq("SELECT c.id,c.name,c.total_aum FROM customers c WHERE c.total_aum>100000 ORDER BY RANDOM() LIMIT 3")
        for r in (manual_pool or []):
            opps.append({"opp_id":f"OPP_MAN_{r['id']}","source":"手动创建","cust_id":r["id"],"cust_name":r["name"],"type":"大额配置建议","estimated_value":float(r["total_aum"])*0.3,"confidence":0.5,"reasoning":f"客户AUM{float(r['total_aum'])/10000:.0f}万, 资产以存款为主, 建议引导理财配置","status":"待跟进"})

        # AI 智能挖掘: 从 opportunities 表读取已入库的 AI 商机
        ai_opps = await aq(
            "SELECT * FROM opportunities WHERE source='AI-opp_mining' AND status='待跟进' ORDER BY confidence DESC, generated_at DESC LIMIT 10"
        )
        for r in (ai_opps or []):
            opps.append({
                "opp_id": r["opp_id"],
                "source": "AI挖掘",
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

        # 查询已有的作战包，建立 opp_id -> bp_id 映射
        bp_rows = await aq("SELECT bp_id, opp_id FROM battle_packages")
        opp_bp_map = {}
        for r in (bp_rows or []):
            opp_bp_map[r["opp_id"]] = r["bp_id"]
        for o in opps:
            if o["opp_id"] in opp_bp_map:
                o["bp_id"] = opp_bp_map[o["opp_id"]]

        return ok({"opportunities":opps,"summary":{"total_count":len(opps),"total_value":sum(o["estimated_value"] for o in opps),"rule_based_count":sum(1 for o in opps if o["source"]=="规则匹配"),"ai_mined_count":sum(1 for o in opps if o["source"]=="AI挖掘"),"manual_count":sum(1 for o in opps if o["source"]=="手动创建")}})

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
        ci = []
        for cl in (clues or []):
            p = json.loads(cl["products"]) if isinstance(cl["products"],str) else cl["products"]
            d = json.loads(cl["deviation_branches"]) if cl["deviation_branches"] and isinstance(cl["deviation_branches"],str) else cl["deviation_branches"]
            ci.append({"clue_id":cl["clue_id"],"priority":cl["priority"],"title":cl["title"],"discovery_basis":cl["discovery_basis"],"strategy":cl["strategy"],"opening_script":cl["opening_script"],"products":p,"deviation_branches":d})
        return ok({"bp_id":row["bp_id"],"opp_id":row["opp_id"],"cust_id":row["cust_id"],"cust_name":row["cn"],"mode":row["mode"],"status":row["status"],"customer_overview":ov,"agenda":ag,"clues":ci,"risk_warnings":rw,"post_visit_actions":pa,"generated_at":row["generated_at"],"expires_at":row["expires_at"],"used_at":row["used_at"]})

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

    # 引入全局 harness（用于 invoke 调用，自动记录运行日志和 token 消耗）
    from agentos.harness import harness as h
    # 设置 DB 回调（同步 ex，用于 _log_run / _log_token）
    h.set_db_callback(ex)
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

        # 入库商机信号
        if result.get("all_signals"):
            now = datetime.now().isoformat()
            ts = int(datetime.now().timestamp())
            for i, s in enumerate(result["all_signals"]):
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

            return ok({
                "status": result["status"],
                "total_customers": result["total_customers"],
                "skipped": result.get("skipped", 0),
                "signals": result["signals"],
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
                    # 入库商机信号
                    if result.get("all_signals"):
                        now = datetime.now().isoformat()
                        for i, s in enumerate(result["all_signals"]):
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

    @app.post("/api/ai/battle-package/generate")
    async def ai_battle_package_generate(body: dict):
        """
        生成作战包（同步）

        Request:
          {
            "cust_id": 1,
            "mode": "标准版",           // 标准版
            "opportunity_info": {        // 可选：关联的商机信息
              "type": "产品到期承接",
              "title": "定存到期",
              "reasoning": "30天内50万定存到期",
              "estimated_value": 250000,
              "confidence": 0.85
            }
          }

        Response:
          {
            "code": 0,
            "data": {
              "bp_id": "BP_AI_...",
              "cust_id": 1,
              "cust_name": "王建国",
              "mode": "面谈版",
              "status": "未使用",
              "bp_data": { ... },
              "generated_at": "...",
              "expires_at": "..."
            }
          }
        """
        cust_id = body.get("cust_id")
        mode = body.get("mode", "电话版")
        opportunity_info = body.get("opportunity_info")
        opp_id = body.get("opp_id", "")

        if not cust_id:
            raise HTTPException(400, "缺少 cust_id")
        if mode not in ("电话版", "面谈版", "标准版"):
            raise HTTPException(400, "mode 必须为'标准版'")

        ctx = AgentContext(scope="on_demand")

        # 检查是否有洞察快照，有则注入到作战包中
        insight_data = query_customer_insight(cust_id)
        if insight_data:
            print(f"[BP] 使用已有洞察快照: cust_id={cust_id}, risk={insight_data.get('risk_level', 'green')}")

        # 生成作战包（通过 harness.invoke 自动记录运行日志和 token）
        bp_result = await h.invoke(
            "battle_package_maker", "generate_battle_package",
            ctx, cust_id=cust_id, mode=mode, opportunity_info=opportunity_info,
            insight_data=insight_data
        )

        if bp_result.get("status") == "failed":
            return {"code": 500, "data": None, "message": bp_result.get("error", "生成失败")}

        # 保存到数据库（含异常保护：写入失败不应让整个请求 500）
        try:
            saved = battle_pkg_agent.save_battle_package(bp_result, get_db(), opp_id=opp_id)
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
        SSE 流式生成作战包：实时推送进度事件

        Request: { "cust_id": 1, "mode": "面谈版", "opportunity_info": {...} }
        SSE Events:
          event: phase       → {"phase":"loading_data","message":"..."}
          event: phase       → {"phase":"matching_products","customer_name":"..."}
          event: phase       → {"phase":"generating","message":"..."}
          event: done        → {"status":"completed",...}
          event: error       → {"message":"..."}
        """
        cust_id = body.get("cust_id")
        mode = body.get("mode", "电话版")
        opportunity_info = body.get("opportunity_info")
        opp_id = body.get("opp_id", "")

        if not cust_id:
            raise HTTPException(400, "缺少 cust_id")
        if mode not in ("电话版", "面谈版", "标准版"):
            raise HTTPException(400, "mode 必须为'标准版'")

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
                        opportunity_info=opportunity_info,
                        insight_data=stream_insight_data,
                        progress_callback=push_event,
                    )

                    if result.get("status") == "completed":
                        # 保存到数据库（含异常保护）
                        try:
                            saved = battle_pkg_agent.save_battle_package(result, get_db(), opp_id=opp_id)
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
            refined = await scheduler_agent.ai_refine_schedule(ctx, schedule)
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
        """定时数据日推进（每日 07:30）— 注入当日交易/行为/沟通数据"""
        job_id = "daily_data_tick"
        job_name = "数据日推进"
        started_at = datetime.now().isoformat()
        start_ts = datetime.now()
        print(f"\n[Scheduler] {job_name}启动 @ {started_at}")
        try:
            result = daily_tick(TODAY.isoformat(), DB_PATH)
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            summary = str(result.get("stats", result)) if isinstance(result, dict) else str(result)
            print(f"[Scheduler] {job_name}完成: {result}")
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (job_id, job_name, "success", summary, "", started_at, datetime.now().isoformat(), duration_ms)
            )
        except Exception as e:
            import traceback
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}失败: {e}")
            traceback.print_exc()
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (job_id, job_name, "error", "", str(e), started_at, datetime.now().isoformat(), duration_ms)
            )

    async def scheduled_schedule_gen():
        """定时批量日程排程（每日 08:00）— 生成 7 日周计划"""
        job_id = "daily_schedule_gen"
        job_name = "日程排程"
        started_at = datetime.now().isoformat()
        start_ts = datetime.now()
        print(f"\n[Scheduler] {job_name}启动 @ {started_at}")
        sd = TODAY.isoformat()
        mgr_count = 0
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

                if tasks:
                    # 生成 7 日周计划（含 7 天日排程数据）
                    weekly = scheduler_agent.generate_weekly_plan(
                        tasks, manager_id=mid, start_date=sd
                    )
                    # 保存 7 天排程
                    for day_schedule in weekly.days:
                        scheduler_agent.save_schedule(day_schedule, get_db())

            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}完成: {mgr_count} 位经理")
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (job_id, job_name, "success", f"已为 {mgr_count} 位经理生成日程", "", started_at, datetime.now().isoformat(), duration_ms)
            )
        except Exception as e:
            import traceback
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}失败: {e}")
            traceback.print_exc()
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (job_id, job_name, "error", "", str(e), started_at, datetime.now().isoformat(), duration_ms)
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
            summary = f"批量洞察完成" if isinstance(result, dict) else str(result)
            print(f"[Scheduler] {job_name}完成: {result}")
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (job_id, job_name, "success", summary, "", started_at, datetime.now().isoformat(), duration_ms)
            )
        except Exception as e:
            import traceback
            duration_ms = int((datetime.now() - start_ts).total_seconds() * 1000)
            print(f"[Scheduler] {job_name}失败: {e}")
            traceback.print_exc()
            await ae(
                "INSERT INTO task_execution_history (job_id, job_name, status, result_summary, error_msg, started_at, finished_at, duration_ms) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (job_id, job_name, "error", "", str(e), started_at, datetime.now().isoformat(), duration_ms)
            )

    @app.on_event("startup")
    async def start_scheduler():
        scheduler.add_job(scheduled_data_tick, "cron", hour=7, minute=30, id="daily_data_tick")
        scheduler.add_job(scheduled_schedule_gen, "cron", hour=8, minute=0, id="daily_schedule_gen")
        scheduler.add_job(scheduled_insight_generation, "cron", day_of_week="sun", hour=3, minute=0, id="weekly_insight_gen")
        scheduler.start()
        print(f"Scheduler started: data tick @ 07:30, schedule gen @ 08:00, insight gen @ Sun 03:00")

    # ---- Admin API 注册 ----
    from admin_api import register_admin_routes
    # h 已在前面设置为 harness 全局单例，DB 回调已设置
    register_admin_routes(app, scheduler, get_db, aq, ae, h)

    uvicorn.run(app, host="0.0.0.0", port=8008, log_level="info")

if __name__ == "__main__":
    main()
