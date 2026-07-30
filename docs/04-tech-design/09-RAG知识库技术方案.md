# RAG 知识库技术方案

> **来源**：QAAgent 智能问答助手的知识检索增强子系统。
> **关联**：QAAgent 设计方案见 `docs/03-architecture/07-智能问答助手.md`，智能体体系见 `docs/03-architecture/01-智能体体系总览.md`。
> **版本**：v1.0 | **日期**：2026-07-30 | **状态**：✅ 已实现

---

## 一、技术选型

### 1.1 整体架构

```
┌──────────────────────────────────────────────────────────┐
│                     QAAgent (应用层)                       │
│  ask() → 意图分类 → 检索增强 → LLM 生成 → 合规输出        │
├──────────────────────────────────────────────────────────┤
│                   RAG 子系统 (agentos/rag/)                │
│                                                           │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Indexer  │  │  Retriever   │  │  VectorStore      │   │
│  │ 文档分块  │  │  语义检索    │  │  ChromaDB 封装    │   │
│  │ 规则解析  │  │  规则匹配    │  │  双 Collection    │   │
│  │ 向量入库  │  │  违规识别    │  │  本地持久化       │   │
│  └────┬─────┘  └──────┬───────┘  └────────┬─────────┘   │
│       │               │                    │              │
│  ┌────┴───────────────┴────────────────────┴─────────┐   │
│  │                  Embedder                          │   │
│  │    DashScope text-embedding-v3 (1024维)            │   │
│  │    OpenAI 兼容协议 · batch_size=10                 │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

### 1.2 选型对比

| 组件 | 方案 | 选型理由 |
|------|------|---------|
| **向量数据库** | ChromaDB v1.5.9（嵌入式） | ① 无需独立服务（PersistentClient），零运维；② 与 SQLite 类似，数据文件即数据库；③ Python 原生支持，与 AgentOS 技术栈一致 |
| **Embedding 模型** | 百炼 DashScope text-embedding-v3 | ① 1024 维向量，中文语义表现优秀；② OpenAI 兼容协议（`/compatible-mode/v1`），无需额外 SDK；③ API Key 可跨项目共享 |
| **LLM 问答模型** | DeepSeek V4 Flash | ① 与平台其他 Agent 统一模型；② Flash 版速度快（+60-85%），成本低（1/12 of Pro） |
| **文档分块** | 按 Markdown `##` 标题语义切分 | ① 保留章节语义边界；② ≤1500 字符限制避免超长 embedding |
| **规则处理** | 独立 Collection + 正则解析 | ① 规则与知识分离便于合规审查；② 规则匹配阈值更严格（distance≤1.2） |
| **Python 环境** | Python 3.12.13（uv venv） | Python 3.14.3 无 chromadb 预编译 wheel，降级到 3.12 |

---

## 二、模块设计

### 2.1 Embedder（嵌入客户端）

**文件**：`agentos/rag/embedder.py`（125 行）

**职责**：封装 DashScope text-embedding-v3 API 调用。

```python
class Embedder:
    model = "text-embedding-v3"
    dim = 1024
    batch_size = 10          # DashScope API 硬限制

    def embed(texts: list[str]) -> list[list[float]]
        """批量向量化，自动按 10 条/批拆分"""

    def embed_single(text: str) -> list[float]
        """单条文本向量化"""

    def embed_query(query: str) -> list[float]
        """查询向量化，前缀增强：'为下述问题检索相关知识：{query}'"""
```

**API 端点**：
- Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Endpoint: `POST /embeddings`
- 协议: OpenAI-compatible（使用 `openai` SDK）

**配置（.env）**：
```bash
DASHSCOPE_API_KEY=sk-xxx
DASHSCOPE_EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v3
DASHSCOPE_EMBEDDING_DIM=1024
```

### 2.2 VectorStore（向量库封装）

**文件**：`agentos/rag/vector_store.py`（266 行）

**职责**：封装 ChromaDB PersistentClient，管理双 Collection。

```python
class VectorStore:
    COLLECTION_KNOWLEDGE = "rag_knowledge"       # 知识文档 chunks
    COLLECTION_RULES = "rag_business_rules"       # 业务规则约束

    def __init__(persist_dir="./chroma_db")
        """ChromaDB PersistentClient，数据文件即数据库"""

    # 知识文档操作
    def add_knowledge(ids, documents, embeddings, metadatas)
    def search_knowledge(query_embedding, top_k=5, category_filter=None) → list[dict]
        """语义检索，返回 {id, document, metadata, distance}"""

    # 业务规则操作
    def add_rules(ids, documents, embeddings, metadatas)
    def search_rules(query_embedding, top_k=10) → list[dict]
    def get_rule_by_id(rule_id) → dict

    # 管理操作
    def count_knowledge() → int
    def count_rules() → int
    def reset()                            # 清空所有 collection
    def stats() → dict
```

