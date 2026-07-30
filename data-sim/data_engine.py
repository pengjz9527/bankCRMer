"""
数据日推进引擎 (Data Daily Engine)
=====================================
每日增量生成交易/行为/沟通数据，模拟真实银行客户的日常金融活动。

设计原则：
- 增量追加 (INSERT ONLY)：不修改历史数据，AI 产出数据不受影响
- 幂等保障：同一天执行多次不会重复插入
- 画像驱动：基于客户静态属性（等级/AUM/职业/年龄）差异化行为模式
- 时间窗轮转：Agent 查询的 180 天窗口自然滚动，旧数据自动退出
- 信号注入：低概率触发大额异动、他行转账、职业变动等关键事件

调度集成：
  data-sim/app.py → scheduled_data_tick() → daily at 07:30
  (在 daily_schedule_gen 08:00 之前，确保 Agent 能检测到"昨日"新数据)
"""

import sqlite3
import random
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional


# ============================================================
# 全局配置
# ============================================================
DEFAULT_DB_PATH = str(Path(__file__).parent / "yihuiban_sim.db")

# 产品代码池（按页面类型，用于行为日志 product_code 字段）
PRODUCT_CODES = {
    "理财": ["W001", "W002", "W003", "W004", "W005"],
    "基金": ["F001", "F002", "F003", "F004"],
    "存款": ["C001", "C002", "C003", "C004"],
    "保险": ["I001", "I002"],
    "贵金属": ["G001", "G002"],
    "贷款": ["L001", "L002"],
    "信用卡": ["CC001", "CC002"],
}

# 薪资范围（等级 → 月薪区间元）
SALARY_RANGES = {
    "千元以下": (800, 5000),
    "千元户": (3000, 8000),
    "万元户": (5000, 15000),
    "优质": (8000, 25000),
    "财富": (15000, 40000),
    "高净值": (25000, 60000),
    "私钻": (40000, 100000),
    "私行": (60000, 200000),
}

# 等级 → 日活概率映射
TIER_ACTIVE_MAP = {
    "千元以下": 0.25,
    "千元户": 0.22,
    "万元户": 0.18,
    "优质": 0.15,
    "财富": 0.12,
    "高净值": 0.10,
    "私钻": 0.08,
    "私行": 0.06,
}

# 等级 → 月交易频率
def txn_per_month_from_aum(aum: float) -> int:
    if aum > 5_000_000:
        return 2
    elif aum > 1_000_000:
        return 3
    elif aum > 200_000:
        return 5
    elif aum > 50_000:
        return 8
    return 12


# ============================================================
# 辅助函数
# ============================================================

def _weighted_choice(weights: dict):
    """按权重随机选择 key"""
    items = list(weights.keys())
    probs = list(weights.values())
    total = sum(probs)
    r = random.random() * total
    cumulative = 0.0
    for item, prob in zip(items, probs):
        cumulative += prob
        if r <= cumulative:
            return item
    return items[-1]


def _poisson_sample(lam: float, max_k: int = 5) -> int:
    """泊松分布采样（每日事件数）"""
    import math
    r = random.random()
    cumulative = 0.0
    for k in range(max_k + 1):
        cumulative += (lam ** k) * math.exp(-lam) / math.factorial(k)
        if r <= cumulative:
            return k
    return max_k


# ============================================================
# 客户画像推导
# ============================================================

def derive_profile(cust: dict) -> dict:
    """
    从客户静态属性推导日活参数。

    不依赖原始模板（templates.py 中的 ALL_TEMPLATES 映射关系），
    纯基于 customers 表中的已存储字段推断。
    """
    tier = cust["tier"]
    aum = float(cust["total_aum"])
    emp = cust["employment_status"]
    occ = cust.get("occupation", "") or ""
    age = cust["age"]

    # -- 1. 日活概率 --
    active_prob = TIER_ACTIVE_MAP.get(tier, 0.15)
    if emp in ("无业", "待业"):
        active_prob *= 0.4
    elif emp == "自由职业":
        active_prob *= 0.8

    # -- 2. 月交易频率 --
    monthly_txn = txn_per_month_from_aum(aum)
    if emp in ("无业", "待业"):
        monthly_txn = max(2, monthly_txn - 3)

    # -- 3. 行为偏好 --
    bias = _derive_behavior_bias(occ, age, tier, emp)

    # -- 4. 行为日活概率 --
    behavior_prob = 0.05 * (active_prob / 0.15)

    # -- 5. 薪资判定 --
    salary_occ_set = {
        "工程师", "教师", "公务员", "销售经理", "会计", "IT项目经理",
        "医生", "护士", "企业中层", "银行职员",
    }
    is_salary = emp == "在职" and occ in salary_occ_set
    salary_day = random.randint(8, 12) if is_salary else None

    # -- 6. 周末判定 --
    is_weekend = date.today().weekday() >= 5

    return {
        "daily_active_prob": active_prob,
        "txn_per_month": monthly_txn,
        "behavior_bias": bias,
        "behavior_daily_prob": behavior_prob,
        "is_salary_worker": is_salary,
        "salary_day": salary_day,
        "is_weekend": is_weekend,
        "aum": aum,
        "tier": tier,
        "emp": emp,
        "occ": occ,
        "age": age,
    }


