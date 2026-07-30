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
# 日程排程 — 任务收集（基础待办 + 商机 + 洞察联动）
# ============================================================

def query_tasks_for_schedule(manager_id: str, schedule_date: str = None) -> list[dict]:
    """
    收集指定日期的全部待办任务，用于日程排程输入。
    包含三类来源：基础待办（产品到期/贷款逾期/大额异动/联络超期）
              + 商机待办（opportunities 表）
              + 洞察预警（customer_insights 表）

    Args:
        manager_id: 客户经理 ID
        schedule_date: 排程基准日期（YYYY-MM-DD），默认为今天

    Returns:
        [{task_id, type, type_code, cust_id, cust_name, summary, cust_count,
          priority, priority_weight, is_opportunity_task, deadline_date,
          customer_ids, customer_names, ...}]
    """
    from datetime import date, timedelta

    conn = _db()
    try:
        sd = schedule_date or date.today().isoformat()
        sd_date = date.fromisoformat(sd)

        # 获取该经理的管户 ID 集合
        mgr_rows = conn.execute(
            "SELECT cust_id FROM cust_manager_rel WHERE manager_id = ?", (manager_id,)
        ).fetchall()
        mgr_cust_ids = set(r["cust_id"] for r in (mgr_rows or []))
        if not mgr_cust_ids:
            return []

        tasks = []

        # ---- 1. 产品到期 ----
        due_rows = conn.execute(
            """SELECT h.cust_id, c.name, COUNT(*) as cnt, SUM(h.amount) as total,
                      MIN(h.maturity_date) as earliest_due
               FROM holdings h JOIN customers c ON h.cust_id = c.id
               WHERE h.maturity_date BETWEEN ? AND ?
               GROUP BY h.cust_id, c.name""",
            (sd, (sd_date + timedelta(days=7)).isoformat()),
        ).fetchall()
        for r in due_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            tasks.append({
                "task_id": f"TK_DUE_{r['cust_id']}",
                "type": "产品到期", "type_code": "due",
                "cust_id": r["cust_id"], "cust_name": r["name"],
                "summary": f"{r['cnt']}笔产品到期, 合计{float(r['total'] or 0)/10000:.0f}万",
                "cust_count": r["cnt"], "priority": "高", "priority_weight": 100,
                "is_opportunity_task": True,
                "deadline_date": r["earliest_due"],
                "customer_ids": [r["cust_id"]],
                "customer_names": [r["name"]],
            })

        # ---- 2. 贷款逾期 ----
        overdue_rows = conn.execute(
            """SELECT l.cust_id, c.name, l.overdue_count
               FROM loans l JOIN customers c ON l.cust_id = c.id
               WHERE l.overdue_count > 0"""
        ).fetchall()
        for r in overdue_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            tasks.append({
                "task_id": f"TK_OD_{r['cust_id']}",
                "type": "贷款逾期", "type_code": "overdue",
                "cust_id": r["cust_id"], "cust_name": r["name"],
                "summary": f"贷款逾期{r['overdue_count']}期",
                "cust_count": 1, "priority": "高", "priority_weight": 80,
                "is_opportunity_task": False,
                "deadline_date": sd,
                "customer_ids": [r["cust_id"]],
                "customer_names": [r["name"]],
            })

        # ---- 3. 大额异动 ----
        big_rows = conn.execute(
            """SELECT t.cust_id, c.name, t.amount
               FROM transactions t JOIN customers c ON t.cust_id = c.id
               WHERE t.txn_date = ? AND t.amount > 30000 AND t.txn_type = 'out'
               ORDER BY t.amount DESC LIMIT 3""",
            (sd,),
        ).fetchall()
        for r in big_rows:
            if r["cust_id"] not in mgr_cust_ids:
                continue
            tasks.append({
                "task_id": f"TK_BIG_{r['cust_id']}",
                "type": "大额异动", "type_code": "big_move",
                "cust_id": r["cust_id"], "cust_name": r["name"],
                "summary": f"昨日转出{float(r['amount'])/10000:.1f}万",
                "cust_count": 1, "priority": "高", "priority_weight": 80,
                "is_opportunity_task": True,
                "deadline_date": (sd_date + timedelta(days=1)).isoformat(),
                "customer_ids": [r["cust_id"]],
                "customer_names": [r["name"]],
            })

        # ---- 4. 联络超期 ----
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
            if r["last_date"]:
                days = (sd_date - date.fromisoformat(r["last_date"])).days
                summary = f"超期{days}天未联络"
            else:
                summary = "从未联络"
            tasks.append({
                "task_id": f"TK_CT_{r['id']}",
                "type": "联络超期", "type_code": "contact_lapse",
                "cust_id": r["id"], "cust_name": r["name"],
                "summary": summary,
                "cust_count": 1, "priority": "中", "priority_weight": 50,
                "is_opportunity_task": True,
                "deadline_date": (sd_date + timedelta(days=3)).isoformat(),
                "customer_ids": [r["id"]],
                "customer_names": [r["name"]],
            })

        # ---- 5. 商机待办（Agent 联动：opportunities 表）----
        opp_rows = conn.execute(
            """SELECT opp_id, cust_id, cust_name, title, priority, suggested_action,
                      generated_at, estimated_value
               FROM opportunities
               WHERE manager_id = ? AND status = '待跟进'
                 AND generated_at >= ?
               ORDER BY priority DESC, estimated_value DESC""",
            (manager_id, (sd_date - timedelta(days=7)).isoformat()),
        ).fetchall()
        for r in opp_rows:
            opp_deadline = (date.fromisoformat(r["generated_at"][:10]) + timedelta(days=7)).isoformat()
            priority_map = {"高": 75, "中": 50, "低": 30}
            pw = priority_map.get(r["priority"], 50)
            tasks.append({
                "task_id": f"TK_OPP_{r['opp_id']}",
                "type": "商机待办", "type_code": "opp",
                "cust_id": r["cust_id"], "cust_name": r["cust_name"],
                "summary": r["title"] or "",
                "cust_count": 1, "priority": r["priority"], "priority_weight": pw,
                "is_opportunity_task": True,
                "deadline_date": opp_deadline,
                "customer_ids": [r["cust_id"]],
                "customer_names": [r["cust_name"]],
            })

        # ---- 6. 洞察预警（Agent 联动：customer_insights 表）----
        import json as _json
        insight_rows = conn.execute(
            """SELECT ci.cust_id, c.name, ci.risk_level, ci.change_signals_json,
                      ci.risk_signals_json, ci.generated_at
               FROM customer_insights ci
               INNER JOIN customers c ON ci.cust_id = c.id
               WHERE ci.manager_id = ?
                 AND ci.generated_at = (
                   SELECT MAX(ci2.generated_at)
                   FROM customer_insights ci2
                   WHERE ci2.cust_id = ci.cust_id
                 )
                 AND (ci.risk_level IN ('orange', 'red')
                      OR (ci.change_signals_json IS NOT NULL
                          AND ci.change_signals_json != ''
                          AND ci.change_signals_json != '[]'))
               ORDER BY CASE ci.risk_level
                   WHEN 'red' THEN 0 WHEN 'orange' THEN 1 ELSE 2 END""",
            (manager_id,),
        ).fetchall()
        for r in insight_rows:
            has_risk = r["risk_level"] in ("orange", "red")
            has_change = bool(r["change_signals_json"] and r["change_signals_json"] not in ("", "[]"))
            signals = []
            if has_risk:
                try:
                    risk_sigs = _json.loads(r["risk_signals_json"] or "[]")
                    signals.extend([s.get("title", "风险信号") for s in risk_sigs[:2]])
                except Exception:
                    pass
            if has_change:
                try:
                    change_sigs = _json.loads(r["change_signals_json"] or "[]")
                    signals.extend([s.get("title", "变化信号") for s in change_sigs[:1]])
                except Exception:
                    pass
            summary = "；".join(signals) if signals else "洞察预警"

            tasks.append({
                "task_id": f"TK_INS_{r['cust_id']}",
                "type": "洞察预警", "type_code": "insight_alert",
                "cust_id": r["cust_id"], "cust_name": r["name"],
                "summary": summary,
                "cust_count": 1, "priority": "高", "priority_weight": 75,
                "is_opportunity_task": False,
                "deadline_date": (sd_date + timedelta(days=2)).isoformat(),
                "customer_ids": [r["cust_id"]],
                "customer_names": [r["name"]],
            })

        # ---- 7. 批量查询 contact_prefer（客户联系时段偏好）----
        all_cust_ids = list(set(
            t["cust_id"] for t in tasks if t.get("cust_id", 0) > 0
        ))
        contact_prefer_map = {}
        if all_cust_ids:
            placeholders = ",".join("?" for _ in all_cust_ids)
            cp_rows = conn.execute(
                f"SELECT id, contact_prefer FROM customers WHERE id IN ({placeholders})",
                all_cust_ids,
            ).fetchall()
            contact_prefer_map = {r["id"]: r["contact_prefer"] for r in cp_rows}

        for t in tasks:
            t["contact_prefer"] = contact_prefer_map.get(t.get("cust_id", 0), "不限定")

        return tasks
    finally:
        conn.close()
