"""
易会办 客户洞察模拟数据集 — 客户画像模板定义
定义了6类典型客户画像的字段模板、概率分布与取值范围
"""
import random

# ============================================================
# 全局常量
# ============================================================
SURNAMES = ["王","李","张","刘","陈","杨","赵","黄","周","吴","徐","孙","胡","朱","高","林","何","郭","马","罗",
            "梁","宋","郑","谢","韩","唐","冯","于","董","萧","程","曹","袁","邓","许","傅","沈","曾","彭","吕"]
MALE_NAMES = ["建国","伟","强","磊","军","勇","涛","明","辉","斌","鹏","杰","浩","宇","文","博","睿","志","飞","超"]
FEMALE_NAMES = ["丽","芳","秀英","敏","静","婷","雪","艳","娟","玲","红","霞","兰","慧","洁","燕","颖","萍","娜","蕾"]
CITIES = ["合肥","芜湖","马鞍山","安庆","蚌埠","阜阳","淮南","宣城","六安","滁州"]
OCCUPATIONS = {
    "在职": ["工程师","教师","公务员","销售经理","会计","IT项目经理","医生","护士","企业中层","银行职员"],
    "自由职业": ["自媒体","设计师","咨询顾问","自由撰稿人","摄影师"],
    "无业": ["暂无"],
    "待业": ["暂无"],
    "不确定": ["待确认"],
}
INDUSTRIES = ["金融业","信息技术","制造业","教育","医疗","房地产","零售","交通运输","建筑","农林牧渔"]
EDUCATIONS = ["高中","大专","本科","硕士","博士"]
COMPANY_PREFIX = ["徽商","恒信","通达","瑞丰","天元","中盛","博源","华泰科技","江淮","长城"]

# 等级与AUM范围映射(元)
TIER_AUM_RANGE = {
    "千元以下": (0, 999),
    "千元户": (1000, 9999),
    "万元户": (10000, 49999),
    "优质": (50000, 199999),
    "财富": (200000, 999999),
    "高净值": (1000000, 2999999),
    "私钻": (3000000, 5999999),
    "私行": (6000000, 20000000),
}

# 产品名称库
PRODUCTS = {
    "存款": [("活期存款", "C001"), ("定期存款一年", "C002"), ("大额存单", "C003"), ("通知存款", "C004")],
    "理财": [("XX稳健增长A", "W001"), ("YY悦享周期90天", "W002"), ("ZZ现金管理", "W003"), ("AA尊享理财", "W004"), ("BB季季盈", "W005")],
    "基金": [("AA稳健混合", "F001"), ("BB债券增强", "F002"), ("CC指数联接", "F003"), ("DD行业精选", "F004")],
    "贵金属": [("积存金", "G001"), ("账户贵金属", "G002")],
    "保险": [("CC金宝贝年金险", "I001"), ("终身寿险尊享版", "I002")],
}

RISK_LEVELS = ["R1", "R2", "R3", "R4", "R5"]
RISK_RESULTS = ["保守型", "稳健型", "平衡型", "进取型", "激进型"]

