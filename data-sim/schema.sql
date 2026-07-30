-- 易会办 客户洞察模拟数据集 DDL
-- PostgreSQL 16+

-- ============================================================
-- Domain 1: 客户基础信息
-- ============================================================
CREATE TYPE employment_status_enum AS ENUM ('在职', '无业', '待业', '自由职业', '不确定');
CREATE TYPE customer_tier_enum AS ENUM (
    '千元以下', '千元户', '万元户', '优质', '财富', '高净值', '私钻', '私行'
);

CREATE TABLE customers (
    id              SERIAL PRIMARY KEY,
    cust_no         VARCHAR(20) NOT NULL UNIQUE,       -- 客户号
    name            VARCHAR(30) NOT NULL,
    age             INT NOT NULL,
    gender          CHAR(1) NOT NULL CHECK (gender IN ('M', 'F')),
    occupation      VARCHAR(50),
    industry        VARCHAR(50),
    city            VARCHAR(30),
    education       VARCHAR(20),
    phone_masked    VARCHAR(15),                        -- 脱敏手机号
    tier            customer_tier_enum NOT NULL,
    total_aum       DECIMAL(14,2) NOT NULL DEFAULT 0,  -- 总资产(元)
    employment_status employment_status_enum DEFAULT '在职'
);

-- ============================================================
-- Domain 2: 家庭结构
-- ============================================================
CREATE TYPE child_education_enum AS ENUM (
    '幼儿园', '小学', '初中', '高中', '大学', '研究生', '已毕业', '留学中'
);
CREATE TYPE study_abroad_intent_enum AS ENUM ('无', '有', '已留学');

CREATE TABLE family_info (
    id                      SERIAL PRIMARY KEY,
    cust_id                 INT NOT NULL REFERENCES customers(id),
    marriage                BOOLEAN DEFAULT false,
    children                BOOLEAN DEFAULT false,
    child_count             INT DEFAULT 0,
    child_age               INT,
    child_education         child_education_enum,
    study_abroad_intent     study_abroad_intent_enum DEFAULT '无',
    study_abroad_target_country VARCHAR(30),
    spouse_has_income       BOOLEAN,
    UNIQUE(cust_id)
);

-- ============================================================
-- Domain 3: 经营信息
-- ============================================================
CREATE TABLE business_info (
    id              SERIAL PRIMARY KEY,
    cust_id         INT NOT NULL REFERENCES customers(id),
    business_name   VARCHAR(100),
    duration_years  INT,
    share_ratio     DECIMAL(5,2),
    reg_capital     DECIMAL(14,2),
    address         VARCHAR(100),
    scope           VARCHAR(200),
    continuity      BOOLEAN,                            -- 经营持续性
    verified        BOOLEAN DEFAULT true,                -- 身份是否已确认
    verified_source VARCHAR(50),                        -- 确认来源
    UNIQUE(cust_id)
);

-- ============================================================
-- Domain 4: 就业状态
-- ============================================================
CREATE TABLE employment_status (
    id                      SERIAL PRIMARY KEY,
    cust_id                 INT NOT NULL REFERENCES customers(id),
    status                  employment_status_enum NOT NULL,
    unemployment_benefits   BOOLEAN DEFAULT false,
    benefit_amount          DECIMAL(10,2),
    benefit_start_date      DATE,
    benefit_end_date        DATE,
    verified                BOOLEAN DEFAULT true,
    last_verified_date      DATE,
    UNIQUE(cust_id)
);

-- ============================================================
-- Domain 5: 金融资产持仓
-- ============================================================
CREATE TYPE holding_type_enum AS ENUM ('存款', '理财', '基金', '贵金属', '保险');
CREATE TYPE risk_level_enum AS ENUM ('R1', 'R2', 'R3', 'R4', 'R5');