def _derive_behavior_bias(occ: str, age: int, tier: str, emp: str) -> dict:
    """从职业/年龄/等级推导页面浏览偏好"""
    # 基准分布
    bias = {"理财": 0.30, "基金": 0.20, "存款": 0.25, "保险": 0.10, "贷款": 0.10, "信用卡": 0.05}

    # 职业调整
    finance_occ = {"销售经理", "企业中层", "银行职员", "咨询顾问"}
    tech_occ = {"工程师", "IT项目经理", "设计师"}
    stable_occ = {"教师", "公务员", "会计"}
    medical_occ = {"医生", "护士"}
    freelance_occ = {"自媒体", "自由撰稿人", "摄影师"}

    if occ in finance_occ:
        bias = {"理财": 0.35, "基金": 0.25, "存款": 0.20, "保险": 0.10, "贷款": 0.05, "信用卡": 0.05}
    elif occ in tech_occ:
        bias = {"理财": 0.20, "基金": 0.35, "存款": 0.15, "保险": 0.05, "贷款": 0.15, "信用卡": 0.10}
    elif occ in stable_occ:
        bias = {"理财": 0.25, "基金": 0.15, "存款": 0.35, "保险": 0.15, "贷款": 0.05, "信用卡": 0.05}
    elif occ in medical_occ:
        bias = {"理财": 0.25, "基金": 0.20, "存款": 0.20, "保险": 0.20, "贷款": 0.10, "信用卡": 0.05}
    elif occ in freelance_occ:
        bias = {"理财": 0.30, "基金": 0.25, "存款": 0.15, "保险": 0.10, "贷款": 0.10, "信用卡": 0.10}
    elif emp in ("无业", "待业"):
        bias = {"理财": 0.20, "基金": 0.10, "存款": 0.40, "保险": 0.05, "贷款": 0.20, "信用卡": 0.05}

    # 年龄调整
    if age >= 50:
        bias["存款"] = bias.get("存款", 0.20) + 0.10
        bias["保险"] = bias.get("保险", 0.10) + 0.05
        bias["基金"] = max(0.05, bias.get("基金", 0.15) - 0.05)
    elif age <= 30:
        bias["基金"] = bias.get("基金", 0.20) + 0.05
        bias["信用卡"] = bias.get("信用卡", 0.05) + 0.05

    # 高等级客户偏好调整
    if tier in ("私钻", "私行", "高净值"):
        bias["保险"] = bias.get("保险", 0.10) + 0.05
        bias["理财"] = bias.get("理财", 0.30) + 0.05

    # 归一化
    total = sum(bias.values())
    return {k: v / total for k, v in bias.items()}


# ============================================================
# 生成器：交易流水
# ============================================================

