"""
易会办 客户洞察模拟数据集 — 数据生成脚本
基于 templates.py 中定义的6类画像模板，生成100人模拟数据集并写入 PostgreSQL
"""
import random
import json
import psycopg2
from datetime import date, timedelta, datetime
from templates import (
    ALL_TEMPLATES, TIER_AUM_RANGE, PRODUCTS, RISK_LEVELS, RISK_RESULTS,
    CITIES, INDUSTRIES, EDUCATIONS, COMPANY_PREFIX, weighted_choice,
    generate_name, child_education_from_age
)

random.seed(42)  # 可复现

TODAY = date.today()
DAYS_180 = TODAY - timedelta(days=180)
DAYS_365 = TODAY - timedelta(days=365)
DAYS_90 = TODAY - timedelta(days=90)

# ============================================================
# 全局ID计数器
# ============================================================
class Counter:
    def __init__(self, start=1):
        self._n = start
    def next(self):
        n = self._n
        self._n += 1
        return n

cust_counter = Counter(1)
hold_counter = Counter(1)
txn_counter = Counter(1)
loan_counter = Counter(1)
rej_counter = Counter(1)
beh_counter = Counter(1)
rel_counter = Counter(1)
comm_counter = Counter(1)
risk_counter = Counter(1)
benefit_counter = Counter(1)
act_counter = Counter(1)

# ============================================================
# 数据容器
# ============================================================
customers = []           # (id, cust_no, name, age, gender, occupation, industry, city, education, phone, tier, total_aum, emp_status)
family_infos = []        # (id, cust_id, marriage, children, child_count, child_age, child_edu, study_abroad_intent, country, spouse_income)
business_infos = []      # (id, cust_id, name, duration, share, reg_cap, addr, scope, continuity, verified, source)
emp_statuses = []        # (id, cust_id, status, benefits, amount, start, end, verified, last_verify)
holdings = []            # (id, cust_id, type, name, code, amount, yield_, risk, maturity, purchase, status)
transactions = []        # (id, cust_id, date, type, amount, counterparty, summary, channel)
loans = []               # (id, cust_id, product, credit_line, used, overdue, rate, start, maturity)
loan_rejections = []     # (id, cust_id, product, reason, date)
behavior_logs = []       # (id, cust_id, date, time, channel, page_type, action, duration, product_code, product_type)
customer_relations = []  # (id, cust_a, cust_b, rel_type, evidence, field)
communications = []      # (id, cust_id, date, time, channel, duration, summary, topics)
risk_assessments = []    # (id, cust_id, result, valid_until, tested_date, w_score, w_time, dim_a, dim_i, dim_s)
product_catalog = []     # (id, code, name, type, risk, yield, min_amt, manager, status)
benefits = []            # (id, cust_id, name, type, desc, tier_req, rarity, acquired, expiry, status)

# Activities are global
activities = []          # (id, activity_id, title, type, start, end, desc, target_tier, reward)
activity_parts = []      # (id, cust_id, activity_id, date, status, note)

# Battle packages
battle_pkgs = []         # (id, bp_id, opp_id, cust_id, mode, status, overview_json, agenda_json, risk_warns, post_actions, gen_at, exp_at, used_at)
bp_clues = []            # (id, clue_id, bp_id, priority, title, basis, strategy, script, products_json, deviation_json)


def generate():
    """主生成函数"""
    print("Generating 100 customer dataset...")

    # 1. 生成产品目录
    gen_product_catalog()

    # 2. 逐类型生成客户数据
    for template in ALL_TEMPLATES:
        gen_customer_type(template)

    # 3. 生成关系数据
    gen_relations()

    # 4. 生成沟通记录
    gen_communications()

    # 5. 生成风测与财富分
    gen_risk_assessments()

    # 6. 生成权益数据
    gen_benefits()

    # 7. 生成活动数据
    gen_activities()

    # 8. 生成作战包
    gen_battle_packages()

    print(f"Done! Generated {len(customers)} customers across {len(ALL_TEMPLATES)} types.")
    print_stats()


def gen_product_catalog():
    """生成产品目录(全局20条)"""
    pid = 1
    for ptype, items in PRODUCTS.items():
        for name, code in items:
            product_catalog.append((pid, code, name, ptype,
                random.choice(RISK_LEVELS[:2]) if ptype in ("存款","保险") else random.choice(RISK_LEVELS[1:4]),
                round(random.uniform(0.5, 5.5), 4),
                random.choice([1, 1000, 10000]),
                random.choice(["徽银","兴银","杭银","南银","平安","博时","易方达"]),
                "在售"))
            pid += 1