**Collection 设计**：

| 属性 | rag_knowledge | rag_business_rules |
|------|--------------|-------------------|
| 用途 | 知识文档检索 | 合规规则匹配 |
| 数据量 | 1450 chunks | 383 rules |
| 检索阈值 | distance ≤ 1.8 | distance ≤ 1.2 |
| 元数据 | source, title, section, category | rule_id, scenario, scenario_type, tags |

**存储**：
```
chroma_db/
├── chroma.sqlite3          # 元数据 + 向量索引 (21MB)
└── 06526140-.../           # Collection 分片目录
```

### 2.3 Indexer（索引构建器）

**文件**：`agentos/rag/indexer.py`（400 行）

**职责**：读取 rag_docs 目录，分块/解析 → 向量化 → 入库。

```python
class Indexer:
    docs_dir = "rag_docs/"
    CHUNK_MAX_CHARS = 1500      # 单块最大字符数
    CHUNK_OVERLAP_CHARS = 200   # 块间重叠字符数

    def build(force_rebuild=False) → dict
        """完整构建流程"""
```

**构建流程**：
```
build(force_rebuild=False)
  ├─→ 1. _collect_files()
  │     遍历 rag_docs/ 所有 .md 文件
  │     分类: 知识文件 (165个) / 规则文件 (7个)
  │     跳过: AI对话约束规则.md (模板，非规则)
  │     Skip: .DS_Store, __pycache__, .git
  │
  ├─→ 2. _index_knowledge_files(files) → 1450 chunks
  │     ├─ _chunk_knowledge_doc()     # 按 ## 标题分块
  │     ├─ _split_long_text()          # 长文本段落切分
  │     ├─ _make_chunk_id()            # MD5(相对路径:段落号) 生成唯一 ID
  │     ├─ embedder.embed(texts)        # 批量向量化 (10条/批)
  │     └─ store.add_knowledge()        # 写入 ChromaDB
  │
  └─→ 3. _index_rule_files(files) → 383 rules
        ├─ _parse_rule_file()           # 正则解析规则块
        │    pattern: r"\*\*规则编号[：:]\s*\*\*\s*(R\d+)\s*\n(.*?)..."
        │    提取: rule_id, scenario, scenario_type, tags
        ├─ embedder.embed(rule_texts)   # 批量向量化
        └─ store.add_rules()            # 写入 ChromaDB
```

**知识文档分块策略**：
- 按 `## 二级标题` 切分，保留一级标题作为上下文
- 单块 ≤ 1500 字符，超出则在段落边界（`\n\n`）切分
- 块间重叠 200 字符，避免语义截断
- 元数据自动从路径推导类别（如 `02-零售业务产品介绍` → 类别="产品介绍"）

**业务规则解析策略**：
- 正则匹配 `**规则编号：** R\d+` 到下一个 `---` 或 `##` 之间
- 提取场景类型标签：`[信息咨询]`/`[业务咨询]`/`[风险警示]`
- 规则 ID 格式：`源文件名:R编号`（如 `01-个人贷款管理办法-AI业务规则约束:R00001`）
- 跨文件同号规则通过前缀避免冲突

**类别映射**：
```python
CATEGORY_MAP = {
    "01-零售业务分类": "零售业务基础",
    "02-零售业务产品介绍": "产品介绍",
    "03-零售业务办理流程": "业务流程",
    "04-管理办法与政策法规": "政策法规",
    "05-渠道服务功能": "渠道服务",
    "06-业务对象专题": "业务对象",
    "业务规则约束": "业务规则",
}
```

### 2.4 Retriever（检索器）

**文件**：`agentos/rag/retriever.py`（239 行）

**职责**：组合知识检索与规则匹配，输出 LLM 可用上下文。

```python
class Retriever:
    def retrieve(query, top_k_knowledge=5, top_k_rules=10,
                 distance_threshold=1.5) → RetrievalResult
        """统一检索入口"""

    def retrieve_for_qa(query) → RetrievalResult
        """问答场景：宽松阈值 (knowledge≤1.8, rules≤1.2)"""

    def retrieve_for_compliance_check(query) → RetrievalResult
        """合规检查：严格阈值 + 更多规则 (top_k=20)"""

    def format_context(result) → str
        """格式化 LLM 上下文"""
```

**检索流程**：
```
retrieve(query)
  ├─→ 1. embedder.embed_query(query)          # 查询向量化
  │      enhanced_query = "为下述问题检索相关知识：{query}"
  │
  ├─→ 2. store.search_knowledge(emb, top_k)   # 知识检索
  │     过滤: distance ≤ threshold (1.5~1.8)
  │     返回: [{id, document, metadata, distance}, ...]
  │
  ├─→ 3. store.search_rules(emb, top_k)       # 规则检索
  │     过滤: distance ≤ 1.2 (更严格)
  │     返回: [{id, document, metadata, distance}, ...]
  │
  └─→ 4. _check_violations(query, rules)      # 违规识别
        标记 scenario_type ∈ {风险警示, 合规警示} 或 tags 含 "禁止"/"违规"
```