# ============================================================
# 类型 A：代发薪白领 25人
# ============================================================
TEMPLATE_A = {
    "type_name": "A·代发薪白领",
    "count": 25,
    "age_range": (25, 40),
    "gender_ratio": {"M": 0.55, "F": 0.45},
    "city_weights": {"合肥": 0.50, "芜湖": 0.15, "马鞍山": 0.10, "安庆": 0.10, "蚌埠": 0.05, "阜阳": 0.05, "其他": 0.05},
    "tier_weights": {"千元以下": 0.05, "千元户": 0.15, "万元户": 0.35, "优质": 0.45},
    "education_weights": {"高中": 0.10, "大专": 0.30, "本科": 0.50, "硕士": 0.10, "博士": 0.00},
    "employment": {
        "status_weights": {"在职": 0.95, "自由职业": 0.05},
        "unemployment_benefits_prob": 0.0,
    },
    "family": {
        "married_prob": 0.60,
        "children_prob": 0.45,
        "child_count_range": (1, 1),
        "child_age_range": (0, 8),
        "child_education_weights": {"幼儿园": 0.45, "小学": 0.35, "初中": 0.15, "高中": 0.05},
        "study_abroad_intent_prob": 0.03,
        "spouse_has_income_prob": 0.70,
    },
    "holdings_template": {
        "存款": {"prob": 1.0, "amount_range": (2000, 50000), "count_range": (1, 2)},
        "理财": {"prob": 0.40, "amount_range": (10000, 80000), "count_range": (1, 2)},
        "基金": {"prob": 0.15, "amount_range": (5000, 30000), "count_range": (1, 1)},
        "贵金属": {"prob": 0.02, "amount_range": (1000, 5000)},
        "保险": {"prob": 0.05, "amount_range": (10000, 30000)},
    },
    "loan_prob": 0.05,
    "loan_type_weights": {"消费贷": 1.0},
    "salary_disbursement": True,
    "salary_range": {  # 月代发范围(元)
        "千元以下": (800, 5000),
        "千元户": (3000, 8000),
        "万元户": (5000, 12000),
        "优质": (8000, 20000),
    },
    "tier_specifics": {  # 等级对应的AUM范围及典型性别
        "千元以下": {"aum_range": (300, 800), "active_prob": 0.5},
        "千元户":   {"aum_range": (2000, 8000), "active_prob": 0.6},
        "万元户":   {"aum_range": (15000, 45000), "active_prob": 0.7},
        "优质":     {"aum_range": (60000, 180000), "active_prob": 0.8},
    },
    "behavior_bias": {"理财": 0.40, "基金": 0.20, "存款": 0.30, "保险": 0.05, "贷款": 0.05},
    "behavior_daily_prob": 0.08,  # 每天有行为日志的概率
    "opportunity_signals": ["代发到账", "理财配置"],
    "communications_per_month": 0.4,
}

# ============================================================
# 类型 B：财富理财客 20人
# ============================================================
TEMPLATE_B = {
    "type_name": "B·财富理财客",
    "count": 20,
    "age_range": (35, 60),
    "gender_ratio": {"M": 0.50, "F": 0.50},
    "city_weights": {"合肥": 0.60, "芜湖": 0.15, "马鞍山": 0.10, "安庆": 0.10, "其他": 0.05},
    "tier_weights": {"财富": 0.50, "高净值": 0.35, "私钻": 0.10, "私行": 0.05},
    "education_weights": {"高中": 0.05, "大专": 0.15, "本科": 0.50, "硕士": 0.20, "博士": 0.10},
    "employment": {
        "status_weights": {"在职": 0.75, "自由职业": 0.15, "不确定": 0.10},
        "unemployment_benefits_prob": 0.0,
    },
    "family": {
        "married_prob": 0.80,
        "children_prob": 0.70,
        "child_count_range": (1, 2),
        "child_age_range": (12, 25),
        "child_education_weights": {"初中": 0.10, "高中": 0.30, "大学": 0.40, "研究生": 0.15, "留学中": 0.05},
        "study_abroad_intent_prob": 0.20,
        "spouse_has_income_prob": 0.60,
    },
    "holdings_template": {
        "存款": {"prob": 1.0, "amount_range": (50000, 500000), "count_range": (1, 2)},
        "理财": {"prob": 0.80, "amount_range": (50000, 800000), "count_range": (2, 4)},
        "基金": {"prob": 0.60, "amount_range": (30000, 500000), "count_range": (1, 3)},
        "贵金属": {"prob": 0.10, "amount_range": (5000, 50000)},
        "保险": {"prob": 0.15, "amount_range": (50000, 300000)},
    },
    "loan_prob": 0.15,
    "loan_type_weights": {"房贷": 0.8, "消费贷": 0.2},
    "salary_disbursement": False,
    "tier_specifics": {
        "财富":    {"aum_range": (250000, 900000), "active_prob": 0.85},
        "高净值":  {"aum_range": (1100000, 2800000), "active_prob": 0.90},
        "私钻":    {"aum_range": (3200000, 5500000), "active_prob": 0.90},
        "私行":    {"aum_range": (6500000, 15000000), "active_prob": 0.90},
    },
    "behavior_bias": {"理财": 0.35, "基金": 0.35, "存款": 0.15, "保险": 0.10, "贷款": 0.05},
    "behavior_daily_prob": 0.12,
    "opportunity_signals": ["产品到期", "基金挖掘", "教育金规划"],
    "communications_per_month": 0.7,
}

