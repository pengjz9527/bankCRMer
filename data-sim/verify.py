"""
易会办 客户洞察模拟数据集 — 验证脚本
验证所有断言项，输出通过/失败报告
"""
import sys
import json
import urllib.request
from datetime import date, timedelta

# ============================================================
# 配置
# ============================================================
DB_CONFIG = "dbname=yihuiban_sim user=yihuiban password=yihuiban_dev host=localhost port=5432"
API_BASE = "http://localhost:8008"
TODAY = date.today()

try:
    import psycopg2
    import psycopg2.extras
    HAS_DB = True
except ImportError:
    HAS_DB = False
    print("[WARN] psycopg2 not installed, skipping DB checks")

# ============================================================
# 数据库查询辅助
# ============================================================
def query(sql, params=None):
    conn = psycopg2.connect(DB_CONFIG)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_one(sql, params=None):
    rows = query(sql, params)
    return rows[0] if rows else None


# ============================================================
# API 查询辅助
# ============================================================
def api_get(path):
    try:
        url = API_BASE + path
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"code": -1, "message": str(e)}


def api_post(path, body=None):
    try:
        data = json.dumps(body or {}).encode("utf-8")
        req = urllib.request.Request(API_BASE + path, data=data, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"code": -1, "message": str(e)}


# ============================================================
# 验证器
# ============================================================
class Verifier:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def check(self, name, condition, detail=""):
        if condition:
            self.passed += 1
            print(f"  ✅ {name}")
        else:
            self.failed += 1
            msg = f"  ❌ {name}"
            if detail:
                msg += f" — {detail}"
            print(msg)
            self.errors.append(name)

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"验证完成: {self.passed}/{total} 通过, {self.failed}/{total} 失败")
        if self.errors:
            print("失败项:")
            for e in self.errors:
                print(f"  - {e}")
        print(f"{'='*60}")
        return self.failed == 0


v = Verifier()

# ============================================================
# 1. 数据完整性 — 行数检查
# ============================================================
print("\n--- 1. 数据完整性 ---")
tables_expected = {
    "customers": 100,
    "family_info": 60,
    "business_info": 10,
    "employment_status": 15,
    "holdings": 300,
    "transactions": 3000,
    "loans": 15,
    "loan_rejections": 3,
    "behavior_logs": 2000,
    "customer_relations": 15,
    "communications": 200,
    "risk_assessments": 60,
    "customer_benefits": 100,
    "available_activities": 8,
    "customer_activity_participation": 50,
    "battle_packages": 10,
    "battle_package_clues": 30,
}

for table, expected in tables_expected.items():
    row = query_one(f"SELECT COUNT(*) as cnt FROM {table}")
    actual = row["cnt"] if row else 0
    v.check(f"{table}: {actual} >= {expected}", actual >= expected,
            f"实际={actual}, 期望>={expected}")

# ============================================================
# 2. 等级一致性
# ============================================================
print("\n--- 2. 等级一致性 ---")
tier_map = {
    "千元以下": (0, 999),
    "千元户": (1000, 9999),
    "万元户": (10000, 49999),
    "优质": (50000, 199999),
    "财富": (200000, 999999),
    "高净值": (1000000, 2999999),
    "私钻": (3000000, 5999999),
    "私行": (6000000, 20000000),
}
rows = query("SELECT id,name,tier,total_aum FROM customers")
mismatches = 0
for r in rows:
    tier = r["tier"]
    aum = float(r["total_aum"])
    lo, hi = tier_map.get(tier, (0, 999999999))
    if not (lo <= aum <= hi):
        mismatches += 1
v.check(f"等级与AUM一致: {mismatches} 不匹配", mismatches == 0,
        f"{mismatches} customers out of range")

# ============================================================
# 3. 关系可发现
# ============================================================
print("\n--- 3. 关系可发现 ---")
rel_count = query_one("SELECT COUNT(*) as cnt FROM customer_relations WHERE relation_type='同企业代发'")
v.check(f"同企业代发关系 >= 3对", rel_count and rel_count["cnt"] >= 3,
        f"实际={rel_count['cnt'] if rel_count else 0}")