def gen_customer_type(tmpl):
    """按画像模板生成一类客户"""
    for i in range(tmpl["count"]):
        cust_id = cust_counter.next()
        cust_no = f"C{datetime.now().strftime('%y%m')}{cust_id:04d}"

        # 基础属性
        gender = weighted_choice(tmpl["gender_ratio"])
        age = random.randint(*tmpl["age_range"])
        tier = weighted_choice(tmpl["tier_weights"])
        city = weighted_choice(tmpl["city_weights"])
        if city == "其他":
            city = random.choice([c for c in CITIES if c not in tmpl.get("city_weights", {})])

        education = weighted_choice(tmpl["education_weights"])

        # 就业状态
        emp_status = weighted_choice(tmpl["employment"]["status_weights"])
        occupation = random.choice(OCCUPATIONS.get(emp_status, ["待确认"]))
        industry = random.choice(INDUSTRIES) if emp_status in ("在职","自由职业") else None

        # AUM
        tier_spec = tmpl["tier_specifics"][tier]
        aum = int(random.uniform(*tier_spec["aum_range"]))

        # 手机号(脱敏)
        phone = f"1{random.randint(30,99)}{random.randint(1000,9999)}{random.randint(1000,9999)}"
        phone_masked = phone[:3] + "****" + phone[-4:]

        name = generate_name(gender)
        gender_char = "M" if gender == "M" else "F"

        customers.append((cust_id, cust_no, name, age, gender_char, occupation, industry, city, education, phone_masked, tier, aum, emp_status))

        # 家庭信息
        gen_family(tmpl, cust_id, age, gender_char)
        # 经营信息
        gen_business(tmpl, cust_id)
        # 就业状态明细
        gen_employment_detail(tmpl, cust_id, emp_status)
        # 持仓
        gen_holdings(tmpl, cust_id, tier, aum)
        # 贷款
        gen_loans(tmpl, cust_id)
        # 行为日志
        gen_behavior_logs(tmpl, cust_id, tier_spec["active_prob"])
        # 交易流水
        gen_transactions(tmpl, cust_id, tier, aum, emp_status)


def gen_family(tmpl, cust_id, age, gender):
    """生成家庭结构"""
    fam = tmpl.get("family", {})
    married = random.random() < fam.get("married_prob", 0.5)
    children = married and random.random() < fam.get("children_prob", 0.5)

    if children:
        child_count = random.randint(*fam.get("child_count_range", (1, 1)))
        child_age = random.randint(*fam.get("child_age_range", (0, 18)))
        child_edu = child_education_from_age(child_age)
        study_intent = "已留学" if child_edu == "留学中" else ("有" if random.random() < fam.get("study_abroad_intent_prob", 0.1) else "无")
        country = random.choice(["美国","英国","澳大利亚","加拿大","新加坡"]) if study_intent in ("有","已留学") else None
    else:
        child_count = 0
        child_age = None
        child_edu = None
        study_intent = "无"
        country = None

    spouse_income = random.random() < fam.get("spouse_has_income_prob", 0.5) if married else None

    family_infos.append((cust_id, cust_id, married, children, child_count, child_age, child_edu, study_intent, country, spouse_income))


def gen_business(tmpl, cust_id):
    """生成经营信息"""
    has_biz = random.random() < tmpl.get("has_business_info_probt", 0)
    if not has_biz:
        return

    verified = random.random() < tmpl.get("business_verified_prob", 0.7)
    source = "客户经理确认" if verified else random.choice(["交易流水推断","待面谈确认"])

    prefix = random.choice(COMPANY_PREFIX)
    biz_name = f"{prefix}{random.choice(['贸易','科技','实业','商贸','电子','建材'])}有限公司"
    duration = random.randint(2, 15)
    share = round(random.uniform(30, 100), 2)
    reg_cap = random.choice([50, 100, 200, 500, 1000]) * 10000
    addr = f"合肥市{random.choice(['蜀山','庐阳','包河','瑶海'])}区"
    scope = random.choice(["日用百货批发零售","电子产品销售","建筑装饰工程","餐饮管理","信息技术服务","机械设备销售"])

    business_infos.append((cust_id, cust_id, biz_name, duration, share, reg_cap, addr, scope, True, verified, source))