**RetrievalResult 结构**：
```python
class RetrievalResult:
    query: str = ""                   # 原始查询
    knowledge_chunks: list[dict]      # 匹配的知识 chunks
    matched_rules: list[dict]         # 匹配的规则
    rule_violations: list[dict]       # 可能违规的规则 (需审查)
```

**format_context 输出格式**：
```
## 相关知识文档

### 1. **文档标题** > 小节标题 _(来源: 文件路径)_
{chunk 内容}

## 匹配的业务规则约束

### 规则 1. **R00001** [信息咨询]
{规则内容 - 编号、场景、话术、标签}

## ⚠️ 可能违反的业务规则（需重点审查）
- **R00017**: 需按标准话术拦截
```

---

## 三、知识库数据源

### 3.1 目录结构

```
data-sim/rag_docs/
├── AI对话约束规则.md                    # 输出格式模板（不入库）
├── INDEX.md                             # 知识库索引
├── README.md                            # 说明文档
├── 文档来源记录.md                       # 来源追踪
├── 来源引用审查报告.md                   # 引用审查
│
├── 01-零售业务分类/                      # 7 个文件
│   ├── 01-个人存款业务分类.md
│   ├── 02-个人贷款业务分类.md
│   ├── 03-银行卡业务分类.md
│   ├── 04-理财与财富管理分类.md
│   ├── 05-中间业务分类.md
│   ├── 06-电子银行与渠道分类.md
│   └── 07-普惠金融与特色业务分类.md
│
├── 02-零售业务产品介绍/                  # 约 60 个文件
│   ├── 存款产品/
│   ├── 理财产品/
│   ├── 贷款产品/
│   ├── 银行卡产品/
│   └── 中间业务产品/
│
├── 03-零售业务办理流程/                  # 约 20 个文件
│   ├── 存款业务/
│   ├── 理财业务/
│   ├── 贷款业务/
│   ├── 银行卡业务/
│   └── 综合业务/
│
├── 04-管理办法与政策法规/                # 约 30 个文件
│   ├── 国家法律法规/
│   ├── 监管规章/
│   ├── 行业规范/
│   └── 城商行农商行专项政策/
│
├── 05-渠道服务功能/                      # 约 30 个文件
│   ├── 手机银行/
│   ├── 网上银行/
│   ├── 微信银行/
│   ├── 柜面服务/
│   ├── 智能柜台与自助设备/
│   ├── 远程银行/
│   └── 开放银行与生态合作/
│
├── 06-业务对象专题/                      # 约 10 个文件
│   ├── 01-个人客户/
│   ├── 02-账户体系/
│   └── 03-风控与合规/
│
└── 业务规则约束/                         # 7 个文件，383 条规则
    ├── 01-个人贷款管理办法-AI业务规则约束.md
    ├── 02-商业银行理财业务监督管理办法-AI业务规则约束.md
    ├── 03-商业银行信用卡业务监督管理办法-AI业务规则约束.md
    ├── 04-商业银行互联网贷款管理暂行办法-AI业务规则约束.md
    ├── 05-银行保险机构消费者权益保护管理办法-AI业务规则约束.md
    ├── 06-个人金融信息保护规定-AI业务规则约束.md
    └── 07-商业银行金融资产风险分类办法-AI业务规则约束.md
```

### 3.2 数据规模

| 指标 | 数值 |
|------|:---:|
| 知识文件 | 165 个 |
| 知识 Chunks | 1,450 |
| 规则文件 | 7 个 |
| 规则条目 | 383 条 |
| 向量维度 | 1,024 |
| 数据库文件 | ~21 MB (chroma.sqlite3) |
| Embedding API 调用 | 约 183 批 (145+38) |

---

## 四、运行时设计

### 4.1 懒初始化与单例模式

所有 RAG 组件均采用全局懒初始化单例：

```python
# embedder.py
_embedder: Optional[Embedder] = None
def get_embedder() → Embedder    # 首次调用时创建

# vector_store.py
_store: Optional[VectorStore] = None
def get_vector_store() → VectorStore

# retriever.py
_retriever: Optional[Retriever] = None
def get_retriever() → Retriever
```

**优势**：
- 不在 import 时初始化（避免阻塞进程启动）
- 仅在首次问答调用时加载 ChromaDB
- 所有 Agent 实例共享同一向量库连接

### 4.2 索引构建时机

