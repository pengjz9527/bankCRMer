"""
VectorStore — ChromaDB 嵌入式向量库封装

无需独立服务，数据持久化到本地磁盘。
"""

import os
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

_env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_env_path)

log = logging.getLogger("agentos.rag.vector_store")

# ChromaDB 持久化路径
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

# 集合名称
COLLECTION_KNOWLEDGE = "rag_knowledge"    # 知识文档
COLLECTION_RULES = "rag_business_rules"   # 业务规则约束


class VectorStore:
    """
    ChromaDB 向量库封装

    两个 Collection：
      - rag_knowledge: 存储知识文档 chunks
      - rag_business_rules: 存储业务规则约束（含规则编号、场景、标签等元数据）

    用法:
        store = VectorStore()
        store.add_knowledge(docs, embeddings, metadatas)
        results = store.search_knowledge(query_embedding, top_k=5)
    """

    def __init__(self, persist_dir: str = None):
        import chromadb
        from chromadb.config import Settings

        self.persist_dir = persist_dir or CHROMA_PERSIST_DIR
        # 确保目录存在
        os.makedirs(self.persist_dir, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._knowledge_col = None
        self._rules_col = None

    @property
    def knowledge_col(self):
        """知识文档集合（懒初始化）"""
        if self._knowledge_col is None:
            self._knowledge_col = self._client.get_or_create_collection(
                name=COLLECTION_KNOWLEDGE,
                metadata={"description": "银行零售业务知识文档，含产品介绍/办理流程/政策法规/渠道服务等"},
            )
        return self._knowledge_col

    @property
    def rules_col(self):
        """业务规则约束集合（懒初始化）"""
        if self._rules_col is None:
            self._rules_col = self._client.get_or_create_collection(
                name=COLLECTION_RULES,
                metadata={"description": "AI对话业务规则约束，含规则编号/场景/标准话术/标签"},
            )
        return self._rules_col

    # ---- 知识文档操作 ----

    def add_knowledge(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ):
        """
        批量添加知识文档 chunks

        Args:
            ids: 唯一标识列表
            documents: 文档文本列表
            embeddings: 对应向量列表
            metadatas: 元数据列表 [{source, category, title, chunk_index}, ...]
        """
        if not ids:
            return
        self.knowledge_col.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        log.info(f"Added {len(ids)} knowledge chunks to ChromaDB")

    def search_knowledge(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        category_filter: str = None,
    ) -> list[dict]:
        """
        语义检索知识文档

        Args:
            query_embedding: 查询向量
            top_k: 返回 Top-K 结果
            category_filter: 可选类别过滤（如 "理财产品", "贷款产品"）

        Returns:
            [{id, document, metadata, distance}, ...]
        """
        where = None
        if category_filter:
            where = {"category": category_filter}

        results = self.knowledge_col.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        formatted = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                formatted.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                })

        return formatted

    # ---- 业务规则操作 ----

    def add_rules(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ):
        """
        批量添加业务规则约束

        Args:
            ids: 规则编号列表 ["R00001", "R00002", ...]
            documents: 规则话术文本
            embeddings: 对应向量
            metadatas: 元数据 [{rule_id, scenario, tags, source_file}, ...]
        """
        if not ids:
            return
        self.rules_col.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        log.info(f"Added {len(ids)} business rules to ChromaDB")

    def search_rules(
        self,
        query_embedding: list[float],
        top_k: int = 10,
    ) -> list[dict]:
        """
        语义检索匹配的业务规则

        Returns:
            [{id, document, metadata, distance}, ...]
        """
        results = self.rules_col.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        formatted = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                formatted.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                })

        return formatted

    def get_rule_by_id(self, rule_id: str) -> Optional[dict]:
        """按规则编号精确查询"""
        results = self.rules_col.get(
            ids=[rule_id],
            include=["documents", "metadatas"],
        )
        if results["ids"]:
            return {
                "id": results["ids"][0],
                "document": results["documents"][0],
                "metadata": results["metadatas"][0] if results["metadatas"] else {},
            }
        return None

    def get_all_rule_ids(self) -> list[str]:
        """获取所有规则编号"""
        result = self.rules_col.get(include=[])
        return result.get("ids", [])

    # ---- 管理操作 ----

    def count_knowledge(self) -> int:
        """知识文档 chunk 总数"""
        return self.knowledge_col.count()

    def count_rules(self) -> int:
        """业务规则总数"""
        return self.rules_col.count()

    def reset(self):
        """清空所有集合（重建索引前调用）"""
        try:
            self._client.delete_collection(COLLECTION_KNOWLEDGE)
            log.info(f"Deleted collection: {COLLECTION_KNOWLEDGE}")
        except Exception:
            pass
        try:
            self._client.delete_collection(COLLECTION_RULES)
            log.info(f"Deleted collection: {COLLECTION_RULES}")
        except Exception:
            pass
        self._knowledge_col = None
        self._rules_col = None

    def stats(self) -> dict:
        """向量库统计信息"""
        return {
            "persist_dir": self.persist_dir,
            "collections": {
                COLLECTION_KNOWLEDGE: self.count_knowledge(),
                COLLECTION_RULES: self.count_rules(),
            },
        }


# 全局单例
_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取全局 VectorStore 单例"""
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