def gen_employment_detail(tmpl, cust_id, emp_status):
    """生成就业状态明细"""
    ben = False
    ben_amt = None
    ben_start = None
    ben_end = None
    verified = emp_status != "不确定"
    last_verify = TODAY if verified else (TODAY - timedelta(days=random.randint(30, 90)))

    if emp_status in ("无业","待业"):
        ben = random.random() < tmpl["employment"].get("unemployment_benefits_prob", 0.5)
        if ben:
            ben_amt = round(random.uniform(1500, 4000), 2)
            ben_start = TODAY - timedelta(days=random.randint(60, 180))
            ben_end = ben_start + timedelta(days=random.randint(90, 365))

    emp_statuses.append((cust_id, cust_id, emp_status, ben, ben_amt, ben_start, ben_end, verified, last_verify))


def gen_holdings(tmpl, cust_id, tier, aum):
    """生成金融资产持仓"""
    ht = tmpl["holdings_template"]
    remaining_aum = aum

    for ptype, cfg in ht.items():
        if random.random() > cfg["prob"]:
            continue
        count = random.randint(*cfg.get("count_range", (1, 1)))
        for _ in range(count):
            amount = int(random.uniform(*cfg["amount_range"]))
            amount = min(amount, int(remaining_aum * 0.7))
            if amount <= 0:
                continue
            remaining_aum -= amount

            prod_pool = PRODUCTS.get(ptype, [("未知产品","X000")])
            prod_name, prod_code = random.choice(prod_pool)
            yield_rate = round(random.uniform(1.5, 4.5), 4) if ptype != "贵金属" else None
            risk = random.choice(RISK_LEVELS[:3]) if ptype != "存款" else "R1"

            # 到期日: 部分已过期、部分即将到期
            if ptype in ("存款","理财"):
                offset = random.choice([-5, -1, 3, 7, 15, 30, 60, 90, 180])
                maturity = TODAY + timedelta(days=offset)
            else:
                maturity = None

            purchase = TODAY - timedelta(days=random.randint(30, 365))
            status = "持有中"

            holdings.append((hold_counter.next(), cust_id, ptype, prod_name, prod_code, amount, yield_rate, risk, maturity, purchase, status))


def gen_loans(tmpl, cust_id):
    """生成贷款数据"""
    if random.random() > tmpl.get("loan_prob", 0.1):
        return

    loan_types = tmpl.get("loan_type_weights", {"房贷": 1.0})
    ltype = weighted_choice(loan_types)

    if ltype == "房贷":
        product = f"{random.choice(['首套','二套'])}住房贷款"
        credit = int(random.uniform(300000, 1500000))
    elif ltype == "经营贷":
        product = "个人经营性贷款"
        credit = int(random.uniform(200000, 1000000))
    else:
        product = "个人消费贷款"
        credit = int(random.uniform(50000, 300000))

    used = int(credit * random.uniform(0.3, 0.95))
    overdue = random.randint(0, 5) if random.random() < tmpl.get("loan_overdue_prob", 0.2) else 0
    rate = round(random.uniform(3.5, 6.5), 4)
    start = TODAY - timedelta(days=random.randint(180, 1825))
    mat = start + timedelta(days=random.randint(1825, 7300))

    loans.append((loan_counter.next(), cust_id, product, credit, used, overdue, rate, start, mat))

    # 被拒记录
    if random.random() < tmpl.get("loan_rejection_prob", 0.1):
        rej_product = random.choice(["XX信用贷款","ZZ经营贷"])
        rej_reason = random.choice(["征信记录不良","收入证明不足","负债率过高"])
        rej_date = TODAY - timedelta(days=random.randint(90, 365))
        loan_rejections.append((rej_counter.next(), cust_id, rej_product, rej_reason, rej_date))


