"""
Skill 技能库 — Data 查询层
Agent 通过 ctx.skill('query_xxx', ...) 调用，获取结构化客户数据
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("agentos.skills")

DB_PATH = str(Path(__file__).parent.parent / "yihuiban_sim.db")


def _db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


# ============================================================
# 客户查询
# ============================================================

def query_customers(
    branch: str = None,
    manager_id: str = None,
    active: bool = True,
    page: int = 1,
    limit: int = 100,
) -> list[dict]:
    """
    查询客户列表，支持按机构/客户经理筛选
    返回基础信息（不含手机号）
    """
    conn = _db()
    try:
        sql = """SELECT c.id, c.cust_no, c.name, c.age, c.gender, c.occupation, c.industry,
                        c.city, c.education, c.tier, c.total_aum, c.employment_status
                 FROM customers c"""
        params = []
        # 按客户经理过滤
        if manager_id:
            sql += """ INNER JOIN cust_manager_rel cmr ON c.id = cmr.cust_id
                      WHERE cmr.manager_id = ?"""
            params.append(manager_id)
        else:
            sql += " WHERE 1=1"
        if active:
            pass  # 所有客户默认 active
        sql += " ORDER BY c.total_aum DESC LIMIT ?"
        params.append(limit * page)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_customers_by_ids(cust_ids: list[int]) -> list[dict]:
    """按 ID 列表批量查询客户"""
    if not cust_ids:
        return []
    conn = _db()
    try:
        placeholders = ",".join("?" for _ in cust_ids)
        sql = f"""SELECT id, cust_no, name, age, gender, occupation, industry,
                         city, education, tier, total_aum, employment_status
                  FROM customers WHERE id IN ({placeholders})"""
        rows = conn.execute(sql, cust_ids).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# 持仓查询
# ============================================================

def query_holdings(cust_id: int) -> list[dict]:
    """查询客户全部持仓（含活期存款）"""
    conn = _db()
    try:
        rows = conn.execute(
            """SELECT id, product_type, product_name, product_code,
                      amount, yield_rate, risk_level, maturity_date,
                      purchase_date, status
               FROM holdings WHERE cust_id = ?""",
            (cust_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# 交易流水查询
# ============================================================

def query_transactions(cust_id: int, days: int = 180) -> list[dict]:
    """查询客户近 N 天交易流水"""
    from datetime import date, timedelta
    since = (date.today() - timedelta(days=days)).isoformat()
    conn = _db()
    try:
        rows = conn.execute(
            """SELECT id, txn_date, txn_type, amount, counterparty,
                      summary, channel, counterparty_cust_id
               FROM transactions
               WHERE cust_id = ? AND txn_date >= ?
               ORDER BY txn_date DESC""",
            (cust_id, since),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# 行为日志查询
# ============================================================

def query_behavior(cust_id: int, days: int = 90) -> list[dict]:
    """查询客户近 N 天行为日志"""
    from datetime import date, timedelta
    since = (date.today() - timedelta(days=days)).isoformat()
    conn = _db()
    try:
        rows = conn.execute(
            """SELECT id, event_date, event_time, channel, page_type,
                      action, duration_sec, product_code, product_type
               FROM behavior_logs
               WHERE cust_id = ? AND event_date >= ?
               ORDER BY event_date DESC""",
            (cust_id, since),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# 沟通记录查询
# ============================================================

def query_communications(cust_id: int, days: int = 180) -> list[dict]:
    """查询客户近 N 天沟通记录"""
    from datetime import date, timedelta
    since = (date.today() - timedelta(days=days)).isoformat()
    conn = _db()
    try:
        rows = conn.execute(
            """SELECT id, comm_date, comm_time, channel, duration_min,
                      summary, key_topics
               FROM communications
               WHERE cust_id = ? AND comm_date >= ?
               ORDER BY comm_date DESC""",
            (cust_id, since),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# 风测 + 历史查询
# ============================================================

def query_risk(cust_id: int) -> dict:
    """查询客户当前风测 + 历史快照"""
    conn = _db()
    try:
        current = conn.execute(
            """SELECT test_result, valid_until, tested_date, wealth_score,
                      dimension_asset, dimension_income, dimension_social
               FROM risk_assessments WHERE cust_id = ?""",
            (cust_id,),
        ).fetchone()

        history = conn.execute(
            """SELECT test_result, tested_date, wealth_score,
                      dimension_asset, dimension_income, dimension_social
               FROM risk_assessment_history
               WHERE cust_id = ?
               ORDER BY tested_date ASC""",
            (cust_id,),
        ).fetchall()

        return {
            "current": dict(current) if current else None,
            "history": [dict(r) for r in history],
        }
    finally:
        conn.close()


# ============================================================
# 关系图谱查询
# ============================================================

def query_relations(cust_id: int) -> list[dict]:
    """查询客户的关系图谱（同企业代发/亲属）"""
    conn = _db()
    try:
        rows = conn.execute(
            """SELECT cr.id, cr.relation_type, cr.evidence,
                      CASE WHEN cr.cust_id_a = ? THEN cr.cust_id_b ELSE cr.cust_id_a END as related_cust_id
               FROM customer_relations cr
               WHERE cr.cust_id_a = ? OR cr.cust_id_b = ?""",
            (cust_id, cust_id, cust_id),
        ).fetchall()
        results = []
        for r in rows:
            rd = dict(r)
            # 附上关联客户的姓名
            rel = conn.execute(
                "SELECT name, tier FROM customers WHERE id = ?",
                (rd["related_cust_id"],),
            ).fetchone()
            if rel:
                rd["related_cust_name"] = rel["name"]
                rd["related_cust_tier"] = rel["tier"]
            results.append(rd)
        return results
    finally:
        conn.close()


# ============================================================
# 家庭信息查询
# ============================================================

def query_family(cust_id: int) -> dict:
    """查询客户家庭信息"""
    conn = _db()
    try:
        row = conn.execute(
            """SELECT marriage, children, child_count, child_age,
                      child_education, study_abroad_intent,
                      study_abroad_target_country, spouse_has_income,
                      updated_at
               FROM family_info WHERE cust_id = ?""",
            (cust_id,),
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


# ============================================================
# 经营信息查询
# ============================================================

def query_business(cust_id: int) -> dict:
    """查询客户经营信息（小微企业主）"""
    conn = _db()
    try:
        row = conn.execute(
            """SELECT business_name, duration_years, share_ratio,
                      reg_capital, address, scope
               FROM business_info WHERE cust_id = ?""",
            (cust_id,),
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


# ============================================================
# 贷款信息查询
# ============================================================

def query_loans(cust_id: int) -> list[dict]:
    """查询客户贷款信息"""
    conn = _db()
    try:
        rows = conn.execute(
            """SELECT product_name, credit_line, used_amount, (credit_line-used_amount) as remaining,
                      overdue_count, interest_rate, start_date, maturity_date
               FROM loans WHERE cust_id = ?""",
            (cust_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# 组合查询：获取一位客户的完整上下文
# ============================================================

def query_customer_full(cust_id: int) -> dict:
    """
    获取一位客户的全部 Mining 所需数据
    返回结构匹配 prompts/opportunity_mining.md 中定义的输入格式
    """
    conn = _db()
    try:
        cust = conn.execute(
            """SELECT id, name, age, gender, occupation, industry,
                      city, education, tier, total_aum, employment_status, contact_prefer
               FROM customers WHERE id = ?""",
            (cust_id,),
        ).fetchone()
        if not cust:
            return {}
        result = {"customer": dict(cust)}
        conn.close()  # 先关闭，后续用各自函数
    except Exception:
        return {}
    finally:
        try:
            conn.close()
        except Exception:
            pass

    result["family"] = query_family(cust_id)
    result["holdings"] = query_holdings(cust_id)
    result["transactions"] = query_transactions(cust_id)
    result["behavior_logs"] = query_behavior(cust_id)
    result["communications"] = query_communications(cust_id)
    result["risk_assessment"] = query_risk(cust_id)
    result["relations"] = query_relations(cust_id)
    result["business"] = query_business(cust_id)
    result["loans"] = query_loans(cust_id)
    result["benefits"] = query_benefits(cust_id)
    result["activities"] = query_activities(cust_id)

    return result


# ============================================================
# 权益与活动查询
# ============================================================

def query_benefits(cust_id: int) -> list[dict]:
    """查询客户持有的权益"""
    conn = _db()
    try:
        rows = conn.execute(
            """SELECT benefit_name, benefit_type, description,
                      tier_requirement, rarity, acquired_date,
                      expiry_date, status
               FROM customer_benefits WHERE cust_id = ?""",
            (cust_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_activities(cust_id: int) -> list[dict]:
    """查询客户参与及可参与的活动"""
    conn = _db()
    try:
        rows = conn.execute(
            """SELECT cap.activity_id, aa.title, aa.type,
                      aa.description, aa.reward_desc,
                      cap.participated_date, cap.status
               FROM customer_activity_participation cap
               JOIN available_activities aa ON cap.activity_id = aa.activity_id
               WHERE cap.cust_id = ?""",
            (cust_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# 客户洞察查询
# ============================================================

def query_customer_insight(cust_id: int) -> dict:
    """查询客户最新洞察快照"""
    conn = _db()
    try:
        row = conn.execute(
            """SELECT id, cust_id, manager_id, overview_json,
                      change_signals_json, risk_signals_json, risk_level,
                      generated_at, expires_at
               FROM customer_insights
               WHERE cust_id = ?
               ORDER BY generated_at DESC LIMIT 1""",
            (cust_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        import json
        d["overview"] = json.loads(d["overview_json"]) if isinstance(d["overview_json"], str) else d["overview_json"]
        d["change_signals"] = json.loads(d["change_signals_json"]) if isinstance(d["change_signals_json"], str) else d["change_signals_json"]
        d["risk_signals"] = json.loads(d["risk_signals_json"]) if isinstance(d["risk_signals_json"], str) else d["risk_signals_json"]
        return d
    finally:
        conn.close()


def query_customers_by_insight_filter(manager_id: str, insight_filter: str) -> list[dict]:
    """
    按洞察信号筛选客户
    insight_filter: 'change' = 有变化信号, 'risk' = 有预警信号
    """
    conn = _db()
    try:
        if insight_filter == 'change':
            sql = """SELECT DISTINCT c.id, c.name, c.tier, c.total_aum
                     FROM customers c
                     INNER JOIN customer_insights ci ON c.id = ci.cust_id
                     WHERE ci.manager_id = ?
                       AND ci.change_signals_json != '[]'
                       AND ci.change_signals_json IS NOT NULL
                       AND ci.change_signals_json != ''
                     ORDER BY c.total_aum DESC LIMIT 50"""
        elif insight_filter == 'risk':
            sql = """SELECT DISTINCT c.id, c.name, c.tier, c.total_aum
                     FROM customers c
                     INNER JOIN customer_insights ci ON c.id = ci.cust_id
                     WHERE ci.manager_id = ?
                       AND ci.risk_level IN ('orange', 'red')
                     ORDER BY c.total_aum DESC LIMIT 50"""
        else:
            return []
        rows = conn.execute(sql, (manager_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_customer_insights_by_manager(manager_id: str) -> list[dict]:
    """查询某经理所有客户的最新洞察快照列表"""
    conn = _db()
    try:
        rows = conn.execute(
            """SELECT ci.cust_id, c.name, c.tier, c.total_aum,
                      ci.risk_level, ci.generated_at, ci.expires_at,
                      ci.change_signals_json, ci.risk_signals_json
               FROM customer_insights ci
               INNER JOIN customers c ON ci.cust_id = c.id
               WHERE ci.manager_id = ?
                 AND ci.generated_at = (
                   SELECT MAX(ci2.generated_at)
                   FROM customer_insights ci2
                   WHERE ci2.cust_id = ci.cust_id
                 )
               ORDER BY c.total_aum DESC""",
            (manager_id,),
        ).fetchall()
        results = []
        import json
        for r in rows:
            d = dict(r)
            cs = d.get("change_signals_json", "[]")
            rs = d.get("risk_signals_json", "[]")
            d["has_change"] = bool(cs and cs != "[]" and cs != "")
            d["has_risk"] = d["risk_level"] in ("orange", "red")
            d["change_count"] = len(json.loads(cs)) if (cs and cs != "[]") else 0
            d["risk_count"] = len(json.loads(rs)) if (rs and rs != "[]") else 0
            results.append(d)
        return results
    finally:
        conn.close()


# ============================================================
# 日程排程 — 新架构：信号收集 → 商机挖掘 → 商机→待办 → 聚合
# ============================================================

# ---- 信号类型配置 ----
# signal_type → {type_name, strategy_tags, priority_weight, table/query info}
SIGNAL_TYPE_CONFIG: dict[str, dict] = {
    "due": {
        "type_name": "产品到期",
        "strategy_tags": ["资金承接", "产品续接", "流失防范"],
        "priority_weight": 100,
    },
    "overdue": {
        "type_name": "贷款逾期",
        "strategy_tags": ["贷后催收", "债务重组", "他行资金转入"],
        "priority_weight": 80,
    },
    "big_move": {
        "type_name": "大额异动",
        "strategy_tags": ["资金流向追踪", "反欺诈核实", "大额挽留"],
        "priority_weight": 80,
    },
    "salary_in": {
        "type_name": "代发工资",
        "strategy_tags": ["工资理财", "定投推荐", "代发留存"],
        "priority_weight": 60,
    },
    "contact_lapse": {
        "type_name": "联络超期",
        "strategy_tags": ["关系唤醒", "需求再发现", "服务回访"],
        "priority_weight": 50,
    },
    "birthday": {
        "type_name": "生日提醒",
        "strategy_tags": ["关系维护", "权益赠送", "年度财务回顾"],
        "priority_weight": 50,
    },
    "low_aum": {
        "type_name": "AUM走低",
        "strategy_tags": ["流失挽回", "降级预警", "小额激活"],
        "priority_weight": 55,
    },
    "high_aum_idle": {
        "type_name": "大额闲置",
        "strategy_tags": ["资金效率提升", "大额配置", "通知存款引导"],
        "priority_weight": 65,
    },
    "fund_browse": {
        "type_name": "基金意向",
        "strategy_tags": ["基金推荐", "风险适配", "组合配置"],
        "priority_weight": 60,
    },
    "wealth_browse": {
        "type_name": "理财产品意向",
        "strategy_tags": ["理财推荐", "期限匹配", "收益对比"],
        "priority_weight": 55,
    },
    "loan_browse": {
        "type_name": "贷款产品意向",
        "strategy_tags": ["信贷需求", "利率对比", "用途分析"],
        "priority_weight": 55,
    },
    "insurance_browse": {
        "type_name": "保险意向",
        "strategy_tags": ["保障需求", "家庭保单", "重疾推荐"],
        "priority_weight": 60,
    },
    "risk_retest": {
        "type_name": "风评变更",
        "strategy_tags": ["风评变化", "调仓建议", "风险重匹配"],
        "priority_weight": 70,
    },
    "insight_change": {
        "type_name": "洞察变化",
        "strategy_tags": ["综合判断", "交叉验证", "AI发现"],
        "priority_weight": 75,
    },
    "insight_risk": {
        "type_name": "洞察预警",
        "strategy_tags": ["紧急关注", "即刻响应", "风险干预"],
        "priority_weight": 80,
    },
}


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


# ============================================================
# Step 1: 信号收集 — 从各数据源收集客户事件/信号，写入 customer_signals 表
# ============================================================

def collect_signals(manager_id: str, schedule_date: str = None) -> int:
    """
    扫描所有数据源，收集客户事件/信号写入 customer_signals 表。
    每天同类型同客户只保留最新一条（通过 signal_id 去重）。

    Returns:
        新增信号数量
    """
    from datetime import date, timedelta
    import json as _json

    conn = _db()
    try:
        sd = schedule_date or date.today().isoformat()
        sd_date = date.fromisoformat(sd)

        mgr_rows = conn.execute(
            "SELECT cust_id FROM cust_manager_rel WHERE manager_id = ?", (manager_id,)
        ).fetchall()
        mgr_cust_ids = set(r["cust_id"] for r in (mgr_rows or []))
        if not mgr_cust_ids:
            return 0

        now_iso = date.today().isoformat()
        new_count = 0

        def _insert(sql, params):
            """执行 INSERT OR IGNORE，返回是否实际插入了新行"""
            cur = conn.execute(sql, params)
            return cur.rowcount > 0

        # ---- 1. 产品到期 (1-30天) ----
        due_rows = conn.execute(
            """SELECT h.cust_id, c.name, h.product_name, h.product_type, h.amount, h.maturity_date
               FROM holdings h JOIN customers c ON h.cust_id = c.id
               WHERE h.maturity_date BETWEEN ? AND ?
               ORDER BY h.maturity_date""",
            (sd, (sd_date + timedelta(days=30)).isoformat()),
        ).fetchall()
        due_by_cust: dict[int, list] = {}
        for r in due_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            due_by_cust.setdefault(r["cust_id"], []).append(dict(r))
        for cid, products in due_by_cust.items():
            signal_id = f"SIG_DUE_{cid}_{sd}"
            total_amt = sum(p["amount"] for p in products)
            earliest = min(p["maturity_date"] for p in products)
            days_until = (date.fromisoformat(earliest) - sd_date).days
            cfg = SIGNAL_TYPE_CONFIG["due"]
            if _insert(
                """INSERT OR IGNORE INTO customer_signals
                   (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                    priority_weight, valid_from, valid_until, status)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (signal_id, cid, "due",
                 _json.dumps({"products": products, "total_amount": total_amt,
                              "earliest_due": earliest, "days_until_due": days_until,
                              "product_count": len(products)}, ensure_ascii=False),
                 _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                 cfg["priority_weight"], sd, earliest, "active"),
            ):
                new_count += 1

        # ---- 2. 贷款逾期 ----
        overdue_rows = conn.execute(
            """SELECT l.cust_id, c.name, l.product_name, l.overdue_count, l.used_amount, l.credit_line
               FROM loans l JOIN customers c ON l.cust_id = c.id
               WHERE l.overdue_count > 0"""
        ).fetchall()
        for r in overdue_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            signal_id = f"SIG_OVERDUE_{r['cust_id']}"
            cfg = SIGNAL_TYPE_CONFIG["overdue"]
            conn.execute(
                """INSERT OR IGNORE INTO customer_signals
                   (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                    priority_weight, valid_from, status)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (signal_id, r["cust_id"], "overdue",
                 _json.dumps({"product_name": r["product_name"], "overdue_count": r["overdue_count"],
                              "used_amount": r["used_amount"], "credit_line": r["credit_line"]},
                             ensure_ascii=False),
                 _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                 cfg["priority_weight"], sd, "active"),
            )
            if True:  # INSERT OR IGNORE already handles dedup
                new_count += 1

        # ---- 3. 大额异动 ----
        big_rows = conn.execute(
            """SELECT t.cust_id, c.name, t.amount, t.summary, t.channel
               FROM transactions t JOIN customers c ON t.cust_id = c.id
               WHERE t.txn_date = ? AND t.amount > 30000 AND t.txn_type = 'out'
               ORDER BY t.amount DESC LIMIT 5""",
            (sd,),
        ).fetchall()
        for r in big_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            signal_id = f"SIG_BIGMOVE_{r['cust_id']}_{sd}"
            cfg = SIGNAL_TYPE_CONFIG["big_move"]
            conn.execute(
                """INSERT OR IGNORE INTO customer_signals
                   (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                    priority_weight, valid_from, status)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (signal_id, r["cust_id"], "big_move",
                 _json.dumps({"amount": r["amount"], "summary": r["summary"],
                              "channel": r["channel"]}, ensure_ascii=False),
                 _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                 cfg["priority_weight"], sd, "active"),
            )
            if True:  # INSERT OR IGNORE already handles dedup
                new_count += 1

        # ---- 4. 代发工资 (近 7 天) ----
        sal_rows = conn.execute(
            """SELECT DISTINCT t.cust_id, c.name, t.amount, t.txn_date
               FROM transactions t JOIN customers c ON t.cust_id = c.id
               WHERE t.summary = '工资' AND t.txn_date >= ?""",
            ((sd_date - timedelta(days=7)).isoformat(),),
        ).fetchall()
        for r in sal_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            signal_id = f"SIG_SALARY_{r['cust_id']}_{sd}"
            cfg = SIGNAL_TYPE_CONFIG["salary_in"]
            conn.execute(
                """INSERT OR IGNORE INTO customer_signals
                   (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                    priority_weight, valid_from, status)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (signal_id, r["cust_id"], "salary_in",
                 _json.dumps({"amount": r["amount"], "txn_date": r["txn_date"]}, ensure_ascii=False),
                 _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                 cfg["priority_weight"], sd, "active"),
            )
            if True:  # INSERT OR IGNORE already handles dedup
                new_count += 1

        # ---- 5. 联络超期 ----
        cutoff = (sd_date - timedelta(days=14)).isoformat()
        lapse_rows = conn.execute(
            """SELECT c.id, c.name, MAX(cm.comm_date) as last_date
               FROM customers c
               LEFT JOIN communications cm ON c.id = cm.cust_id
               GROUP BY c.id
               HAVING MAX(cm.comm_date) IS NULL OR MAX(cm.comm_date) < ?
               LIMIT 5""",
            (cutoff,),
        ).fetchall()
        for r in lapse_rows:
            if r["id"] not in mgr_cust_ids:
                continue
            signal_id = f"SIG_LAPSE_{r['id']}"
            cfg = SIGNAL_TYPE_CONFIG["contact_lapse"]
            if r["last_date"]:
                days_lapse = (sd_date - date.fromisoformat(r["last_date"])).days
            else:
                days_lapse = 999
            conn.execute(
                """INSERT OR IGNORE INTO customer_signals
                   (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                    priority_weight, valid_from, status)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (signal_id, r["id"], "contact_lapse",
                 _json.dumps({"last_date": r["last_date"], "days_lapse": days_lapse},
                             ensure_ascii=False),
                 _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                 cfg["priority_weight"], sd, "active"),
            )
            if True:  # INSERT OR IGNORE already handles dedup
                new_count += 1

        # ---- 6. 生日提醒 (7 天内) ----
        # 从 customers 表根据 birthday 或推算（此处用简易推算：age 字段无明确生日，暂用 age+1 基于今天）
        # 实际场景中应有 birthday 字段；此处用占位逻辑 — 不对虚构数据强依赖生日

        # ---- 7. AUM 走低 ----
        low_rows = conn.execute(
            """SELECT c.id, c.name, c.total_aum, c.tier
               FROM customers c
               WHERE c.total_aum < 50000 AND c.tier IN ('千元以下', '千元户')
               ORDER BY c.total_aum ASC LIMIT 5"""
        ).fetchall()
        for r in low_rows:
            if r["id"] not in mgr_cust_ids:
                continue
            signal_id = f"SIG_LOWAUM_{r['id']}"
            cfg = SIGNAL_TYPE_CONFIG["low_aum"]
            conn.execute(
                """INSERT OR IGNORE INTO customer_signals
                   (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                    priority_weight, valid_from, status)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (signal_id, r["id"], "low_aum",
                 _json.dumps({"total_aum": r["total_aum"], "tier": (r["tier"] or "")},
                             ensure_ascii=False),
                 _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                 cfg["priority_weight"], sd, "active"),
            )
            if True:  # INSERT OR IGNORE already handles dedup
                new_count += 1

        # ---- 8. 大额闲置 ----
        # 活期存款 > 50 万且无理财/基金持仓
        idle_rows = conn.execute(
            """SELECT h.cust_id, c.name, SUM(h.amount) as idle_amount
               FROM holdings h JOIN customers c ON h.cust_id = c.id
               WHERE h.product_type = '存款' AND h.maturity_date IS NULL
               GROUP BY h.cust_id
               HAVING SUM(h.amount) > 500000 LIMIT 10"""
        ).fetchall()
        for r in idle_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            signal_id = f"SIG_IDLE_{r['cust_id']}"
            cfg = SIGNAL_TYPE_CONFIG["high_aum_idle"]
            conn.execute(
                """INSERT OR IGNORE INTO customer_signals
                   (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                    priority_weight, valid_from, status)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (signal_id, r["cust_id"], "high_aum_idle",
                 _json.dumps({"idle_amount": r["idle_amount"]}, ensure_ascii=False),
                 _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                 cfg["priority_weight"], sd, "active"),
            )
            if True:  # INSERT OR IGNORE already handles dedup
                new_count += 1

        # ---- 9. 基金浏览意向 ----
        fund_rows = conn.execute(
            """SELECT b.cust_id, c.name, COUNT(*) as cnt
               FROM behavior_logs b JOIN customers c ON b.cust_id = c.id
               WHERE b.page_type = '基金'
                 AND c.id NOT IN (SELECT cust_id FROM holdings WHERE product_type = '基金')
               GROUP BY b.cust_id
               HAVING COUNT(*) >= 5 LIMIT 8"""
        ).fetchall()
        for r in fund_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            signal_id = f"SIG_FUNDB_{r['cust_id']}"
            cfg = SIGNAL_TYPE_CONFIG["fund_browse"]
            conn.execute(
                """INSERT OR IGNORE INTO customer_signals
                   (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                    priority_weight, valid_from, status)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (signal_id, r["cust_id"], "fund_browse",
                 _json.dumps({"browse_count": r["cnt"]}, ensure_ascii=False),
                 _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                 cfg["priority_weight"], sd, "active"),
            )
            if True:  # INSERT OR IGNORE already handles dedup
                new_count += 1

        # ---- 10. 理财产品浏览意向 ----
        wealth_rows = conn.execute(
            """SELECT b.cust_id, c.name, COUNT(*) as cnt
               FROM behavior_logs b JOIN customers c ON b.cust_id = c.id
               WHERE b.page_type = '理财'
               GROUP BY b.cust_id
               HAVING COUNT(*) >= 5 LIMIT 8"""
        ).fetchall()
        for r in wealth_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            signal_id = f"SIG_WEALTHB_{r['cust_id']}"
            cfg = SIGNAL_TYPE_CONFIG["wealth_browse"]
            conn.execute(
                """INSERT OR IGNORE INTO customer_signals
                   (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                    priority_weight, valid_from, status)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (signal_id, r["cust_id"], "wealth_browse",
                 _json.dumps({"browse_count": r["cnt"]}, ensure_ascii=False),
                 _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                 cfg["priority_weight"], sd, "active"),
            )
            if True:  # INSERT OR IGNORE already handles dedup
                new_count += 1

        # ---- 11. 贷款产品浏览意向 ----
        loanb_rows = conn.execute(
            """SELECT b.cust_id, c.name, COUNT(*) as cnt
               FROM behavior_logs b JOIN customers c ON b.cust_id = c.id
               WHERE b.page_type = '贷款'
               GROUP BY b.cust_id
               HAVING COUNT(*) >= 3 LIMIT 8"""
        ).fetchall()
        for r in loanb_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            signal_id = f"SIG_LOANB_{r['cust_id']}"
            cfg = SIGNAL_TYPE_CONFIG["loan_browse"]
            conn.execute(
                """INSERT OR IGNORE INTO customer_signals
                   (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                    priority_weight, valid_from, status)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (signal_id, r["cust_id"], "loan_browse",
                 _json.dumps({"browse_count": r["cnt"]}, ensure_ascii=False),
                 _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                 cfg["priority_weight"], sd, "active"),
            )
            if True:  # INSERT OR IGNORE already handles dedup
                new_count += 1

        # ---- 12. 保险浏览意向 ----
        insb_rows = conn.execute(
            """SELECT b.cust_id, c.name, COUNT(*) as cnt
               FROM behavior_logs b JOIN customers c ON b.cust_id = c.id
               WHERE b.page_type = '保险'
               GROUP BY b.cust_id
               HAVING COUNT(*) >= 3 LIMIT 8"""
        ).fetchall()
        for r in insb_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            signal_id = f"SIG_INSB_{r['cust_id']}"
            cfg = SIGNAL_TYPE_CONFIG["insurance_browse"]
            conn.execute(
                """INSERT OR IGNORE INTO customer_signals
                   (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                    priority_weight, valid_from, status)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (signal_id, r["cust_id"], "insurance_browse",
                 _json.dumps({"browse_count": r["cnt"]}, ensure_ascii=False),
                 _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                 cfg["priority_weight"], sd, "active"),
            )
            if True:  # INSERT OR IGNORE already handles dedup
                new_count += 1

        # ---- 13. 风评变更 ----
        risk_rows = conn.execute(
            """SELECT ra.cust_id, c.name, ra.test_result, ra.tested_date
               FROM risk_assessments ra JOIN customers c ON ra.cust_id = c.id
               WHERE ra.tested_date >= ?""",
            ((sd_date - timedelta(days=30)).isoformat(),),
        ).fetchall()
        for r in risk_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            # 检查是否有历史风评可对比
            prev = conn.execute(
                """SELECT test_result FROM risk_assessment_history
                   WHERE cust_id = ? AND tested_date < ?
                   ORDER BY tested_date DESC LIMIT 1""",
                (r["cust_id"], r["tested_date"]),
            ).fetchone()
            if not prev or prev["test_result"] == r["test_result"]:
                continue  # 无变化则跳过
            signal_id = f"SIG_RISKR_{r['cust_id']}"
            cfg = SIGNAL_TYPE_CONFIG["risk_retest"]
            conn.execute(
                """INSERT OR IGNORE INTO customer_signals
                   (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                    priority_weight, valid_from, status)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (signal_id, r["cust_id"], "risk_retest",
                 _json.dumps({"old_result": prev["test_result"], "new_result": r["test_result"],
                              "tested_date": r["tested_date"]}, ensure_ascii=False),
                 _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                 cfg["priority_weight"], sd, "active"),
            )
            if True:  # INSERT OR IGNORE already handles dedup
                new_count += 1

        # ---- 14. 洞察变化信号 (customer_insights) ----
        insight_rows = conn.execute(
            """SELECT ci.cust_id, c.name, ci.change_signals_json, ci.risk_signals_json,
                      ci.risk_level, ci.generated_at
               FROM customer_insights ci
               INNER JOIN customers c ON ci.cust_id = c.id
               WHERE ci.manager_id = ?
                 AND ci.generated_at = (
                   SELECT MAX(ci2.generated_at)
                   FROM customer_insights ci2
                   WHERE ci2.cust_id = ci.cust_id
                 )""",
            (manager_id,),
        ).fetchall()
        for r in insight_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            # 拆分为多条独立信号（change_signals 中的每条单独入库）
            try:
                change_sigs = _json.loads(r["change_signals_json"] or "[]")
            except Exception:
                change_sigs = []
            try:
                risk_sigs = _json.loads(r["risk_signals_json"] or "[]")
            except Exception:
                risk_sigs = []

            for idx, cs in enumerate(change_sigs):
                signal_id = f"SIG_INSCHG_{r['cust_id']}_{idx}"
                cfg = SIGNAL_TYPE_CONFIG["insight_change"]
                conn.execute(
                    """INSERT OR IGNORE INTO customer_signals
                       (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                        priority_weight, valid_from, status)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (signal_id, r["cust_id"], "insight_change",
                     _json.dumps({"title": cs.get("title", ""), "detail": cs.get("detail", ""),
                                  "severity": cs.get("severity", "中"),
                                  "suggested_action": cs.get("suggested_action", "")},
                                 ensure_ascii=False),
                     _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                     cfg["priority_weight"], sd, "active"),
                )
                if True:  # INSERT OR IGNORE already handles dedup
                    new_count += 1

            for idx, rs in enumerate(risk_sigs):
                signal_id = f"SIG_INSRISK_{r['cust_id']}_{idx}"
                cfg = SIGNAL_TYPE_CONFIG["insight_risk"]
                conn.execute(
                    """INSERT OR IGNORE INTO customer_signals
                       (signal_id, cust_id, signal_type, signal_data, strategy_tags,
                        priority_weight, valid_from, status)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (signal_id, r["cust_id"], "insight_risk",
                     _json.dumps({"title": rs.get("title", ""), "detail": rs.get("detail", ""),
                                  "level": rs.get("level", "medium"),
                                  "suggested_action": rs.get("suggested_action", "")},
                                 ensure_ascii=False),
                     _json.dumps(cfg["strategy_tags"], ensure_ascii=False),
                     cfg["priority_weight"], sd, "active"),
                )
                if True:  # INSERT OR IGNORE already handles dedup
                    new_count += 1

        conn.commit()
        return new_count
    finally:
        conn.close()


# ============================================================
# Step 2+3: 信号去重与商机状态维护（日常闭环维护）
# ============================================================

def _maintain_signals_and_opps(manager_id: str, schedule_date: str, conn) -> None:
    """
    每日维护：
      1. 标记已被活跃商机关联的信号 → consumed
      2. 释放已关闭/已过期商机关联的信号 → active
      3. 标记过期信号 → expired
      4. 标记过期商机 → expired
    """
    from datetime import date
    sd_date = date.fromisoformat(schedule_date) if schedule_date else date.today()
    sd = sd_date.isoformat()

    # 3a. 收集所有活跃商机的 trigger_signals
    active_opps = conn.execute(
        """SELECT opp_id, trigger_signals FROM opportunities
           WHERE manager_id = ? AND status IN ('待跟进','处理中')""",
        (manager_id,),
    ).fetchall()
    active_signal_ids = set()
    for ao in active_opps:
        ts = ao["trigger_signals"] or "[]"
        try:
            import json as _json
            sigs = _json.loads(ts)
            active_signal_ids.update(sigs)
        except Exception:
            pass

    # 3b. 标记 signal：被活跃商机关联 → consumed（只更新未标记的）
    for sids_batch in _chunk_list(list(active_signal_ids), 100):
        placeholders = ",".join("?" for _ in sids_batch)
        conn.execute(
            f"""UPDATE customer_signals SET status='consumed', consumed_at=?
                 WHERE signal_id IN ({placeholders})
                   AND status='active' AND consumed_by_opp IS NULL""",
            [sd] + sids_batch,
        )

    # 3c. 释放已关闭/已过期商机关联的信号 → active
    closed_opps = conn.execute(
        """SELECT opp_id, trigger_signals FROM opportunities
           WHERE manager_id = ? AND status IN ('已关闭','已过期')""",
        (manager_id,),
    ).fetchall()
    for co in closed_opps:
        ts = co["trigger_signals"] or "[]"
        try:
            import json as _json
            sigs = _json.loads(ts)
            for sid in sigs:
                conn.execute(
                    """UPDATE customer_signals SET status='active', consumed_by_opp=NULL, consumed_at=NULL
                       WHERE signal_id = ? AND status='consumed'""",
                    (sid,),
                )
        except Exception:
            pass

    # 3d. 标记过期信号 (valid_until < today)
    conn.execute(
        """UPDATE customer_signals SET status='expired'
           WHERE status='active' AND valid_until IS NOT NULL AND valid_until < ?""",
        (sd,),
    )

    # 3e. 标记过期商机 (生成超过 7 天且仍为待跟进)
    from datetime import timedelta
    cutoff = (sd_date - timedelta(days=7)).isoformat()
    conn.execute(
        """UPDATE opportunities SET status='已过期',
                 status_history = json_set(status_history, '$[#]',
                   json_object('from','待跟进','to','已过期','at',?,'note','超7天未跟进自动过期'))
           WHERE status='待跟进' AND generated_at < ?""",
        (sd, cutoff),
    )


def _chunk_list(lst: list, size: int) -> list[list]:
    """将列表切分为指定大小的块"""
    return [lst[i:i + size] for i in range(0, len(lst), size)]


# ============================================================
# Step 4: 商机挖掘 — 规则引擎将信号归并为商机
# ============================================================

# 信号归并规则：具有共同策略标签的信号更容易合并为一个商机
# 同一客户的信号按标签相似度分组
_SIGNAL_GROUP_RULES = [
    # (组内信号类型集合, 商机类型, 商机标题模板)
    ({"due", "salary_in"}, "资产配置", "到期资金与工资理财综合配置"),
    ({"due"}, "到期承接", "产品到期承接方案"),
    ({"overdue"}, "贷后管理", "贷款逾期跟进处理"),
    ({"big_move"}, "资金异动核实", "大额资金转出跟进"),
    ({"contact_lapse"}, "关系维护", "客户关系唤醒与需求再发现"),
    ({"salary_in"}, "代发配置", "工资代发理财配置"),
    ({"low_aum"}, "流失挽回", "低资产客户激活挽回"),
    ({"high_aum_idle"}, "资金效率", "活期闲置资金配置建议"),
    ({"fund_browse"}, "基金推荐", "基金产品配置推荐"),
    ({"wealth_browse"}, "理财推荐", "理财产品配置推荐"),
    ({"loan_browse"}, "信贷推荐", "贷款产品需求跟进"),
    ({"insurance_browse"}, "保险推荐", "保险保障需求跟进"),
    ({"risk_retest"}, "调仓建议", "风评变更后的持仓调整"),
    ({"insight_change"}, "综合跟进", "AI洞察综合跟进"),
    ({"insight_risk"}, "风险干预", "AI风险预警紧急处理"),
    # 复合组（多类信号合并）
    ({"due", "high_aum_idle"}, "资产配置", "到期资金与闲置资金综合规划"),
    ({"due", "fund_browse"}, "资产配置", "到期资金与基金配置方案"),
    ({"salary_in", "fund_browse"}, "资产配置", "工资理财与基金定投方案"),
    ({"due", "insurance_browse"}, "综合规划", "到期资金与保险保障综合规划"),
]


def mine_opportunities_from_signals(manager_id: str, schedule_date: str = None) -> int:
    """
    从 customer_signals 表中挖掘商机。
    规则引擎：按策略标签相似度将同客户的活跃信号分组，每组生成一个商机。

    Returns:
        新生成商机数量
    """
    from datetime import date, timedelta
    import json as _json
    import time as _time

    conn = _db()
    try:
        sd = schedule_date or date.today().isoformat()
        sd_date = date.fromisoformat(sd)
        now_ts = int(_time.time())
        new_opp_count = 0
        # 用于生成唯一递增序号（同一客户可能有多条同类型商机）
        _opp_seq: dict[str, int] = {}

        # 获取该经理管户的所有活跃信号（未被消费的）
        active_signals = conn.execute(
            """SELECT cs.*, c.name as cust_name
               FROM customer_signals cs
               JOIN customers c ON cs.cust_id = c.id
               WHERE cs.status = 'active'
                 AND cs.cust_id IN (
                   SELECT cust_id FROM cust_manager_rel WHERE manager_id = ?
                 )
               ORDER BY cs.cust_id, cs.priority_weight DESC""",
            (manager_id,),
        ).fetchall()

        if not active_signals:
            return 0

        # 按客户分组信号
        signals_by_cust: dict[int, list[dict]] = {}
        for s in active_signals:
            cid = s["cust_id"]
            signals_by_cust.setdefault(cid, []).append(dict(s))

        # 对每个客户，按规则归并信号为商机
        for cust_id, sigs in signals_by_cust.items():
            sig_types = set(s["signal_type"] for s in sigs)
            used_signal_ids = set()

            # 按规则顺序匹配（优先匹配复合规则）
            for rule_types, opp_type, opp_title in _SIGNAL_GROUP_RULES:
                # 检查该客户是否拥有规则要求的所有信号类型
                matching_types = rule_types & sig_types
                if not matching_types:
                    continue

                # 收集属于这些类型的、未被使用的信号
                matched_sigs = [s for s in sigs
                                if s["signal_type"] in matching_types
                                and s["signal_id"] not in used_signal_ids]
                if not matched_sigs:
                    continue

                # 标记这些信号为已使用
                for ms in matched_sigs:
                    used_signal_ids.add(ms["signal_id"])

                # 聚合信号数据为商机描述
                summaries = []
                total_pw = 0
                for ms in matched_sigs:
                    sd_data = _json.loads(ms["signal_data"] or "{}")
                    type_cfg = SIGNAL_TYPE_CONFIG.get(ms["signal_type"], {})
                    # 生成信号摘要
                    if ms["signal_type"] == "due":
                        amt = sd_data.get("total_amount", 0) / 10000
                        summaries.append(f"{sd_data.get('product_count',0)}笔到期共{amt:.0f}万")
                    elif ms["signal_type"] == "insight_change":
                        summaries.append(sd_data.get("title", "洞察变化"))
                    elif ms["signal_type"] == "insight_risk":
                        summaries.append(sd_data.get("title", "洞察预警"))
                    else:
                        summaries.append(type_cfg.get("type_name", ms["signal_type"]))
                    total_pw = max(total_pw, ms["priority_weight"])

                # 生成商机 ID（确定性，避免重复创建）
                rule_key = "_".join(sorted(matching_types))
                opp_id = f"OPP_SIG_{cust_id}_{rule_key}"

                title = f"{opp_title}（{'；'.join(summaries[:2])}）" if summaries else opp_title
                priority = "高" if total_pw >= 75 else ("中" if total_pw >= 50 else "常规")
                estimated_value = 0
                # 估算价值
                for ms in matched_sigs:
                    if ms["signal_type"] == "due":
                        sd_data = _json.loads(ms["signal_data"] or "{}")
                        estimated_value += int(sd_data.get("total_amount", 0))

                signal_id_list = [ms["signal_id"] for ms in matched_sigs]

                conn.execute(
                    """INSERT OR IGNORE INTO opportunities
                       (opp_id, cust_id, cust_name, opportunity_type, title, confidence,
                        estimated_value, reasoning, suggested_action, priority, source,
                        source_method, trigger_signals, status, generated_at, manager_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (opp_id, cust_id, matched_sigs[0].get("cust_name", ""),
                     opp_type, title, 0.7, estimated_value,
                     "；".join(summaries), "", priority,
                     "rule", "signal_mining",
                     _json.dumps(signal_id_list, ensure_ascii=False),
                     "待跟进", sd, manager_id),
                )
                if True:  # INSERT OR IGNORE already handles dedup
                    new_opp_count += 1
                    # 立即标记信号为 consumed
                    conn.execute(
                        f"""UPDATE customer_signals SET status='consumed',
                               consumed_by_opp=?, consumed_at=?
                             WHERE signal_id IN ({','.join('?' for _ in signal_id_list)})""",
                        [opp_id, sd] + signal_id_list,
                    )

            # 处理剩余未匹配的信号：每类至少生成一个商机
            remaining_sigs = [s for s in sigs if s["signal_id"] not in used_signal_ids]
            remaining_by_type: dict[str, list] = {}
            for s in remaining_sigs:
                remaining_by_type.setdefault(s["signal_type"], []).append(s)

            for stype, rsigs in remaining_by_type.items():
                if not rsigs:
                    continue
                type_cfg = SIGNAL_TYPE_CONFIG.get(stype, {})
                type_name = type_cfg.get("type_name", stype)
                signal_id_list = [s["signal_id"] for s in rsigs]

                # 生成摘要
                summaries = []
                total_pw = 0
                for s in rsigs:
                    sd_data = _json.loads(s["signal_data"] or "{}")
                    if stype == "due":
                        amt = sd_data.get("total_amount", 0) / 10000
                        summaries.append(f"{sd_data.get('product_count',0)}笔到期共{amt:.0f}万")
                    elif stype in ("insight_change", "insight_risk"):
                        summaries.append(sd_data.get("title", type_name))
                    else:
                        summaries.append(sd_data.get("title", type_name))
                    total_pw = max(total_pw, s["priority_weight"])

                opp_type_map = {
                    "due": "到期承接", "overdue": "贷后管理", "big_move": "资金异动核实",
                    "salary_in": "代发配置", "contact_lapse": "关系维护",
                    "low_aum": "流失挽回", "high_aum_idle": "资金效率",
                    "fund_browse": "基金推荐", "wealth_browse": "理财推荐",
                    "loan_browse": "信贷推荐", "insurance_browse": "保险推荐",
                    "risk_retest": "调仓建议", "insight_change": "综合跟进",
                    "insight_risk": "风险干预",
                }
                opp_type = opp_type_map.get(stype, "综合跟进")
                opp_id = f"OPP_SIG_{cust_id}_{stype}"

                title = f"{type_name}跟进（{'；'.join(summaries[:2])}）" if summaries else f"{type_name}跟进"
                priority = "高" if total_pw >= 75 else ("中" if total_pw >= 50 else "常规")

                conn.execute(
                    """INSERT OR IGNORE INTO opportunities
                       (opp_id, cust_id, cust_name, opportunity_type, title, confidence,
                        estimated_value, reasoning, suggested_action, priority, source,
                        source_method, trigger_signals, status, generated_at, manager_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (opp_id, cust_id, rsigs[0].get("cust_name", ""),
                     opp_type, title, 0.65, 0,
                     "；".join(summaries), "", priority,
                     "rule", "signal_mining",
                     _json.dumps(signal_id_list, ensure_ascii=False),
                     "待跟进", sd, manager_id),
                )
                if True:  # INSERT OR IGNORE already handles dedup
                    new_opp_count += 1
                    conn.execute(
                        f"""UPDATE customer_signals SET status='consumed',
                               consumed_by_opp=?, consumed_at=?
                             WHERE signal_id IN ({','.join('?' for _ in signal_id_list)})""",
                        [opp_id, sd] + signal_id_list,
                    )

        conn.commit()
        return new_opp_count
    finally:
        conn.close()


# ============================================================
# Step 5+6: 商机→待办  +  聚合
# ============================================================

def _aggregate_by_customer(tasks: list[dict], schedule_date: str) -> list[dict]:
    """
    将事件级任务按客户聚合为一个综合待办。

    聚合规则：
      - 按 cust_id 分组
      - 每个客户输出一条待办，包含所有子事件（sub_items）和关联商机（opp_ids）
      - priority_weight 取子事件最大值
      - summary 拼接关键子事件摘要（最多 3 项 + "等 N 项"）
      - deadline_date 取最早子事件截止日
      - task_id 改为 TK_CUST_{cust_id}
      - type_code 改为 customer_synthesis

    Returns:
        客户级聚合任务列表
    """
    from collections import defaultdict
    from datetime import date

    sd_date = date.fromisoformat(schedule_date) if schedule_date else date.today()

    groups: dict[int, list[dict]] = defaultdict(list)
    for t in tasks:
        cid = t.get("cust_id", 0)
        if cid > 0:
            groups[cid].append(t)

    aggregated = []
    for cust_id, tlist in groups.items():
        tlist.sort(key=lambda x: -x.get("priority_weight", 0))

        primary = tlist[0]
        cust_name = primary.get("cust_name", "")

        sub_items = []
        opp_ids = []
        all_summaries = []
        max_priority_weight = 0
        earliest_deadline = ""

        for t in tlist:
            tc = t.get("type_code", "")
            tn = t.get("type", "")
            summary = t.get("summary", "")
            pw = t.get("priority_weight", 0)
            dl = t.get("deadline_date", "")

            sub_items.append({
                "type_code": tc,
                "type_name": tn,
                "summary": summary,
                "priority_weight": pw,
            })
            all_summaries.append(summary)

            if pw > max_priority_weight:
                max_priority_weight = pw

            if dl:
                if not earliest_deadline or dl < earliest_deadline:
                    earliest_deadline = dl

            oid = t.get("opp_id", "")
            if oid and oid not in opp_ids:
                opp_ids.append(oid)

        top_summaries = all_summaries[:3]
        summary_text = "，".join(top_summaries)
        remaining = len(all_summaries) - 3
        if remaining > 0:
            summary_text += f" 等{remaining}项"

        if max_priority_weight >= 80:
            priority_label = "高"
        elif max_priority_weight >= 50:
            priority_label = "中"
        else:
            priority_label = "常规"

        aggregated.append({
            "task_id": f"TK_CUST_{cust_id}",
            "type": "客户综合待办",
            "type_code": "customer_synthesis",
            "cust_id": cust_id,
            "cust_name": cust_name,
            "summary": summary_text,
            "cust_count": 1,
            "priority": priority_label,
            "priority_weight": max_priority_weight,
            "deadline_date": earliest_deadline,
            "customer_ids": [cust_id],
            "customer_names": [cust_name],
            "contact_prefer": primary.get("contact_prefer", "不限定"),
            "sub_items": sub_items,
            "opp_ids": opp_ids,
        })

    return aggregated


def query_tasks_for_schedule(manager_id: str, schedule_date: str = None) -> list[dict]:
    """
    新架构：信号收集 → 商机挖掘 → 商机→待办 → 客户聚合

    Step 1: collect_signals() — 收集所有客户事件/信号
    Step 2: _maintain_signals_and_opps() — 信号去重 + 商机状态维护
    Step 3: mine_opportunities_from_signals() — 规则引擎挖掘商机
    Step 4: 从 opportunities 表捞取活跃商机 → 转为待办
    Step 5: _aggregate_by_customer() — 按客户聚合

    Returns:
        [{task_id, type_code, cust_id, ...}] 客户级聚合待办列表
    """
    from datetime import date, timedelta

    sd = schedule_date or date.today().isoformat()
    sd_date = date.fromisoformat(sd)

    # 快速检查管户列表（用完即关，避免长时间持锁）
    conn = _db()
    try:
        mgr_rows = conn.execute(
            "SELECT cust_id FROM cust_manager_rel WHERE manager_id = ?", (manager_id,)
        ).fetchall()
        mgr_cust_ids = set(r["cust_id"] for r in (mgr_rows or []))
        if not mgr_cust_ids:
            return []
    finally:
        conn.close()

    # ---- Step 1: 收集信号（独立连接，用完即关）----
    signal_count = collect_signals(manager_id, sd)
    log.info(f"query_tasks: collected {signal_count} new signals for {manager_id}")

    # ---- Step 2: 信号去重 + 商机状态维护（独立连接）----
    conn2 = _db()
    try:
        _maintain_signals_and_opps(manager_id, sd, conn2)
        conn2.commit()
    finally:
        conn2.close()

    # ---- Step 3: 商机挖掘（独立连接，用完即关）----
    opp_count = mine_opportunities_from_signals(manager_id, sd)
    log.info(f"query_tasks: mined {opp_count} new opportunities for {manager_id}")

    # ---- Step 4+5: 商机→待办 + 聚合（独立连接）----
    conn3 = _db()
    try:

        # ---- Step 4: 商机→待办 ----
        # 捞取所有活跃状态商机（待跟进 + 处理中）
        opp_rows = conn3.execute(
            """SELECT opp_id, cust_id, cust_name, title, priority, suggested_action,
                      generated_at, estimated_value, opportunity_type, source, trigger_signals
               FROM opportunities
               WHERE manager_id = ? AND status IN ('待跟进', '处理中')
                 AND generated_at >= ?
               ORDER BY priority DESC, estimated_value DESC""",
            (manager_id, (sd_date - timedelta(days=14)).isoformat()),
        ).fetchall()

        # 去重逻辑保留
        _seen_types = set()
        _kept_titles = []
        _opp_rows = []
        for r in opp_rows:
            cid = r["cust_id"]
            otype = r["opportunity_type"] or ""
            title = r["title"] or ""
            type_key = (cid, otype)
            if type_key in _seen_types:
                continue
            is_dup = False
            for kc, kt in _kept_titles:
                if kc == cid and _has_common_substring(title, kt, 10):
                    is_dup = True
                    break
            if is_dup:
                continue
            _seen_types.add(type_key)
            _kept_titles.append((cid, title))
            _opp_rows.append(r)
        opp_rows = _opp_rows

        tasks = []
        opp_type_map = {
            "代发配置": ("opp_salary", "代发配置"),
            "到期承接": ("opp_due", "到期承接"),
            "流失挽回": ("opp_decline", "流失预警"),
            "基金推荐": ("opp_fund", "基金意向"),
            "资产配置": ("opp_big_aum", "大额配置"),
            "贷后管理": ("opp_overdue", "贷后管理"),
            "资金异动核实": ("opp_big_move", "资金异动"),
            "关系维护": ("opp_lapse", "关系维护"),
            "资金效率": ("opp_idle", "资金效率"),
            "理财推荐": ("opp_wealth", "理财推荐"),
            "信贷推荐": ("opp_loan", "信贷推荐"),
            "保险推荐": ("opp_insure", "保险推荐"),
            "调仓建议": ("opp_rebalance", "调仓建议"),
            "综合跟进": ("opp_insight", "综合跟进"),
            "风险干预": ("opp_risk", "风险干预"),
            "综合规划": ("opp_plan", "综合规划"),
        }
        priority_map = {"高": 75, "中": 50, "常规": 30}

        for r in opp_rows:
            opp_deadline = (date.fromisoformat(r["generated_at"][:10]) + timedelta(days=7)).isoformat()
            pw = priority_map.get(r["priority"], 50)
            opp_type = r["opportunity_type"] or ""
            src = r["source"] or ""

            if src in ("rule", "signal_mining") and opp_type in opp_type_map:
                tc, tn = opp_type_map[opp_type]
            elif src == "AI-opp_mining":
                tc, tn = "opp", "AI挖掘"
            else:
                # signal_mining 或其他：还原类型
                mapped = opp_type_map.get(opp_type)
                tc, tn = mapped if mapped else ("opp", opp_type or "AI挖掘")

            tasks.append({
                "task_id": f"TK_OPP_{r['opp_id']}",
                "type": tn, "type_code": tc,
                "cust_id": r["cust_id"], "cust_name": r["cust_name"],
                "summary": r["title"] or "",
                "cust_count": 1, "priority": r["priority"], "priority_weight": pw,
                "deadline_date": opp_deadline,
                "customer_ids": [r["cust_id"]],
                "customer_names": [r["cust_name"]],
                "opp_id": r["opp_id"],
            })

        # ---- 批量查询 contact_prefer ----
        all_cust_ids = list(set(t["cust_id"] for t in tasks if t.get("cust_id", 0) > 0))
        contact_prefer_map = {}
        if all_cust_ids:
            placeholders = ",".join("?" for _ in all_cust_ids)
            cp_rows = conn3.execute(
                f"SELECT id, contact_prefer FROM customers WHERE id IN ({placeholders})",
                all_cust_ids,
            ).fetchall()
            contact_prefer_map = {r["id"]: r["contact_prefer"] for r in cp_rows}

        for t in tasks:
            t["contact_prefer"] = contact_prefer_map.get(t.get("cust_id", 0), "不限定")

        # ---- Step 5: 按客户聚合 ----
        tasks = _aggregate_by_customer(tasks, sd)

        return tasks
    finally:
        conn3.close()
