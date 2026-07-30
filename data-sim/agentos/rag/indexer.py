"""
Indexer — rag_docs 文档分块与向量化入库

处理两类文档：
  1. 知识文档：按 ## 章节标题切分，带重叠
  2. 业务规则：按规则编号（R00001...）切分，每个规则独立存储
"""

import os
import re
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional

from .embedder import Embedder, get_embedder
from .vector_store import VectorStore, get_vector_store

log = logging.getLogger("agentos.rag.indexer")

# rag_docs 根目录
RAG_DOCS_DIR = Path(__file__).parent.parent.parent / "rag_docs"

# 分块参数
CHUNK_MAX_CHARS = 1500   # 单块最大字符数
CHUNK_OVERLAP_CHARS = 200  # 块间重叠字符数

# 跳过文件/目录
SKIP_PATTERNS = [".DS_Store", "__pycache__", ".git"]

# 类别映射（从目录路径推导）
CATEGORY_MAP = {
    "01-零售业务分类": "零售业务基础",
    "02-零售业务产品介绍": "产品介绍",
    "03-零售业务办理流程": "业务流程",
    "04-管理办法与政策法规": "政策法规",
    "05-渠道服务功能": "渠道服务",
    "06-业务对象专题": "业务对象",
    "业务规则约束": "业务规则",
}


