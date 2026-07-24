"""
OppMiningAgent — 商机挖掘智能体
基于客户行为/生命周期/关系图谱数据，批量或按需发现潜在商机信号

触发方式：
  - 定时批量：每日凌晨 2:00，全行全量扫描
  - 按需挖掘：客户经理在 APP 手动点击"AI 挖掘"
"""

import os
import json
import time
import logging
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import Optional

from ..harness import Agent, AgentContext, agent, skill
from ..skills import (
    query_customer_full,
    query_customers,
    query_customers_by_ids,
)
from ..model_adapter import get_adapter

log = logging.getLogger("agentos.opp_mining")

# ============================================================
# 商机信号数据类
# ============================================================

@dataclass
class OpportunitySignal:
    """商机信号"""
    customer_id: int
    customer_name: str
    opportunity_type: str          # e.g. "活期沉淀盘活"
    title: str                     # 一句话摘要（≤30字）
    confidence: float              # 置信度 0.0-1.0
    estimated_value: float         # 预估价值（万元）
    reasoning: str                 # 推理链路（必填）
    suggested_action: str          # 建议行动
    priority: str                  # 高/中/常规
    source: str = "AI-opp_mining"
    source_method: str = ""
    trigger_signals: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "opportunity_type": self.opportunity_type,
            "title": self.title,
            "confidence": round(self.confidence, 2),
            "estimated_value": round(self.estimated_value, 1),
            "reasoning": self.reasoning,
            "suggested_action": self.suggested_action,
            "priority": self.priority,
            "source": self.source,
            "source_method": self.source_method,
            "trigger_signals": self.trigger_signals,
        }


# ============================================================
# Agent 定义
# ============================================================