def gen_behavior_logs(tmpl, cust_id, active_prob):
    """生成行为日志(近3月)"""
    bias = tmpl["behavior_bias"]
    daily_prob = tmpl.get("behavior_daily_prob", 0.05) * active_prob

    current = DAYS_90
    while current <= TODAY:
        if random.random() < daily_prob:
            # 当天1-3条行为
            for _ in range(random.randint(1, 3)):
                page = weighted_choice(bias)
                action = random.choice(["浏览","搜索","点击详情","收藏","对比"][:random.randint(1, 5)])
                dur = random.randint(10, 300)
                prod_code = random.choice(PRODUCTS.get(page, [("","X000")]))[1]
                t = f"{random.randint(8,22):02d}:{random.randint(0,59):02d}:00"
                channel = random.choice(["手机银行","网银","微信"])

                behavior_logs.append((beh_counter.next(), cust_id, current, t, channel, page, action, dur, prod_code, page))
        current += timedelta(days=1)


def gen_transactions(tmpl, cust_id, tier, aum, emp_status):
    """生成交易流水(近6月)"""
    freq_per_month = 3 if aum > 1000000 else (5 if aum > 200000 else (8 if aum > 50000 else 12))
    channels = ["手机银行","网银","柜台","ATM"]

    current = DAYS_180
    while current <= TODAY:
        n_txn = max(1, int(random.uniform(0, freq_per_month / 30.0 * 2)))
        for _ in range(n_txn):
            is_in = random.random() < 0.55
            if is_in:
                amt = round(random.uniform(100, aum * 0.02), 2)
            else:
                amt = round(random.uniform(50, aum * 0.03), 2)

            counterparty = random.choice(["支付宝","微信","他行账户","本行账户","公司","个人"])
            summary = ""
            if is_in:
                summary = random.choice(["工资","奖金","报销","退款","转账","理财赎回"])
            else:
                summary = random.choice(["消费","转账","取现","还款","缴费","理财购买"])

            channel = random.choice(channels)
            transactions.append((txn_counter.next(), cust_id, current, "in" if is_in else "out", amt, counterparty, summary, channel))
        current += timedelta(days=1)

    # 注入信号事件
    inject_signals(tmpl, cust_id, emp_status)


def inject_signals(tmpl, cust_id, emp_status):
    """注入关键信号事件"""
    # 大额异动(昨日)
    if random.random() < 0.08:
        amt = round(random.uniform(50000, 300000), 2)
        transactions.append((txn_counter.next(), cust_id, TODAY - timedelta(days=1), "out", amt, "他行账户", "大额转出", "手机银行"))

    # 代发工资(近1-7天)
    if tmpl.get("salary_disbursement", False):
        for offset in range(1, 8):
            salary_date = TODAY - timedelta(days=offset)
            if random.random() < 0.5:
                amt = round(random.uniform(3000, 20000), 2)
                transactions.append((txn_counter.next(), cust_id, salary_date, "in", amt, "公司", "工资", "手机银行"))

    # 失业金入账
    if emp_status in ("无业","待业"):
        for m in range(1, 7):
            ben_date = TODAY - timedelta(days=30 * m)
            if random.random() < 0.5:
                amt = round(random.uniform(1500, 3500), 2)
                transactions.append((txn_counter.next(), cust_id, ben_date, "in", amt, "社保局", "失业金", "手机银行"))

    # 经营流水(小微企业主)
    if tmpl.get("type_name") == "F·小微企业主":
        for m in range(1, 4):
            biz_date = TODAY - timedelta(days=15 * m)
            amt = round(random.uniform(5000, 80000), 2)
            summary = random.choice(["货款","采购款","结算款","预付款","服务费"])
            transactions.append((txn_counter.next(), cust_id, biz_date, "in", amt, "企业账户", summary, "网银"))

    # 他行转账(流失风险)
    if tmpl.get("other_bank_transfer_prob", 0) > 0 and random.random() < tmpl["other_bank_transfer_prob"]:
        amt = round(random.uniform(10000, 200000), 2)
        transactions.append((txn_counter.next(), cust_id, TODAY - timedelta(days=random.randint(1, 30)), "out", amt, "他行账户", "他行转账", "手机银行"))

    # 学费/教育支出
    for cid, fam in [(f[0], f) for f in family_infos if f[1] == cust_id]:
        if fam[7] in ("有","已留学") or (fam[5] and fam[5] in ("高中","大学","留学中")):
            amt = round(random.uniform(5000, 50000), 2)
            transactions.append((txn_counter.next(), cust_id, TODAY - timedelta(days=random.randint(1, 60)), "out", amt, "学校", "学费", "手机银行"))


