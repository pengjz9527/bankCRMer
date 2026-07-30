# AgentOS 运行时设计

> **来源**：拆分自 `prototype/AI智能平台架构设计-AgentOS.md` §三+§四。
> **关联**：总体架构见 `docs/03-architecture/00-AgentOS总体架构.md`，智能体体系见 `docs/03-architecture/01-智能体体系总览.md`。
> **版本**：v2.0 | **日期**：2026-07-18

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