def gen_transactions(conn: sqlite3.Connection, cust: dict, profile: dict, today: date) -> int:
    """
    为客户生成当日交易（日常消费 + 信号注入）。

    返回生成的交易笔数。
    """
    n_generated = 0
    cust_id = cust["id"]
    aum = profile["aum"]
    today_str = today.isoformat()

    # -- 1. 日常交易（泊松采样）--
    daily_rate = profile["txn_per_month"] / 30.0
    # 周末交易减半
    if profile["is_weekend"]:
        daily_rate *= 0.5
    n_txn = _poisson_sample(daily_rate)

    # 交易渠道偏好
    channels = ["手机银行", "手机银行", "网银", "柜台", "ATM"]
    if profile["is_weekend"]:
        channels = ["手机银行", "手机银行", "手机银行", "微信", "ATM"]

    for _ in range(n_txn):
        is_in = random.random() < 0.50
        if is_in:
            amt = round(random.uniform(30, aum * 0.008), 2)
            amt = max(1.0, amt)
            counterparty = random.choice(["支付宝", "微信", "他行账户", "本行账户", "公司", "个人"])
            summary = random.choice(["转账收入", "退款", "红包", "理财赎回", "报销"])
        else:
            amt = round(random.uniform(20, aum * 0.01), 2)
            amt = max(1.0, amt)
            counterparty = random.choice(["支付宝", "微信", "他行账户", "本行账户", "商户", "个人"])
            summary = random.choice(["消费支付", "转账", "取现", "还款", "缴费", "理财购买"])

        conn.execute(
            """INSERT INTO transactions (cust_id, txn_date, txn_type, amount,
               counterparty, summary, channel, counterparty_cust_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, NULL)""",
            (cust_id, today_str, "in" if is_in else "out", amt, counterparty, summary,
             random.choice(channels)),
        )
        n_generated += 1

    # -- 2. 发薪日注入 --
    if (profile["is_salary_worker"] and profile["salary_day"] is not None
            and today.day == profile["salary_day"] and random.random() < 0.70):
        lo, hi = SALARY_RANGES.get(profile["tier"], (3000, 15000))
        salary_amt = round(random.uniform(lo, hi), 2)
        conn.execute(
            "INSERT INTO transactions (cust_id, txn_date, txn_type, amount,"
            " counterparty, summary, channel, counterparty_cust_id)"
            " VALUES (?, ?, 'in', ?, '公司', '工资', '手机银行', NULL)",
            (cust_id, today_str, salary_amt),
        )
        n_generated += 1

    # -- 3. 大额异动注入（5% 概率）--
    if random.random() < 0.05:
        ratio = random.uniform(0.03, 0.20)
        big_amt = round(aum * ratio, 2)
        big_amt = max(20000, min(big_amt, 500000))
        direction = random.choice(["out", "out", "in"])  # 偏大额转出
        if direction == "in":
            summary = random.choice(["大额转入", "理财到期回款", "资产归集"])
        else:
            summary = random.choice(["大额转出", "购房款", "投资款"])
        conn.execute(
            "INSERT INTO transactions (cust_id, txn_date, txn_type, amount,"
            " counterparty, summary, channel, counterparty_cust_id)"
            " VALUES (?, ?, ?, ?, '他行账户', ?, '手机银行', NULL)",
            (cust_id, today_str, direction, big_amt, summary),
        )
        n_generated += 1

    # -- 4. 经营流水（小微企业主特征）--
    if profile["occ"] in ("企业中层",) and random.random() < 0.25:
        biz_amt = round(random.uniform(5000, 80000), 2)
        direction = random.choice(["in", "in", "out"])
        if direction == "in":
            summary = random.choice(["货款", "采购款", "结算款", "预付款", "服务费"])
        else:
            summary = random.choice(["付款", "采购支出", "工资发放"])
        conn.execute(
            "INSERT INTO transactions (cust_id, txn_date, txn_type, amount,"
            " counterparty, summary, channel, counterparty_cust_id)"
            " VALUES (?, ?, ?, ?, '企业账户', ?, '网银', NULL)",
            (cust_id, today_str, direction, biz_amt, summary),
        )
        n_generated += 1

    # -- 5. 他行转账流失信号（2% 概率）--
    if random.random() < 0.02:
        ratio = random.uniform(0.03, 0.15)
        loss_amt = round(aum * ratio, 2)
        loss_amt = max(10000, loss_amt)
        conn.execute(
            "INSERT INTO transactions (cust_id, txn_date, txn_type, amount,"
            " counterparty, summary, channel, counterparty_cust_id)"
            " VALUES (?, ?, 'out', ?, '他行账户', '他行转账', '手机银行', NULL)",
            (cust_id, today_str, loss_amt),
        )
        n_generated += 1

    return n_generated


# ============================================================
# 生成器：行为日志
# ============================================================

