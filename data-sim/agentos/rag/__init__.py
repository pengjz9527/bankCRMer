"""
RAG 知识库系统 — 基于 ChromaDB + DashScope text-embedding-v3

模块：
  - embedder: 向量嵌入客户端
  - vector_store: ChromaDB 向量库封装
  - indexer: 文档分块与索引构建
  - retriever: 语义检索 + 业务规则匹配
"""

from .embedder import Embedder, get_embedder
from .vector_store import VectorStore, get_vector_store
from .indexer import Indexer, build_index
from .retriever import Retriever, retrieve

__all__ = [
    "Embedder", "get_embedder",
    "VectorStore", "get_vector_store",
    "Indexer", "build_index",
    "Retriever", "retrieve",
]
