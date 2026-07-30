"""
QAAgent — 智能问答助手智能体

基于 RAG（ChromaDB + DashScope text-embedding-v3）检索知识库，
为客户经理提供产品信息查询、业务知识解答和综合理财建议。

触发方式：
  - 按需：客户经理在 AI 对话面板提问
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Optional

from ..harness import Agent, AgentContext, agent, skill
from ..model_adapter import get_adapter
from ..rag.retriever import Retriever, get_retriever, RetrievalResult
from ..rag.indexer import build_index

log = logging.getLogger("agentos.qa_assistant")


# ============================================================
# Agent 定义
# ============================================================

@agent(
    name="智能问答助手",
    role="qa_assistant",
    description="产品信息查询解读、业务知识问答、综合理财建议，基于 RAG 知识库检索增强",
    skills=[
        "search_products",
        "explain_product",
        "answer_business_qa",
        "advise_allocation",
        "ask",  # 统一问答入口
    ],
    triggers=["on_demand"],
    rate_limit=60,
    timeout=120,
)
class QAAssistantAgent(Agent):
    """智能问答领域专家"""

    system_prompt = "prompts/qa_assistant.md"

    def __init__(self, adapter=None):
        super().__init__(adapter)
        self.load_prompt(self.system_prompt)
        self._retriever: Optional[Retriever] = None
        self._index_built = False

    @property
    def retriever(self) -> Retriever:
        """懒初始化检索器"""
        if self._retriever is None:
            self._retriever = get_retriever()
        return self._retriever

    def ensure_index(self):
        """确保 RAG 索引已构建"""
        if self._index_built:
            return

        try:
            result = build_index(force_rebuild=False)
            if result.get("skipped"):
                log.info(f"RAG index already exists: {result}")
            else:
                log.info(f"RAG index built: {result}")
            self._index_built = True
        except Exception as e:
            log.error(f"Failed to build RAG index: {e}")
            # 不阻断 Agent 启动，允许降级运行

    # ================================================================
    # 统一问答入口
    # ================================================================

    @skill(description="统一问答入口，接收自然语言问题，返回 RAG 增强的专业解答")
    async def ask(self, ctx: AgentContext, params: dict) -> dict:
        """
        处理用户提问

        Args:
            params: {
                "question": str,       # 用户问题
                "manager_id": str,     # 客户经理 ID（可选）
                "history": list[dict], # 历史对话 [{role, content}]（可选）
            }

        Returns:
            {"answer": str, "intent": str, "sources": list, "rules": list}
        """
        question = params.get("question", "").strip()
        if not question:
            return {"answer": "请提供您的问题，我将为您解答。", "intent": "empty"}

        manager_id = params.get("manager_id", "")
        history = params.get("history", [])

        # 确保索引可用
        self.ensure_index()

        log.info(f"QAAgent ask: question='{question[:80]}...' manager={manager_id}")

        # Step 1: 意图分类
        intent = await self._classify_intent(question)

        # Step 2: RAG 检索
        retrieval = self.retriever.retrieve_for_qa(
            query=question,
            top_k_knowledge=6,
            top_k_rules=12,
        )

        # Step 3: 构建 prompt 并调用 LLM
        answer = await self._generate_answer(
            question=question,
            intent=intent,
            retrieval=retrieval,
            history=history,
            manager_id=manager_id,
        )

        # Step 4: 提取摘要
        summary, full_answer = self._extract_summary(answer)

        # Step 5: 组装结果
        sources = []
        for chunk in retrieval.knowledge_chunks[:3]:
            meta = chunk.get("metadata", {})
            sources.append({
                "title": meta.get("title", ""),
                "source": meta.get("source", ""),
                "section": meta.get("section", ""),
            })

        matched_rules = []
        for rule in retrieval.matched_rules[:5]:
            meta = rule.get("metadata", {})
            matched_rules.append({
                "rule_id": meta.get("rule_id", ""),
                "scenario": meta.get("scenario_type", ""),
            })

        return {
            "answer": full_answer,
            "summary": summary,
            "intent": intent,
            "sources": sources,
            "matched_rules": matched_rules,
            "knowledge_count": len(retrieval.knowledge_chunks),
            "rules_count": len(retrieval.matched_rules),
        }

    # ================================================================
    # 意图分类
    # ================================================================

    async def _classify_intent(self, question: str) -> str:
        """
        分类用户意图

        Returns:
            "product_search"   - 产品查询（"有什么R2理财"）
            "product_explain"  - 产品解读（"结构性存款是什么"）
            "business_qa"      - 业务问答（"怎么申请贷款"）
            "allocation_advice" - 配置建议（"50万怎么配置"）
            "general"          - 通用问答
        """
        # 轻量规则优先
        q = question.lower()

        # 配置建议特征
        allocation_keywords = ["怎么配置", "如何配置", "怎么分配", "买什么", "推荐", "建议配置"]
        if any(kw in q for kw in allocation_keywords):
            # 确认包含金额/期限描述
            if any(c.isdigit() for c in question):
                return "allocation_advice"

        # 产品查询特征
        product_search_keywords = ["有什么", "有哪些", "推荐几款", "找一下", "搜索", "查一下"]
        if any(kw in q for kw in product_search_keywords):
            return "product_search"

        # 产品解读特征（"是什么"、"什么是"、"区别"）
        explain_keywords = ["是什么", "什么是", "区别", "对比", "解释", "介绍一下"]
        if any(kw in q for kw in explain_keywords):
            return "product_explain"

        # 业务问答特征（"怎么"、"如何"、"流程"、"条件"、"需要"）
        business_keywords = ["怎么", "如何", "流程", "条件", "需要什么", "要求", "规定"]
        if any(kw in q for kw in business_keywords):
            return "business_qa"

        return "general"

    # ================================================================
    # 生成回答
    # ================================================================

    async def _generate_answer(
        self,
        question: str,
        intent: str,
        retrieval: RetrievalResult,
        history: list[dict],
        manager_id: str,
    ) -> str:
        """调用 LLM 生成 RAG 增强回答"""

        # 构建用户 prompt
        user_prompt = self._build_user_prompt(
            question=question,
            intent=intent,
            retrieval=retrieval,
        )

        # 构建消息列表
        messages = [
            {"role": "system", "content": self.system_prompt_text},
        ]

        # 添加历史对话（最近 4 轮）
        for h in history[-8:]:
            messages.append({
                "role": h.get("role", "user"),
                "content": h.get("content", ""),
            })

        messages.append({"role": "user", "content": user_prompt})

        # 调用 LLM
        try:
            resp = self.adapter.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
            answer = resp.get("content", "")
            log.info(f"QAAgent answer: {len(answer)} chars, tokens={resp.get('usage', {}).get('total_tokens', 0)}")
            return answer
        except Exception as e:
            log.error(f"QAAgent LLM call failed: {e}")
            return self._fallback_answer(question, retrieval)

    def _build_user_prompt(
        self,
        question: str,
        intent: str,
        retrieval: RetrievalResult,
    ) -> str:
        """构建发送给 LLM 的用户 prompt"""

        parts = []

        # 意图提示
        intent_hints = {
            "product_search": "用户正在查询产品信息，请结合知识库中的产品知识给出推荐。",
            "product_explain": "用户希望了解产品概念或对比产品，请结合知识库给出专业解读。",
            "business_qa": "用户询问业务办理相关的问题，请结合知识库中的流程和政策法规解答。",
            "allocation_advice": "用户希望获得资产配置建议，请结合知识库中的产品信息给出专业配置方案。",
            "general": "用户提出了通用问题，请结合知识库给出专业解答。",
        }
        hint = intent_hints.get(intent, intent_hints["general"])
        parts.append(f"# 用户意图\n{hint}\n")

        # 知识上下文
        knowledge_context = self.retriever.format_context(retrieval)
        if knowledge_context:
            parts.append(f"# 知识上下文\n{knowledge_context}\n")
        else:
            parts.append("# 知识上下文\n（未检索到相关知识文档，请基于你的专业知识诚实回答）\n")

        # 用户问题
        parts.append(f"# 用户当前提问\n{question}\n")

        # 输出指令（必须与系统 prompt 中的输出格式要求一致）
        parts.append("# 输出要求")
        parts.append("严格按照以下结构输出，使用 Markdown 格式：")
        parts.append("")
        parts.append("## 摘要")
        parts.append("[必填，2-3句话总结核心结论，80字以内，让用户快速了解最重要信息。有合规拦截第一时间说明。]")
        parts.append("")
        parts.append("（如有规则命中，追加：）")
        parts.append("## 合规判断")
        parts.append("[判断违规情况，标注规则编号]")
        parts.append("")
        parts.append("## 详细解答")
        parts.append("[分###子标题展开，使用表格、列表、加粗等格式，段落间留空行]")

        return "\n".join(parts)

    def _fallback_answer(self, question: str, retrieval: RetrievalResult) -> str:
        """LLM 调用失败时的降级回答"""
        if retrieval.has_knowledge():
            chunks = retrieval.knowledge_chunks[:2]
            parts = ["## 业务解答\n"]
            parts.append("（以下是基于知识库的直接检索结果，未经 AI 润色）\n")
            for chunk in chunks:
                meta = chunk.get("metadata", {})
                title = meta.get("title", "")
                parts.append(f"### {title}")
                parts.append(chunk.get("document", "")[:800])
                parts.append("")
            parts.append("\n---\n*注：AI 模型暂时不可用，以上为知识库直接检索结果。*")
            return "\n".join(parts)
        else:
            return "抱歉，我暂时无法回答您的问题。请稍后重试或联系您的客户经理获取帮助。"

    @staticmethod
    def _extract_summary(answer: str) -> tuple:
        """
        从 LLM 回答中提取摘要部分

        Args:
            answer: LLM 返回的完整 Markdown 回答

        Returns:
            (summary: str, full_answer: str) 摘要文本和完整回答
        """
        import re
        # 尝试匹配 ## 摘要 段落（## 摘要 到下一个 ## 或 ### 之间）
        # 支持多种变体：## 摘要、##摘要、## 摘要（必填）等
        pattern = r"##\s*摘要[^\n]*\n(.*?)(?=\n##\s|\n###\s|\Z)"
        match = re.search(pattern, answer, re.DOTALL)

        if match:
            summary = match.group(1).strip()
            # 清理摘要中的 markdown 标记
            summary = re.sub(r'[*_]{1,2}', '', summary)
            # 如果摘要为空或太短，取前 120 字符作为降级摘要
            if len(summary) < 10:
                clean = re.sub(r"^#{1,3}\s+", "", answer).strip()
                # 取前两行作为摘要
                lines = [l.strip() for l in clean.split('\n') if l.strip()]
                summary = ' '.join(lines[:2])
                if len(summary) > 120:
                    summary = summary[:120] + '...'
        else:
            # 没有摘要段落，取正文前 120 字符
            clean = re.sub(r"^#{1,3}\s+", "", answer).strip()
            summary = clean[:120] + ("..." if len(clean) > 120 else "")

        return summary, answer

    # ================================================================
    # 专项技能（供外部调用）
    # ================================================================

    @skill(description="搜索产品信息")
    async def search_products(self, ctx: AgentContext, params: dict) -> dict:
        """
        产品搜索

        Args:
            params: {
                "query": str,         # 自然语言查询
                "category": str,      # 产品类别（可选）
                "risk_level": str,    # 风险等级（可选）
                "limit": int,         # 返回数量
            }
        """
        params["question"] = params.get("query", "")
        # 调用统一问答入口，intent 由内部分类
        return await self.ask(ctx, params)

    @skill(description="解读产品详情")
    async def explain_product(self, ctx: AgentContext, params: dict) -> dict:
        """
        产品解读

        Args:
            params: {"product_name": str, "question": str}
        """
        product_name = params.get("product_name", "")
        question = params.get("question", f"请详细介绍{product_name}这款产品")
        params["question"] = question
        return await self.ask(ctx, params)

    @skill(description="回答业务知识问题")
    async def answer_business_qa(self, ctx: AgentContext, params: dict) -> dict:
        """
        业务问答

        Args:
            params: {"question": str}
        """
        return await self.ask(ctx, params)

    @skill(description="提供资产配置建议")
    async def advise_allocation(self, ctx: AgentContext, params: dict) -> dict:
        """
        配置建议

        Args:
            params: {
                "question": str,         # 用户问题
                "amount": float,         # 可用金额
                "term_months": int,      # 投资期限（月）
                "risk_tolerance": str,   # 风险承受 (R1-R5)
            }
        """
        question = params.get("question", "")
        if not question:
            amount = params.get("amount", "")
            term = params.get("term_months", "")
            risk = params.get("risk_tolerance", "")
            question = f"我有{amount}万元闲置资金，投资期限约{term}个月，风险偏好{risk}，应该如何配置？"

        params["question"] = question
        return await self.ask(ctx, params)


# ============================================================
# 便捷函数
# ============================================================

def create_qa_agent() -> QAAssistantAgent:
    """创建智能问答 Agent 实例（注册到全局 harness）"""
    from ..harness import harness as h
    agent_instance = QAAssistantAgent()
    h.registry.register(QAAssistantAgent.meta, agent_instance)
    return agent_instance