def gen_behaviors(conn: sqlite3.Connection, cust: dict, profile: dict, today: date) -> int:
    """
    为客户生成当日 App/网银行为日志。

    返回生成的行为条数。
    """
    if random.random() > profile["behavior_daily_prob"]:
        return 0

    cust_id = cust["id"]
    today_str = today.isoformat()

    # 行为条数：1-3 条，周末更多
    if profile["is_weekend"]:
        n_actions = random.choices([1, 2, 3], weights=[0.4, 0.4, 0.2])[0]
    else:
        n_actions = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]

    # 渠道：手机银行为主，周末偏微信
    if profile["is_weekend"]:
        channels = ["手机银行", "手机银行", "微信", "微信", "网银"]
    else:
        channels = ["手机银行", "手机银行", "手机银行", "网银", "微信"]

    # 动作类型
    if profile["is_weekend"]:
        actions_pool = ["浏览", "浏览", "搜索", "点击详情", "收藏"]
    else:
        actions_pool = ["浏览", "搜索", "点击详情", "收藏", "对比"]

    bias = profile["behavior_bias"]

    for _ in range(n_actions):
        page = _weighted_choice(bias)
        action = random.choice(actions_pool)

        # 停留时长：周末更长
        if profile["is_weekend"]:
            dur = random.randint(30, 600)
        else:
            dur = random.randint(15, 300)

        prod_code = random.choice(PRODUCT_CODES.get(page, ["X000"]))

        # 时间分布
        if profile["is_weekend"]:
            hour = random.randint(9, 23)
        else:
            hour = random.randint(8, 22)
        t = f"{hour:02d}:{random.randint(0, 59):02d}:00"
        channel = random.choice(channels)

        conn.execute(
            """INSERT INTO behavior_logs (cust_id, event_date, event_time, channel,
               page_type, action, duration_sec, product_code, product_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cust_id, today_str, t, channel, page, action, dur, prod_code, page),
        )

    return n_actions


# ============================================================
# 生成器：持仓到期处理
# ============================================================

def process_maturing_holdings(conn: sqlite3.Connection, today: date) -> int:
    """
    处理当日到期产品：
    1. 将状态更新为 '已到期'
    2. 20% 概率自动续购新产品

    返回受影响的持仓数。
    """
    today_str = today.isoformat()

    # 标记到期
    cursor = conn.execute(
        "UPDATE holdings SET status = '已到期' WHERE maturity_date = ? AND status = '持有中'",
        (today_str,),
    )
    n_updated = cursor.rowcount

    if n_updated == 0:
        return 0

    # 查询本轮到期的产品
    matured = conn.execute(
        "SELECT cust_id, amount, product_type FROM holdings"
        " WHERE maturity_date = ? AND status = '已到期'",
        (today_str,),
    ).fetchall()

    for m in matured:
        if random.random() < 0.20:
            new_name = f"{m['product_type']}续期"
            new_code = f"AUTO_{today.strftime('%m%d')}_{m['cust_id']}"
            new_amount = int(float(m["amount"]) * random.uniform(0.8, 1.2))
            mat_days = random.choice([30, 60, 90, 180, 365])
            conn.execute(
                """INSERT INTO holdings (cust_id, product_type, product_name, product_code,
                   amount, yield_rate, risk_level, maturity_date, purchase_date, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '持有中')""",
                (
                    m["cust_id"], m["product_type"], new_name, new_code,
                    new_amount, round(random.uniform(1.5, 4.5), 4),
                    random.choice(["R1", "R2", "R3"]),
                    (today + timedelta(days=mat_days)).isoformat(), today_str,
                ),
            )
            n_updated += 1

    return n_updated


# ============================================================
# 生成器：客户经理沟通
# ============================================================

def gen_manager_communications(conn: sqlite3.Connection, today: date) -> int:
    """
    模拟客户经理对近期事件的响应式沟通：
    - 对昨日大额异动客户电话回访（40% 概率）
    - 对 7 日内到期客户发微信提醒（取前 3 位，50% 概率）

    返回生成的沟通条数。
    """
    n_generated = 0
    today_str = today.isoformat()
    yesterday_str = (today - timedelta(days=1)).isoformat()

    # -- 大额异动回访 --
    big_custs = conn.execute(
        """SELECT DISTINCT t.cust_id, c.name
           FROM transactions t JOIN customers c ON t.cust_id = c.id
           WHERE t.txn_date = ? AND t.amount > 30000 AND t.txn_type = 'out'
           LIMIT 5""",
        (yesterday_str,),
    ).fetchall()

    for bc in big_custs:
        if random.random() < 0.40:
            channel = random.choice(["电话", "电话", "微信"])
            dur = random.randint(5, 20) if channel == "电话" else None
            summary = (
                f"客户经理联系{bc['name']}，了解昨日资金转出情况，"
                f"确认用途并探讨理财配置需求"
            )
            conn.execute(
                """INSERT INTO communications (cust_id, comm_date, comm_time, channel,
                   duration_min, summary, key_topics)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    bc["cust_id"], today_str,
                    f"{random.randint(9, 17):02d}:00:00", channel,
                    dur, summary, "大额异动,资金用途,理财配置",
                ),
            )
            n_generated += 1

    # -- 产品到期提醒（取前 3 位）--
    week_later = (today + timedelta(days=7)).isoformat()
    due_custs = conn.execute(
        """SELECT DISTINCT h.cust_id, c.name
           FROM holdings h JOIN customers c ON h.cust_id = c.id
           WHERE h.maturity_date BETWEEN ? AND ? AND h.status = '持有中'
           LIMIT 3""",
        (today_str, week_later),
    ).fetchall()

    for dc in due_custs:
        if random.random() < 0.50:
            products = conn.execute(
                "SELECT product_name FROM holdings WHERE cust_id = ?"
                " AND maturity_date BETWEEN ? AND ? AND status = '持有中'",
                (dc["cust_id"], today_str, week_later),
            ).fetchall()
            prod_names = "、".join([p["product_name"] for p in products[:2]])
            summary = (
                f"客户经理给{dc['name']}发微信，提醒{prod_names}即将到期，"
                f"建议择日来行办理续期或重新配置"
            )
            conn.execute(
                """INSERT INTO communications (cust_id, comm_date, comm_time, channel,
                   duration_min, summary, key_topics)
                   VALUES (?, ?, ?, '微信', 3, ?, ?)""",
                (
                    dc["cust_id"], today_str,
                    f"{random.randint(9, 18):02d}:00:00",
                    summary, "产品到期,续期提醒,资产配置",
                ),
            )
            n_generated += 1

    return n_generated


# ============================================================
# 生成器：稀缺事件
# ============================================================

