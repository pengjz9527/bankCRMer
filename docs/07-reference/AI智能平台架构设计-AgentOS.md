# 易会办 · AI 智能平台架构设计（AgentOS）

> **定位**：定义易会办前台（客户经理APP）和后台（管理驾驶舱）统一的 AI 智能平台架构。采用多 Agent 协作模式，以领域专家智能体群 + 技能库 + 定时编排引擎，同时服务一线执行和经营决策。
>
> **核心原则**：大模型可灵活替换 · 前后台统一平台 · Agent 领域化 · 批量任务定时编排
>
> **版本**：v2.0 | **日期**：2026-07-18

---

## 目录

- [一、架构总览](#一架构总览)
- [二、Agent 体系设计](#二agent-体系设计)
- [三、Agent Harness（AgentOS 运行时）](#三agent-harnessagentos-运行时)
- [四、Skill 技能库](#四skill-技能库)
- [五、定时任务与工作流编排](#五定时任务与工作流编排)
- [六、模型适配层](#六模型适配层)
- [七、AI 网关](#七ai-网关)
- [八、技术选型总表](#八技术选型总表)
- [九、目录结构](#九目录结构)
- [十、实施路线](#十实施路线)
- [十一、关键设计决策](#十一关键设计决策)

---

## 一、架构总览

### 1.1 场景全景

前台 16 个 + 后台 12 个 = **28 个 AI 场景**，由统一的 Agent 平台承载。

```
┌──────────────────────────────────────────────────────────────┐
│                    前台 AI (客户经理APP)                       │
│  感知层 · 智能排程/商机识别/客户洞察/风险预警/资讯摘要           │
│  交互层 · AI对话/作战包/话术/偏离应对/智能搜索/新客推荐         │
│  回顾层 · 昨日回顾/周报/业绩解读/策略建议                       │
├──────────────────────────────────────────────────────────────┤
│                    后台 AI (管理驾驶舱)                        │
│  诊断预测 · 健康诊断/归因分析/预测预警/排名解读                  │
│  洞察提炼 · 标杆发现/行为挖掘/套路提炼/辅导建议                  │
│  内容生成 · 经营报告/复盘材料/目标分解                          │
│  对话交互 · 管理者AI对话助手                                    │
├──────────────────────────────────────────────────────────────┤
│                共用 AgentOS 平台 (统一引擎)                     │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 分层架构图

```
┌──────────────────────────────────────────────────────────────────┐
│                         前端入口层                                 │
│  ┌─────────────────────┐        ┌──────────────────────────┐     │
│  │  客户经理 APP        │        │   管理后台 Web             │     │
│  │  AI FAB / AI卡片    │        │   侧边AI面板 / AI诊断卡片  │     │
│  └──────────┬──────────┘        └────────────┬─────────────┘     │
│             │ SSE/HTTP                       │ SSE/HTTP          │
├─────────────┼────────────────────────────────┼───────────────────┤
│             ▼                                ▼                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    AI Gateway                             │    │
│  │  统一入口 · 鉴权 · 限流 · 降级 · 上下文注入                  │    │
│  │  POST /api/ai/chat     (实时对话, SSE流式)                 │    │
│  │  POST /api/ai/generate (同步/异步生成)                     │    │
│  │  POST /api/ai/workflow (触发工作流)                        │    │
│  └──────────────────────────┬───────────────────────────────┘    │
│                             │                                     │
│                             ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                  Agent Harness (AgentOS)                   │    │
│  │                                                           │    │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌─────────┐  │    │
│  │  │ 对话路由  │  │ 技能调度   │  │ 上下文   │  │ Agent   │  │    │
│  │  │ Router   │  │ Skill     │  │ 记忆管理  │  │ 生命周期 │  │    │
│  │  │          │  │ Executor  │  │ Memory   │  │ Lifecycle│  │    │
│  │  └──────────┘  └───────────┘  └──────────┘  └─────────┘  │    │
│  │                                                           │    │
│  │  ┌──────────────────────────────────────────────────┐    │    │
│  │  │            Agent 注册中心 (Agent Registry)         │    │    │
│  │  │  每个 Agent 注册: 名称/角色/能力描述/技能列表/      │    │    │
│  │  │  触发方式(实时/定时/事件)/适用的模型                 │    │    │
│  │  └──────────────────────────────────────────────────┘    │    │
│  └──────────────────────────┬───────────────────────────────┘    │
│                             │                                     │
│     ┌───────────────────────┼───────────────────────┐            │
│     ▼                       ▼                       ▼            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐  │
│  │ Agent Pool   │   │  Skill Pool  │   │  Knowledge Base      │  │
│  │ 14个领域专家 │   │  公共工具库   │   │  客户/产品/机构/     │  │
│  │ 智能体       │   │              │   │  行为/商机/套路      │  │
│  └──────────────┘   └──────────────┘   └──────────────────────┘  │
│                                                                   │
│  ┌──────────────────────┐   ┌──────────────────────────────┐    │
│  │   Task Scheduler     │   │   Workflow Engine             │    │
│  │   定时任务调度        │   │   多Agent编排 & 流程引擎       │    │
│  │   Cron / Interval    │   │   DAG / 并行 / 条件分支       │    │
│  └──────────────────────┘   └──────────────────────────────┘    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │               Model Adapter (LiteLLM)                     │    │
│  │  一行配置切换: gpt-4o ↔ claude-sonnet ↔ qwen-max ↔ local │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

### 1.3 核心设计理念

| 理念 | 说明 |
|------|------|
| **Agent 领域化** | 每个 Agent 是特定领域的专家，拥有独立 prompt、技能集、知识域 |
| **前后台统一** | 同一 Agent 群同时服务一线执行(前台)和经营决策(后台) |
| **技能共享** | Agent 通过 Skill 库调用公共能力，避免重复建设 |
| **定时编排** | 商机挖掘、套路提炼等重任务通过定时工作流批量执行 |
| **模型可替换** | 按 Agent 粒度独立指定模型，全局切换只改一行配置 |
| **声明式注册** | `@agent` 装饰器注册，30 行代码定义一个完整 Agent |

---

## 二、Agent 体系设计

### 2.1 Agent 全景图（14 个领域专家智能体）

```
                              对话路由智能体
                              RouterAgent
                         (意图识别 + Agent分发)
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
    ┌─────┴─────┐            ┌─────┴─────┐            ┌─────┴─────┐
    │ 前台 Agent群│            │ 后台 Agent群│            │ 系统 Agent │
    │  (8个)     │            │  (5个)     │            │  (1个)     │
    └───────────┘            └───────────┘            └───────────┘
```

### 2.2 前台 Agent 群（服务客户经理）

| Agent | 代号 | 角色定位 | 核心技能 | 触发方式 |
|-------|:---:|---------|---------|:---:|
| **排程智能体** | `SchedulerAgent` | 每日智能排程专家，综合优先级/距离/偏好生成最优日程 | `query_tasks`, `query_customer_priority`, `optimize_schedule` | 定时(每日8:00) + 按需 |
| **商机挖掘智能体** | `OppMiningAgent` | 全量扫描管户数据，基于行为/生命周期/关系图谱发现商机信号 | `scan_portfolio`, `detect_signals`, `evaluate_confidence`, `create_opportunity` | 定时(批量) + 按需(一键挖掘) |
| **客户洞察智能体** | `CustomerInsightAgent` | 360°客户理解，行为变化监测，风险预警 | `query_profile`, `analyze_behavior`, `detect_risk` | 定时 + 事件触发 |
| **作战包智能体** | `BattlePkgAgent` | 生成访前作战包，含客户速览/营销线索/切入话术/产品推荐/风险提示 | `gen_overview`, `gen_clues`, `gen_scripts`, `match_products` | 按需(实时) |
| **面谈辅助智能体** | `MeetingAgent` | 面谈中实时辅助：偏离应对/即时话术/产品搜索与对比 | `gen_deviation_response`, `search_product`, `compare_products` | 实时(流式) |
| **内容生成智能体** | `ContentAgent` (role=`content_gen`) | 信息秘书：总结/摘要/资讯解读/面谈口述转写 | `gen_review`(昨日回顾), `gen_digest`(资讯摘要), `gen_summary`(周报), `transcribe_dictation`(面谈转写) | 定时(20:00回顾+08:35摘要) + 按需 + 事件触发 |
| **推荐智能体** | `RecommendAgent` | 新客推荐/产品匹配/策略建议 | `match_similar_profiles`, `rank_candidates`, `gen_reasons` | 按需 |
| **智能问答助手** | `QAAgent` (role=`qa_assistant`) | 产品信息查询解读、业务知识问答、综合理财建议，基于 RAG(ChromaDB+DashScope)检索增强 | `ask`, `search_products`, `explain_product`, `answer_business_qa`, `advise_allocation` | 按需 |

### 2.3 后台 Agent 群（服务管理者）

| Agent | 代号 | 角色定位 | 核心技能 | 触发方式 |
|-------|:---:|---------|---------|:---:|
| **经营诊断智能体** | `DiagnosisAgent` | 全机构经营健康度扫描，异常识别与归因分析 | `scan_metrics`, `detect_anomalies`, `drill_down`, `attribute_causes` | 定时(每日) |
| **预测预警智能体** | `ForecastAgent` | 期末预测/缺口预警/趋势判断 | `predict_completion`, `estimate_gap`, `trigger_alert` | 定时(每日) |
| **洞察提炼智能体** | `InsightAgent` | 标杆自动发现/行为模式挖掘/套路提炼与效果评估 | `discover_benchmarks`, `mine_patterns`, `extract_tactics`, `evaluate_effect` | 定时(每周) + 按需 |
| **辅导智能体** | `CoachingAgent` | 1v1辅导建议：短板诊断/套路匹配/辅导计划 | `assess_gaps`, `match_tactics`, `gen_coaching_plan` | 定时(每日) + 按需 |
| **报告智能体** | `ReportAgent` | 经营报告/复盘材料/目标分解方案生成 | `gen_report`, `gen_review_material`, `gen_decomposition_plan` | 按需 |

### 2.4 系统 Agent

| Agent | 代号 | 角色定位 | 核心技能 |
|-------|:---:|---------|---------|
| **对话路由智能体** | `RouterAgent` | 识别用户意图，分发给对应领域 Agent，合并多 Agent 响应 | `classify_intent`, `route_to_expert`, `merge_responses` |

### 2.5 Agent 定义规范（声明式）

```python
# agents/opportunity_mining.py
from harness import Agent, skill, scheduled

@agent(
    name="商机挖掘智能体",
    role="opportunity_miner",
    description="基于客户行为、生命周期事件、关系图谱等数据，批量或按需发现潜在商机",
    skills=[
        "scan_portfolio",
        "detect_signals",
        "evaluate_confidence",
        "create_opportunity",
        "query_customers",
        "query_behavior",
        "query_holdings",
    ],
    model="gpt-4o",                      # 每个 Agent 可独立指定模型
    triggers=["scheduled", "on_demand"],  # 支持的触发方式
    rate_limit=50,                        # 每分钟最大调用次数
    timeout=600,                          # 单次执行超时(秒)
)
class OpportunityMiningAgent(Agent):
    """商机挖掘领域专家"""

    # System prompt 外部化
    system_prompt = "prompts/opportunity_mining.md"

    # ---- 定时批量挖掘（核心能力） ----
    @scheduled(cron="0 2 * * *", scope="全行")
    async def batch_mine_all(self, ctx):
        """每天凌晨2点，全量扫描所有管户，批量生成商机"""
        branches = await ctx.skill("query_all_branches")

        # 每个分行并行挖掘
        results = await ctx.harness.parallel_map(
            agent=self,
            items=branches,
            method="mine_branch",
            max_concurrency=6,
        )

        # 汇总、去重、入库
        all_signals = []
        for r in results:
            all_signals.extend(r)
        await ctx.skill("batch_upsert_opportunities", all_signals)

        # 推送给管理者和客户经理
        high_conf = [s for s in all_signals if s.confidence >= 0.7]
        await ctx.skill("notify_managers", {
            "title": "每日商机挖掘完成",
            "summary": f"全行发现 {len(all_signals)} 个商机信号，其中高置信度 {len(high_conf)} 个",
            "details": f"预估总价值 {sum(s.estimated_value for s in high_conf):.1f} 万",
        })

    # ---- 单分行挖掘 ----
    async def mine_branch(self, ctx, branch):
        """挖掘单个分行的商机"""
        customers = await ctx.skill("query_customers", branch=branch, active=True)

        signals = []
        for batch in ctx.chunk(customers, 50):
            batch_signals = await self.llm.analyze(
                prompt="detect_opportunity_signals",
                context={
                    "customers": batch,
                    "branch": branch,
                },
                tools=["query_behavior", "query_holdings", "query_transactions"],
            )
            signals.extend(batch_signals)

        # 评估置信度，过滤低质量信号
        evaluated = await self.evaluate_batch(ctx, signals)
        return [s for s in evaluated if s.confidence >= 0.6]

    # ---- 按需挖掘（前台"一键 AI 挖掘"按钮） ----
    @skill(description="接收前台一键挖掘请求，异步执行并推送结果")
    async def mine_on_demand(self, ctx, params):
        """客户经理手动触发，scope = 该经理的管户列表"""
        manager_id = params["manager_id"]
        ctx.ack({"message": "AI 挖掘已启动，完成后将推送通知", "estimated_seconds": 30})

        # 范围限定：仅该经理的管户
        customers = await ctx.skill("query_customers", manager_id=manager_id, active=True)

        # 去重：跳过最近 24 小时内已生成商机的客户
        recent_ids = await ctx.skill("query_recent_opp_cust_ids", hours=24, manager_id=manager_id)
        fresh_customers = [c for c in customers if c.id not in recent_ids]

        # 无新数据：所有管户已在 24h 内挖掘过
        if not fresh_customers:
            await ctx.skill("notify_manager", {
                "manager_id": manager_id,
                "title": "AI 商机挖掘完成",
                "summary": f"您的 {len(customers)} 位管户近 24 小时内已挖掘，数据无变化，暂无新商机",
                "highlights": [],
            })
            return {"status": "no_new_data", "total_customers": len(customers), "signals": 0}

        signals = []
        for batch in ctx.chunk(fresh_customers, 50):
            batch_signals = await self.llm.analyze(
                prompt="detect_opportunity_signals",
                context={
                    "customers": batch,
                    "scope": "on_demand",
                    "manager_id": manager_id,
                },
                tools=["query_behavior", "query_holdings", "query_transactions"],
            )
            signals.extend(batch_signals)

        evaluated = await self.evaluate_batch(ctx, signals)
        qualified = [s for s in evaluated if s.confidence >= 0.6]

        # 入库
        if qualified:
            await ctx.skill("batch_upsert_opportunities", qualified)

        # 推送给该经理（含空结果）
        high_conf = [s for s in qualified if s.confidence >= 0.7]
        await ctx.skill("notify_manager", {
            "manager_id": manager_id,
            "title": "AI 商机挖掘完成",
            "summary": f"扫描 {len(fresh_customers)} 位管户（已跳过 {len(customers) - len(fresh_customers)} 位近期已挖掘），" +
                       (f"发现 {len(qualified)} 个商机信号" if qualified else "未发现符合条件的商机"),
            "highlights": [{"cust_name": s.customer_name, "title": s.title} for s in high_conf[:5]],
        })

        return {"status": "completed", "total_customers": len(fresh_customers), "signals": len(qualified)}
```

### 2.6 Agent 与场景映射表

| Agent | 前台场景 | 后台场景 |
|-------|---------|---------|
| `SchedulerAgent` | 智能排程、AI 重排 | — |
| `OppMiningAgent` | 商机识别、一键 AI 挖掘 | AI 商机效果评估 |
| `CustomerInsightAgent` | 客户洞察、风险预警、大额异动 | 流失预警客户清单 |
| `BattlePkgAgent` | 作战包生成、话术生成 | 话术精华提取(协作) |
| `MeetingAgent` | 偏离应对、实时产品搜索/对比 | — |
| `ContentAgent` | 昨日回顾、周报、资讯摘要、面谈口述转写回填 | — |
| `QAAgent` | 产品查询、业务问答、合规咨询、配置建议 | — |
| `RecommendAgent` | 新客推荐、策略建议 | 目标分解建议 |
| `DiagnosisAgent` | — | 健康诊断、归因分析、排名解读 |
| `ForecastAgent` | — | 预测预警、期末预测、缺口计算 |
| `InsightAgent` | — | 标杆发现、行为挖掘、套路提炼 |
| `CoachingAgent` | — | 辅导建议生成 |
| `ReportAgent` | — | 经营报告、复盘材料生成 |
| `RouterAgent` | AI 对话(FAB) | 管理者 AI 对话助手 |

---

## 三、Agent Harness（AgentOS 运行时）

### 3.1 核心模块

```
Agent Harness
├── Router          # 对话路由：意图识别 → Agent 分发 → 响应合并
├── Skill Executor  # 技能调度：安全执行预注册函数，带限流/缓存/日志
├── Memory Store    # 上下文记忆：按 user_id + agent 维度隔离对话历史
├── Lifecycle       # Agent 生命周期：注册/初始化/健康检查/优雅关闭
├── Registry        # Agent 注册中心：维护所有 Agent 的能力元数据
└── Monitor         # 可观测性：Token消耗/调用耗时/错误率/Agent健康状态
```

### 3.2 对话路由流程

```
用户输入 ──→ RouterAgent.classify_intent()
                  │
                  │ 输出: { intent: "opportunity_mining",
                  │         confidence: 0.92,
                  │         target_agents: ["OppMiningAgent"],
                  │         params: { scope: "北京分行" } }
                  │
       ┌──────────┼──────────┐
       ▼          ▼          ▼
  单Agent      多Agent     无法识别
  直接调用     并行调用     RouterAgent
              + 合并响应    .fallback()
```

### 3.3 上下文记忆管理

```
Memory Key: session:{user_id}:{agent_name}
TTL: 24小时(对话) / 7天(辅导/诊断上下文)

存储结构:
{
  "messages": [
    { "role": "user", "content": "...", "ts": "..." },
    { "role": "assistant", "content": "...", "ts": "..." }
  ],
  "context": {
    "current_page": "W3商机管理",
    "current_customer_id": "cust_001",
    "current_org": "北京分行",
  },
  "max_messages": 50,       # 最多保留50轮
  "summarize_threshold": 30 # 超过30轮自动压缩前文
}
```

---

## 四、Skill 技能库

### 4.1 技能分类

```
skills/
├── data/                   # 数据查询类
│   ├── query_customers     # 客户查询(分页/筛选/脱敏)
│   ├── query_products      # 产品查询(按类型/风险/期限)
│   ├── query_opportunities # 商机查询(按状态/来源/机构)
│   ├── query_tasks         # 待办查询(按类型/状态/客户经理)
│   ├── query_performance   # 业绩查询(按机构/个人/指标)
│   ├── query_behavior      # 行为日志查询(按客户经理/时段)
│   └── query_org_tree      # 机构树查询
│
├── action/                 # 操作类
│   ├── create_opportunity  # 创建商机(含来源标识/置信度/推理链路)
│   ├── update_task_status  # 更新待办状态
│   ├── send_notification   # 推送通知(App内/消息中心)
│   ├── create_report       # 生成报告文件(PDF/Excel)
│   └── publish_tactic      # 发布套路到套路库
│
├── analysis/               # 分析类
│   ├── calculate_funnel    # 转化漏斗计算
│   ├── compare_groups      # 分组对比(A/B test)
│   ├── detect_anomaly      # 异常检测(统计方法)
│   └── rank_entities       # 排名计算
│
└── orchestration/          # 编排类
    ├── parallel_map        # 并行扇出(多Agent/多分片)
    ├── conditional_branch  # 条件分支
    └── human_approval      # 人工审批节点(注入工作流)
```

### 4.2 Skill 定义规范

```python
@skill(
    name="query_customers",
    description="查询客户列表，支持按机构/等级/标签筛选，自动脱敏",
    parameters={
        "branch": "机构代码(可选)",
        "tier": "客户等级(可选)",
        "tags": "标签列表(可选)",
        "page": "页码(默认1)",
        "limit": "每页数量(默认100, 最大500)",
    },
    rate_limit=100,         # 每分钟最多调用次数
    cache_ttl=300,          # 缓存时间(秒)
    retry=3,                # 失败重试次数
)
async def query_customers(branch=None, tier=None, tags=None, page=1, limit=100):
    """Agent 通过 ctx.skill('query_customers', ...) 调用"""
    ...
```

### 4.3 技能安全机制

| 机制 | 说明 |
|------|------|
| **白名单注册** | 只有 `@skill` 装饰的函数可被 Agent 调用 |
| **参数校验** | 基于 `parameters` 定义自动校验入参类型和范围 |
| **限流** | 每个 Skill 独立限流，防止 Agent 过度调用 |
| **超时** | 每个 Skill 默认 30s 超时，可配置 |
| **审计日志** | 记录每次 Skill 调用的参数/耗时/结果摘要 |
| **数据脱敏** | 查询类 Skill 自动对客户姓名/手机号等字段脱敏 |

---

## 五、定时任务与工作流编排

### 5.1 定时任务全景矩阵

| 时间 | Agent | 任务 | 说明 |
|------|-------|------|------|
| **每日 2:00** | `OppMiningAgent` | 全量商机挖掘 | 扫描全部管户，批量生成商机信号 |
| **每日 6:00** | `CustomerInsightAgent` | 客户画像刷新 | 行为分析/风险标签/流失概率更新 |
| **每日 7:00** | `DiagnosisAgent` | 全机构健康度扫描 | 生成当日诊断简报，识别异常指标 |
| **每日 7:30** | `ForecastAgent` | 期末预测 + 缺口预警 | 按当前节奏预测完成率，触发商机闭环调整 |
| **每日 8:00** | `SchedulerAgent` | 生成当日排程 | 为每位客户经理生成最优日程 |
| **每日 8:00** | `CoachingAgent` | 生成团队辅导建议 | 分析客户经理短板，匹配辅导策略 |
| **每日 8:30** | `ContentAgent` | 今日资讯摘要 | AI 解读当日金融资讯 |
| **每日 20:00** | `ContentAgent` | 昨日回顾草稿 | 自动生成当日工作总结草稿 |
| **每周一 6:00** | `InsightAgent` | 套路提炼 + 标杆刷新 | 多 Agent 协作，生成结构化套路初稿 |
| **每周一 8:00** | `ContentAgent` + `ReportAgent` | 周报生成 | 经营周报 + 个人周报 |
| **每月 1日** | `InsightAgent` | 月度标杆画像更新 | 长周期行为模式分析 |
| **实时** | `CustomerInsightAgent` | 大额异动检测 | 事件驱动，阈值触发即时预警 |

### 5.2 工作流编排模式

工作流引擎（基于 Celery Canvas）支持以下编排模式：

```
┌─────────────────────────────────────────┐
│  编排模式                                 │
├─────────────────────────────────────────┤
│  顺序链:   A → B → C                     │
│            chain(agentA, agentB, agentC) │
│                                          │
│  并行扇出: A → [B1, B2, B3] → C          │
│            chord(                          │
│              group(B1, B2, B3),           │
│              C                             │
│            )                               │
│                                          │
│  条件分支: A → if x: B else: C           │
│            自定义 conditional_task        │
│                                          │
│  循环:     for item in items:            │
│              agent.process(item)          │
│            parallel_map(items, agent)     │
│                                          │
│  人工审批: A → [等待] → B                │
│            注入 human_approval 节点       │
└─────────────────────────────────────────┘
```

### 5.3 多 Agent 协作示例：每周套路提炼

```
Workflow: weekly_tactic_extraction
Schedule: 0 6 * * 1 (每周一早 6:00)
──────────────────────────────────────────────────────────

Step 1 ──→ InsightAgent.discover_benchmarks()
           │  输入: 上周全量客户经理行为数据
           │  输出: 标杆名单(综合/单项/进步最快各5名)
           │
Step 2 ──→ InsightAgent.mine_patterns()          ← 对每个标杆并行
           │  输入: 标杆 vs 对照组行为对比数据
           │  输出: 差异化行为模式列表(按显著性排序)
           │
Step 3 ──→ InsightAgent.extract_tactics()        ← 融合多Agent视角
           │  协作: 调用 BattlePkgAgent 评估话术质量
           │        调用 RecommendAgent 评估产品组合有效性
           │  输出: 结构化套路初稿
           │
Step 4 ──→ ForecastAgent.evaluate_tactic_potential()
           │  输入: 套路初稿 + 历史采纳数据
           │  输出: 预期效果评分 + 适用场景 + 风险提示
           │
Step 5 ──→ [人工审批]  ← 管理者审核/编辑后确认入库
           │
Step 6 ──→ CoachingAgent.match_tactics_to_managers()
             输入: 套路库 + 客户经理短板画像
             输出: "人-套路"匹配建议 → 推送给支行管理者
```

### 5.4 工作流状态追踪

每个 Workflow Run 记录：

```python
{
    "run_id": "wf_20260718_001",
    "workflow": "weekly_tactic_extraction",
    "status": "running",              # pending/running/completed/failed
    "started_at": "2026-07-18T06:00:00Z",
    "steps": [
        {
            "step": "discover_benchmarks",
            "agent": "InsightAgent",
            "status": "completed",
            "duration_ms": 12400,
            "input_summary": "上周行为数据 1,280 条",
            "output_summary": "发现 15 名标杆候选人",
        },
        ...
    ],
    "retry_count": 0,
    "error": null,
}
```

---

## 六、模型适配层

### 6.1 设计原则

- **一行配置切换模型**：修改 `AI_CONFIG["default_model"]` 即可全局切换
- **Agent 粒度指定**：每个 Agent 可独立指定模型（高价值任务用强模型，摘要类用轻量模型）
- **降级链**：主模型不可用时自动切换降级模型
- **成本可控**：按 token 消耗统计，Agent 维度成本可视化

### 6.2 模型配置

```python
# ai/config.py
AI_CONFIG = {
    # 全局默认
    "adapter": "litellm",              # litellm | openai | claude | qwen
    "default_model": "openai/gpt-4o",
    "fallback_chain": [
        "claude-3-5-sonnet",           # 降级1: Claude
        "qwen/qwen-max",               # 降级2: 通义千问
    ],

    # 按 Agent 粒度指定（可选，覆盖全局配置）
    "agent_models": {
        "OppMiningAgent":     "openai/gpt-4o",          # 商机挖掘需要强推理
        "BattlePkgAgent":     "openai/gpt-4o",          # 作战包质量要求高
        "InsightAgent":       "openai/gpt-4o",          # 套路提炼需要深度分析
        "ContentAgent":       "openai/gpt-4o-mini",     # 摘要/资讯用轻量模型
        "QAAgent":           "openai/gpt-4o",           # QA 需要强推理和合规判断
        "DiagnosisAgent":     "openai/gpt-4o",          # 诊断归因需要强推理
        "CoachingAgent":      "openai/gpt-4o",          # 辅导建议需个性化
        "ReportAgent":        "openai/gpt-4o-mini",     # 报告生成可模板化
        "RouterAgent":        "openai/gpt-4o-mini",     # 意图分类轻量即可
    },

    # 全局参数
    "stream": True,
    "max_tokens": {
        "chat": 2048,
        "summary": 1024,
        "battle_pkg": 4096,
        "report": 8192,
    },
}
```

### 6.3 适配器接口

```python
# ai/adapters/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator

@dataclass
class ChatMessage:
    role: str       # system / user / assistant / tool
    content: str

@dataclass
class ChatResponse:
    content: str
    model: str
    usage: dict     # { prompt_tokens, completion_tokens, total_tokens }

class BaseModelAdapter(ABC):
    """模型适配器基类"""

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        stream: bool = False,
        max_tokens: int = 2048,
    ) -> ChatResponse: ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]: ...
```

### 6.4 切换模型示例

```bash
# 切换到 Claude
export AI_DEFAULT_MODEL="claude-3-5-sonnet"

# 切换到通义千问
export AI_DEFAULT_MODEL="qwen/qwen-max"

# 切换到本地 Ollama
export AI_DEFAULT_MODEL="ollama/llama3.1:70b"

# 只换商机挖掘的模型
export AI_AGENT_MODEL_OppMiningAgent="claude-3-5-sonnet"
```

---

## 七、AI 网关

### 7.1 端点设计

| 端点 | 方法 | 说明 | 响应方式 |
|------|:---:|------|:---:|
| `/api/ai/chat` | POST | 实时对话（前台FAB / 后台AI助手） | SSE 流式 |
| `/api/ai/generate` | POST | 同步/异步生成（作战包/报告/摘要） | JSON / 异步任务ID |
| `/api/ai/workflow` | POST | 触发工作流（商机挖掘/套路提炼） | 异步任务ID |
| `/api/ai/agents` | GET | 查询可用 Agent 列表和能力 | JSON |
| `/api/ai/health` | GET | AI 服务健康检查 | JSON |

### 7.2 请求/响应格式

```json
// POST /api/ai/chat
{
  "user_id": "user_001",
  "context": {
    "page": "W3商机管理",
    "customer_id": "cust_001",
    "org": "北京分行"
  },
  "message": "帮我分析一下这个客户有什么商机",
  "stream": true
}

// SSE 响应
event: thinking
data: {"agent": "RouterAgent", "intent": "opportunity_mining"}

event: message
data: {"agent": "OppMiningAgent", "content": "正在分析王建国的商机信号..."}

event: tool_call
data: {"skill": "query_behavior", "params": {"customer_id": "cust_001"}}

event: message
data: {"agent": "OppMiningAgent", "content": "发现3个潜在商机：\n1. 定存到期承接(置信度92%)..."}

event: done
data: {"tokens": {"prompt": 1240, "completion": 380, "total": 1620}}
```

### 7.3 降级策略

| 场景 | 策略 |
|------|------|
| 模型超时(>30s) | 自动切换降级模型重试 |
| 模型不可用(5xx) | 按 `fallback_chain` 依次尝试 |
| 全部模型不可用 | 返回兜底文案 + 建议稍后重试 |
| 单 Agent 故障 | 其他 Agent 继续服务，故障 Agent 降级为规则引擎 |
| 定时任务失败 | 自动重试3次，仍失败则告警 + 记录 |

---

## 八、技术选型总表

| 层级 | 组件 | 选型 | 说明 |
|------|------|------|------|
| **API 框架** | 后端 | FastAPI | 原生 async，SSE 流式支持好，已有项目基础 |
| **Agent 框架** | Agent Harness | 自研轻量 | 声明式 `@agent`，场景明确无需 LangChain 复杂度 |
| **模型适配** | 统一接口 | LiteLLM | 支持 OpenAI/Claude/Qwen/Ollama 等 100+ 模型 |
| **流式输出** | 协议 | SSE | 比 WebSocket 轻量，浏览器原生 `EventSource` |
| **技能执行** | Skill Executor | 自研沙箱 | 白名单注册 + 参数校验 + 限流 + 审计 |
| **上下文记忆** | 存储 | Redis / dict | 按 user_id+agent 维度隔离，TTL 自动过期 |
| **定时调度** | 调度器 | APScheduler + Celery | APScheduler 定义 cron，Celery 分布式执行 |
| **工作流编排** | 编排引擎 | Celery Canvas | chain/group/chord 原生 DAG 支持 |
| **消息队列** | Agent间通信 | Redis Pub/Sub | 轻量，已有 Redis 则零额外依赖 |
| **提示词管理** | 模板 | Markdown + Jinja2 | 可版本控制，非开发人员可调优 |
| **向量检索** | 知识库 | ChromaDB | RAG 场景：产品知识/合规条款/话术库检索 |
| **语音输入** | 语音 | Web Speech API → Whisper | 浏览器端采集 + 后端转写 |
| **可观测性** | 监控 | Prometheus + 自研 Dashboard | Token消耗/Agent调用/任务队列深度 |

---

## 九、目录结构

```
data-sim/
├── app.py                          # 现有 API（保持不变）
├── ai/                             # ← AI 模块
│   ├── config.py                   # 模型配置（切换模型的唯一入口）
│   ├── gateway.py                  # AI 网关路由
│   │
│   ├── harness/                    # AgentOS 运行时
│   │   ├── router.py               # 对话路由（意图识别 → Agent分发）
│   │   ├── skill_executor.py       # 技能调度执行器
│   │   ├── memory.py               # 上下文记忆管理
│   │   ├── lifecycle.py            # Agent 生命周期管理
│   │   ├── registry.py             # Agent 注册中心
│   │   └── monitor.py              # 可观测性
│   │
│   ├── adapters/                   # 模型适配器
│   │   ├── base.py                 # 抽象基类
│   │   └── litellm_adapter.py      # LiteLLM 适配器
│   │
│   ├── agents/                     # Agent 定义（每个 Agent 一个文件）
│   │   ├── router.py               # 对话路由智能体
│   │   ├── scheduler.py            # 排程智能体
│   │   ├── opportunity_mining.py   # 商机挖掘智能体
│   │   ├── customer_insight.py     # 客户洞察智能体
│   │   ├── battle_package.py       # 作战包智能体
│   │   ├── meeting.py              # 面谈辅助智能体
│   │   ├── content.py              # 内容生成智能体
│   │   ├── recommend.py            # 推荐智能体
│   │   ├── diagnosis.py            # 经营诊断智能体
│   │   ├── forecast.py             # 预测预警智能体
│   │   ├── insight.py              # 洞察提炼智能体
│   │   ├── coaching.py             # 辅导智能体
│   │   └── report.py               # 报告智能体
│   │
│   ├── skills/                     # 技能库
│   │   ├── data/                   # 数据查询技能
│   │   │   ├── query_customers.py
│   │   │   ├── query_products.py
│   │   │   ├── query_opportunities.py
│   │   │   ├── query_tasks.py
│   │   │   ├── query_performance.py
│   │   │   ├── query_behavior.py
│   │   │   └── query_org_tree.py
│   │   ├── action/                 # 操作技能
│   │   │   ├── create_opportunity.py
│   │   │   ├── update_task_status.py
│   │   │   ├── send_notification.py
│   │   │   ├── create_report.py
│   │   │   └── publish_tactic.py
│   │   ├── analysis/               # 分析技能
│   │   │   ├── calculate_funnel.py
│   │   │   ├── compare_groups.py
│   │   │   ├── detect_anomaly.py
│   │   │   └── rank_entities.py
│   │   └── orchestration/          # 编排技能
│   │       ├── parallel_map.py
│   │       ├── conditional_branch.py
│   │       └── human_approval.py
│   │
│   ├── prompts/                    # 提示词模板（Markdown）
│   │   ├── router.md
│   │   ├── scheduler.md
│   │   ├── opportunity_mining.md
│   │   ├── customer_insight.md
│   │   ├── battle_package.md
│   │   ├── meeting.md
│   │   ├── content.md
│   │   ├── recommend.md
│   │   ├── diagnosis.md
│   │   ├── forecast.md
│   │   ├── insight.md
│   │   ├── coaching.md
│   │   └── report.md
│   │
│   ├── workflows/                  # 工作流定义
│   │   ├── daily_opportunity_mining.py
│   │   ├── weekly_tactic_extraction.py
│   │   ├── daily_diagnosis.py
│   │   └── daily_scheduling.py
│   │
│   └── knowledge/                  # 知识库（RAG 用）
│       ├── product_knowledge/      # 产品知识文档
│       ├── compliance_rules/       # 合规条款
│       └── script_library/         # 话术精华库
```

---

## 十、实施路线

### Phase 0：AgentOS 骨架（基础平台）

**目标**：Agent 可以注册、对话可以路由、模型可以切换

| 交付项 | 说明 |
|-------|------|
| Agent Harness 框架 | `@agent` 装饰器、Registry、Lifecycle |
| Model Adapter | LiteLLM 适配器 + 配置切换 |
| Skill Executor | `@skill` 装饰器 + 白名单 + 限流 |
| AI Gateway | `/api/ai/chat`、`/api/ai/health` |
| RouterAgent | 意图分类 + Agent 分发 |
| Memory Store | 会话上下文管理 |

### Phase 1：前台核心能力

**目标**：客户经理可以对话、生成作战包、获得智能排程

| 交付项 | 覆盖场景 |
|-------|---------|
| `BattlePkgAgent` | 作战包生成、话术生成 |
| `ContentAgent` | Block 1 AI 摘要、昨日回顾、资讯摘要 |
| `SchedulerAgent` | 每日智能排程、AI 重排 |
| `MeetingAgent` | 面谈中偏离应对、实时产品搜索 |
| `RecommendAgent` | 新客推荐 |
| 前端 FAB 对话接入 | SSE 流式对话 |

### Phase 2：后台诊断 + 定时商机挖掘

**目标**：管理者看到 AI 诊断，商机自动批量生成

| 交付项 | 覆盖场景 |
|-------|---------|
| `OppMiningAgent` | 定时全量商机挖掘 + 一键 AI 挖掘 |
| `DiagnosisAgent` | 经营健康度诊断、归因分析 |
| `ForecastAgent` | 预测预警、期末缺口估算 |
| Task Scheduler | APScheduler 定时任务调度 |
| Workflow Engine | 商机挖掘工作流（并行分片） |

### Phase 3：洞察闭环

**目标**：标杆自动发现 → 套路提炼 → 辅导建议，完整闭环

| 交付项 | 覆盖场景 |
|-------|---------|
| `InsightAgent` | 标杆发现、行为模式挖掘、套路自动提炼 |
| `CoachingAgent` | 1v1 辅导建议生成 |
| `ReportAgent` | 经营报告、复盘材料生成 |
| Workflow Engine 升级 | 多 Agent 协作编排（套路提炼工作流） |
| 套路库管理 | 套路入库、审核、发布、效果跟踪 |

### Phase 4：深度智能

**目标**：全量定时任务上线，向量检索，语音输入

| 交付项 | 说明 |
|-------|------|
| 全量定时任务 | 所有 cron 任务上线运行 |
| 知识库(RAG) | ChromaDB 接入，产品/合规/话术检索 |
| 语音输入 | Web Speech API + Whisper |
| 成本监控 | Token 消耗看板，Agent 维度成本分析 |
| A/B 实验 | 套路推广效果对比 |

---

## 十一、关键设计决策

| 决策点 | 选择 | 理由 |
|-------|------|------|
| **Agent 框架** | 自研轻量，不依赖 LangChain | 场景明确、Agent 数量可控，自研框架更易维护和调试 |
| **多 Agent 协作** | RouterAgent 意图分发 + Celery Canvas 工作流 | 对话场景由 Router 分发；批量任务由 Canvas 编排，职责清晰 |
| **模型网关** | LiteLLM | 社区活跃、模型覆盖全、API 兼容 OpenAI SDK |
| **定时调度** | APScheduler(开发) → Celery(生产) | 渐进式升级，开发阶段无需 Redis |
| **流式协议** | SSE 而非 WebSocket | 单向流足够，浏览器原生支持，实现简单 |
| **技能管理** | 白名单注册 + 装饰器声明 | 安全可控，避免 Agent 任意调用函数 |
| **提示词管理** | Markdown 文件 + 版本控制 | 可 diff/可 review/非开发人员可编辑 |
| **Agent 粒度** | 14 个，按领域划分 | 内聚性好，每个 Agent 职责单一，prompt 可精细调优 |
| **模型粒度** | 按 Agent 独立指定 | 高价值任务(商机挖掘/作战包)用强模型，摘要类用轻量模型，控制成本 |
| **不引入向量库** | MVP 阶段用全文检索 + prompt 注入 | 数据量小，向量库 ROI 待验证 |

---

> **版本历史**：
> - v1.0 (2026-07-18)：初版，分层服务架构，仅覆盖前台 16 个 AI 场景
> - v2.0 (2026-07-18)：重构为 AgentOS 架构，统一前后台，新增 Agent/Skill/Workflow 体系