CREATE TABLE holdings (
    id              SERIAL PRIMARY KEY,
    cust_id         INT NOT NULL REFERENCES customers(id),
    product_type    holding_type_enum NOT NULL,
    product_name    VARCHAR(100) NOT NULL,
    product_code    VARCHAR(30),
    amount          DECIMAL(14,2) NOT NULL,
    yield_rate      DECIMAL(6,4),                       -- 展示收益率
    risk_level      risk_level_enum,
    maturity_date   DATE,                               -- 到期日(定存/理财有效)
    purchase_date   DATE,
    status          VARCHAR(20) DEFAULT '持有中',
    CONSTRAINT chk_holdings_amount CHECK (amount > 0)
);

-- ============================================================
-- Domain 6: 交易流水
-- ============================================================
CREATE TYPE transaction_type_enum AS ENUM ('in', 'out');

CREATE TABLE transactions (
    id              SERIAL PRIMARY KEY,
    cust_id         INT NOT NULL REFERENCES customers(id),
    txn_date        DATE NOT NULL,
    txn_type        transaction_type_enum NOT NULL,
    amount          DECIMAL(14,2) NOT NULL,
    counterparty    VARCHAR(50),
    summary         VARCHAR(200),                       -- 交易摘要(承载语义关键词)
    channel         VARCHAR(20)                         -- 渠道: 网银/手机银行/柜台
);

-- ============================================================
-- Domain 7: 信贷数据
-- ============================================================
CREATE TABLE loans (
    id              SERIAL PRIMARY KEY,
    cust_id         INT NOT NULL REFERENCES customers(id),
    product_name    VARCHAR(100) NOT NULL,
    credit_line     DECIMAL(14,2) NOT NULL,
    used_amount     DECIMAL(14,2) NOT NULL DEFAULT 0,
    remaining       DECIMAL(14,2) GENERATED ALWAYS AS (credit_line - used_amount) STORED,
    overdue_count   INT DEFAULT 0,
    interest_rate   DECIMAL(5,4),
    start_date      DATE,
    maturity_date   DATE
);

CREATE TABLE loan_rejections (
    id              SERIAL PRIMARY KEY,
    cust_id         INT NOT NULL REFERENCES customers(id),
    product_name    VARCHAR(100) NOT NULL,
    reject_reason   VARCHAR(200),
    rejected_date   DATE NOT NULL
);

-- ============================================================
-- Domain 8: 行为日志
-- ============================================================
CREATE TYPE page_type_enum AS ENUM ('理财', '基金', '保险', '存款', '贷款', '信用卡', '客户管理');
CREATE TYPE action_type_enum AS ENUM ('浏览', '搜索', '收藏', '对比', '购买', '赎回', '点击详情');

CREATE TABLE behavior_logs (
    id              SERIAL PRIMARY KEY,
    cust_id         INT NOT NULL REFERENCES customers(id),
    event_date      DATE NOT NULL,
    event_time      TIME,
    channel         VARCHAR(20) NOT NULL,               -- 手机银行/网银/微信
    page_type       page_type_enum NOT NULL,
    action          action_type_enum NOT NULL,
    duration_sec    INT DEFAULT 0,
    product_code    VARCHAR(30),
    product_type    VARCHAR(30)
);

-- ============================================================
-- Domain 9: 客户关系
-- ============================================================
CREATE TYPE relation_type_enum AS ENUM (
    '同企业代发', '亲属', '资金往来', '担保', '同客户经理'
);

CREATE TABLE customer_relations (
    id              SERIAL PRIMARY KEY,
    cust_id_a       INT NOT NULL REFERENCES customers(id),
    cust_id_b       INT NOT NULL REFERENCES customers(id),
    relation_type   relation_type_enum NOT NULL,
    evidence        VARCHAR(200),                       -- 发现依据
    evidence_field  VARCHAR(100),                       -- 依据来源字段
    CONSTRAINT chk_no_self_relation CHECK (cust_id_a <> cust_id_b)
);

