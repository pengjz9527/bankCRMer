"""
CustomerInsightAgent — 客户洞察智能体
每周定时批量生成客户洞察快照，含客户速览/变化信号/风险预警

触发方式：
  - 定时批量：每周日凌晨 3:00，全量生成
  - 按需：单客户洞察生成（供作战包等下游消费）
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
    query_customer_insight,
    query_customer_insights_by_manager,
    query_customers_by_insight_filter,
)
from ..model_adapter import get_adapter

log = logging.getLogger("agentos.customer_insight")


# ============================================================
# Agent 定义
# ============================================================

@agent(
    name="客户洞察智能体",
    role="customer_insight",
    description="360°客户洞察分析，生成客户速览/变化信号/风险预警快照",
    skills=[
        "query_profile", "analyze_behavior", "detect_risk",
        "query_customer_full", "query_customer_insight",
    ],
    triggers=["scheduled", "on_demand"],
    rate_limit=30,
    timeout=600,
)
class CustomerInsightAgent(Agent):
    """客户洞察领域专家"""

    system_prompt = "prompts/customer_insight.md"

    def __init__(self, adapter=None):
        super().__init__(adapter)
        self.load_prompt(self.system_prompt)

    # ================================================================
    # 定时批量生成（每周一次）
    # ================================================================

    async def batch_generate_all(self, ctx: AgentContext, max_per_batch: int = 8):
        """
        全量扫描所有管户，批量生成洞察快照

        流程：
          查询全量客户 → 分批(每批8人) → LLM 分析 → 入库
        """
        log.info(f"batch_generate_all start: scope={ctx.scope}")

        customers = query_customers(limit=10000)
        log.info(f"batch_generate_all: {len(customers)} customers to analyze")

        results = []
        batches = self.chunk(customers, max_per_batch)

        for i, batch in enumerate(batches):
            log.info(f"Insight batch {i+1}/{len(batches)}: {len(batch)} customers")
            batch_results = await self._analyze_batch(batch, ctx)
            results.extend(batch_results)

        # 入库
        saved_count = 0
        for r in results:
            if r.get("overview"):
                saved = self._save_insight(r, ctx.manager_id)
                if saved:
                    saved_count += 1

        log.info(f"batch_generate_all done: {len(results)} generated, {saved_count} saved")
        return {"total_generated": len(results), "saved": saved_count}

    # ================================================================
    # 单客户洞察生成（供作战包等下游消费）
    # ================================================================

    async def generate_single(self, ctx: AgentContext, cust_id: int) -> dict:
        """
        为单个客户生成洞察（供作战包等使用）

        Returns:
            {"overview": {...}, "change_signals": [...], "risk_signals": [...], "risk_level": "green", ...}
        """
        log.info(f"generate_single: cust_id={cust_id}")

        full = query_customer_full(cust_id)
        if not full:
            return {"error": "客户不存在", "cust_id": cust_id}

        user_prompt = self._build_user_prompt([full], ctx)

        start = time.time()
        try:
            resp = self.adapter.analyze_json(
                system_prompt=self.system_prompt_text,
                user_prompt=user_prompt,
                temperature=0.3,
            )
            result = resp["result"]
            elapsed = time.time() - start
            log.info(f"Insight generated for cust_id={cust_id}: {elapsed:.1f}s, tokens={resp['usage']['total_tokens']}")
            return result
        except Exception as e:
            log.error(f"Insight generation failed for cust_id={cust_id}: {e}")
            return {"error": str(e), "cust_id": cust_id}

    # ================================================================
    # 核心分析逻辑
    # ================================================================

    async def _analyze_batch(
        self, customers: list[dict], ctx: AgentContext
    ) -> list[dict]:
        """分析一批客户，调用 LLM 生成洞察"""
        enriched = []
        for c in customers:
            full = query_customer_full(c["id"])
            if full:
                enriched.append(full)

        if not enriched:
            return []

        user_prompt = self._build_user_prompt(enriched, ctx)

        start = time.time()
        try:
            resp = self.adapter.analyze_json(
                system_prompt=self.system_prompt_text,
                user_prompt=user_prompt,
                temperature=0.3,
            )
            result = resp["result"]
            elapsed = time.time() - start
            log.info(f"LLM insight batch: {len(enriched)} customers, {elapsed:.1f}s, tokens={resp['usage']['total_tokens']}")

            # 解析结果：LLM 返回可能是 list[dict] 或 {"results": [...]}
            if isinstance(result, list):
                return result
            elif isinstance(result, dict) and "results" in result:
                return result["results"]
            elif isinstance(result, dict) and "overview" in result:
                return [result]
            else:
                log.warning(f"Unexpected insight result format: {type(result)}")
                return []
        except Exception as e:
            log.error(f"LLM insight batch failed: {e}")
            return []

    def _build_user_prompt(self, customers: list[dict], ctx: AgentContext) -> str:
        """构建发送给 LLM 的 user prompt"""
        slim = []
        for c in customers:
            cust = c.get("customer", {})
            item = {
                "customer": cust,
                "family": c.get("family", {}),
                "holdings": c.get("holdings", []),
                "transactions": c.get("transactions", [])[:15],
                "behavior_logs": c.get("behavior_logs", [])[:10],
                "communications": c.get("communications", [])[:5],
                "risk_assessment": c.get("risk_assessment", {}).get("current"),
                "relations": c.get("relations", [])[:5],
                "loans": c.get("loans", []),
                "benefits": c.get("benefits", []),
                "activities": c.get("activities", []),
            }
            slim.append(item)

        data_json = json.dumps(slim, ensure_ascii=False, indent=2)

        prompt = f"""请为以下 {len(slim)} 位客户生成客户洞察报告，按 system prompt 中定义的格式输出。