# ============================================================
# 类型 C：信贷客户 15人
# ============================================================
TEMPLATE_C = {
    "type_name": "C·信贷客户",
    "count": 15,
    "age_range": (30, 50),
    "gender_ratio": {"M": 0.60, "F": 0.40},
    "city_weights": {"合肥": 0.40, "芜湖": 0.20, "马鞍山": 0.10, "安庆": 0.10, "其他": 0.20},
    "tier_weights": {"万元户": 0.30, "优质": 0.40, "财富": 0.25, "高净值": 0.05},
    "education_weights": {"高中": 0.20, "大专": 0.35, "本科": 0.40, "硕士": 0.05, "博士": 0.00},
    "employment": {
        "status_weights": {"在职": 0.80, "自由职业": 0.20},
        "unemployment_benefits_prob": 0.0,
    },
    "family": {
        "married_prob": 0.70,
        "children_prob": 0.50,
        "child_count_range": (1, 2),
        "child_age_range": (5, 18),
        "child_education_weights": {"幼儿园": 0.15, "小学": 0.30, "初中": 0.30, "高中": 0.25},
        "study_abroad_intent_prob": 0.05,
        "spouse_has_income_prob": 0.50,
    },
    "holdings_template": {
        "存款": {"prob": 0.90, "amount_range": (5000, 100000), "count_range": (1, 2)},
        "理财": {"prob": 0.20, "amount_range": (10000, 50000)},
        "基金": {"prob": 0.10, "amount_range": (5000, 30000)},
        "保险": {"prob": 0.10, "amount_range": (10000, 50000)},
    },
    "loan_prob": 0.90,
    "loan_type_weights": {"房贷": 0.60, "经营贷": 0.20, "消费贷": 0.20},
    "loan_overdue_prob": 0.30,  # 有逾期记录的概率
    "loan_rejection_prob": 0.15,  # 有被拒记录的概率
    "salary_disbursement": False,
    "tier_specifics": {
        "万元户":   {"aum_range": (15000, 45000), "active_prob": 0.6},
        "优质":     {"aum_range": (60000, 180000), "active_prob": 0.7},
        "财富":     {"aum_range": (220000, 800000), "active_prob": 0.8},
        "高净值":   {"aum_range": (1100000, 2500000), "active_prob": 0.8},
    },
    "behavior_bias": {"理财": 0.20, "基金": 0.10, "存款": 0.30, "保险": 0.05, "贷款": 0.35},
    "behavior_daily_prob": 0.05,
    "opportunity_signals": ["贷款逾期", "交叉销售理财"],
    "communications_per_month": 0.3,
}

# ============================================================
# 类型 D：高净值私行客 10人
# ============================================================
TEMPLATE_D = {
    "type_name": "D·高净值私行客",
    "count": 10,
    "age_range": (45, 65),
    "gender_ratio": {"M": 0.70, "F": 0.30},
    "city_weights": {"合肥": 0.70, "芜湖": 0.15, "马鞍山": 0.10, "其他": 0.05},
    "tier_weights": {"私钻": 0.60, "私行": 0.40},
    "education_weights": {"本科": 0.40, "硕士": 0.40, "博士": 0.20},
    "employment": {
        "status_weights": {"在职": 0.60, "自由职业": 0.40},
        "unemployment_benefits_prob": 0.0,
    },
    "family": {
        "married_prob": 0.90,
        "children_prob": 0.80,
        "child_count_range": (1, 3),
        "child_age_range": (15, 30),
        "child_education_weights": {"高中": 0.10, "大学": 0.35, "研究生": 0.25, "留学中": 0.20, "已毕业": 0.10},
        "study_abroad_intent_prob": 0.40,
        "spouse_has_income_prob": 0.40,
    },
    "holdings_template": {
        "存款": {"prob": 1.0, "amount_range": (200000, 2000000), "count_range": (1, 2)},
        "理财": {"prob": 0.90, "amount_range": (200000, 3000000), "count_range": (3, 6)},
        "基金": {"prob": 0.80, "amount_range": (100000, 2000000), "count_range": (2, 5)},
        "贵金属": {"prob": 0.40, "amount_range": (50000, 500000), "count_range": (1, 2)},
        "保险": {"prob": 0.30, "amount_range": (100000, 1000000)},
    },
    "loan_prob": 0.20,
    "loan_type_weights": {"经营贷": 0.70, "房贷": 0.30},
    "salary_disbursement": False,
    "has_business_info_probt": 0.70,  # 有经营信息的概率
    "business_verified_prob": 0.85,
    "tier_specifics": {
        "私钻": {"aum_range": (3500000, 5500000), "active_prob": 0.90},
        "私行": {"aum_range": (7000000, 20000000), "active_prob": 0.95},
    },
    "behavior_bias": {"理财": 0.30, "基金": 0.30, "存款": 0.15, "保险": 0.15, "贷款": 0.10},
    "behavior_daily_prob": 0.10,
    "opportunity_signals": ["资产配置优化", "家族财富传承", "子女留学"],
    "communications_per_month": 0.8,
    # 关系图谱 — 至少有1个同企业代发关系对
    "relation_group_id": "D_NETWORK",
}