-- ============================================================
-- Domain 9b: 管户关系 (客户经理 ↔ 客户)
-- ============================================================
CREATE TABLE cust_manager_rel (
    id              SERIAL PRIMARY KEY,
    cust_id         INT NOT NULL REFERENCES customers(id),
    manager_id      VARCHAR(20) NOT NULL,
    manager_name    VARCHAR(50) NOT NULL,
    assigned_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    is_primary      BOOLEAN DEFAULT TRUE,               -- TRUE=主客户经理
    CONSTRAINT uq_cust_manager UNIQUE (cust_id, manager_id)
);
CREATE INDEX idx_cmr_cust ON cust_manager_rel (cust_id);
CREATE INDEX idx_cmr_mgr ON cust_manager_rel (manager_id);

-- ============================================================
-- Domain 10: 沟通记录
-- ============================================================
CREATE TYPE comm_channel_enum AS ENUM ('电话', '面谈', '微信', '短信', '手机银行消息');

CREATE TABLE communications (
    id              SERIAL PRIMARY KEY,
    cust_id         INT NOT NULL REFERENCES customers(id),
    comm_date       DATE NOT NULL,
    comm_time       TIME,
    channel         comm_channel_enum NOT NULL,
    duration_min    INT,
    summary         TEXT NOT NULL,                      -- 沟通摘要
    key_topics      VARCHAR(200)                        -- 关键话题(逗号分隔)
);

-- ============================================================
-- Domain 11: 风测与财富分
-- ============================================================
CREATE TABLE risk_assessments (
    id              SERIAL PRIMARY KEY,
    cust_id         INT NOT NULL REFERENCES customers(id),
    test_result     VARCHAR(20) NOT NULL,               -- 稳健型/进取型/保守型等
    valid_until     DATE,
    tested_date     DATE NOT NULL,
    wealth_score    INT,                                -- 财富分(0-100)
    score_time      DATE,
    dimension_asset DECIMAL(5,2),                       -- 资产配置维度分
    dimension_income DECIMAL(5,2),                      -- 收入稳定性维度分
    dimension_social DECIMAL(5,2),                      -- 社会身份与资源维度分
    UNIQUE(cust_id)
);

-- ============================================================
-- Domain 12: 产品目录(全局)
-- ============================================================
CREATE TYPE product_catalog_type_enum AS ENUM ('存款', '理财', '基金', '保险', '贵金属');

CREATE TABLE product_catalog (
    id              SERIAL PRIMARY KEY,
    product_code    VARCHAR(30) NOT NULL UNIQUE,
    product_name    VARCHAR(100) NOT NULL,
    product_type    product_catalog_type_enum NOT NULL,
    risk_level      risk_level_enum,
    yield_rate      DECIMAL(6,4),
    min_amount      DECIMAL(14,2) DEFAULT 1,
    manager         VARCHAR(50),                        -- 管理机构/基金公司
    status          VARCHAR(20) DEFAULT '在售'
);

-- ============================================================
-- Domain 13: 客户权益
-- ============================================================
CREATE TYPE benefit_type_enum AS ENUM ('出行', '健康', '购物', '教育', '美食', '其他');
CREATE TYPE benefit_rarity_enum AS ENUM ('普通', '稀有', '限时');
CREATE TYPE benefit_status_enum AS ENUM ('有效', '已使用', '已过期');

CREATE TABLE customer_benefits (
    id              SERIAL PRIMARY KEY,
    cust_id         INT NOT NULL REFERENCES customers(id),
    benefit_name    VARCHAR(100) NOT NULL,
    benefit_type    benefit_type_enum NOT NULL,
    description     VARCHAR(200),
    tier_requirement customer_tier_enum,
    rarity          benefit_rarity_enum DEFAULT '普通',
    acquired_date   DATE NOT NULL,
    expiry_date     DATE,
    status          benefit_status_enum DEFAULT '有效'
);

-- ============================================================
-- Domain 14: 营销活动
-- ============================================================
CREATE TYPE activity_type_enum AS ENUM ('理财', '基金', '保险', '存款', '信用卡', '综合');
CREATE TYPE participation_status_enum AS ENUM ('已参与', '已报名', '已完成', '已放弃');

