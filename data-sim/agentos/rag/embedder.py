"""
Embedder — 百炼 DashScope text-embedding-v3 向量化客户端

使用 OpenAI 兼容协议调用，输出 1024 维向量。
"""

import os
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# 加载 .env
_env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_env_path)

log = logging.getLogger("agentos.rag.embedder")

# DashScope text-embedding-v3 配置
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
DASHSCOPE_MODEL = os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v3")
DASHSCOPE_DIM = int(os.getenv("DASHSCOPE_EMBEDDING_DIM", "1024"))


class Embedder:
    """
    DashScope text-embedding-v3 客户端（OpenAI 兼容协议）
    
    用法:
        embedder = Embedder()
        vectors = embedder.embed(["文本1", "文本2"])  # list[list[float]]
        vector = embedder.embed_single("单条文本")     # list[float]
    """

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        dim: int = None,
    ):
        self.api_key = api_key or DASHSCOPE_API_KEY
        self.base_url = base_url or DASHSCOPE_BASE_URL
        self.model = model or DASHSCOPE_MODEL
        self.dim = dim or DASHSCOPE_DIM
        self._client = None

        if not self.api_key:
            log.warning("DASHSCOPE_API_KEY 未设置，Embedder 将无法工作")

    @property
    def client(self):
        """懒初始化 OpenAI 兼容客户端"""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=60,
            )
        return self._client

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        批量文本向量化

        Args:
            texts: 文本列表，单次最多 25 条（DashScope 限制）

        Returns:
            向量列表，每个向量 1024 维
        """
        if not texts:
            return []

        # DashScope text-embedding-v3 单次最多 10 条
        all_vectors = []
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                resp = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    dimensions=self.dim,
                )
                vectors = [d.embedding for d in resp.data]
                all_vectors.extend(vectors)
                log.debug(f"Embedded batch {i // batch_size + 1}: {len(batch)} texts")
            except Exception as e:
                log.error(f"Embedding failed for batch starting at {i}: {e}")
                raise

        return all_vectors

    def embed_single(self, text: str) -> list[float]:
        """单条文本向量化"""
        vectors = self.embed([text])
        return vectors[0] if vectors else []

    def embed_query(self, query: str) -> list[float]:
        """
        查询向量化（使用 instruction 前缀提升检索效果）

        text-embedding-v3 支持 instruction 参数优化查询向量。
        """
        # DashScope text-embedding-v3 兼容接口可能不直接支持 instruction，
        # 但可以通过在文本前加指令前缀来改善检索效果
        enhanced_query = f"为下述问题检索相关知识：{query}"
        return self.embed_single(enhanced_query)


# 全局单例
_embedder: Optional[Embedder] = None


def get_embedder() -> Embedder:
    """获取全局 Embedder 单例"""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