# ============================================================
# 4. 待办可触发
# ============================================================
print("\n--- 4. 待办可触发 ---")
due = query_one(
    "SELECT COUNT(*) as cnt FROM holdings WHERE maturity_date BETWEEN %s AND %s",
    (TODAY, TODAY + timedelta(days=7)))
v.check(f"7天内到期产品 >= 5条", due and due["cnt"] >= 5,
        f"实际={due['cnt'] if due else 0}")

# ============================================================
# 5. 行为->偏好链路
# ============================================================
print("\n--- 5. 行为->偏好链路 ---")
fund_rows = query(
    "SELECT cust_id,COUNT(*) as cnt FROM behavior_logs "
    "WHERE page_type='基金' GROUP BY cust_id HAVING COUNT(*) >= 15")
v.check(f"浏览基金>=15次的客户 >= 3人", len(fund_rows) >= 3,
        f"实际={len(fund_rows)}人")

# ============================================================
# 6. 家庭关系自洽
# ============================================================
print("\n--- 6. 家庭关系自洽 ---")
fam_rows = query("SELECT child_age,child_education FROM family_info WHERE children=true AND child_age IS NOT NULL")
mismatches = 0
for r in fam_rows:
    age = r["child_age"]
    edu = r["child_education"]
    if age <= 6 and edu not in ("幼儿园", "小学", None):
        mismatches += 1
    elif 7 <= age <= 12 and edu not in ("小学", None):
        mismatches += 1
    elif 13 <= age <= 15 and edu not in ("初中", None):
        mismatches += 1
    elif 16 <= age <= 18 and edu not in ("高中", None):
        mismatches += 1
    elif 19 <= age <= 22 and edu not in ("大学", None):
        mismatches += 1
v.check(f"子女年龄与学习阶段自洽: {mismatches} 不匹配", mismatches == 0)

# ============================================================
# 7. 就业状态覆盖
# ============================================================
print("\n--- 7. 就业状态覆盖 ---")
unemp = query_one(
    "SELECT COUNT(*) as cnt FROM employment_status WHERE status IN ('无业','待业')")
v.check(f"无业/待业客户 >= 5人", unemp and unemp["cnt"] >= 5,
        f"实际={unemp['cnt'] if unemp else 0}")

# ============================================================
# 8. 失业金关联
# ============================================================
print("\n--- 8. 失业金关联 ---")
ben_row = query_one(
    "SELECT COUNT(*) as cnt FROM employment_status WHERE unemployment_benefits=true")
ben_txn = query_one(
    "SELECT COUNT(DISTINCT t.cust_id) as cnt FROM transactions t "
    "JOIN employment_status e ON t.cust_id=e.cust_id "
    "WHERE e.unemployment_benefits=true AND t.summary='失业金'")
v.check(f"失业金领取且交易中有失业金入账 >= 2人",
        ben_row and ben_row["cnt"] >= 2 and ben_txn and ben_txn["cnt"] >= 2,
        f"benefits={ben_row['cnt'] if ben_row else 0}, txn={ben_txn['cnt'] if ben_txn else 0}")

# ============================================================
# 9. 身份待确认
# ============================================================
print("\n--- 9. 身份待确认 ---")
unverified = query_one(
    "SELECT COUNT(*) as cnt FROM business_info WHERE verified=false")
v.check(f"business_info.verified=false >= 3条", unverified and unverified["cnt"] >= 3,
        f"实际={unverified['cnt'] if unverified else 0}")

# 对应沟通记录
unv_ids = [r["cust_id"] for r in query("SELECT cust_id FROM business_info WHERE verified=false")]
if unv_ids:
    comm_check = query_one(
        "SELECT COUNT(*) as cnt FROM communications WHERE cust_id = ANY(%s) AND key_topics LIKE %s",
        (unv_ids, "%确认%"))
    v.check(f"未确认客户有'确认'类沟通记录 >= 1条",
            comm_check and comm_check["cnt"] >= 1,
            f"实际={comm_check['cnt'] if comm_check else 0}")