class Indexer:
    """
    文档索引构建器

    用法:
        indexer = Indexer()
        indexer.build(force_rebuild=False)  # 构建/增量更新索引
    """

    def __init__(
        self,
        embedder: Embedder = None,
        store: VectorStore = None,
        docs_dir: Path = None,
    ):
        self.embedder = embedder or get_embedder()
        self.store = store or get_vector_store()
        self.docs_dir = docs_dir or RAG_DOCS_DIR

    # ================================================================
    # 主流程
    # ================================================================

    def build(self, force_rebuild: bool = False):
        """
        构建完整索引

        Args:
            force_rebuild: 是否强制重建（清空已有数据）
        """
        if force_rebuild:
            log.info("Force rebuild: resetting vector store...")
            self.store.reset()

        existing_knowledge = self.store.count_knowledge()
        existing_rules = self.store.count_rules()

        if existing_knowledge > 0 and existing_rules > 0 and not force_rebuild:
            log.info(f"Index already built: {existing_knowledge} knowledge chunks, {existing_rules} rules. Use force_rebuild=True to rebuild.")
            return {
                "knowledge_chunks": existing_knowledge,
                "rules_count": existing_rules,
                "skipped": True,
            }

        # 1. 收集所有文档
        knowledge_files, rule_files = self._collect_files()

        log.info(f"Found {len(knowledge_files)} knowledge files, {len(rule_files)} rule files")

        # 2. 处理知识文档
        knowledge_count = 0
        if knowledge_files:
            knowledge_count = self._index_knowledge_files(knowledge_files)

        # 3. 处理业务规则
        rules_count = 0
        if rule_files:
            rules_count = self._index_rule_files(rule_files)

        log.info(f"Index built: {knowledge_count} knowledge chunks, {rules_count} rules")
        return {
            "knowledge_chunks": knowledge_count,
            "rules_count": rules_count,
            "knowledge_files": len(knowledge_files),
            "rule_files": len(rule_files),
        }

    # ================================================================
    # 文件收集
    # ================================================================

    def _collect_files(self) -> tuple[list[Path], list[Path]]:
        """收集知识文档和规则文件"""

        # 收集所有 .md 文件
        all_md_files = []
        for root, dirs, files in os.walk(self.docs_dir):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_PATTERNS]
            for f in files:
                if f.endswith(".md") and f not in SKIP_PATTERNS:
                    all_md_files.append(Path(root) / f)

        # 分类：业务规则 vs 知识文档
        rule_files = []
        knowledge_files = []

        for fp in all_md_files:
            rel = fp.relative_to(self.docs_dir)
            parts = rel.parts

            # 判断是否为业务规则文件
            is_rule = "业务规则约束" in parts or fp.name == "AI对话约束规则.md"

            if is_rule:
                rule_files.append(fp)
            else:
                knowledge_files.append(fp)

        return knowledge_files, rule_files

    # ================================================================
    # 知识文档处理
    # ================================================================

    def _index_knowledge_files(self, file_paths: list[Path]) -> int:
        """索引知识文档：分块 → 向量化 → 存储"""
        all_chunks = []  # [(chunk_id, text, metadata), ...]

        for fp in file_paths:
            chunks = self._chunk_knowledge_doc(fp)
            all_chunks.extend(chunks)

        if not all_chunks:
            log.warning("No knowledge chunks generated")
            return 0

        log.info(f"Generated {len(all_chunks)} knowledge chunks, embedding...")

        # 分批向量化
        chunk_texts = [c[1] for c in all_chunks]
        embeddings = self.embedder.embed(chunk_texts)

        # 批量存入 ChromaDB
        ids = [c[0] for c in all_chunks]
        docs = [c[1] for c in all_chunks]
        metadatas = [c[2] for c in all_chunks]

        self.store.add_knowledge(ids, docs, embeddings, metadatas)

        return len(all_chunks)

    def _chunk_knowledge_doc(self, file_path: Path) -> list[tuple]:
        """
        将知识文档按 ## 标题拆分为 chunks。

        Returns:
            [(chunk_id, text, metadata), ...]
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            log.warning(f"Failed to read {file_path}: {e}")
            return []

        if not content.strip():
            return []

        # 提取文档元数据
        rel_path = file_path.relative_to(self.docs_dir)
        parts = rel_path.parts

        # 推断类别
        category = "其他"
        sub_category = ""
        for part in parts:
            if part in CATEGORY_MAP:
                category = CATEGORY_MAP[part]
            elif part.endswith("产品") or part.endswith("业务") or part.endswith("体系") or part.endswith("功能"):
                sub_category = part

        # 提取文档标题（第一个 # 行）
        title = rel_path.stem  # fallback
        title_match = re.match(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()

        # 按 ## 标题分块（保留一级标题作为上下文前缀）
        sections = re.split(r"\n(?=## )", content)

        chunks = []
        for i, section in enumerate(sections):
            # 清理文本
            text = section.strip()
            if not text:
                continue

            # 提取小节标题
            section_title = ""
            h2_match = re.match(r"^##\s+(.+)$", text, re.MULTILINE)
            if h2_match:
                section_title = h2_match.group(1).strip()

            # 如果单块过长，进一步拆分
            if len(text) > CHUNK_MAX_CHARS:
                sub_chunks = self._split_long_text(text, title, section_title)
                for j, sub in enumerate(sub_chunks):
                    chunk_id = self._make_chunk_id(file_path, i, j)
                    metadata = {
                        "source": str(rel_path),
                        "title": title,
                        "section": section_title,
                        "category": category,
                        "sub_category": sub_category,
                        "chunk_index": f"{i}-{j}",
                    }
                    chunks.append((chunk_id, sub, metadata))
            else:
                chunk_id = self._make_chunk_id(file_path, i, 0)
                metadata = {
                    "source": str(rel_path),
                    "title": title,
                    "section": section_title,
                    "category": category,
                    "sub_category": sub_category,
                    "chunk_index": str(i),
                }
                chunks.append((chunk_id, text, metadata))

        return chunks

    def _split_long_text(self, text: str, doc_title: str, section_title: str) -> list[str]:
        """将长文本分段，带重叠"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + CHUNK_MAX_CHARS
            chunk = text[start:end]

            # 尝试在段落边界断开
            if end < len(text):
                last_para = chunk.rfind("\n\n")
                if last_para > CHUNK_MAX_CHARS // 2:
                    end = start + last_para
                    chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - CHUNK_OVERLAP_CHARS if end < len(text) else len(text)

        return chunks

    def _make_chunk_id(self, file_path: Path, section_idx: int, sub_idx: int) -> str:
        """生成唯一 chunk ID（含相对路径以避免同名文件冲突）"""
        rel = file_path.relative_to(self.docs_dir)
        raw = f"{rel}:{section_idx}:{sub_idx}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    # ================================================================
    # 业务规则处理
    # ================================================================

    def _index_rule_files(self, file_paths: list[Path]) -> int:
        """索引业务规则文件：按规则编号拆分 → 向量化 → 存储"""
        all_rules = []  # [(rule_id, text, metadata), ...]

        for fp in file_paths:
            if fp.name == "AI对话约束规则.md":
                continue  # 这是模板文件，不是具体规则

            rules = self._parse_rule_file(fp)
            all_rules.extend(rules)

        if not all_rules:
            log.warning("No business rules parsed")
            return 0

        log.info(f"Parsed {len(all_rules)} business rules, embedding...")

        # 分批向量化
        rule_texts = [r[1] for r in all_rules]
        embeddings = self.embedder.embed(rule_texts)

        # 批量存入 ChromaDB
        ids = [r[0] for r in all_rules]
        docs = [r[1] for r in all_rules]
        metadatas = [r[2] for r in all_rules]

        self.store.add_rules(ids, docs, embeddings, metadatas)

        return len(all_rules)

    def _parse_rule_file(self, file_path: Path) -> list[tuple]:
        """
        解析业务规则文件，每个规则独立提取。

        规则格式：
            **规则编号：** R00001
            **适用场景：** [信息咨询] — ...
            **规则话术：** ...
            **规则标签：** ...
            ---

        Returns:
            [(rule_id, rule_text, metadata), ...]
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            log.warning(f"Failed to read rule file {file_path}: {e}")
            return []

        rel_path = file_path.relative_to(self.docs_dir)

        # 按 --- 分隔规则条目
        # 先按 ## 大节分组，再按 --- 分具体规则
        rules = []

        # 匹配每个规则块：从 **规则编号** 到下一个 --- 或 ##
        rule_pattern = re.compile(
            r"\*\*规则编号[：:]\s*\*\*\s*(R\d+)\s*\n"
            r"(.*?)"
            r"(?=\n---\s*\n|\n\*\*规则编号|\n## |\Z)",
            re.DOTALL,
        )

        for match in rule_pattern.finditer(content):
            rule_id = match.group(1)
            rule_body = match.group(0).strip()

            # 提取元数据
            scenario = ""
            scenario_match = re.search(r"\*\*适用场景[：:]\s*\*\*\s*(.+?)(?:\n|$)", rule_body)
            if scenario_match:
                scenario = scenario_match.group(1).strip()

            tags = ""
            tags_match = re.search(r"\*\*规则标签[：:]\s*\*\*\s*(.+?)(?:\n|$)", rule_body)
            if tags_match:
                tags = tags_match.group(1).strip()

            # 提取场景类型 [信息咨询] / [业务咨询] / [风险警示] 等
            scenario_type = ""
            type_match = re.search(r"\[([^\]]+)\]", scenario)
            if type_match:
                scenario_type = type_match.group(1)

            # 使用 "源文件名:R编号" 确保跨文件唯一
            unique_id = f"{rel_path.stem}:{rule_id}"

            metadata = {
                "rule_id": unique_id,
                "scenario": scenario,
                "scenario_type": scenario_type,
                "tags": tags,
                "source": str(rel_path),
            }

            rules.append((unique_id, rule_body, metadata))

        return rules


# ================================================================
# 便捷函数
# ================================================================

def build_index(force_rebuild: bool = False) -> dict:
    """
    一键构建索引

    Args:
        force_rebuild: 是否强制重建

    Returns:
        {"knowledge_chunks": int, "rules_count": int}
    """
    indexer = Indexer()
    return indexer.build(force_rebuild=force_rebuild)