def gen_relations():
    """生成关系图谱数据"""
    # 类型D高净值网络 — 同企业代发关系对
    d_customers = [c for c in customers if any(b[1] == c[0] for b in business_infos)]
    for i in range(len(d_customers)):
        for j in range(i + 1, min(i + 3, len(d_customers))):
            if random.random() < 0.4:
                company = f"徽商{random.choice(['科技','贸易','实业'])}集团"
                customer_relations.append((rel_counter.next(), d_customers[i][0], d_customers[j][0], "同企业代发", f"同一企业代发: {company}", "transactions.summary"))

    # 亲属关系 — 同姓氏、地址相近
    for i in range(len(customers)):
        for j in range(i + 1, len(customers)):
            if customers[i][7] == customers[j][7] and customers[i][2][:1] == customers[j][2][:1]:
                if random.random() < 0.05:
                    customer_relations.append((rel_counter.next(), customers[i][0], customers[j][0], "亲属", "同姓氏同城市", "customers.city"))

    # 资金往来关系
    if len(customers) >= 2 and random.random() < 0.3:
        a, b = random.sample(customers, 2)
        customer_relations.append((rel_counter.next(), a[0], b[0], "资金往来", "频繁大额转账", "transactions.counterparty"))

    # 担保关系
    loan_custs = [c[0] for c in customers if any(l[1] == c[0] for l in loans)]
    if len(loan_custs) >= 2:
        a, b = random.sample(loan_custs, 2)
        customer_relations.append((rel_counter.next(), a, b, "担保", "贷款共同担保人", "loans"))

    # 同客户经理关系(所有客户归李经理)
    for c in customers[:30]:
        for c2 in customers[30:60]:
            if random.random() < 0.02:
                customer_relations.append((rel_counter.next(), c[0], c2[0], "同客户经理", "李经理", "customers"))


def gen_communications():
    """生成沟通记录"""
    for tmpl in ALL_TEMPLATES:
        freq = tmpl.get("communications_per_month", 0.3)
        signals = tmpl.get("opportunity_signals", [])
        type_custs = [c for c in customers if c[12] in tmpl["employment"]["status_weights"]] if tmpl["type_name"] in ("E·沉睡/流失风险客",) else customers[-tmpl["count"]:]

        for c in customers:
            for m in range(1, 7):
                comm_date = TODAY - timedelta(days=30 * m)
                if random.random() < freq / 4:
                    channel = random.choice(["电话","面谈","微信","短信"])
                    dur = random.randint(5, 45)
                    # 根据画像类型生成话题
                    topics = []
                    if tmpl.get("family", {}).get("study_abroad_intent_prob", 0) > 0.1:
                        if random.random() < 0.3:
                            topics.append("子女教育")
                    if "产品到期" in signals:
                        topics.append(random.choice(["定存到期","理财续期"]))
                    if "基金挖掘" in signals:
                        topics.append("基金关注")
                    if "流失预警" in signals:
                        topics.append(random.choice(["资金规划","活期余额"]))
                    if "就业状态确认" in signals:
                        topics.append("确认就业状态")

                    if not topics:
                        topics = ["日常问候","产品咨询","账户服务"]

                    summary = f"客户经理{random.choice(['致电','面见'])}客户，沟通{','.join(topics[:2])}"
                    communications.append((comm_counter.next(), c[0], comm_date, f"{random.randint(9,17):02d}:00:00", channel, dur, summary, ",".join(topics)))


def gen_risk_assessments():
    """生成风测与财富分"""
    for c in customers:
        if random.random() < 0.65:
            result = random.choice(RISK_RESULTS[:3])  # 大部分保守/稳健
            valid = TODAY + timedelta(days=365)
            tested = TODAY - timedelta(days=random.randint(30, 365))
            w_score = int(random.uniform(20, 95))
            w_time = TODAY - timedelta(days=random.randint(1, 30))
            dim_a = round(random.uniform(10, 40), 2)
            dim_i = round(random.uniform(10, 35), 2)
            dim_s = round(random.uniform(5, 25), 2)
            risk_assessments.append((risk_counter.next(), c[0], result, valid, tested, w_score, w_time, dim_a, dim_i, dim_s))


