"""
BattlePkgAgent — 作战包生成智能体
基于客户全维度数据，生成访前作战包（客户速览/营销线索/切入话术/产品推荐/风险提示）

触发方式：
  - 按需(实时)：客户经理在商机待办/商机看板点击"生成作战包"
"""
import os
import json
import time
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

from ..harness import Agent, AgentContext, agent, skill
from ..skills import (
    query_customer_full,
    query_customers,
    query_holdings,
    query_transactions,
    query_behavior,
    query_communications,
    query_risk,
    query_relations,
    query_family,
    query_loans,
    query_benefits,
    query_activities,
)
from ..model_adapter import get_adapter

log = logging.getLogger("agentos.battle_pkg")

# 产品数据库路径
PRODUCT_DB_PATH = Path(__file__).parent.parent.parent.parent / "原型设计" / "data" / "product_database.json"


def load_product_db() -> dict:
    """加载产品数据库"""
    if PRODUCT_DB_PATH.exists():
        try:
            with open(PRODUCT_DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Failed to load product DB: {e}")
    return {"products": []}


def select_products_for_customer(
    customer: dict,
    product_db: dict,
    risk_result: str = "稳健型",
    max_count: int = 6,
) -> list[dict]:
    """
    根据客户画像筛选合适的产品（规则初筛）

    Args:
        customer: 客户基本信息
        product_db: 产品数据库
        risk_result: 客户风测结果
        max_count: 最多返回产品数

    Returns:
        适合客户的产品列表
    """
    products = product_db.get("products", [])
    if not products:
        return []

    # 风测→风险等级映射
    risk_map = {
        "保守型": ["R1"],
        "稳健型": ["R1", "R2"],
        "平衡型": ["R1", "R2", "R3"],
        "成长型": ["R1", "R2", "R3", "R4"],
        "进取型": ["R1", "R2", "R3", "R4", "R5"],
    }
    allowed_risks = risk_map.get(risk_result, ["R1", "R2"])

    # 客户AUM
    total_aum = float(customer.get("total_aum", 0) or 0)

    # 客户行为偏好
    behavior_tags = set()
    holdings = query_holdings(customer.get("id", 0))
    for h in holdings:
        behavior_tags.add(h.get("product_type", ""))

    scored = []
    for p in products:
        if p.get("risk_level", "R5") not in allowed_risks:
            continue
        if p.get("status") != "在售":
            continue

        score = 0

        # 场景标签匹配
        scenario_tags = p.get("scenario_tags", [])
        if total_aum < 50000 and "活钱管理" in scenario_tags:
            score += 10
        if total_aum > 100000 and "稳健投资" in scenario_tags:
            score += 8
        if total_aum > 500000 and ("高收益" in scenario_tags or "中长期理财" in scenario_tags):
            score += 6
        if "保本保息" in scenario_tags and risk_result == "保守型":
            score += 10
        if "存款" in behavior_tags and p.get("category") == "存款":
            score += 5
        if "理财" in behavior_tags and p.get("category") == "理财":
            score += 5
        if "基金" in behavior_tags and p.get("category") == "基金":
            score += 5

        # 门槛匹配
        min_amount = p.get("min_amount", 0) or 0
        if min_amount <= 10000 and total_aum > min_amount * 10:
            score += 3

        # 收益率加分
        if p.get("expected_return_max", 0) and p["expected_return_max"] > 3:
            score += 3

        scored.append((score, p))

    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:max_count]]


def format_product_context(products: list[dict]) -> str:
    """将产品列表格式化为 LLM 上下文"""
    lines = []
    for i, p in enumerate(products):
        lines.append(f"  产品{i+1}: {p.get('short_name', p.get('product_name', ''))}")
        lines.append(f"    全称: {p.get('product_name', '')}")
        lines.append(f"    类别: {p.get('category', '')}/{p.get('sub_category', '')}")
        lines.append(f"    风险: {p.get('risk_level', '')}（{p.get('risk_name', '')}）")
        lines.append(f"    期限: {p.get('term_desc', '')}")
        lines.append(f"    起购: {p.get('min_amount_desc', '')}")
        er_min = p.get('expected_return_min', '')
        er_max = p.get('expected_return_max', '')
        if er_min or er_max:
            lines.append(f"    收益: {er_min}%~{er_max}%（{p.get('return_type', '')}）")
        if p.get('selling_points'):
            lines.append(f"    卖点: {'; '.join(p['selling_points'][:3])}")
        if p.get('scenario_tags'):
            lines.append(f"    场景: {', '.join(p['scenario_tags'])}")
        lines.append("")
    return "\n".join(lines)


