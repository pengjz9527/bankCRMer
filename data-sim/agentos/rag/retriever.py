"""
Retriever — 语义检索 + 业务规则匹配

查询流程：
  1. 用户问题 → Embedder → 查询向量
  2. 向量检索知识文档（Top-K 相关 chunks）
  3. 向量检索业务规则（Top-K 匹配规则）
  4. 组装检索结果返回
"""

import logging
from typing import Optional

from .embedder import Embedder, get_embedder
from .vector_store import VectorStore, get_vector_store

log = logging.getLogger("agentos.rag.retriever")


class RetrievalResult:
    """单次检索结果"""

    def __init__(self):
        self.query: str = ""
        self.knowledge_chunks: list[dict] = []   # 知识文档 chunks
        self.matched_rules: list[dict] = []       # 匹配的业务规则
        self.rule_violations: list[dict] = []     # 可能违规的规则（需要检查）

    def has_knowledge(self) -> bool:
        return len(self.knowledge_chunks) > 0

    def has_rules(self) -> bool:
        return len(self.matched_rules) > 0


class Retriever:
    """
    检索器 — 组合知识检索和规则匹配

    用法:
        retriever = Retriever()
        result = retriever.retrieve("什么是结构性存款？", top_k=5)
        # result.knowledge_chunks → 相关知识文档
        # result.matched_rules → 匹配的业务规则
    """

    def __init__(
        self,
        embedder: Embedder = None,
        store: VectorStore = None,
    ):
        self.embedder = embedder or get_embedder()
        self.store = store or get_vector_store()

    def retrieve(
        self,
        query: str,
        top_k_knowledge: int = 5,
        top_k_rules: int = 10,
        distance_threshold: float = 1.5,
    ) -> RetrievalResult:
        """
        执行检索

        Args:
            query: 用户问题
            top_k_knowledge: 知识文档返回数
            top_k_rules: 业务规则返回数
            distance_threshold: 距离阈值（余弦距离，越小越相关）

        Returns:
            RetrievalResult 包含知识文档和匹配规则
        """
        result = RetrievalResult()
        result.query = query

        # 1. 查询向量化
        query_embedding = self.embedder.embed_query(query)
        if not query_embedding:
            log.warning("Failed to embed query")
            return result

        # 2. 检索知识文档
        try:
            knowledge = self.store.search_knowledge(
                query_embedding=query_embedding,
                top_k=top_k_knowledge,
            )
            # 按距离阈值过滤
            result.knowledge_chunks = [
                k for k in knowledge
                if k.get("distance", 999) <= distance_threshold
            ]
            log.debug(f"Knowledge search: {len(knowledge)} raw, {len(result.knowledge_chunks)} filtered")
        except Exception as e:
            log.warning(f"Knowledge search failed: {e}")

        # 3. 检索业务规则
        try:
            rules = self.store.search_rules(
                query_embedding=query_embedding,
                top_k=top_k_rules,
            )
            # 规则匹配通常更严格
            result.matched_rules = [
                r for r in rules
                if r.get("distance", 999) <= 1.2  # 规则匹配阈值更严
            ]
            log.debug(f"Rule search: {len(rules)} raw, {len(result.matched_rules)} filtered")
        except Exception as e:
            log.warning(f"Rule search failed: {e}")

        # 4. 识别潜在违规（规则标签中有 "禁止"、"违规"、"不得" 等）
        result.rule_violations = self._check_violations(query, result.matched_rules)

        return result

    def _check_violations(self, query: str, matched_rules: list[dict]) -> list[dict]:
        """
        检查查询中是否涉及违规意图

        如果用户问题关键词匹配到"禁止"类规则 → 标记为潜在违规
        """
        violations = []
        for rule in matched_rules:
            metadata = rule.get("metadata", {})
            scenario_type = metadata.get("scenario_type", "")
            tags = metadata.get("tags", "")

            # 标记风险警示类规则
            if scenario_type in ("风险警示", "合规警示") or "禁止" in tags or "违规" in tags:
                violations.append(rule)

        return violations

    def retrieve_for_qa(
        self,
        query: str,
        top_k_knowledge: int = 6,
        top_k_rules: int = 12,
    ) -> RetrievalResult:
        """
        面向问答场景的检索（更宽松的阈值）
        """
        return self.retrieve(
            query=query,
            top_k_knowledge=top_k_knowledge,
            top_k_rules=top_k_rules,
            distance_threshold=1.8,
        )

    def retrieve_for_compliance_check(
        self,
        query: str,
        top_k_rules: int = 20,
    ) -> RetrievalResult:
        """
        面向合规检查的检索（重点匹配规则）
        """
        result = self.retrieve(
            query=query,
            top_k_knowledge=2,
            top_k_rules=top_k_rules,
            distance_threshold=1.5,
        )
        return result

    def format_context(self, result: RetrievalResult) -> str:
        """
        将检索结果格式化为 LLM 可用的上下文字符串

        Returns:
            拼接好的上下文字符串
        """
        parts = []

        # 知识文档上下文
        if result.knowledge_chunks:
            parts.append("## 相关知识文档\n")
            for i, chunk in enumerate(result.knowledge_chunks):
                meta = chunk.get("metadata", {})
                source = meta.get("source", "未知来源")
                title = meta.get("title", "")
                section = meta.get("section", "")

                header = f"**{title}**"
                if section:
                    header += f" > {section}"
                header += f" _(来源: {source})_"

                parts.append(f"### {i + 1}. {header}")
                parts.append(chunk.get("document", ""))
                parts.append("")

        # 业务规则上下文
        if result.matched_rules:
            parts.append("## 匹配的业务规则约束\n")
            for i, rule in enumerate(result.matched_rules):
                meta = rule.get("metadata", {})
                rule_id = meta.get("rule_id", rule.get("id", ""))
                scenario = meta.get("scenario_type", "")

                header = f"**{rule_id}**"
                if scenario:
                    header += f" [{scenario}]"

                parts.append(f"### 规则 {i + 1}. {header}")
                parts.append(rule.get("document", ""))
                parts.append("")

        # 违规警示
        if result.rule_violations:
            parts.append("## ⚠️ 可能违反的业务规则（需重点审查）\n")
            for rule in result.rule_violations:
                meta = rule.get("metadata", {})
                rule_id = meta.get("rule_id", "")
                parts.append(f"- **{rule_id}**: 需按标准话术拦截")
            parts.append("")

        return "\n".join(parts)


# 全局单例
_retriever: Optional[Retriever] = None


def get_retriever() -> Retriever:
    """获取全局 Retriever 单例"""
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def retrieve(query: str, top_k: int = 5) -> RetrievalResult:
    """便捷检索函数"""
    r = get_retriever()
    return r.retrieve(query, top_k_knowledge=top_k)