**当前日期**：{date.today().isoformat()}
**分析范围**：{ctx.scope}

注意：
- 每位客户必须独立分析，输出各自的 overview、change_signals、risk_signals
- 所有数值型结论必须有数据依据
- 变化信号和风险信号宁可少报也不能编造
- 如果是批量分析，输出一个数组，每位客户一个元素

客户数据：
```json
{data_json}
```

请严格按照 system prompt 中定义的 JSON 格式返回结果。
如果是单客户分析，返回单个对象；如果是批量分析，返回包含 "results" 数组的对象：{{"results": [...]}}"""

        return prompt

    # ================================================================
    # 保存洞察快照
    # ================================================================

    def _save_insight(self, result: dict, manager_id: str) -> bool:
        """将单客户洞察快照保存到数据库"""
        cust_id = result.get("customer_id") or result.get("cust_id")
        overview = result.get("overview")

        if not cust_id or not overview:
            # 尝试从 overview.basic 推断
            if overview and isinstance(overview, dict):
                basic = overview.get("basic", {})
                cust_name = basic.get("name", "")
                if cust_name:
                    # 通过 name 查找 cust_id
                    cust_id = self._find_cust_id_by_name(cust_name)
            if not cust_id:
                return False

        from pathlib import Path
        import sqlite3
        db_path = str(Path(__file__).parent.parent.parent / "yihuiban_sim.db")

        now = datetime.now().isoformat()
        expires = (date.today() + timedelta(days=7)).isoformat()

        # 获取实际的 manager_id（如果未传入）
        if not manager_id:
            manager_id = self._get_manager_id(cust_id, db_path)

        overview_json = json.dumps(overview, ensure_ascii=False)
        change_signals = result.get("change_signals", [])
        risk_signals = result.get("risk_signals", [])
        change_json = json.dumps(change_signals, ensure_ascii=False)
        risk_json = json.dumps(risk_signals, ensure_ascii=False)
        risk_level = result.get("risk_level", "green")

        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                """INSERT OR REPLACE INTO customer_insights
                   (cust_id, manager_id, overview_json, change_signals_json,
                    risk_signals_json, risk_level, generated_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (cust_id, manager_id, overview_json, change_json,
                 risk_json, risk_level, now, expires),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            log.error(f"Failed to save insight for cust_id={cust_id}: {e}")
            return False

    def _find_cust_id_by_name(self, name: str) -> int:
        """通过客户姓名查找 cust_id"""
        from pathlib import Path
        import sqlite3
        db_path = str(Path(__file__).parent.parent.parent / "yihuiban_sim.db")
        try:
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT id FROM customers WHERE name = ?", (name,)
            ).fetchone()
            conn.close()
            return row[0] if row else 0
        except Exception:
            return 0

    def _get_manager_id(self, cust_id: int, db_path: str) -> str:
        """获取客户的主管经理ID"""
        import sqlite3
        try:
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT manager_id FROM cust_manager_rel WHERE cust_id = ? AND is_primary = 1",
                (cust_id,),
            ).fetchone()
            conn.close()
            return row[0] if row else "M001"
        except Exception:
            return "M001"

    # ================================================================
    # 提供洞察数据给作战包
    # ================================================================

    def get_customer_overview(self, cust_id: int) -> dict:
        """
        获取客户速览，供作战包 Agent 使用。
        优先取最新洞察快照；若无则返回空。
        """
        insight = query_customer_insight(cust_id)
        if insight and insight.get("overview"):
            return {
                "source": "customer_insight_agent",
                "overview": insight["overview"],
                "change_signals": insight.get("change_signals", []),
                "risk_signals": insight.get("risk_signals", []),
                "risk_level": insight.get("risk_level", "green"),
                "generated_at": insight.get("generated_at", ""),
            }
        return {}


# ============================================================
# 便捷函数
# ============================================================

def create_customer_insight_agent() -> CustomerInsightAgent:
    """创建客户洞察 Agent 实例（注册到全局 harness）"""
    from ..harness import harness as h
    agent_instance = CustomerInsightAgent()
    h.registry.register(CustomerInsightAgent.meta, agent_instance)
    return agent_instance