else:
    v.check("未确认客户有'确认'类沟通记录", False, "没有verified=false的客户")

# ============================================================
# 10. 留学意向
# ============================================================
print("\n--- 10. 留学意向 ---")
abroad = query_one(
    "SELECT COUNT(*) as cnt FROM family_info WHERE study_abroad_intent IN ('有','已留学')")
v.check(f"留学意向 >= 3条", abroad and abroad["cnt"] >= 3,
        f"实际={abroad['cnt'] if abroad else 0}")

# ============================================================
# 11. 权益覆盖
# ============================================================
print("\n--- 11. 权益覆盖 ---")
ben_total = query_one("SELECT COUNT(*) as cnt FROM customer_benefits")
ben_multi = query_one(
    "SELECT COUNT(*) as cnt FROM (SELECT cust_id,COUNT(*) as c FROM customer_benefits GROUP BY cust_id HAVING COUNT(*)>=2) sub")
v.check(f"权益 >= 100行", ben_total and ben_total["cnt"] >= 100,
        f"实际={ben_total['cnt'] if ben_total else 0}")
v.check(f">=2条权益的客户 >= 5人", ben_multi and ben_multi["cnt"] >= 5,
        f"实际={ben_multi['cnt'] if ben_multi else 0}")

# ============================================================
# 12. 活动覆盖
# ============================================================
print("\n--- 12. 活动覆盖 ---")
act_cnt = query_one("SELECT COUNT(*) as cnt FROM available_activities")
part_cnt = query_one("SELECT COUNT(*) as cnt FROM customer_activity_participation")
v.check(f"活动 >= 8条", act_cnt and act_cnt["cnt"] >= 8,
        f"实际={act_cnt['cnt'] if act_cnt else 0}")
v.check(f"参与记录 >= 50条", part_cnt and part_cnt["cnt"] >= 50,
        f"实际={part_cnt['cnt'] if part_cnt else 0}")

# ============================================================
# 13. 作战包链路
# ============================================================
print("\n--- 13. 作战包链路 ---")
bp_cnt = query_one("SELECT COUNT(*) as cnt FROM battle_packages")
v.check(f"作战包 >= 10个", bp_cnt and bp_cnt["cnt"] >= 10,
        f"实际={bp_cnt['cnt'] if bp_cnt else 0}")

# 每个作战包有 opp_id 和线索
bp_no_opp = query_one(
    "SELECT COUNT(*) as cnt FROM battle_packages WHERE opp_id IS NULL OR opp_id=''")
v.check(f"所有作战包关联opp_id", bp_no_opp and bp_no_opp["cnt"] == 0,
        f"实际={bp_no_opp['cnt'] if bp_no_opp else 0}个无opp_id")

# 每个作战包有1-3条线索
bp_no_clue = query(
    "SELECT bp.bp_id,COUNT(bpc.id) as cnt FROM battle_packages bp "
    "LEFT JOIN battle_package_clues bpc ON bp.bp_id=bpc.bp_id "
    "GROUP BY bp.bp_id HAVING COUNT(bpc.id) < 1 OR COUNT(bpc.id) > 3")
v.check(f"作战包线索数1-3条", len(bp_no_clue) == 0,
        f"{len(bp_no_clue)}个不符合")

# 存在已过期
exp_bp = query_one("SELECT COUNT(*) as cnt FROM battle_packages WHERE status='已过期'")
v.check(f"存在已过期的作战包", exp_bp and exp_bp["cnt"] >= 1,
        f"实际={exp_bp['cnt'] if exp_bp else 0}")