def gen_benefits():
    """生成权益数据"""
    benefit_pool = [
        ("机场贵宾厅","出行","每年6次免费使用","财富", "稀有"),
        ("三甲医院体检","健康","每年1次VIP体检套餐","高净值", "稀有"),
        ("商超满减券","购物","满200减50","优质", "普通"),
        ("子女教育咨询","教育","专业教育规划师1对1咨询","财富", "限时"),
        ("高端餐厅折扣","美食","指定餐厅8折","财富", "普通"),
        ("留学规划服务","教育","免费留学规划1次","私钻", "稀有"),
        ("代驾服务","出行","每年12次免费代驾","高净值", "限时"),
        ("生日礼遇","购物","生日当月专属礼品","优质", "普通"),
        ("高尔夫练习场","健康","每月2次免费","私钻", "稀有"),
        ("法律咨询服务","其他","免费法律咨询1次","私行", "限时"),
    ]

    tier_order = ["千元以下","千元户","万元户","优质","财富","高净值","私钻","私行"]
    for c in customers:
        n = random.randint(0, 4)
        c_tier_idx = tier_order.index(c[11]) if c[11] in tier_order else 3
        eligible = [b for b in benefit_pool if tier_order.index(b[3]) <= c_tier_idx]
        chosen = random.sample(eligible, min(n, len(eligible))) if eligible else []
        for bn, bt, desc, treq, rar in chosen:
            acquired = TODAY - timedelta(days=random.randint(1, 180))
            expiry = acquired + timedelta(days=random.randint(180, 365))
            benefits.append((benefit_counter.next(), c[0], bn, bt, desc, treq, rar, acquired, expiry, "有效"))


def gen_activities():
    """生成营销活动"""
    act_list = [
        ("ACT001","新客理财专享","理财", TODAY - timedelta(days=30), TODAY + timedelta(days=60), "首次购买理财享额外收益加成","优质","年化+0.5%"),
        ("ACT002","基金定投大赛","基金", TODAY - timedelta(days=15), TODAY + timedelta(days=90), "参与定投赢取大奖","千元户","最高500元红包"),
        ("ACT003","保险保障月","保险", TODAY - timedelta(days=5), TODAY + timedelta(days=55), "指定保险产品首年保费9折","财富","保费折扣"),
        ("ACT004","大额存单抢购","存款", TODAY + timedelta(days=1), TODAY + timedelta(days=30), "限量大额存单年化3.5%","优质","高利率锁定"),
        ("ACT005","信用卡推荐有礼","信用卡", TODAY - timedelta(days=60), TODAY + timedelta(days=30), "推荐好友办卡双方各得100元","千元以下","现金奖励"),
        ("ACT006","贵金属投资讲座","贵金属", TODAY + timedelta(days=10), TODAY + timedelta(days=40), "专家解读贵金属市场走势","高净值","精美伴手礼"),
        ("ACT007","暑期亲子财商营","综合", TODAY + timedelta(days=5), TODAY + timedelta(days=35), "带孩子学习理财知识","财富","亲子互动礼盒"),
        ("ACT008","留学金融一站式","综合", TODAY - timedelta(days=10), TODAY + timedelta(days=80), "留学贷款+外汇+保险组合方案","高净值","手续费减免"),
        ("ACT009","代发薪客户权益升级","综合", TODAY - timedelta(days=20), TODAY + timedelta(days=40), "代发客户专享理财额度提升","千元户","专享额度"),
        ("ACT010","年终回馈抽奖","综合", TODAY + timedelta(days=30), TODAY + timedelta(days=90), "消费满额参与抽奖","优质","最高8888元"),
    ]

    for act_id, title, atype, start, end, desc, tier, reward in act_list:
        activities.append((act_counter.next(), act_id, title, atype, start, end, desc, tier, reward))

    # 客户参与记录
    tier_order = ["千元以下","千元户","万元户","优质","财富","高净值","私钻","私行"]
    for c in customers:
        n = random.randint(0, 3)
        c_tier_idx = tier_order.index(c[11]) if c[11] in tier_order else 3
        eligible_acts = [a for a in act_list if tier_order.index(a[6]) <= c_tier_idx]
        chosen = random.sample(eligible_acts, min(n, len(eligible_acts))) if eligible_acts else []
        for act in chosen:
            part_date = TODAY - timedelta(days=random.randint(1, 30))
            status = random.choice(["已参与","已完成"])
            note = random.choice(["客户反馈积极","已推荐产品","待跟进",""]) if status == "已参与" else "已完成购买"
            activity_parts.append((act_counter.next(), c[0], act[0], part_date, status, note))