# ============================================================
# 类型 E：沉睡/流失风险客 20人
# ============================================================
TEMPLATE_E = {
    "type_name": "E·沉睡/流失风险客",
    "count": 20,
    "age_range": (25, 60),
    "gender_ratio": {"M": 0.50, "F": 0.50},
    "city_weights": {"合肥": 0.40, "芜湖": 0.15, "马鞍山": 0.10, "安庆": 0.10, "其他": 0.25},
    "tier_weights": {"千元以下": 0.05, "千元户": 0.10, "万元户": 0.15, "优质": 0.30, "财富": 0.30, "高净值": 0.10},
    "education_weights": {"高中": 0.15, "大专": 0.30, "本科": 0.45, "硕士": 0.10, "博士": 0.00},
    "employment": {
        "status_weights": {"在职": 0.55, "无业": 0.10, "待业": 0.10, "自由职业": 0.10, "不确定": 0.15},
        "unemployment_benefits_prob": 0.50,
    },
    "family": {
        "married_prob": 0.55,
        "children_prob": 0.40,
        "child_count_range": (1, 2),
        "child_age_range": (3, 20),
        "child_education_weights": {"幼儿园": 0.20, "小学": 0.30, "初中": 0.20, "高中": 0.15, "大学": 0.15},
        "study_abroad_intent_prob": 0.05,
        "spouse_has_income_prob": 0.40,
    },
    "holdings_template": {
        "存款": {"prob": 0.85, "amount_range": (500, 50000), "count_range": (1, 1)},
        "理财": {"prob": 0.25, "amount_range": (5000, 50000), "count_range": (1, 1)},
        "基金": {"prob": 0.10, "amount_range": (3000, 20000)},
        "保险": {"prob": 0.05, "amount_range": (5000, 30000)},
    },
    "loan_prob": 0.10,
    "loan_type_weights": {"消费贷": 0.7, "房贷": 0.3},
    "salary_disbursement": False,
    "tier_specifics": {
        "千元以下": {"aum_range": (200, 800), "active_prob": 0.2},
        "千元户":   {"aum_range": (1500, 8000), "active_prob": 0.3},
        "万元户":   {"aum_range": (12000, 40000), "active_prob": 0.4},
        "优质":     {"aum_range": (55000, 170000), "active_prob": 0.5},
        "财富":     {"aum_range": (220000, 800000), "active_prob": 0.6},
        "高净值":   {"aum_range": (1100000, 2400000), "active_prob": 0.55},
    },
    "behavior_bias": {"理财": 0.25, "基金": 0.15, "存款": 0.40, "保险": 0.10, "贷款": 0.10},
    "behavior_daily_prob": 0.03,  # 活跃度低
    "opportunity_signals": ["联络超期", "流失预警", "就业状态确认"],
    "communications_per_month": 0.15,  # 沟通频率低
    "aum_decline_trend": True,  # AUM下降趋势
    "other_bank_transfer_prob": 0.40,  # 有他行转账记录
}

