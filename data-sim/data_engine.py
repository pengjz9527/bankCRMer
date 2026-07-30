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

        # ---- 6. 记录完成标记 ----
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
    elif "reason" in result:
        print(f"  reason: {result['reason']}")
    elif "message" in result:
        print(f"  error: {result['message']}")