CREATE TABLE available_activities (
    id              SERIAL PRIMARY KEY,
    activity_id     VARCHAR(30) NOT NULL UNIQUE,
    title           VARCHAR(100) NOT NULL,
    type            activity_type_enum NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    description     VARCHAR(300),
    target_tier     customer_tier_enum,
    reward_desc     VARCHAR(200)
);

CREATE TABLE customer_activity_participation (
    id                  SERIAL PRIMARY KEY,
    cust_id             INT NOT NULL REFERENCES customers(id),
    activity_id         VARCHAR(30) NOT NULL REFERENCES available_activities(activity_id),
    participated_date   DATE NOT NULL,
    status              participation_status_enum DEFAULT '已参与',
    result_note         VARCHAR(200)
);

-- ============================================================
-- Domain 15: 作战包
-- ============================================================
CREATE TYPE bp_mode_enum AS ENUM ('电话版', '面谈版');
CREATE TYPE bp_status_enum AS ENUM ('未使用', '已使用', '已过期');

CREATE TABLE battle_packages (
    id                  SERIAL PRIMARY KEY,
    bp_id               VARCHAR(30) NOT NULL UNIQUE,
    opp_id              VARCHAR(30) NOT NULL,           -- 关联商机ID
    cust_id             INT NOT NULL REFERENCES customers(id),
    mode                bp_mode_enum NOT NULL,
    status              bp_status_enum DEFAULT '未使用',
    customer_overview   JSONB NOT NULL,                 -- 客户速览
    agenda              JSONB,                          -- 面谈议程(仅面谈版)
    risk_warnings       TEXT[] NOT NULL DEFAULT '{}',   -- 风险提示列表
    post_visit_actions  TEXT[] NOT NULL DEFAULT '{}',   -- 后续行动建议
    generated_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at          DATE NOT NULL,                  -- generated_at + 7天
    used_at             TIMESTAMP
);

-- ============================================================
-- Domain 16: 作战包线索
-- ============================================================
CREATE TYPE clue_priority_enum AS ENUM ('高', '中', '常规');

CREATE TABLE battle_package_clues (
    id                  SERIAL PRIMARY KEY,
    clue_id             VARCHAR(30) NOT NULL UNIQUE,
    bp_id               VARCHAR(30) NOT NULL REFERENCES battle_packages(bp_id),
    priority            clue_priority_enum NOT NULL,
    title               VARCHAR(100) NOT NULL,
    discovery_basis     TEXT NOT NULL,
    strategy            TEXT NOT NULL,
    opening_script      TEXT NOT NULL,
    products            JSONB NOT NULL DEFAULT '[]',    -- 推荐产品列表
    deviation_branches  JSONB                           -- 偏离预制分支(仅面谈版)
);

-- ============================================================
-- 索引
-- ============================================================
CREATE INDEX idx_customers_tier ON customers(tier);
CREATE INDEX idx_customers_city ON customers(city);
CREATE INDEX idx_holdings_cust ON holdings(cust_id);
CREATE INDEX idx_holdings_maturity ON holdings(maturity_date);
CREATE INDEX idx_transactions_cust ON transactions(cust_id);
CREATE INDEX idx_transactions_date ON transactions(txn_date);
CREATE INDEX idx_transactions_type ON transactions(txn_type);
CREATE INDEX idx_behavior_cust ON behavior_logs(cust_id);
CREATE INDEX idx_behavior_date ON behavior_logs(event_date);
CREATE INDEX idx_relations_a ON customer_relations(cust_id_a);
CREATE INDEX idx_relations_b ON customer_relations(cust_id_b);
CREATE INDEX idx_comm_cust ON communications(cust_id);
CREATE INDEX idx_bp_cust ON battle_packages(cust_id);
CREATE INDEX idx_bp_status ON battle_packages(status);
CREATE INDEX idx_bp_clues_bpid ON battle_package_clues(bp_id);
CREATE INDEX idx_benefits_cust ON customer_benefits(cust_id);
CREATE INDEX idx_activity_part_cust ON customer_activity_participation(cust_id);