@agent(
    name="作战包生成智能体",
    role="battle_package_maker",
    description="生成访前作战包，含客户速览/营销线索/切入话术/产品推荐/风险提示",
    skills=[
        "gen_overview", "gen_clues", "gen_scripts",
        "match_products", "query_customers", "query_holdings",
    ],
    model="deepseek-chat",
    triggers=["on_demand"],
    rate_limit=20,
    timeout=300,
)
class BattlePackageAgent(Agent):
    """作战包生成领域专家"""

    system_prompt = "prompts/battle_package.md"

    def __init__(self, adapter=None):
        super().__init__(adapter)
        self.load_prompt(self.system_prompt)
        self._product_db = None

    @property
    def product_db(self) -> dict:
        if self._product_db is None:
            self._product_db = load_product_db()
        return self._product_db

    def _build_customer_context(self, cust_id: int) -> dict:
        """组装客户全维度上下文"""
        full = query_customer_full(cust_id)
        if not full:
            return {}

        customer = full.get("customer", {})
        family = full.get("family", {})
        holdings = full.get("holdings", [])
        transactions = full.get("transactions", [])[:20]
        behavior_logs = full.get("behavior_logs", [])[:15]
        communications = full.get("communications", [])[:5]
        risk_assessment = full.get("risk_assessment", {})
        relations = full.get("relations", [])[:3]
        loans = full.get("loans", [])
        benefits = full.get("benefits", [])
        activities = full.get("activities", [])

        return {
            "customer": customer,
            "family": family,
            "holdings": holdings,
            "transactions": transactions,
            "behavior_logs": behavior_logs,
            "communications": communications,
            "risk_assessment": risk_assessment,
            "relations": relations,
            "loans": loans,
            "benefits": benefits,
            "activities": activities,
        }

    def _build_user_prompt(
        self,
        cust_id: int,
        mode: str,
        opportunity_info: dict = None,
    ) -> str:
        """构建发送给 LLM 的 user prompt"""
        ctx = self._build_customer_context(cust_id)

        customer = ctx.get("customer", {})
        risk = ctx.get("risk_assessment", {})
        risk_current = risk.get("current", {}) if isinstance(risk, dict) else {}
        risk_result = risk_current.get("test_result", "稳健型") if isinstance(risk_current, dict) else "稳健型"

        # 格式化客户上下文
        cust_info = json.dumps({
            "基本信息": {
                "姓名": customer.get("name", ""),
                "年龄": customer.get("age", ""),
                "性别": "男" if customer.get("gender") == "M" else "女",
                "职业": customer.get("occupation", ""),
                "行业": customer.get("industry", ""),
                "城市": customer.get("city", ""),
                "学历": customer.get("education", ""),
                "客户等级": customer.get("tier", ""),
                "总资产(AUM)": f"{float(customer.get('total_aum', 0) or 0)/10000:.1f}万",
            },
            "家庭信息": {
                "婚姻": "已婚" if ctx.get("family", {}).get("marriage") else "未婚",
                "子女数": ctx.get("family", {}).get("child_count", 0),
                "子女年龄": ctx.get("family", {}).get("child_age"),
                "子女教育阶段": ctx.get("family", {}).get("child_education"),
                "留学意向": ctx.get("family", {}).get("study_abroad_intent"),
            } if ctx.get("family") else None,
            "持仓概览": [
                {
                    "产品": h.get("product_name"),
                    "类型": h.get("product_type"),
                    "金额": f"{float(h.get('amount', 0) or 0)/10000:.1f}万",
                    "收益率": h.get("yield_rate"),
                    "风险": h.get("risk_level"),
                    "到期日": h.get("maturity_date"),
                }
                for h in ctx.get("holdings", [])
            ],
            "近期交易(摘要)": [
                {
                    "日期": t.get("txn_date"),
                    "类型": "收入" if t.get("txn_type") == "in" else "支出",
                    "金额": round(float(t.get("amount", 0) or 0), 2),
                    "摘要": t.get("summary"),
                }
                for t in ctx.get("transactions", [])[:10]
            ],
            "行为偏好": [
                {
                    "日期": b.get("event_date"),
                    "渠道": b.get("channel"),
                    "浏览页面": b.get("page_type"),
                    "动作": b.get("action"),
                }
                for b in ctx.get("behavior_logs", [])[:10]
            ],
            "沟通记录": [
                {
                    "日期": c.get("comm_date"),
                    "渠道": c.get("channel"),
                    "摘要": c.get("summary"),
                }
                for c in ctx.get("communications", [])[:5]
            ],
            "风测结果": {
                "结果": risk_result,
                "财富分": risk_current.get("wealth_score") if isinstance(risk_current, dict) else None,
            },
            "贷款": [
                {
                    "产品": l.get("product_name"),
                    "额度": f"{float(l.get('credit_line', 0) or 0)/10000:.1f}万",
                    "已用": f"{float(l.get('used_amount', 0) or 0)/10000:.1f}万",
                    "逾期次数": l.get("overdue_count", 0),
                }
                for l in ctx.get("loans", [])
            ] if ctx.get("loans") else None,
            "权益与活动": {
                "已持有权益": [
                    {
                        "名称": b.get("benefit_name"),
                        "类型": b.get("benefit_type"),
                        "描述": b.get("description"),
                        "价值": b.get("rarity"),
                        "状态": b.get("status"),
                        "到期日": b.get("expiry_date"),
                    }
                    for b in ctx.get("benefits", [])
                ],
                "参与活动": [
                    {
                        "名称": a.get("title"),
                        "类型": a.get("type"),
                        "奖励": a.get("reward_desc"),
                        "状态": a.get("status"),
                    }
                    for a in ctx.get("activities", [])
                ],
            } if (ctx.get("benefits") or ctx.get("activities")) else None,
        }, ensure_ascii=False, indent=2)

        # 匹配产品
        matched_products = select_products_for_customer(
            customer, self.product_db, risk_result=risk_result
        )
        product_ctx = format_product_context(matched_products)

        # 商机信息
        opp_section = ""
        if opportunity_info:
            opp_section = f"""
**关联商机信息**：
- 商机类型: {opportunity_info.get('type', '')}
- 商机标题: {opportunity_info.get('title', '')}
- 发现依据: {opportunity_info.get('reasoning', '')}
- 预估价值: {opportunity_info.get('estimated_value', '')}元
- 置信度: {opportunity_info.get('confidence', '')}
"""

        prompt = f"""请为以下客户生成一份"{"面谈版(全功能)" if mode == "面谈版" else "电话版(轻量)"}"作战包。

**当前日期**: {date.today().isoformat()}
**作战包模式**: {mode}

{opp_section}

**客户全维度数据**：
```json
{cust_info}
```

**可选产品库**（从产品数据库中预筛选了 {len(matched_products)} 个适合该客户的产品）：
{product_ctx}

**重要提示**：
1. 这是{"面谈版" if mode == "面谈版" else "电话版"}作战包，请按对应格式输出
2. 营销线索的发现依据必须引用上述客户数据中的具体数字/事实
3. 推荐产品必须从上述产品库中选择（填写产品全名），不要编造产品
4. 切入话术必须是自然的口语对话，包含引导性问题
5. 请严格按照 system prompt 中定义的 JSON 输出格式返回结果"""

        return prompt

    async def generate_battle_package(
        self,
        ctx: AgentContext,
        cust_id: int,
        mode: str = "面谈版",
        opportunity_info: dict = None,
        progress_callback=None,
    ) -> dict:
        """
        生成作战包

        Args:
            ctx: 执行上下文
            cust_id: 客户ID
            mode: 作战包模式 (电话版/面谈版)
            opportunity_info: 关联的商机信息
            progress_callback: 可选 SSE 进度回调

        Returns:
            作战包数据 dict
        """
        log.info(f"generate_battle_package: cust_id={cust_id}, mode={mode}")

        if progress_callback:
            await progress_callback("phase", {
                "phase": "loading_data",
                "message": "正在加载客户数据...",
            })

        # 构建客户上下文
        full = self._build_customer_context(cust_id)
        if not full.get("customer"):
            return {"error": "客户不存在", "cust_id": cust_id}

        customer = full["customer"]

        if progress_callback:
            await progress_callback("phase", {
                "phase": "matching_products",
                "message": "正在匹配产品...",
                "customer_name": customer.get("name", ""),
            })

        # 构建 prompt
        user_prompt = self._build_user_prompt(cust_id, mode, opportunity_info)

        if progress_callback:
            await progress_callback("phase", {
                "phase": "generating",
                "message": "AI 正在生成作战包...",
            })

        # 调用 LLM
        start = time.time()
        try:
            result = self.adapter.analyze_json(
                system_prompt=self.system_prompt_text,
                user_prompt=user_prompt,
                temperature=0.4,
            )
            elapsed = time.time() - start
            log.info(f"BattlePackage generated: {elapsed:.1f}s, tokens_approx={len(user_prompt)//3}")

            if progress_callback:
                await progress_callback("phase", {
                    "phase": "completed",
                    "message": "AI 生成完成，正在保存...",
                    "elapsed_s": round(elapsed, 1),
                })

            return {
                "status": "completed",
                "cust_id": cust_id,
                "cust_name": customer.get("name", ""),
                "mode": mode,
                "bp_data": result,
                "elapsed_s": round(elapsed, 1),
            }
        except Exception as e:
            log.error(f"BattlePackage generation failed: {e}")
            if progress_callback:
                await progress_callback("error", {"message": f"生成失败: {str(e)}"})
            return {
                "status": "failed",
                "cust_id": cust_id,
                "cust_name": customer.get("name", ""),
                "error": str(e),
            }

    def save_battle_package(self, bp_result: dict, db) -> dict:
        """
        将生成的作战包保存到数据库

        Args:
            bp_result: generate_battle_package 的返回结果
            db: SQLite 数据库连接

        Returns:
            {"bp_id": "...", "clue_ids": [...]}
        """
        if bp_result.get("status") != "completed":
            return {"error": "Cannot save failed result"}

        bp_data = bp_result.get("bp_data", {})
        cust_id = bp_result["cust_id"]
        mode = bp_result["mode"]
        now = datetime.now().isoformat()
        expires = (date.today() + timedelta(days=7)).isoformat()

        bp_id = f"BP_AI_{int(datetime.now().timestamp())}"
        opp_id = f"OPP_{bp_id}"

        # 保存 customer_overview
        overview = bp_data.get("customer_overview", {})
        overview_json = json.dumps(overview, ensure_ascii=False)

        # 保存 agenda
        agenda = bp_data.get("agenda")
        agenda_json = json.dumps(agenda, ensure_ascii=False) if agenda else None

        # 保存 risk_warnings
        risk_warnings = bp_data.get("risk_warnings", [])
        risk_json = json.dumps(risk_warnings, ensure_ascii=False)

        # 保存 post_visit_actions
        post_actions = bp_data.get("post_visit_actions", [])
        post_json = json.dumps(post_actions, ensure_ascii=False)

        cur = db.cursor()
        cur.execute(
            """INSERT INTO battle_packages
               (bp_id, opp_id, cust_id, mode, status, customer_overview,
                agenda, risk_warnings, post_visit_actions,
                generated_at, expires_at)
               VALUES (?, ?, ?, ?, '未使用', ?, ?, ?, ?, ?, ?)""",
            (bp_id, opp_id, cust_id, mode, overview_json,
             agenda_json, risk_json, post_json, now, expires),
        )

        # 保存 clues
        clues = bp_data.get("clues", [])
        clue_ids = []
        for i, clue in enumerate(clues):
            clue_id = f"CL_{bp_id}_{i+1:02d}"
            products_json = json.dumps(clue.get("products", []), ensure_ascii=False)
            deviation = clue.get("deviation_branches")
            deviation_json = json.dumps(deviation, ensure_ascii=False) if deviation else None

            cur.execute(
                """INSERT INTO battle_package_clues
                   (clue_id, bp_id, priority, title, discovery_basis,
                    strategy, opening_script, products, deviation_branches)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (clue_id, bp_id,
                 clue.get("priority", "中"),
                 clue.get("title", ""),
                 clue.get("discovery_basis", ""),
                 clue.get("strategy", ""),
                 clue.get("opening_script", ""),
                 products_json,
                 deviation_json),
            )
            clue_ids.append(clue_id)

        db.commit()
        log.info(f"BattlePackage saved: {bp_id}, {len(clue_ids)} clues")

        return {
            "bp_id": bp_id,
            "opp_id": opp_id,
            "cust_id": cust_id,
            "cust_name": bp_result.get("cust_name", ""),
            "mode": mode,
            "status": "未使用",
            "clue_ids": clue_ids,
            "generated_at": now,
            "expires_at": expires,
        }


# ============================================================
# 便捷函数
# ============================================================

def create_battle_pkg_agent() -> BattlePackageAgent:
    """创建作战包 Agent 实例（注册到全局 harness）"""
    from ..harness import harness as h
    agent = BattlePackageAgent()
    h.registry.register(BattlePackageAgent.meta, agent)
    return agent