def inject_rare_events(conn: sqlite3.Connection, today: date) -> int:
    """
    注入低概率但影响重大的事件：
    - 0.3%：客户就业状态变更（在职→待业 或 自由职业→在职）
    - 0.5%：客户发起贷款申请（新增 loan 记录）

    返回注入的事件数。
    """
    n_events = 0
    today_str = today.isoformat()

    # -- 职业变动（0.3%）--
    if random.random() < 0.003:
        custs = conn.execute(
            "SELECT id, name, employment_status FROM customers ORDER BY RANDOM() LIMIT 1"
        ).fetchall()
        if custs:
            c = custs[0]
            old_status = c["employment_status"]
            options = [s for s in ("在职", "待业", "自由职业") if s != old_status]
            if options:
                new_status = random.choice(options)
                conn.execute(
                    "UPDATE customers SET employment_status = ? WHERE id = ?",
                    (new_status, c["id"]),
                )
                # 同步就业状态表
                conn.execute(
                    """INSERT OR REPLACE INTO employment_status
                       (cust_id, status, unemployment_benefits, verified, last_verified_date)
                       VALUES (?, ?, 0, 0, ?)""",
                    (c["id"], new_status, today_str),
                )
                n_events += 1
                print(f"  [Event] 客户 {c['name']}(ID={c['id']}) "
                      f"就业状态变更: {old_status} → {new_status}")

    return n_events


# ============================================================
# 生成器：产品变更/上新
# ============================================================

# 银行理财产品名称模板
PRODUCT_NAMES = {
    "理财": [
        "稳利增盈", "鑫享添利", "瑞盈优选", "财富成长", "金葵花增利",
        "安盈宝", "聚益生金", "天添金", "月月盈", "双利丰",
    ],
    "基金": [
        "优选蓝筹", "成长动力", "价值精选", "稳健回报", "科技创新",
        "消费升级", "医疗健康", "新能源动力", "ESG主题", "红利精选",
    ],
    "存款": [
        "整存整取一年期", "整存整取三年期", "大额存单", "通知存款", "零存整取",
    ],
    "保险": [
        "安康终身寿险", "稳盈年金险", "百万医疗险", "重疾保障险", "如意分红险",
    ],
}

# 产品公告模板（行内产品通知风格）
PRODUCT_ANNOUNCE_TEMPLATES = [
    {
        "type": "product",
        "priority": "high",
        "title_templates": [
            "关于{name}产品收益率调整的公告",
            "关于{name}产品销售规则变更的通知",
            "关于{name}产品起购金额调整的公告",
        ],
        "content_templates": [
            "尊敬的客户：\n\n自{date}起，{name}产品预期年化收益率由{old}调整为{new}，已持有客户不受影响，新申购按调整后收益率执行。如您有任何疑问，请联系您的客户经理或拨打客服热线。\n\n{org}分行\n{date}",
            "尊敬的客户：\n\n为优化客户体验，自{date}起，{name}产品起购金额由{old}元调整为{new}元，其他规则不变。如需了解详情，请登录手机银行或联系您的客户经理。\n\n{org}分行零售业务部\n{date}",
        ],
    },
    {
        "type": "product",
        "priority": "high",
        "title_templates": [
            "{name}产品上架通知",
            "关于代销{name}产品的公告",
        ],
        "content_templates": [
            "各营业网点：\n\n根据总行产品准入安排，{name}产品自{date}起正式上架销售，产品风险等级{risk}，适合{target}客户。请各网点做好产品培训与客户推介工作。产品详细信息请查询行内产品管理系统。\n\n{org}分行个人金融部\n{date}",
        ],
    },
    {
        "type": "product",
        "priority": "normal",
        "title_templates": [
            "关于{name}产品暂停销售的公告",
            "关于{name}产品到期下架的通知",
        ],
        "content_templates": [
            "尊敬的客户：\n\n{name}产品将于{date}起暂停销售，已持有客户不受影响。该产品持有的客户可继续持有至到期，到期后将自动到账。如您需要替代产品建议，请联系您的客户经理。\n\n{org}分行\n{date}",
        ],
    },
]