```
首次 ask() 调用
  ├─→ ensure_index() 检查
  │     ├─ store.count_knowledge() > 0 && store.count_rules() > 0
  │     │   → 已构建，跳过
  │     └─ 否则 → build_index(force_rebuild=False)
  │
  └─→ 后续调用直接复用已有索引（无需重复构建）
```

**手动重建**：
```python
from agentos.rag.indexer import build_index
build_index(force_rebuild=True)   # 知识库更新后执行
```

### 4.3 LLM 调用降级

```python
async def _generate_answer(...):
    try:
        resp = self.adapter.chat(messages, temperature=0.3, max_tokens=2048)
        return resp["content"]
    except Exception as e:
        log.error(f"LLM call failed: {e}")
        return self._fallback_answer(question, retrieval)
        # → 直接返回 RAG 检索到的原文片段（未经 AI 润色）
```

### 4.4 查询增强策略

```python
def embed_query(query: str) -> list[float]:
    # 通过前缀指令提升检索效果
    enhanced_query = f"为下述问题检索相关知识：{query}"
    return self.embed_single(enhanced_query)
```

---

## 五、配置与部署

### 5.1 依赖清单

```
# requirements.txt (RAG 相关)
chromadb>=0.5.0          # 嵌入式向量数据库
openai>=1.0.0            # OpenAI 兼容客户端 (调用 DashScope)
dashscope>=1.20.0        # 百炼 SDK
python-dotenv>=1.0.0     # 环境变量管理
```

### 5.2 Python 环境

项目使用 `uv` 管理的 Python 3.12.13 虚拟环境：

```bash
# 创建
cd data-sim
uv venv --python 3.12

# 激活
source .venv/bin/activate

# 安装
uv pip install -i https://pypi.tuna.tsinghua.edu.cn/simple chromadb openai dashscope python-dotenv
```

> **注意**：Python 3.14.3 (arm64 macOS) 无 chromadb 预编译 wheel，需使用 Python 3.12。

### 5.3 环境变量

```bash
# .env
# === RAG 向量嵌入 ===
DASHSCOPE_API_KEY=sk-xxx
DASHSCOPE_EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v3
DASHSCOPE_EMBEDDING_DIM=1024

# === ChromaDB 本地存储 ===
CHROMA_PERSIST_DIR=./chroma_db
```

### 5.4 验证命令

```bash
# 验证 Embedding API
python3 -c "
from agentos.rag.embedder import Embedder
v = Embedder().embed_single('测试')
print(f'Vector dim: {len(v)}')  # → 1024
"

# 构建索引
python3 -c "
from agentos.rag.indexer import build_index
print(build_index(force_rebuild=True))
# → {'knowledge_chunks': 1450, 'rules_count': 383, ...}
"

# 查看索引状态
python3 -c "
from agentos.rag.vector_store import get_vector_store
print(get_vector_store().stats())
# → {'collections': {'rag_knowledge': 1450, 'rag_business_rules': 383}}
"

# 测试检索
python3 -c "
from agentos.rag.retriever import get_retriever
r = get_retriever()
result = r.retrieve('个人住房贷款申请流程', top_k_knowledge=3)
for c in result.knowledge_chunks:
    print(c['metadata']['title'], c['distance'])
"
```

---

## 六、已知限制与规划

### 6.1 当前限制

| 限制 | 影响 | 缓解措施 |
|------|------|---------|
| DashScope batch=10 | 1450 chunks 需 145 次 API 调用 | 索引构建一次性成本，后续复用 |
| ChromaDB 本地存储 | 不可跨进程共享 | 单进程 AgentOS 部署可接受 |
| 分块固定大小 | 超长文档可能被截断 | 1500 字符可覆盖大多数文档章节 |
| 无增量更新 | 知识库变更需全量重建 | 当前可接受，后续可优化 |

### 6.2 后续规划

1. **增量索引**：检测文件修改时间，仅 re-index 变更文件
2. **混合检索**：BM25 关键词 + 向量语义，提升精确匹配召回率
3. **重排序（Rerank）**：粗排(top_k=20) → 精排模型重排序
4. **多轮对话记忆**：将历史 QA 对注入检索上下文
5. **产品数据库集成**：RAG 检索与结构化产品查询（product_database.json）融合

---

> **关联文档**：
> - QAAgent 设计方案：[docs/03-architecture/07-智能问答助手.md](../03-architecture/07-智能问答助手.md)
> - 实现代码：
>   - [agentos/rag/embedder.py](../data-sim/agentos/rag/embedder.py)
>   - [agentos/rag/vector_store.py](../data-sim/agentos/rag/vector_store.py)
>   - [agentos/rag/indexer.py](../data-sim/agentos/rag/indexer.py)
>   - [agentos/rag/retriever.py](../data-sim/agentos/rag/retriever.py)
>   - [agentos/agents/qa_assistant.py](../data-sim/agentos/agents/qa_assistant.py)