def gen_battle_packages():
    """生成作战包(10-15个)"""
    # 选取有明确商机信号的客户
    opp_types = ["产品到期承接","代发到账配置","流失预警挽回","基金挖掘","教育金规划","经营贷续贷"]
    candidates = random.sample(customers, min(15, len(customers)))

    for i, c in enumerate(candidates):
        bp_id = f"BP{c[1]}{i+1:02d}"
        opp_id = f"OPP{c[1]}{i+1:02d}"
        mode = "面谈版" if random.random() < 0.6 else "电话版"

        # 客户速览
        overview = json.dumps({
            "name": c[2], "age": c[3], "gender": "男" if c[4] == "M" else "女",
            "tier": c[11], "total_aum": c[12],
            "visit_purpose": random.choice(opp_types),
            "key_signals": random.choice(["产品即将到期","近期浏览理财产品频繁","AUM下降","代发工资稳定"]),
        }, ensure_ascii=False)

        # 议程(仅面谈版)
        agenda = None
        if mode == "面谈版":
            agenda = json.dumps([
                {"step": 1, "topic": "开场寒暄", "duration": "2-3分钟", "notes": "上次沟通延续"},
                {"step": 2, "topic": f"核心议题: {random.choice(opp_types)}", "duration": "10-15分钟", "notes": "确认意向"},
                {"step": 3, "topic": "延伸议题: 基金配置建议", "duration": "5-10分钟", "notes": "了解兴趣"},
                {"step": 4, "topic": "收尾确认", "duration": "3-5分钟", "notes": "约定下次联系时间"},
            ], ensure_ascii=False)

        # 风险提示
        risk_warnings = "{" + ",".join([
            '"不得承诺收益"', '"不得误导风险等级"', '"基金产品须说明过往业绩不代表未来表现"',
            f'"客户风测为{random.choice(RISK_RESULTS[:3])},推荐产品风险等级不得超过此等级"',
        ]) + "}"

        post_actions = "{" + ",".join([
            '"录入本次沟通记录"', '"标记客户意向产品"', '"创建跟进任务"', '"更新客户标签"',
        ]) + "}"

        gen_at = TODAY - timedelta(days=random.randint(0, 10))
        exp_at = gen_at + timedelta(days=7)
        status = "已过期" if exp_at < TODAY else ("已使用" if random.random() < 0.2 else "未使用")
        used_at = gen_at + timedelta(days=random.randint(1, 5)) if status == "已使用" else None

        battle_pkgs.append((i + 1, bp_id, opp_id, c[0], mode, status, overview, agenda, risk_warnings, post_actions, gen_at, exp_at, used_at))

        # 线索(1-3条)
        n_clues = 1 if mode == "电话版" else random.randint(2, 3)
        for j in range(n_clues):
            clue_id = f"CL{bp_id}{j+1:02d}"
            priority = random.choice(["高","中","常规"])
            title = f"线索#{j+1}: {random.choice(opp_types)}"
            basis = f"系统检测到客户{random.choice(['产品即将到期','近期高频浏览理财','代发工资稳定流入','子女教育需求信号','AUM持续下降'])}"
            strategy = f"以'{random.choice(['到期提醒','理财配置','教育规划','资产保值'])}'为切入点，引导客户了解{random.choice(['稳健理财产品','基金定投','教育年金险'])}"
            script = f"{c[2]}您好，今天约您来是想跟您聊一下{random.choice(['您持有的理财产品','最近的资产配置','孩子的教育规划'])}……"

            # 推荐产品
            prods = []
            for _ in range(random.randint(1, 3)):
                prod = random.choice(product_catalog) if product_catalog else ("","","","R2",2.5,10000,"")
                prods.append({
                    "name": prod[2], "type": prod[3], "risk": prod[4],
                    "yield": prod[5], "reason": random.choice(["符合风测","收益高于定存","期限灵活"]),
                    "script": f"这款产品最大的特点是{random.choice(['稳健','收益好','流动性强'])}……"
                })
            products_json = json.dumps(prods, ensure_ascii=False)

            # 偏离分支(仅面谈版)
            deviation = None
            if mode == "面谈版":
                dev_list = [
                    {"scenario": "客户表示不需要此产品", "response": "了解客户真实需求，转向下一线索", "suggested_products": []},
                    {"scenario": "客户对收益不满意", "response": "推荐收益更高的替代产品", "suggested_products": [{"name": "XX高收益理财", "yield": 4.5}]},
                    {"scenario": "客户透露有其他银行竞争产品", "response": "对比我行产品优势，突出服务和便利性", "suggested_products": []},
                ]
                deviation = json.dumps(random.sample(dev_list, min(3, len(dev_list))), ensure_ascii=False)

            bp_clues.append((j + 1, clue_id, bp_id, priority, title, basis, strategy, script, products_json, deviation))