# 行内公告模板（贴近银行真实风格）
INTERNAL_ANNOUNCE_TEMPLATES = [
    {
        "type": "system",
        "priority": "normal",
        "title_templates": [
            "关于{date_str}日核心系统升级维护的通知",
            "关于网上银行系统升级的公告",
            "关于手机银行版本更新的通知",
        ],
        "content_templates": [
            "各营业网点、全体员工：\n\n根据总行科技部统一安排，拟定于{date_str}（{weekday}）{time_str}进行核心系统升级维护，届时部分业务将暂停服务，预计恢复时间为当{time_str_end}。请各网点提前做好客户告知工作，引导客户合理安排业务办理时间。\n\n如有紧急业务需要处理，请联系科技部值班电话。\n\n{org}分行科技部\n{date_str}",
            "各营业网点：\n\n为提升线上服务能力，手机银行将于{date_str}上线新版本，新增智能客服、语音搜索等功能。请全体客户经理熟悉新功能，适时向客户推介。\n\n{org}分行零售业务部\n{date_str}",
        ],
    },
    {
        "type": "compliance",
        "priority": "high",
        "title_templates": [
            "关于开展客户身份信息核实工作的通知",
            "关于进一步加强反洗钱合规管理的通知",
            "关于客户风险测评到期重测的提醒",
            "关于落实适当性管理要求的通知",
        ],
        "content_templates": [
            "各支行、全体客户经理：\n\n根据监管部门要求，自{date_str}起至{expire_str}，请各网点对存量客户身份信息进行全面核查，重点核实以下内容：\n\n1. 身份证件有效期即将到期或已到期的客户；\n2. 联系电话、地址等基本信息发生变更的客户；\n3. 职业、收入等影响风险承受能力评估的信息发生变化的客户。\n\n核查方式：建议通过电话或面谈方式进行核实。对无法联系的客户，按规定采取账户管控措施。请各部门高度重视，按时完成核查任务。\n\n{org}分行合规部\n{date_str}",
            "各营业网点：\n\n根据《商业银行理财业务监督管理办法》要求，请各网点筛选风险测评有效期不足30天的客户名单，通过电话或短信方式提醒客户及时更新风险测评。客户购买理财产品前须完成有效风险测评，否则将无法完成交易。\n\n{org}分行个人金融部\n{date_str}",
        ],
    },
    {
        "type": "marketing",
        "priority": "normal",
        "title_templates": [
            "关于开展{season}专题营销活动的通知",
            "关于{holiday}客户回馈活动的通知",
            "关于新客户专属礼遇活动的通知",
            "关于开展专项产品推介活动的通知",
        ],
        "content_templates": [
            "各支行、全体客户经理：\n\n为把握{season}营销旺季机遇，分行决定于{start}至{end}期间开展专题营销活动。本次活动以主题产品推介、客户答谢沙龙等为主要形式，各网点可根据自身情况选择适当的方式开展。\n\n活动期间，请结合总行下发的目标客户名单，优先联系近三个月内有资金流入或产品到期的客户进行精准营销。活动结束后，请于三个工作日内将活动总结报送分行。\n\n{org}分行零售业务部\n{date_str}",
            "各营业网点：\n\n为回馈新老客户，分行推出新客户专属礼遇活动：自{date_str}起至{expire_str}止，首次开立理财账户并完成产品申购的客户，可享专属礼品一份。请各网点在厅堂显眼位置摆放宣传物料，并利用微信朋友圈、客户群等方式进行线上推广。\n\n{org}分行零售业务部\n{date_str}",
        ],
    },
]

# 节假日列表
HOLIDAYS = [
    ("1月1日", "元旦", "新年开门红"),
    ("2月14日", "情人节", "情人节"),
    ("3月8日", "三八妇女节", "三八妇女节"),
    ("5月1日", "五一劳动节", "五一"),
    ("6月1日", "六一儿童节", "六一"),
    ("9月10日", "教师节", "教师节"),
    ("10月1日", "国庆节", "国庆黄金周"),
    ("12月25日", "圣诞节", "圣诞"),
]

# 季节映射
SEASONS = {
    1: "开门红", 2: "开门红", 3: "开门红",
    4: "春季", 5: "春季",
    6: "年中冲刺",
    7: "夏季", 8: "夏季",
    9: "秋季", 10: "秋季",
    11: "年末收官", 12: "年末收官",
}

# 分行名称列表
ORG_NAMES = [
    "厦门", "福州", "泉州", "漳州", "龙岩", "莆田", "南宁",
    "深圳", "广州", "杭州", "宁波", "南京", "苏州", "成都",
]


