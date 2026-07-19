"""
易会办 客户洞察模拟数据集 — FastAPI 数据查询服务
提供26个 RESTful 接口，按客户画像模块分段查询
"""
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta, datetime
from typing import Optional, List

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ============================================================
# 配置
# ============================================================
DB_CONFIG = "dbname=yihuiban_sim user=yihuiban password=yihuiban_dev host=localhost port=5432"
TODAY = date.today()

app = FastAPI(title="易会办 客户洞察 API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

pool = ThreadPoolExecutor(max_workers=8)

# ============================================================
# 数据库辅助
# ============================================================
def get_conn():
    return psycopg2.connect(DB_CONFIG)

def query(sql: str, params=None, one=False):
    """同步查询, 返回 dict 列表"""
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = cur.fetchone() if one else cur.fetchall()
        cur.close()
        return [dict(r) for r in rows] if not one and rows else (dict(rows) if rows and one else None)
    finally:
        conn.close()

def execute(sql: str, params=None):
    """同步执行 INSERT/UPDATE"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
    finally:
        conn.close()

async def aquery(sql: str, params=None, one=False):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(pool, lambda: query(sql, params, one))

async def aexecute(sql: str, params=None):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(pool, lambda: execute(sql, params))

# ============================================================
# 公共函数
# ============================================================
def ok(data=None, message="ok"):
    return {"code": 0, "data": data, "message": message}

def err(code: int, message: str):
    return {"code": code, "data": None, "message": message}

def _fmt_date(d):
    if d is None:
        return None
    if isinstance(d, (date, datetime)):
        return d.isoformat()
    return str(d)

def _row_or_none(row):
    """dict → None 如果为空"""
    if row is None:
        return None
    # 检查所有值是否为 None
    if all(v is None for v in row.values()):
        return None
    return row

# ============================================================
# 5.2.1 客户搜索与摘要
# ============================================================
@app.get("/api/customers")
async def customer_list(
    keyword: str = Query(None, description="姓名/手机号模糊搜索"),
    tier: str = Query(None, description="等级筛选, 逗号分隔"),
    risk_level: str = Query(None, description="风测等级"),
    employment: str = Query(None, description="就业状态"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    where = []
    params = []
    if keyword:
        where.append("(c.name ILIKE %s OR c.phone_masked ILIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if tier:
        tiers = [t.strip() for t in tier.split(",")]
        where.append("c.tier::text = ANY(%s)")
        params.append(tiers)
    if risk_level:
        where.append("EXISTS (SELECT 1 FROM risk_assessments r WHERE r.cust_id=c.id AND r.test_result=%s)")
        params.append(risk_level)
    if employment:
        where.append("c.employment_status::text = %s")
        params.append(employment)

    where_clause = " AND ".join(where) if where else "1=1"
    offset = (page - 1) * size

    total_row = await aquery(f"SELECT COUNT(*) as cnt FROM customers c WHERE {where_clause}", params, one=True)
    total = total_row["cnt"] if total_row else 0

    rows = await aquery(
        f"SELECT c.id, c.cust_no, c.name, c.age, c.gender, c.occupation, c.city, c.tier, "
        f"c.total_aum, c.employment_status FROM customers c "
        f"WHERE {where_clause} ORDER BY c.total_aum DESC LIMIT %s OFFSET %s",
        params + [size, offset]
    )

    items = []
    for r in (rows or []):
        items.append({
            "id": r["id"], "cust_no": r["cust_no"], "name": r["name"],
            "age": r["age"], "gender": "男" if r["gender"] == "M" else "女",
            "city": r["city"], "occupation": r["occupation"],
            "tier": r["tier"], "total_aum": r["total_aum"],
            "employment_status": r["employment_status"],
        })

    return ok({"customers": items, "total": total, "page": page, "size": size})


# ============================================================
# 5.2.2 客户画像 — 聚合入口
# ============================================================
@app.get("/api/customers/{cust_id}/profile")
async def customer_profile(cust_id: int):
    # 并行查询6个模块
    basic, family, business, wealth, credit, behavior, emp_detail = await asyncio.gather(
        aquery("SELECT id,name,age,gender,occupation,industry,city,education,tier,total_aum,employment_status FROM customers WHERE id=%s", (cust_id,), one=True),
        aquery("SELECT marriage,children,child_count,child_age,child_education,study_abroad_intent,study_abroad_target_country,spouse_has_income FROM family_info WHERE cust_id=%s", (cust_id,), one=True),
        aquery("SELECT business_name,duration_years,share_ratio,reg_capital,address,scope,continuity,verified,verified_source FROM business_info WHERE cust_id=%s", (cust_id,), one=True),
        aquery("SELECT total_aum,tier FROM customers WHERE id=%s", (cust_id,), one=True),
        aquery("SELECT COUNT(*) as loan_count FROM loans WHERE cust_id=%s", (cust_id,), one=True),
        aquery("SELECT COUNT(*) as log_count FROM behavior_logs WHERE cust_id=%s", (cust_id,), one=True),
        aquery("SELECT status,unemployment_benefits,benefit_amount,benefit_start_date,benefit_end_date,verified,last_verified_date FROM employment_status WHERE cust_id=%s", (cust_id,), one=True),
    )

    if not basic:
        raise HTTPException(404, "客户不存在")

    loaded = ["basic"]
    basic_data = {"name": basic["name"], "age": basic["age"], "gender": "男" if basic["gender"] == "M" else "女",
                  "occupation": basic["occupation"], "industry": basic["industry"], "city": basic["city"],
                  "education": basic["education"], "tier": basic["tier"], "employment_status": basic["employment_status"]}

    family_data = None
    if family:
        loaded.append("family")
        family_data = {"marriage": family["marriage"], "children": family["children"],
                       "child_count": family["child_count"], "child_age": family["child_age"],
                       "child_education": family["child_education"], "study_abroad_intent": family["study_abroad_intent"],
                       "study_abroad_target_country": family["study_abroad_target_country"],
                       "spouse_has_income": family["spouse_has_income"]}

    business_data = None
    if business:
        loaded.append("business")
        business_data = {"business_name": business["business_name"], "duration_years": business["duration_years"],
                         "share_ratio": float(business["share_ratio"]) if business["share_ratio"] else None,
                         "reg_capital": float(business["reg_capital"]) if business["reg_capital"] else None,
                         "address": business["address"], "scope": business["scope"],
                         "verified": business["verified"], "verified_source": business["verified_source"]}

    wealth_summary = {"total_aum": float(wealth["total_aum"]) if wealth else 0, "tier": wealth["tier"] if wealth else None,
                      "wealth_score": None, "yoy_return": None}

    credit_summary = {"loan_count": credit["loan_count"] if credit else 0, "overdue_count": 0, "rejection_count": 0}

    behavior_summary = {"fin_prefs": [], "risk_result": None, "liquidity": None}

    emp_detail_data = None
    if emp_detail:
        loaded.append("employment")
        emp_detail_data = {"status": emp_detail["status"], "unemployment_benefits": emp_detail["unemployment_benefits"],
                           "benefit_amount": float(emp_detail["benefit_amount"]) if emp_detail["benefit_amount"] else None,
                           "benefit_start_date": _fmt_date(emp_detail["benefit_start_date"]),
                           "benefit_end_date": _fmt_date(emp_detail["benefit_end_date"]),
                           "verified": emp_detail["verified"], "last_verified_date": _fmt_date(emp_detail["last_verified_date"])}

    # 补充风测结果
    if behavior["log_count"] > 0:
        loaded.append("behavior")
        risk_row = await aquery("SELECT test_result FROM risk_assessments WHERE cust_id=%s", (cust_id,), one=True)
        if risk_row:
            behavior_summary["risk_result"] = risk_row["test_result"]

    return ok({
        "loaded_modules": loaded,
        "basic": basic_data,
        "family": family_data,
        "business": business_data,
        "wealth_summary": wealth_summary,
        "credit_summary": credit_summary,
        "behavior_summary": behavior_summary,
        "employment_detail": emp_detail_data,
    })


# ============================================================
# 5.2.3 画像分段 — 基础信息 + 家庭 + 就业
# ============================================================
@app.get("/api/customers/{cust_id}/basic")
async def customer_basic(cust_id: int):
    row = await aquery(
        "SELECT id,name,age,gender,occupation,industry,city,education,tier,total_aum,employment_status FROM customers WHERE id=%s",
        (cust_id,), one=True)
    if not row:
        raise HTTPException(404, "客户不存在")
    return ok({
        "id": row["id"], "name": row["name"], "age": row["age"],
        "gender": "男" if row["gender"] == "M" else "女", "occupation": row["occupation"],
        "industry": row["industry"], "city": row["city"], "education": row["education"],
        "tier": row["tier"], "total_aum": float(row["total_aum"]),
        "employment_status": row["employment_status"],
    })


@app.get("/api/customers/{cust_id}/family")
async def customer_family(cust_id: int):
    row = await aquery(
        "SELECT marriage,children,child_count,child_age,child_education,study_abroad_intent,"
        "study_abroad_target_country,spouse_has_income FROM family_info WHERE cust_id=%s",
        (cust_id,), one=True)
    return ok(_row_or_none(row))


@app.get("/api/customers/{cust_id}/employment")
async def customer_employment(cust_id: int):
    row = await aquery(
        "SELECT status,unemployment_benefits,benefit_amount,benefit_start_date,benefit_end_date,"
        "verified,last_verified_date FROM employment_status WHERE cust_id=%s",
        (cust_id,), one=True)
    return ok(_row_or_none(row))


# ============================================================
# 5.2.4 画像分段 — 经营信息
# ============================================================
@app.get("/api/customers/{cust_id}/business")
async def customer_business(cust_id: int):
    row = await aquery(
        "SELECT business_name,duration_years,share_ratio,reg_capital,address,scope,continuity,verified,verified_source "
        "FROM business_info WHERE cust_id=%s",
        (cust_id,), one=True)
    return ok(_row_or_none(row))


# ============================================================
# 5.2.5 画像分段 — 财富解读(4个子接口)
# ============================================================
@app.get("/api/customers/{cust_id}/wealth/summary")
async def wealth_summary(cust_id: int):
    row = await aquery(
        "SELECT total_aum,tier FROM customers WHERE id=%s", (cust_id,), one=True)
    if not row:
        raise HTTPException(404, "客户不存在")

    risk_row = await aquery(
        "SELECT wealth_score,score_time,dimension_asset,dimension_income,dimension_social "
        "FROM risk_assessments WHERE cust_id=%s", (cust_id,), one=True)

    # 标签
    tags = []
    h_count = await aquery("SELECT COUNT(*) as cnt FROM holdings WHERE cust_id=%s", (cust_id,), one=True)
    if h_count and h_count["cnt"] >= 5:
        tags.append("多元配置")
    if risk_row and risk_row["wealth_score"]:
        if risk_row["wealth_score"] >= 70:
            tags.append("优质客户")
        elif risk_row["wealth_score"] >= 40:
            tags.append("成长客户")
        else:
            tags.append("待培养")

    return ok({
        "total_aum": float(row["total_aum"]), "tier": row["tier"],
        "tier_label": row["tier"],
        "tags": tags,
        "wealth_score": risk_row["wealth_score"] if risk_row else None,
        "score_time": _fmt_date(risk_row["score_time"]) if risk_row else None,
        "score_dimensions": {
            "asset": float(risk_row["dimension_asset"]) if risk_row and risk_row["dimension_asset"] else None,
            "income": float(risk_row["dimension_income"]) if risk_row and risk_row["dimension_income"] else None,
            "social": float(risk_row["dimension_social"]) if risk_row and risk_row["dimension_social"] else None,
        } if risk_row else None,
    })


@app.get("/api/customers/{cust_id}/wealth/holdings")
async def wealth_holdings(cust_id: int):
    rows = await aquery(
        "SELECT product_type,product_name,product_code,amount,yield_rate,risk_level,maturity_date,purchase_date,status "
        "FROM holdings WHERE cust_id=%s ORDER BY amount DESC", (cust_id,))
    if not rows:
        return ok(None)

    dist = {}
    total_scale = 0
    details = []
    for r in rows:
        pt = r["product_type"]
        amt = float(r["amount"])
        total_scale += amt
        dist[pt] = dist.get(pt, 0) + amt
        details.append({
            "product_name": r["product_name"], "product_type": r["product_type"],
            "product_code": r["product_code"], "amount": amt,
            "yield_rate": float(r["yield_rate"]) if r["yield_rate"] else None,
            "risk_level": r["risk_level"], "maturity_date": _fmt_date(r["maturity_date"]),
            "purchase_date": _fmt_date(r["purchase_date"]), "status": r["status"],
        })

    return ok({
        "total_scale": total_scale,
        "distribution": {
            "deposit": dist.get("存款", 0),
            "wealth_mgmt": dist.get("理财", 0),
            "fund": dist.get("基金", 0),
            "precious_metal": dist.get("贵金属", 0),
            "insurance": dist.get("保险", 0),
        },
        "details": details,
        "cumulative_return": None, "annual_return": None, "peak_month": None,
    })


@app.get("/api/customers/{cust_id}/wealth/fund-flow")
async def wealth_fund_flow(cust_id: int, months: int = Query(12, ge=1, le=24)):
    since = TODAY - timedelta(days=months * 30)
    rows = await aquery(
        "SELECT txn_type,amount,summary FROM transactions WHERE cust_id=%s AND txn_date >= %s",
        (cust_id, since))
    if not rows:
        return ok(None)

    inflow = sum(float(r["amount"]) for r in rows if r["txn_type"] == "in")
    outflow = sum(float(r["amount"]) for r in rows if r["txn_type"] == "out")

    sources = {}
    out_dist = {}
    for r in rows:
        s = r["summary"] or "其他"
        if r["txn_type"] == "in":
            sources[s] = sources.get(s, 0) + float(r["amount"])
        else:
            out_dist[s] = out_dist.get(s, 0) + float(r["amount"])

    return ok({
        "yearly_inflow": round(inflow, 2),
        "inflow_sources": dict(sorted(sources.items(), key=lambda x: -x[1])[:5]),
        "yearly_outflow": round(outflow, 2),
        "outflow_distribution": dict(sorted(out_dist.items(), key=lambda x: -x[1])[:5]),
        "retention_desc": "资金留存率较高" if inflow > outflow * 0.8 else "资金流出现象需关注",
    })


@app.get("/api/customers/{cust_id}/wealth/salary")
async def wealth_salary(cust_id: int):
    since = TODAY - timedelta(days=210)
    rows = await aquery(
        "SELECT txn_date,amount FROM transactions WHERE cust_id=%s AND txn_type='in' AND summary='工资' "
        "AND txn_date >= %s ORDER BY txn_date DESC", (cust_id, since))
    if not rows:
        return ok(None)

    amounts = [float(r["amount"]) for r in rows]
    current_month = amounts[0] if amounts else 0
    avg_6m = round(sum(amounts[:6]) / min(6, len(amounts)), 2) if amounts else 0
    peak = max(amounts) if amounts else 0

    salary_level = "高收入" if avg_6m > 15000 else ("中等收入" if avg_6m > 8000 else "入门收入")

    return ok({
        "current_month_amount": round(current_month, 2),
        "current_month_date": _fmt_date(rows[0]["txn_date"]) if rows else None,
        "avg_6m": avg_6m,
        "peak_amount": round(peak, 2),
        "salary_level": salary_level,
        "retain_3d": None,
        "retain_7d": None,
    })


# ============================================================
# 5.2.6 画像分段 — 信贷解读
# ============================================================
@app.get("/api/customers/{cust_id}/credit/loans")
async def credit_loans(cust_id: int):
    rows = await aquery(
        "SELECT product_name,credit_line,used_amount,remaining,overdue_count,interest_rate,start_date,maturity_date "
        "FROM loans WHERE cust_id=%s", (cust_id,))
    if not rows:
        return ok(None)
    items = [{
        "product_name": r["product_name"],
        "credit_line": float(r["credit_line"]), "used": float(r["used_amount"]),
        "remaining": float(r["remaining"]), "overdue_count": r["overdue_count"],
        "interest_rate": float(r["interest_rate"]) if r["interest_rate"] else None,
        "start_date": _fmt_date(r["start_date"]), "maturity_date": _fmt_date(r["maturity_date"]),
    } for r in rows]
    return ok({"loans": items, "total_count": len(items)})


@app.get("/api/customers/{cust_id}/credit/rejections")
async def credit_rejections(cust_id: int):
    rows = await aquery(
        "SELECT product_name,reject_reason,rejected_date FROM loan_rejections WHERE cust_id=%s",
        (cust_id,))
    if not rows:
        return ok(None)
    items = [{"product_name": r["product_name"], "reason": r["reject_reason"],
              "rejected_date": _fmt_date(r["rejected_date"])} for r in rows]
    return ok({"rejections": items, "total_count": len(items)})


@app.get("/api/customers/{cust_id}/credit/social-security")
async def credit_social_security(cust_id: int):
    # 从代发工资推断公积金/社保基数
    row = await aquery("SELECT total_aum FROM customers WHERE id=%s", (cust_id,), one=True)
    if not row:
        raise HTTPException(404, "客户不存在")
    # 模拟: 如果有代发工资, 显示社保信息
    has_salary = await aquery(
        "SELECT COUNT(*) as cnt FROM transactions WHERE cust_id=%s AND summary='工资'", (cust_id,), one=True)
    if has_salary and has_salary["cnt"] > 0:
        base = round(float(row["total_aum"]) * 0.1, 2)  # 简化推断
        return ok({
            "housing_fund_base": base, "housing_fund_period": random_period(),
            "social_security_base": base * 1.2, "social_security_period": random_period(),
        })
    return ok(None)


def random_period():
    return f"{random.randint(3,15)}年{random.randint(0,11)}个月"

import random as _random


# ============================================================
# 5.2.7 画像分段 — 行为洞察
# ============================================================
@app.get("/api/customers/{cust_id}/behavior/preferences")
async def behavior_preferences(cust_id: int):
    # 统计行为偏好
    rows = await aquery(
        "SELECT page_type,COUNT(*) as cnt FROM behavior_logs WHERE cust_id=%s GROUP BY page_type ORDER BY cnt DESC",
        (cust_id,))
    if not rows:
        return ok(None)

    total = sum(r["cnt"] for r in rows)
    fin_prefs = []
    for r in rows:
        if r["cnt"] >= 3:
            fin_prefs.append({"label": f"{r['page_type']}偏好", "basis": f"近3个月{r['page_type']}浏览{r['cnt']}次, 占比{r['cnt']*100//total}%"})

    # 风测
    risk_row = await aquery("SELECT test_result FROM risk_assessments WHERE cust_id=%s", (cust_id,), one=True)

    # 渠道偏好
    ch_rows = await aquery(
        "SELECT channel,COUNT(*) as cnt FROM behavior_logs WHERE cust_id=%s GROUP BY channel ORDER BY cnt DESC",
        (cust_id,))

    # 参与活动
    act_count = await aquery("SELECT COUNT(*) as cnt FROM customer_activity_participation WHERE cust_id=%s", (cust_id,), one=True)

    return ok({
        "fin_prefs": fin_prefs,
        "liquidity": "高" if total > 80 else ("中" if total > 30 else "低"),
        "risk": {
            "test_result": risk_row["test_result"] if risk_row else None,
            "browse_distribution": {r["page_type"]: r["cnt"] for r in rows},
        },
        "marketing": {
            "channel_prefs": [r["channel"] for r in (ch_rows or [])[:3]],
            "activity_count_3m": act_count["cnt"] if act_count else 0,
            "best_contact_time": "工作日10:00-11:00",
        },
    })


@app.get("/api/customers/{cust_id}/behavior/logs")
async def behavior_logs_api(cust_id: int, days: int = Query(90, ge=1, le=365), page: int = Query(1), size: int = Query(50, le=200)):
    since = TODAY - timedelta(days=days)
    total_row = await aquery("SELECT COUNT(*) as cnt FROM behavior_logs WHERE cust_id=%s AND event_date >= %s", (cust_id, since), one=True)
    total = total_row["cnt"] if total_row else 0
    offset = (page - 1) * size

    rows = await aquery(
        "SELECT event_date,event_time,channel,page_type,action,duration_sec,product_code,product_type "
        "FROM behavior_logs WHERE cust_id=%s AND event_date >= %s ORDER BY event_date DESC, event_time DESC LIMIT %s OFFSET %s",
        (cust_id, since, size, offset))

    items = [{"date": _fmt_date(r["event_date"]), "time": str(r["event_time"]), "channel": r["channel"],
              "page_type": r["page_type"], "action": r["action"], "duration_sec": r["duration_sec"],
              "product_code": r["product_code"], "product_type": r["product_type"]} for r in (rows or [])]
    return ok({"logs": items, "total": total, "page": page})


# ============================================================
# 5.2.8 关系图谱
# ============================================================
@app.get("/api/customers/{cust_id}/relations")
async def customer_relations_api(cust_id: int):
    rows = await aquery(
        "SELECT cr.id, cr.cust_id_a, cr.cust_id_b, cr.relation_type, cr.evidence, cr.evidence_field, "
        "c1.name as name_a, c1.tier as tier_a, c1.total_aum as aum_a, "
        "c2.name as name_b, c2.tier as tier_b, c2.total_aum as aum_b "
        "FROM customer_relations cr "
        "JOIN customers c1 ON cr.cust_id_a=c1.id "
        "JOIN customers c2 ON cr.cust_id_b=c2.id "
        "WHERE cr.cust_id_a=%s OR cr.cust_id_b=%s", (cust_id, cust_id))
    if not rows:
        return ok({"relations": [], "count": 0})

    items = []
    for r in rows:
        is_a = r["cust_id_a"] == cust_id
        target_id = r["cust_id_b"] if is_a else r["cust_id_a"]
        target_name = r["name_b"] if is_a else r["name_a"]
        target_tier = r["tier_b"] if is_a else r["tier_a"]
        target_aum = float(r["aum_b"]) if is_a else float(r["aum_a"])
        items.append({
            "target_cust_id": target_id, "target_name": target_name,
            "relation_type": r["relation_type"], "evidence": r["evidence"],
            "target_tier": target_tier, "target_aum": target_aum,
        })
    return ok({"relations": items, "count": len(items)})


# ============================================================
# 5.2.9 权益与活动
# ============================================================
@app.get("/api/customers/{cust_id}/benefits")
async def customer_benefits_api(cust_id: int):
    rows = await aquery(
        "SELECT benefit_name,benefit_type,description,tier_requirement,rarity,acquired_date,expiry_date,status "
        "FROM customer_benefits WHERE cust_id=%s ORDER BY acquired_date DESC", (cust_id,))
    if not rows:
        return ok({"benefits": [], "eligible_count": 0})

    items = [{"benefit_name": r["benefit_name"], "type": r["benefit_type"],
              "description": r["description"], "rarity": r["rarity"],
              "acquired_date": _fmt_date(r["acquired_date"]), "expiry_date": _fmt_date(r["expiry_date"]),
              "status": r["status"]} for r in rows]
    # eligible_count: 同等级可获取但未持有的权益数
    cust = await aquery("SELECT tier FROM customers WHERE id=%s", (cust_id,), one=True)
    tier_order = ["千元以下", "千元户", "万元户", "优质", "财富", "高净值", "私钻", "私行"]
    c_tier_idx = tier_order.index(cust["tier"]) if cust and cust["tier"] in tier_order else 0
    has_names = {r["benefit_name"] for r in rows}
    eligible = sum(1 for b in _benefit_pool() if tier_order.index(b[3]) <= c_tier_idx and b[0] not in has_names)
    return ok({"benefits": items, "eligible_count": eligible})


def _benefit_pool():
    return [
        ("机场贵宾厅", "出行", "每年6次免费使用", "财富", "稀有"),
        ("三甲医院体检", "健康", "每年1次VIP体检套餐", "高净值", "稀有"),
        ("商超满减券", "购物", "满200减50", "优质", "普通"),
        ("子女教育咨询", "教育", "专业教育规划师1对1咨询", "财富", "限时"),
        ("高端餐厅折扣", "美食", "指定餐厅8折", "财富", "普通"),
        ("留学规划服务", "教育", "免费留学规划1次", "私钻", "稀有"),
        ("代驾服务", "出行", "每年12次免费代驾", "高净值", "限时"),
        ("生日礼遇", "购物", "生日当月专属礼品", "优质", "普通"),
        ("高尔夫练习场", "健康", "每月2次免费", "私钻", "稀有"),
        ("法律咨询服务", "其他", "免费法律咨询1次", "私行", "限时"),
    ]


@app.get("/api/customers/{cust_id}/activities")
async def customer_activities_api(cust_id: int):
    cust = await aquery("SELECT tier FROM customers WHERE id=%s", (cust_id,), one=True)
    if not cust:
        raise HTTPException(404, "客户不存在")

    # 已参与
    participated = await aquery(
        "SELECT cap.activity_id,aa.title,aa.type,cap.participated_date,cap.status,cap.result_note "
        "FROM customer_activity_participation cap "
        "JOIN available_activities aa ON cap.activity_id=aa.activity_id "
        "WHERE cap.cust_id=%s ORDER BY cap.participated_date DESC", (cust_id,))

    # 可参与 (同等级或以下)
    tier_order = ["千元以下", "千元户", "万元户", "优质", "财富", "高净值", "私钻", "私行"]
    c_tier_idx = tier_order.index(cust["tier"]) if cust["tier"] in tier_order else 3
    eligible_tiers = tier_order[:c_tier_idx + 1]

    all_acts = await aquery("SELECT activity_id,title,type,start_date,end_date,description,target_tier,reward_desc FROM available_activities WHERE end_date >= %s ORDER BY start_date", (TODAY,))

    participated_ids = {p["activity_id"] for p in (participated or [])}
    available = []
    for a in (all_acts or []):
        if a["activity_id"] not in participated_ids and a["target_tier"] in eligible_tiers:
            available.append({
                "activity_id": a["activity_id"], "title": a["title"], "type": a["type"],
                "start_date": _fmt_date(a["start_date"]), "end_date": _fmt_date(a["end_date"]),
                "description": a["description"], "reward_desc": a["reward_desc"],
            })

    return ok({
        "participated": [{"activity_id": p["activity_id"], "title": p["title"], "type": p["type"],
                          "participated_date": _fmt_date(p["participated_date"]),
                          "status": p["status"], "result_note": p["result_note"]} for p in (participated or [])],
        "available": available[:5],  # 限制5条
    })


@app.get("/api/activities")
async def activities_list(
    type_: str = Query(None, alias="type"),
    tier: str = Query(None),
):
    where = ["aa.end_date >= %s"]
    params = [TODAY]
    if type_:
        where.append("aa.type = %s")
        params.append(type_)
    if tier:
        where.append("aa.target_tier = %s")
        params.append(tier)

    rows = await aquery(
        f"SELECT activity_id,title,type,start_date,end_date,description,target_tier,reward_desc "
        f"FROM available_activities aa WHERE {' AND '.join(where)} ORDER BY start_date", params)
    items = [{"activity_id": r["activity_id"], "title": r["title"], "type": r["type"],
              "start_date": _fmt_date(r["start_date"]), "end_date": _fmt_date(r["end_date"]),
              "description": r["description"], "target_tier": r["target_tier"],
              "reward_desc": r["reward_desc"]} for r in (rows or [])]
    return ok({"activities": items})


# ============================================================
# 5.2.10 待办与商机
# ============================================================
@app.get("/api/tasks")
async def tasks(date_: str = Query(None, alias="date")):
    target_date = date.fromisoformat(date_) if date_ else TODAY
    tasks_list = []

    # 1. 产品到期待办
    due_rows = await aquery(
        "SELECT h.cust_id,c.name,COUNT(*) as cnt,MIN(h.maturity_date) as nearest "
        "FROM holdings h JOIN customers c ON h.cust_id=c.id "
        "WHERE h.maturity_date BETWEEN %s AND %s GROUP BY h.cust_id,c.name",
        (target_date - timedelta(days=2), target_date + timedelta(days=7)))
    for r in (due_rows or []):
        tasks_list.append({
            "task_id": f"TK_DUE_{r['cust_id']}", "type": "产品到期",
            "cust_id": r["cust_id"], "cust_name": r["name"],
            "summary": f"{r['cnt']}笔产品将于{r['nearest']}起陆续到期",
            "priority": "高" if r["cnt"] >= 3 else "中",
            "suggested_time": "09:30", "estimated_duration": 30,
            "is_opportunity_task": True, "battle_package_id": None,
        })

    # 2. 贷款逾期
    overdue_rows = await aquery(
        "SELECT l.cust_id,c.name FROM loans l JOIN customers c ON l.cust_id=c.id WHERE l.overdue_count > 0")
    for r in (overdue_rows or []):
        tasks_list.append({
            "task_id": f"TK_OVERDUE_{r['cust_id']}", "type": "贷款逾期",
            "cust_id": r["cust_id"], "cust_name": r["name"],
            "summary": "贷款有逾期记录, 需跟进",
            "priority": "高", "suggested_time": "10:00", "estimated_duration": 20,
            "is_opportunity_task": False, "battle_package_id": None,
        })

    # 3. 联络超期(>14天)
    comm_rows = await aquery(
        "SELECT c.id,c.name,MAX(cm.comm_date) as last_contact FROM customers c "
        "LEFT JOIN communications cm ON c.id=cm.cust_id GROUP BY c.id,c.name "
        "HAVING MAX(cm.comm_date) < %s OR MAX(cm.comm_date) IS NULL",
        (target_date - timedelta(days=14),))
    for r in (comm_rows or [])[:10]:
        tasks_list.append({
            "task_id": f"TK_CONTACT_{r['id']}", "type": "联络超期",
            "cust_id": r["id"], "cust_name": r["name"],
            "summary": f"上次联络超过14天",
            "priority": "中", "suggested_time": "14:00", "estimated_duration": 15,
            "is_opportunity_task": True, "battle_package_id": None,
        })

    # 4. 大额异动(昨日)
    big_rows = await aquery(
        "SELECT t.cust_id,c.name,t.amount FROM transactions t JOIN customers c ON t.cust_id=c.id "
        "WHERE t.txn_date=%s AND t.amount>50000 ORDER BY t.amount DESC",
        (target_date - timedelta(days=1),))
    for r in (big_rows or []):
        tasks_list.append({
            "task_id": f"TK_BIG_{r['cust_id']}", "type": "大额异动",
            "cust_id": r["cust_id"], "cust_name": r["name"],
            "summary": f"昨日大额{float(r['amount']):,.0f}元转出",
            "priority": "高", "suggested_time": "09:00", "estimated_duration": 15,
            "is_opportunity_task": True, "battle_package_id": None,
        })

    return ok({"tasks": tasks_list, "total": len(tasks_list)})


@app.get("/api/opportunities")
async def opportunities():
    opps = []
    # 规则匹配: 代发到账
    salary_rows = await aquery(
        "SELECT DISTINCT t.cust_id,c.name FROM transactions t JOIN customers c ON t.cust_id=c.id "
        "WHERE t.summary='工资' AND t.txn_date >= %s", (TODAY - timedelta(days=7),))
    for r in (salary_rows or []):
        opps.append({
            "opp_id": f"OPP_SALARY_{r['cust_id']}", "source": "规则匹配",
            "cust_id": r["cust_id"], "cust_name": r["name"],
            "type": "代发到账配置", "estimated_value": 20000,
            "confidence": 0.75, "reasoning": "近7天有代发工资到账, 可推荐工资理财配置",
            "status": "待跟进",
        })

    # 规则匹配: 产品到期
    due_rows = await aquery(
        "SELECT h.cust_id,c.name,SUM(h.amount) as total FROM holdings h JOIN customers c ON h.cust_id=c.id "
        "WHERE h.maturity_date BETWEEN %s AND %s GROUP BY h.cust_id,c.name",
        (TODAY, TODAY + timedelta(days=30)))
    for r in (due_rows or []):
        opps.append({
            "opp_id": f"OPP_DUE_{r['cust_id']}", "source": "规则匹配",
            "cust_id": r["cust_id"], "cust_name": r["name"],
            "type": "产品到期承接", "estimated_value": float(r["total"]),
            "confidence": 0.85, "reasoning": f"30天内{float(r['total']):,.0f}元产品到期",
            "status": "待跟进",
        })

    # 规则匹配: 流失预警
    decline_rows = await aquery(
        "SELECT c.id,c.name FROM customers c "
        "WHERE c.total_aum < 50000 AND c.tier IN ('千元以下','千元户') ORDER BY c.total_aum ASC LIMIT 5")
    for r in (decline_rows or []):
        opps.append({
            "opp_id": f"OPP_DECLINE_{r['id']}", "source": "AI挖掘",
            "cust_id": r["id"], "cust_name": r["name"],
            "type": "流失预警挽回", "estimated_value": 5000,
            "confidence": 0.55, "reasoning": "AUM持续走低, 建议联系了解原因",
            "status": "待跟进",
        })

    total_value = sum(o["estimated_value"] for o in opps)
    return ok({
        "opportunities": opps,
        "summary": {
            "total_count": len(opps),
            "total_value": total_value,
            "rule_based_count": sum(1 for o in opps if o["source"] == "规则匹配"),
            "ai_mined_count": sum(1 for o in opps if o["source"] == "AI挖掘"),
            "manual_count": 0,
        },
    })


# ============================================================
# 5.2.11 作战包
# ============================================================
@app.get("/api/battle-packages")
async def battle_packages_list(cust_id: int = Query(None), status: str = Query(None)):
    where = ["1=1"]
    params = []
    if cust_id:
        where.append("bp.cust_id=%s")
        params.append(cust_id)
    if status:
        where.append("bp.status=%s")
        params.append(status)

    rows = await aquery(
        f"SELECT bp.bp_id,bp.opp_id,bp.cust_id,c.name as cust_name,bp.mode,bp.status,bp.generated_at,bp.expires_at,bp.used_at "
        f"FROM battle_packages bp JOIN customers c ON bp.cust_id=c.id "
        f"WHERE {' AND '.join(where)} ORDER BY bp.generated_at DESC", params)

    items = [{"bp_id": r["bp_id"], "opp_id": r["opp_id"], "cust_id": r["cust_id"],
              "cust_name": r["cust_name"], "mode": r["mode"], "status": r["status"],
              "generated_at": _fmt_date(r["generated_at"]), "expires_at": _fmt_date(r["expires_at"]),
              "used_at": _fmt_date(r["used_at"])} for r in (rows or [])]
    return ok({"packages": items, "total": len(items)})


@app.get("/api/battle-packages/{bp_id}")
async def battle_package_detail(bp_id: str):
    row = await aquery(
        "SELECT bp.bp_id,bp.opp_id,bp.cust_id,c.name as cust_name,bp.mode,bp.status,"
        "bp.customer_overview,bp.agenda,bp.risk_warnings,bp.post_visit_actions,"
        "bp.generated_at,bp.expires_at,bp.used_at "
        "FROM battle_packages bp JOIN customers c ON bp.cust_id=c.id WHERE bp.bp_id=%s",
        (bp_id,), one=True)
    if not row:
        raise HTTPException(404, "作战包不存在")

    clues = await aquery(
        "SELECT clue_id,priority,title,discovery_basis,strategy,opening_script,products,deviation_branches "
        "FROM battle_package_clues WHERE bp_id=%s ORDER BY CASE priority WHEN '高' THEN 1 WHEN '中' THEN 2 ELSE 3 END",
        (bp_id,))

    overview = row["customer_overview"] if isinstance(row["customer_overview"], dict) else (json.loads(row["customer_overview"]) if row["customer_overview"] else {})
    agenda = row["agenda"] if isinstance(row["agenda"], dict) else (json.loads(row["agenda"]) if row["agenda"] else None)
    risk_warnings = row["risk_warnings"] if isinstance(row["risk_warnings"], list) else (list(row["risk_warnings"]) if row["risk_warnings"] else [])

    # Clean post_visit_actions: may be a PostgreSQL array or JSON
    post_visit = []
    if row["post_visit_actions"]:
        if isinstance(row["post_visit_actions"], list):
            post_visit = row["post_visit_actions"]
        elif isinstance(row["post_visit_actions"], str):
            try:
                post_visit = json.loads(row["post_visit_actions"])
            except json.JSONDecodeError:
                post_visit = [s.strip().strip('"') for s in row["post_visit_actions"].strip("{}").split(",")]

    clue_items = []
    for cl in (clues or []):
        prods = cl["products"] if isinstance(cl["products"], (list, dict)) else (json.loads(cl["products"]) if cl["products"] else [])
        dev_branches = cl["deviation_branches"]
        if isinstance(dev_branches, str):
            try:
                dev_branches = json.loads(dev_branches)
            except (json.JSONDecodeError, TypeError):
                dev_branches = None
        clue_items.append({
            "clue_id": cl["clue_id"], "priority": cl["priority"], "title": cl["title"],
            "discovery_basis": cl["discovery_basis"], "strategy": cl["strategy"],
            "opening_script": cl["opening_script"], "products": prods,
            "deviation_branches": dev_branches,
        })

    return ok({
        "bp_id": row["bp_id"], "opp_id": row["opp_id"],
        "cust_id": row["cust_id"], "cust_name": row["cust_name"],
        "mode": row["mode"], "status": row["status"],
        "customer_overview": overview,
        "agenda": agenda,
        "clues": clue_items,
        "risk_warnings": risk_warnings,
        "post_visit_actions": post_visit,
        "generated_at": _fmt_date(row["generated_at"]),
        "expires_at": _fmt_date(row["expires_at"]),
        "used_at": _fmt_date(row["used_at"]),
    })


@app.get("/api/battle-packages/{bp_id}/clues")
async def battle_package_clues_api(bp_id: str):
    rows = await aquery(
        "SELECT clue_id,priority,title,opening_script,products,deviation_branches "
        "FROM battle_package_clues WHERE bp_id=%s ORDER BY CASE priority WHEN '高' THEN 1 WHEN '中' THEN 2 ELSE 3 END",
        (bp_id,))
    if not rows:
        return ok({"clues": []})
    items = []
    for cl in rows:
        prods = cl["products"] if isinstance(cl["products"], (list, dict)) else json.loads(cl["products"])
        dev = cl["deviation_branches"]
        if isinstance(dev, str):
            try:
                dev = json.loads(dev)
            except (json.JSONDecodeError, TypeError):
                dev = None
        items.append({"clue_id": cl["clue_id"], "priority": cl["priority"], "title": cl["title"],
                      "opening_script": cl["opening_script"], "products": prods, "deviation_branches": dev})
    return ok({"clues": items})


@app.post("/api/battle-packages/{bp_id}/use")
async def battle_package_use(bp_id: str):
    await aexecute(
        "UPDATE battle_packages SET status='已使用', used_at=NOW() WHERE bp_id=%s", (bp_id,))
    return ok(message="作战包已标记为使用中")


@app.post("/api/battle-packages/generate")
async def battle_package_generate(body: dict):
    opp_id = body.get("opp_id")
    if not opp_id:
        raise HTTPException(400, "缺少 opp_id")

    # 从 opp_id 解析 cust_id (OPP_SALARY_1 → 1)
    parts = opp_id.rsplit("_", 1)
    cust_id = int(parts[-1]) if parts[-1].isdigit() else 1

    cust = await aquery("SELECT id,name,age,gender,tier,total_aum FROM customers WHERE id=%s", (cust_id,), one=True)
    if not cust:
        raise HTTPException(400, "客户不存在")

    bp_id = f"BP_GEN_{int(datetime.now().timestamp())}"

    overview = json.dumps({
        "name": cust["name"], "age": cust["age"],
        "gender": "男" if cust["gender"] == "M" else "女",
        "tier": cust["tier"], "total_aum": float(cust["total_aum"]),
        "visit_purpose": "商机跟进",
    }, ensure_ascii=False)

    gen_at = datetime.now()
    exp_at = gen_at.date() + timedelta(days=7)

    mode = "电话版" if _random.random() < 0.4 else "面谈版"

    risk_warns = '{"不得承诺收益","不得误导风险等级","基金产品须说明过往业绩不代表未来表现"}'
    post_act = '{"录入本次沟通记录","标记客户意向产品","创建跟进任务"}'

    await aexecute(
        "INSERT INTO battle_packages (bp_id,opp_id,cust_id,mode,status,customer_overview,risk_warnings,post_visit_actions,generated_at,expires_at) "
        "VALUES (%s,%s,%s,%s,'未使用',%s,%s,%s,%s,%s)",
        (bp_id, opp_id, cust_id, mode, overview, risk_warns, post_act, gen_at, exp_at))

    # 生成线索
    clue_id = f"CL{bp_id}01"
    products_json = json.dumps([{"name": "XX稳健理财", "type": "理财", "risk": "R2", "yield": 3.5, "reason": "符合风测", "script": "这款产品最大特点是稳健……"}], ensure_ascii=False)
    deviation = None
    if mode == "面谈版":
        deviation = json.dumps([{"scenario": "客户表示不需要", "response": "了解真实需求", "suggested_products": []}], ensure_ascii=False)
    await aexecute(
        "INSERT INTO battle_package_clues (clue_id,bp_id,priority,title,discovery_basis,strategy,opening_script,products,deviation_branches) "
        "VALUES (%s,%s,'中',%s,%s,%s,%s,%s,%s)",
        (clue_id, bp_id, "商机跟进线索", "系统生成", "以商机为切入", f"{cust['name']}您好……", products_json, deviation))

    return ok({"bp_id": bp_id, "mode": mode, "generated_at": gen_at.isoformat(), "expires_at": exp_at.isoformat()})


# ============================================================
# 启动入口
# ============================================================
if __name__ == "__main__":
    import uvicorn
    print(f"启动 易会办 客户洞察 API 服务...")
    print(f"数据库: {DB_CONFIG}")
    print(f"文档: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