# ============================================================
# 14. 作战包模式覆盖
# ============================================================
print("\n--- 14. 作战包模式覆盖 ---")
mtg_cnt = query_one("SELECT COUNT(*) as cnt FROM battle_packages WHERE mode='面谈版'")
tel_cnt = query_one("SELECT COUNT(*) as cnt FROM battle_packages WHERE mode='电话版'")
v.check(f"面谈版 >= 5个", mtg_cnt and mtg_cnt["cnt"] >= 5,
        f"实际={mtg_cnt['cnt'] if mtg_cnt else 0}")
v.check(f"电话版 >= 5个", tel_cnt and tel_cnt["cnt"] >= 5,
        f"实际={tel_cnt['cnt'] if tel_cnt else 0}")

# ============================================================
# 15. API 全覆盖 (仅测试数据可用时)
# ============================================================
print("\n--- 15. API 全覆盖 ---")

# 获取第一个客户ID
first_cust = query_one("SELECT id FROM customers ORDER BY id LIMIT 1")
cust_id = first_cust["id"] if first_cust else 1

# 获取第一个作战包
first_bp = query_one("SELECT bp_id FROM battle_packages ORDER BY id LIMIT 1")
bp_id = first_bp["bp_id"] if first_bp else "BP001"

endpoints = [
    ("GET", f"/api/customers"),
    ("GET", f"/api/customers/{cust_id}/profile"),
    ("GET", f"/api/customers/{cust_id}/basic"),
    ("GET", f"/api/customers/{cust_id}/family"),
    ("GET", f"/api/customers/{cust_id}/employment"),
    ("GET", f"/api/customers/{cust_id}/business"),
    ("GET", f"/api/customers/{cust_id}/wealth/summary"),
    ("GET", f"/api/customers/{cust_id}/wealth/holdings"),
    ("GET", f"/api/customers/{cust_id}/wealth/fund-flow?months=6"),
    ("GET", f"/api/customers/{cust_id}/wealth/salary"),
    ("GET", f"/api/customers/{cust_id}/credit/loans"),
    ("GET", f"/api/customers/{cust_id}/credit/rejections"),
    ("GET", f"/api/customers/{cust_id}/credit/social-security"),
    ("GET", f"/api/customers/{cust_id}/behavior/preferences"),
    ("GET", f"/api/customers/{cust_id}/behavior/logs?days=30"),
    ("GET", f"/api/customers/{cust_id}/relations"),
    ("GET", f"/api/customers/{cust_id}/benefits"),
    ("GET", f"/api/customers/{cust_id}/activities"),
    ("GET", f"/api/activities"),
    ("GET", f"/api/tasks?date={TODAY.isoformat()}"),
    ("GET", f"/api/opportunities"),
    ("GET", f"/api/battle-packages"),
    ("GET", f"/api/battle-packages/{bp_id}"),
    ("GET", f"/api/battle-packages/{bp_id}/clues"),
]

api_ok = 0
api_fail = 0
for method, path in endpoints:
    resp = api_get(path)
    if resp.get("code") == 0:
        api_ok += 1
    else:
        api_fail += 1
        print(f"    {method} {path} → code={resp.get('code')}, message={resp.get('message','')}")

# POST 接口
post_endpoints = [
    (f"/api/battle-packages/{bp_id}/use", {}),
    (f"/api/battle-packages/generate", {"opp_id": f"OPP_TEST_{cust_id}"}),
]
for path, body in post_endpoints:
    resp = api_post(path, body)
    if resp.get("code") == 0:
        api_ok += 1
    else:
        api_fail += 1
        print(f"    POST {path} → code={resp.get('code')}, message={resp.get('message','')}")

v.check(f"API: {api_ok} 通过, {api_fail} 失败 (共{api_ok+api_fail}个接口)", api_fail == 0)

# profile 聚合接口 loaded_modules 检查
profile = api_get(f"/api/customers/{cust_id}/profile")
if profile.get("code") == 0 and profile.get("data"):
    modules = profile["data"].get("loaded_modules", [])
    v.check(f"profile.loaded_modules 非空: {modules}", len(modules) > 0)

# ============================================================
# 总结
# ============================================================
success = v.summary()
sys.exit(0 if success else 1)