WEEKDAY_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _gen_product_updates(conn: sqlite3.Connection, today: date) -> dict:
    """
    生成随机产品变更/上新事件。
    每天有 30% 概率产生 1-3 条产品变更。
    """
    stats = {"product_updates": 0, "announcements": 0}
    today_str = today.isoformat()

    if random.random() > 0.30:
        return stats

    # 加载当前产品目录
    products = conn.execute(
        "SELECT product_code, product_name, product_type, risk_level, yield_rate, status FROM product_catalog"
    ).fetchall()

    if not products:
        return stats

    n_changes = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]

    for _ in range(n_changes):
        change_type = random.choices(
            ["yield_change", "status_change", "new_product"],
            weights=[0.45, 0.30, 0.25],
        )[0]

        if change_type == "new_product":
            # 从模板名称中选一个未使用过的
            ptype = random.choice(["理财", "基金", "保险"])
            name_pool = PRODUCT_NAMES.get(ptype, ["新产品"])
            new_name = random.choice(name_pool) + str(random.randint(1, 99))
            new_code = f"{['W','F','I'][['理财','基金','保险'].index(ptype)]}{random.randint(100, 999)}"
            risk = random.choice(["R2", "R3", "R4"])
            yld = round(random.uniform(2.0, 5.0), 4)

            # 插入新产品
            try:
                conn.execute(
                    """INSERT INTO product_catalog (product_code, product_name, product_type,
                       risk_level, yield_rate, min_amount, manager, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, '在售')""",
                    (new_code, new_name, ptype, risk, yld,
                     random.choice([1, 10000, 50000]),
                     random.choice(ORG_NAMES) + "分行"),
                )
                conn.execute(
                    """INSERT INTO product_updates (product_code, change_type, new_value, changed_at)
                       VALUES (?, 'new_product', ?, ?)""",
                    (new_code, f"{new_name}|{ptype}|{risk}|{yld}%", today_str),
                )
                stats["product_updates"] += 1
            except Exception:
                pass

        elif change_type == "yield_change":
            # 随机选一个理财产品调收益率
            fin_products = [p for p in products if p["product_type"] in ("理财", "基金")]
            if fin_products:
                prod = random.choice(fin_products)
                old_yield = float(prod["yield_rate"] or 2.5)
                new_yield = round(old_yield * random.uniform(0.90, 1.15), 4)
                new_yield = max(0.5, min(8.0, new_yield))

                conn.execute(
                    "UPDATE product_catalog SET yield_rate = ? WHERE product_code = ?",
                    (new_yield, prod["product_code"]),
                )
                conn.execute(
                    """INSERT INTO product_updates (product_code, change_type, old_value, new_value, changed_at)
                       VALUES (?, 'yield_change', ?, ?, ?)""",
                    (prod["product_code"], f"{old_yield}%", f"{new_yield}%", today_str),
                )
                stats["product_updates"] += 1

                # 同时可能生成公告
                if random.random() < 0.4:
                    tmpl = PRODUCT_ANNOUNCE_TEMPLATES[0]
                    title = random.choice(tmpl["title_templates"]).format(
                        name=prod["product_name"]
                    )
                    content = random.choice(tmpl["content_templates"]).format(
                        name=prod["product_name"],
                        date=today_str,
                        old=f"{old_yield}%",
                        new=f"{new_yield}%",
                        org=random.choice(ORG_NAMES),
                    )
                    conn.execute(
                        """INSERT INTO internal_announcements
                           (title, content, ann_type, priority, published_at)
                           VALUES (?, ?, 'product', 'high', ?)""",
                        (title, content, today_str),
                    )
                    stats["announcements"] += 1

        elif change_type == "status_change":
            active_products = [p for p in products if p["status"] == "在售"]
            if active_products:
                prod = random.choice(active_products)
                old_status = prod["status"]
                new_status = random.choice(["停售", "已到期"])

                conn.execute(
                    "UPDATE product_catalog SET status = ? WHERE product_code = ?",
                    (new_status, prod["product_code"]),
                )
                conn.execute(
                    """INSERT INTO product_updates (product_code, change_type, old_value, new_value, changed_at)
                       VALUES (?, 'status_change', ?, ?, ?)""",
                    (prod["product_code"], old_status, new_status, today_str),
                )
                stats["product_updates"] += 1

                # 生成下架公告
                if random.random() < 0.6:
                    tmpl = PRODUCT_ANNOUNCE_TEMPLATES[2]
                    title = random.choice(tmpl["title_templates"]).format(
                        name=prod["product_name"]
                    )
                    content = random.choice(tmpl["content_templates"]).format(
                        name=prod["product_name"],
                        date=today_str,
                        org=random.choice(ORG_NAMES),
                    )
                    conn.execute(
                        """INSERT INTO internal_announcements
                           (title, content, ann_type, priority, published_at)
                           VALUES (?, ?, 'product', 'normal', ?)""",
                        (title, content, today_str),
                    )
                    stats["announcements"] += 1

    return stats