-- ============================================================
-- ContentAgent 数据基础设施
-- ============================================================

-- 昨日回顾存储
CREATE TABLE daily_reviews (
    id              SERIAL PRIMARY KEY,
    manager_id      VARCHAR(20) NOT NULL,
    review_date     DATE NOT NULL,
    content         TEXT NOT NULL,
    generated_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    is_read         BOOLEAN DEFAULT FALSE,
    CONSTRAINT uq_daily_review UNIQUE (manager_id, review_date)
);
CREATE INDEX idx_dr_mgr_date ON daily_reviews(manager_id, review_date);

-- 金融资讯缓存
CREATE TYPE news_source_enum AS ENUM ('tushare', 'sina', 'eastmoney', 'manual');
CREATE TYPE news_category_enum AS ENUM ('finance', 'product', 'policy', 'bank');

CREATE TABLE daily_news (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(300) NOT NULL,
    content         TEXT,
    source          news_source_enum NOT NULL DEFAULT 'tushare',
    category        news_category_enum NOT NULL DEFAULT 'finance',
    news_url        VARCHAR(500),
    fetched_at      DATE NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_dn_fetch_date ON daily_news(fetched_at);
CREATE INDEX idx_dn_category ON daily_news(category);

-- 面谈记录 + PDCA
CREATE TABLE meeting_records (
    id              SERIAL PRIMARY KEY,
    cust_id         INT NOT NULL REFERENCES customers(id),
    bp_id           VARCHAR(30),
    opp_id          VARCHAR(30),
    manager_id      VARCHAR(20) NOT NULL,
    meeting_date    DATE NOT NULL,
    plan_result     TEXT,       -- P：面谈目的达成情况
    deviation_note  TEXT,       -- D：执行偏离记录
    customer_feedback TEXT,     -- C：客户反馈
    action_items    TEXT,       -- A：后续行动项
    dictation_raw   TEXT,       -- 原始口述文本
    generated_at    TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_mr_cust ON meeting_records(cust_id);
CREATE INDEX idx_mr_mgr_date ON meeting_records(manager_id, meeting_date);

-- 画像变更追踪
CREATE TABLE profile_change_log (
    id              SERIAL PRIMARY KEY,
    cust_id         INT NOT NULL REFERENCES customers(id),
    field_name      VARCHAR(50) NOT NULL,
    old_value       TEXT,
    new_value       TEXT,
    source          VARCHAR(30) DEFAULT 'dictation',
    meeting_id      INT REFERENCES meeting_records(id),
    changed_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_pcl_cust_time ON profile_change_log(cust_id, changed_at);

-- 行内公告/活动
CREATE TYPE ann_type_enum AS ENUM ('system', 'product', 'compliance', 'marketing');
CREATE TYPE ann_priority_enum AS ENUM ('urgent', 'high', 'normal', 'low');

CREATE TABLE internal_announcements (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    content         TEXT,
    ann_type        ann_type_enum NOT NULL,
    priority        ann_priority_enum DEFAULT 'normal',
    published_at    DATE NOT NULL,
    expires_at      DATE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_ia_pub_date ON internal_announcements(published_at);

-- 产品变更日志
CREATE TYPE product_change_type_enum AS ENUM ('new_product', 'yield_change', 'rate_change', 'status_change', 'min_amount_change');

CREATE TABLE product_updates (
    id              SERIAL PRIMARY KEY,
    product_code    VARCHAR(30) NOT NULL,
    change_type     product_change_type_enum NOT NULL,
    old_value       TEXT,
    new_value       TEXT,
    changed_at      DATE NOT NULL
);
CREATE INDEX idx_pu_date ON product_updates(changed_at);