def print_stats():
    """打印统计信息"""
    print(f"\n  customers:        {len(customers)}")
    print(f"  family_info:      {len(family_infos)}")
    print(f"  business_info:    {len(business_infos)}")
    print(f"  employment_status:{len(emp_statuses)}")
    print(f"  holdings:         {len(holdings)}")
    print(f"  transactions:     {len(transactions)}")
    print(f"  loans:            {len(loans)}")
    print(f"  loan_rejections:  {len(loan_rejections)}")
    print(f"  behavior_logs:    {len(behavior_logs)}")
    print(f"  customer_relations:{len(customer_relations)}")
    print(f"  communications:   {len(communications)}")
    print(f"  risk_assessments: {len(risk_assessments)}")
    print(f"  product_catalog:  {len(product_catalog)}")
    print(f"  benefits:         {len(benefits)}")
    print(f"  activities:       {len(activities)}")
    print(f"  activity_parts:   {len(activity_parts)}")
    print(f"  battle_packages:  {len(battle_pkgs)}")
    print(f"  bp_clues:         {len(bp_clues)}")


def write_to_db(conn_str: str):
    """写入 PostgreSQL"""
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()

    # 按依赖顺序写入
    tables = [
        ("customers", customers, 13),
        ("family_info", family_infos, 11),
        ("business_info", business_infos, 11),
        ("employment_status", emp_statuses, 9),
        ("product_catalog", product_catalog, 9),
        ("holdings", holdings, 14),
        ("transactions", transactions, 8),
        ("loans", loans, 10),
        ("loan_rejections", loan_rejections, 5),
        ("behavior_logs", behavior_logs, 10),
        ("customer_relations", customer_relations, 6),
        ("communications", communications, 8),
        ("risk_assessments", risk_assessments, 10),
        ("customer_benefits", benefits, 10),
        ("available_activities", activities, 8),
        ("customer_activity_participation", activity_parts, 6),
        ("battle_packages", battle_pkgs, 13),
        ("battle_package_clues", bp_clues, 10),
    ]

    for table, data, ncols in tables:
        placeholders = ",".join(["%s"] * ncols)
        sql = f"INSERT INTO {table} VALUES ({placeholders})"
        for row in data:
            cur.execute(sql, row)
        print(f"  Inserted {len(data)} rows into {table}")

    conn.commit()
    cur.close()
    conn.close()
    print("\nAll data written to PostgreSQL.")


def write_to_sql_file(path: str):
    """导出为SQL INSERT文件(可选备选方案)"""
    with open(path, "w", encoding="utf-8") as f:
        f.write("-- 易会办 模拟数据集 SQL INSERT\n\n")
        tables = [
            ("customers", customers),
            ("family_info", family_infos),
            ("business_info", business_infos),
            ("employment_status", emp_statuses),
            ("product_catalog", product_catalog),
            ("holdings", holdings),
            ("transactions", transactions),
            ("loans", loans),
            ("loan_rejections", loan_rejections),
            ("behavior_logs", behavior_logs),
            ("customer_relations", customer_relations),
            ("communications", communications),
            ("risk_assessments", risk_assessments),
            ("customer_benefits", benefits),
            ("available_activities", activities),
            ("customer_activity_participation", activity_parts),
            ("battle_packages", battle_pkgs),
            ("battle_package_clues", bp_clues),
        ]
        for table, data in tables:
            for row in data[:5]:  # 每表仅头5条示例
                vals = ",".join(repr(v) if v is not None else "NULL" for v in row)
                f.write(f"INSERT INTO {table} VALUES ({vals});\n")
    print(f"Sample SQL written to {path}")


if __name__ == "__main__":
    generate()
    # 写入 PostgreSQL
    write_to_db("dbname=yihuiban_sim user=yihuiban password=yihuiban_dev host=localhost port=5432")