# ============================================================
# 类型 F：小微企业主 10人
# ============================================================
TEMPLATE_F = {
    "type_name": "F·小微企业主",
    "count": 10,
    "age_range": (35, 55),
    "gender_ratio": {"M": 0.70, "F": 0.30},
    "city_weights": {"合肥": 0.50, "芜湖": 0.15, "马鞍山": 0.15, "安庆": 0.10, "其他": 0.10},
    "tier_weights": {"优质": 0.30, "财富": 0.40, "高净值": 0.20, "私钻": 0.10},
    "education_weights": {"高中": 0.15, "大专": 0.35, "本科": 0.40, "硕士": 0.10, "博士": 0.00},
    "employment": {
        "status_weights": {"在职": 0.60, "自由职业": 0.30, "不确定": 0.10},
        "unemployment_benefits_prob": 0.0,
    },
    "family": {
        "married_prob": 0.85,
        "children_prob": 0.70,
        "child_count_range": (1, 2),
        "child_age_range": (10, 22),
        "child_education_weights": {"初中": 0.30, "高中": 0.35, "大学": 0.25, "留学中": 0.05, "已毕业": 0.05},
        "study_abroad_intent_prob": 0.25,
        "spouse_has_income_prob": 0.30,
    },
    "holdings_template": {
        "存款": {"prob": 1.0, "amount_range": (30000, 500000), "count_range": (1, 2)},
        "理财": {"prob": 0.60, "amount_range": (50000, 500000), "count_range": (1, 3)},
        "基金": {"prob": 0.30, "amount_range": (20000, 200000)},
        "贵金属": {"prob": 0.05, "amount_range": (10000, 50000)},
        "保险": {"prob": 0.20, "amount_range": (30000, 200000)},
    },
    "loan_prob": 0.70,
    "loan_type_weights": {"经营贷": 0.60, "房贷": 0.30, "消费贷": 0.10},
    "loan_overdue_prob": 0.10,
    "salary_disbursement": False,
    "has_business_info_probt": 1.0,  # 全部有经营信息
    "business_verified_prob": 0.70,  # 70%已确认，30%待确认
    "tier_specifics": {
        "优质":   {"aum_range": (60000, 190000), "active_prob": 0.75},
        "财富":   {"aum_range": (250000, 950000), "active_prob": 0.80},
        "高净值": {"aum_range": (1100000, 2800000), "active_prob": 0.85},
        "私钻":   {"aum_range": (3200000, 5500000), "active_prob": 0.90},
    },
    "behavior_bias": {"理财": 0.25, "基金": 0.20, "存款": 0.25, "保险": 0.10, "贷款": 0.20},
    "behavior_daily_prob": 0.07,
    "opportunity_signals": ["经营贷续贷", "闲置资金理财", "子女教育规划", "身份确认"],
    "communications_per_month": 0.5,
}

# ============================================================
# 全部模板汇总
# ============================================================
ALL_TEMPLATES = [TEMPLATE_A, TEMPLATE_B, TEMPLATE_C, TEMPLATE_D, TEMPLATE_E, TEMPLATE_F]


# ============================================================
# 辅助函数
# ============================================================
def weighted_choice(weights: dict):
    """按权重随机选择"""
    items = list(weights.keys())
    probs = list(weights.values())
    total = sum(probs)
    r = random.random() * total
    cumulative = 0
    for item, prob in zip(items, probs):
        cumulative += prob
        if r <= cumulative:
            return item
    return items[-1]


def generate_name(gender: str) -> str:
    """生成中文姓名"""
    surname = random.choice(SURNAMES)
    if gender == "M":
        given = random.choice(MALE_NAMES)
    else:
        given = random.choice(FEMALE_NAMES)
    return surname + given


def child_education_from_age(age: int) -> str:
    """根据年龄推断学习阶段"""
    if age <= 3:
        return "幼儿园"
    elif age <= 6:
        return random.choice(["幼儿园", "小学"])
    elif age <= 12:
        return "小学"
    elif age <= 15:
        return "初中"
    elif age <= 18:
        return "高中"
    elif age <= 22:
        return "大学"
    elif age <= 25:
        return random.choice(["研究生", "已毕业"])
    else:
        return "已毕业"
