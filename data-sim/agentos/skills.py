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
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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
            """SELECT product_name, credit_line, used_amount, remaining,
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
                      city, education, tier, total_aum, employment_status
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