def _gen_internal_announcements(conn: sqlite3.Connection, today: date) -> int:
    """
    生成随机行内公告/活动通知。
    每天有 20% 概率生成 1 条公告（节假日概率提升至 50%）。
    """
    today_str = today.isoformat()
    weekday = today.weekday()

    # 检查是否为节假日附近
    month_day = f"{today.month}月{today.day}日"
    is_holiday_nearby = any(
        h[0] == month_day or h[0] == f"{today.month}月{today.day+1}日"
        or h[0] == f"{today.month}月{today.day-1}日"
        for h in HOLIDAYS
    )

    prob = 0.50 if is_holiday_nearby else 0.20
    if random.random() > prob:
        return 0

    # 选择公告类型
    tmpl = random.choice(INTERNAL_ANNOUNCE_TEMPLATES)
    title = random.choice(tmpl["title_templates"])
    priority = tmpl["priority"]

    season = SEASONS.get(today.month, "日常")
    expire_date = (today + timedelta(days=random.choice([7, 14, 30, 60]))).isoformat()
    org = random.choice(ORG_NAMES)

    content = random.choice(tmpl["content_templates"])
    content = content.replace("{date_str}", today_str)
    content = content.replace("{expire_str}", expire_date)
    content = content.replace("{weekday}", WEEKDAY_CN[weekday])
    content = content.replace("{time_str}", random.choice(["22:00", "23:00", "02:00"]))
    content = content.replace("{time_str_end}", random.choice(["日 06:00", "日 08:00", "日 05:30"]))
    content = content.replace("{season}", season)
    content = content.replace("{org}", org)
    content = content.replace(
        "{holiday}",
        next((h[1] for h in HOLIDAYS if h[0] == month_day), season),
    )
    content = content.replace("{start}", today_str)
    content = content.replace(
        "{end}", (today + timedelta(days=random.randint(20, 60))).isoformat()
    )

    # 同时也处理 title 中的模板变量
    title = title.replace("{date_str}", today_str)
    title = title.replace("{season}", season)
    title = title.replace(
        "{holiday}",
        next((h[1] for h in HOLIDAYS if h[0] == month_day), season),
    )

    ann_type = tmpl["type"]

    conn.execute(
        """INSERT INTO internal_announcements
           (title, content, ann_type, priority, published_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (title, content.strip(), ann_type, priority, today_str, expire_date),
    )

    return 1


# ============================================================
# 主入口
# ============================================================

def daily_tick(date_str: str, db_path: Optional[str] = None) -> dict:
    """
    执行单日数据推进。

    调度约定：每日 07:30 调用，在 schedule_gen(08:00) 之前，
    确保 query_tasks_for_schedule 能检测到"昨日"新增的大额异动。

    Args:
        date_str: 推进日期，格式 YYYY-MM-DD
        db_path: SQLite 数据库路径，默认 data-sim/yihuiban_sim.db

    Returns:
        {"status": "ok|skipped|error",
         "stats": {"transactions": N, "behaviors": N, "communications": N,
                   "holding_updates": N, "events": N}}
    """
    db = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row

    try:
        # ---- 幂等检查 ----
        existing = conn.execute(
            "SELECT tick_date FROM data_ticks WHERE tick_date = ?", (date_str,)
        ).fetchone()
        if existing:
            return {"status": "skipped", "reason": f"tick {date_str} already applied"}

        today = date.fromisoformat(date_str)
        stats = {
            "transactions": 0,
            "behaviors": 0,
            "communications": 0,
            "holding_updates": 0,
            "events": 0,
            "product_updates": 0,
            "announcements": 0,
        }

        # ---- 1. 加载全部客户 ----
        customers = conn.execute(
            "SELECT id, name, tier, total_aum, occupation, employment_status, age, city"
            " FROM customers"
        ).fetchall()

        # ---- 2. 逐客户推进 ----
        for row in customers:
            cust = dict(row)
            profile = derive_profile(cust)

            # 日活判断
            if random.random() > profile["daily_active_prob"]:
                continue

            stats["transactions"] += gen_transactions(conn, cust, profile, today)
            stats["behaviors"] += gen_behaviors(conn, cust, profile, today)

        # ---- 3. 持仓到期处理 ----
        stats["holding_updates"] = process_maturing_holdings(conn, today)

        # ---- 4. 客户经理沟通 ----
        stats["communications"] = gen_manager_communications(conn, today)

        # ---- 5. 稀缺事件 ----
        stats["events"] = inject_rare_events(conn, today)

        # ---- 6. 产品变更 ----
        prod_stats = _gen_product_updates(conn, today)
        stats["product_updates"] = prod_stats["product_updates"]
        stats["announcements"] = prod_stats["announcements"]

        # ---- 7. 行内公告 ----
        stats["announcements"] += _gen_internal_announcements(conn, today)

        # ---- 8. 记录完成标记 ----
        conn.execute(
            "INSERT INTO data_ticks (tick_date, stats_json, created_at)"
            " VALUES (?, ?, ?)",
            (date_str, json.dumps(stats, ensure_ascii=False), today.isoformat()),
        )

        conn.commit()
        return {"status": "ok", "stats": stats}

    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


# ============================================================
# CLI 入口（手动测试用）
# ============================================================

if __name__ == "__main__":
    import sys

    target_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    result = daily_tick(target_date)
    print(f"daily_tick({target_date}):")
    print(f"  status: {result['status']}")
    if "stats" in result:
        print(f"  transactions:    {result['stats']['transactions']}")
        print(f"  behaviors:       {result['stats']['behaviors']}")
        print(f"  communications:  {result['stats']['communications']}")
        print(f"  holding_updates: {result['stats']['holding_updates']}")
        print(f"  events:          {result['stats']['events']}")
        print(f"  product_updates: {result['stats'].get('product_updates', 0)}")
        print(f"  announcements:   {result['stats'].get('announcements', 0)}")
    elif "reason" in result:
        print(f"  reason: {result['reason']}")
    elif "message" in result:
        print(f"  error: {result['message']}")