@agent(
    name="商机挖掘智能体",
    role="opportunity_miner",
    description="基于客户行为、生命周期事件、关系图谱等数据，批量或按需发现潜在商机",
    skills=[
        "scan_portfolio", "detect_signals", "evaluate_confidence",
        "create_opportunity", "query_customers", "query_behavior",
        "query_holdings", "query_transactions",
    ],
    model="deepseek-chat",
    triggers=["scheduled", "on_demand"],
    rate_limit=50,
    timeout=600,
)
class OpportunityMiningAgent(Agent):
    """商机挖掘领域专家"""

    # System prompt 外部化
    system_prompt = "prompts/opportunity_mining.md"

    def __init__(self, adapter=None):
        super().__init__(adapter)
        self.load_prompt(self.system_prompt)

    # ================================================================
    # 定时批量挖掘（核心能力）
    # ================================================================

    async def batch_mine_all(self, ctx: AgentContext):
        """
        每天凌晨 2:00，全量扫描所有管户，批量生成商机

        流程：
          查询全量客户 → 分批(50人/批) → LLM 分析 → 评估 → 入库 → 通知
        """
        log.info(f"batch_mine_all start: scope={ctx.scope}")

        # 查询全量活跃客户
        customers = query_customers(limit=10000)
        log.info(f"batch_mine_all: {len(customers)} customers to analyze")

        all_signals: list[OpportunitySignal] = []

        # 分批处理
        batches = self.chunk(customers, 15)
        for i, batch in enumerate(batches):
            log.info(f"Batch {i+1}/{len(batches)}: {len(batch)} customers")
            batch_signals = await self._analyze_batch(batch, ctx)
            all_signals.extend(batch_signals)

        # 评估置信度，过滤低质量信号
        qualified = [s for s in all_signals if s.confidence >= 0.6]
        log.info(f"batch_mine_all done: {len(all_signals)} raw → {len(qualified)} qualified")

        # 入库（由上层调用者处理）
        return qualified

    # ================================================================
    # 按需挖掘（前台"一键 AI 挖掘"按钮）
    # ================================================================

    async def mine_on_demand(
        self, ctx: AgentContext, manager_id: str, max_customers: int = 6,
        progress_callback=None
    ):
        """
        客户经理手动触发，scope = 该经理的管户列表

        Args:
            ctx: 执行上下文
            manager_id: 客户经理 ID
            max_customers: 最大分析客户数（on-demand 限流）
            progress_callback: 可选，async def callback(event_type, data) 用于 SSE 流式推送
        """
        log.info(f"mine_on_demand: manager_id={manager_id}")

        # 查询该经理的管户（按 AUM 排序取 top N，优先高价值客户）
        all_customers = query_customers(manager_id=manager_id, limit=10000)
        # 优先分析高 AUM 客户
        all_customers.sort(key=lambda c: c.get("total_aum", 0) or 0, reverse=True)
        customers = all_customers[:max_customers]
        log.info(f"mine_on_demand: {len(all_customers)} total → top {len(customers)} by AUM")

        # 去重：跳过最近 24 小时内已生成商机的客户
        recent_ids = self._query_recent_opp_cust_ids(hours=24)
        fresh_customers = [c for c in customers if c["id"] not in recent_ids]
        skipped = len(customers) - len(fresh_customers)
        log.info(f"mine_on_demand: {len(customers)} selected → {len(fresh_customers)} fresh (skipped {skipped})")

        # 发送 phase 事件
        if progress_callback:
            await progress_callback("phase", {
                "phase": "start",
                "total_customers": len(all_customers),
                "selected": len(customers),
                "fresh": len(fresh_customers),
                "skipped": skipped,
                "batch_count": (len(fresh_customers) + 3) // 4 if fresh_customers else 0,
            })

        # 无新数据
        if not fresh_customers:
            if progress_callback:
                await progress_callback("done", {
                    "status": "no_new_data",
                    "message": f"您的 {len(all_customers)} 位管户近 24 小时内已挖掘，数据无变化，暂无新商机",
                })
            return {
                "status": "no_new_data",
                "total_customers": len(all_customers),
                "signals": 0,
                "message": f"您的 {len(all_customers)} 位管户近 24 小时内已挖掘，数据无变化，暂无新商机",
            }

        # 分批分析（Flash 快速模型，每批 4 人）
        all_signals: list[OpportunitySignal] = []
        batches = self.chunk(fresh_customers, 4)
        for i, batch in enumerate(batches):
            batch_start = time.time()
            batch_signals = await self._analyze_batch(batch, ctx)
            all_signals.extend(batch_signals)

            # 每批完成后推送进度
            if progress_callback:
                names = [c.get("name", str(c.get("id", "?"))) for c in batch]
                await progress_callback("batch_progress", {
                    "batch": i + 1,
                    "total_batches": len(batches),
                    "customers": names,
                    "batch_signals": len(batch_signals),
                    "total_signals_so_far": len(all_signals),
                    "elapsed_s": round(time.time() - batch_start, 1),
                })

        # 评估 + 过滤
        qualified = [s for s in all_signals if s.confidence >= 0.6]
        high_conf = [s for s in qualified if s.confidence >= 0.7]

        # 完成事件
        if progress_callback:
            await progress_callback("done", {
                "status": "completed",
                "total_customers": len(fresh_customers),
                "skipped": skipped,
                "signals": len(qualified),
                "high_confidence": len(high_conf),
                "highlights": [s.to_dict() for s in high_conf[:5]],
            })

        return {
            "status": "completed",
            "total_customers": len(fresh_customers),
            "skipped": skipped,
            "signals": len(qualified),
            "high_confidence": len(high_conf),
            "highlights": [s.to_dict() for s in high_conf[:5]],
            "all_signals": [s.to_dict() for s in qualified],
        }

    # ================================================================
    # 核心分析逻辑
    # ================================================================

    async def _analyze_batch(
        self, customers: list[dict], ctx: AgentContext
    ) -> list[OpportunitySignal]:
        """
        分析一批客户（最多 50 人），调用 LLM 生成商机信号

        Args:
            customers: 客户基础信息列表 [{"id": 1, "name": "...", ...}]
            ctx: 执行上下文

        Returns:
            商机信号列表
        """
        # 为每位客户组装完整上下文
        enriched = []
        for c in customers:
            full = query_customer_full(c["id"])
            if full:
                enriched.append(full)

        if not enriched:
            return []

        # 构建 user prompt（数据上下文）
        user_prompt = self._build_user_prompt(enriched, ctx)

        # 调用 LLM
        start = time.time()
        try:
            result = self.adapter.analyze_json(
                system_prompt=self.system_prompt_text,
                user_prompt=user_prompt,
            )
            elapsed = time.time() - start
            log.info(f"LLM analyze: {len(enriched)} customers, {elapsed:.1f}s, tokens_approx={len(user_prompt)//3}")

            # 解析结果
            signals = self._parse_batch_result(result)
            return signals
        except Exception as e:
            log.error(f"LLM analyze failed: {e}")
            return []

    def _build_user_prompt(self, customers: list[dict], ctx: AgentContext) -> str:
        """构建发送给 LLM 的 user prompt（数据上下文）"""
        # 精简数据：只保留 prompt 中定义需要的字段
        slim = []
        for c in customers:
            cust = c.get("customer", {})
            item = {
                "customer": cust,
                "family": c.get("family", {}),
                "holdings": c.get("holdings", []),
                "transactions": c.get("transactions", [])[:10],      # 精简至 10 条
                "behavior_logs": c.get("behavior_logs", [])[:5],     # 精简至 5 条
                "communications": c.get("communications", [])[:3],   # 精简至 3 条
                "risk_assessment": c.get("risk_assessment", {}).get("current"),
                "risk_history": c.get("risk_assessment", {}).get("history", [])[:1],
                "relations": c.get("relations", [])[:3],
                "loans": c.get("loans", []),
            }
            slim.append(item)

        data_json = json.dumps(slim, ensure_ascii=False, indent=2)

        return f"""请分析以下 {len(slim)} 位客户的数据，按照 system prompt 中定义的 12 条挖掘方法，发现潜在商机信号。

注意：
- 只输出 confidence >= 0.60 的信号
- 每个信号必须包含 reasoning 字段
- 如果某客户没有符合条件的信号，不要强行生成

**当前日期**：{date.today().isoformat()}
**挖掘范围**：{ctx.scope}

客户数据：
```json
{data_json}
```

请严格按照 system prompt 中定义的 JSON 输出格式返回结果。"""

    def _parse_batch_result(self, result: dict) -> list[OpportunitySignal]:
        """解析 LLM 返回的批次结果"""
        raw_signals = result.get("signals", [])
        signals = []
        for s in raw_signals:
            try:
                signal = OpportunitySignal(
                    customer_id=s.get("customer_id", 0),
                    customer_name=s.get("customer_name", ""),
                    opportunity_type=s.get("opportunity_type", ""),
                    title=s.get("title", ""),
                    confidence=float(s.get("confidence", 0)),
                    estimated_value=float(s.get("estimated_value", 0)),
                    reasoning=s.get("reasoning", ""),
                    suggested_action=s.get("suggested_action", ""),
                    priority=s.get("priority", "常规"),
                    source=s.get("source", "AI-opp_mining"),
                    source_method=s.get("source_method", ""),
                    trigger_signals=s.get("trigger_signals", []),
                )
                if signal.confidence >= 0.6 and signal.customer_id > 0:
                    signals.append(signal)
            except (ValueError, TypeError) as e:
                log.warning(f"Skip malformed signal: {e}")
        return signals

    # ================================================================
    # 去重 & 评估
    # ================================================================

    def _query_recent_opp_cust_ids(self, hours: int = 24) -> set[int]:
        """查询最近 N 小时内已生成商机的客户 ID"""
        import sqlite3
        from pathlib import Path
        db_path = str(Path(__file__).parent.parent.parent / "yihuiban_sim.db")
        try:
            conn = sqlite3.connect(db_path)
            cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
            rows = conn.execute(
                "SELECT DISTINCT cust_id FROM opportunities WHERE generated_at >= ?",
                (cutoff,)
            ).fetchall()
            conn.close()
            ids = {r[0] for r in rows}
            log.info(f"_query_recent_opp_cust_ids: {len(ids)} customers with opps in last {hours}h")
            return ids
        except Exception as e:
            log.warning(f"_query_recent_opp_cust_ids failed: {e}")
            return set()

    async def evaluate_batch(
        self, ctx: AgentContext, signals: list[OpportunitySignal]
    ) -> list[OpportunitySignal]:
        """评估置信度，过滤低质量信号"""
        # 当前简单实现：直接按 confidence 阈值过滤
        # 后续可升级：调用 LLM 二次评估 / 交叉验证
        return [s for s in signals if s.confidence >= 0.6]


# ============================================================
# 便捷函数
# ============================================================

def create_opp_mining_agent() -> OpportunityMiningAgent:
    """创建商机挖掘 Agent 实例（注册到全局 harness）"""
    from ..harness import harness as h
    agent = OpportunityMiningAgent()
    h.registry.register(OpportunityMiningAgent.meta, agent)
    return agent
