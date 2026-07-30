"""
SchedulerAgent — 日程排程智能体
基于待办池数据，智能生成客户经理每日工作日程

工作分类目录（8类触客 + 2类非触客），规则引擎 + LLM 微调混合架构。

触发方式：
  - 定时批量：每日凌晨 0:00，为全行客户经理生成当日日程
  - 按需重排：客户经理手动点击"重新排程" / 调整日程后触发
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
    query_customers,
    query_customer_full,
    query_holdings,
    query_transactions,
    query_communications,
    query_loans,
)
from ..model_adapter import get_adapter

log = logging.getLogger("agentos.scheduler")

# ============================================================
# 工作分类目录（核心数据定义）
# ============================================================

@dataclass
class WorkTypeCatalog:
    """工作分类目录 — 定义每种待办类型的属性"""
    type_code: str              # "due" / "big_move" / ...
    type_name: str              # "产品到期"
    per_customer_minutes: int   # 单客户单待办处理时长（分钟）
    recommended_slots: list     # ["morning"] / ["morning","afternoon"]
    priority_level: str         # "P0" / "P1" / "P2" / "P3"
    priority_weight: int        # 权重分：P0=100, P1=80, P2=50, P3=30
    contact_methods: list       # ["phone","wechat"] / [] 非触客为空
    is_customer_facing: bool    # 是否为触客型工作
    grouping_supported: bool    # 是否支持多客户合并排程
    photo_required: bool        # 是否需要拍照留痕

    def to_dict(self) -> dict:
        return {
            "type_code": self.type_code,
            "type_name": self.type_name,
            "per_customer_minutes": self.per_customer_minutes,
            "recommended_slots": self.recommended_slots,
            "priority_level": self.priority_level,
            "priority_weight": self.priority_weight,
            "contact_methods": self.contact_methods,
            "is_customer_facing": self.is_customer_facing,
            "grouping_supported": self.grouping_supported,
            "photo_required": self.photo_required,
        }


# 工作分类目录 — 10 类待办的完整定义
WORK_TYPE_CATALOG: dict[str, WorkTypeCatalog] = {
    # ======== 触客型工作（8 类）========
    "due": WorkTypeCatalog(
        type_code="due", type_name="产品到期",
        per_customer_minutes=15,
        recommended_slots=["morning"],
        priority_level="P0", priority_weight=100,
        contact_methods=["phone", "wechat"],
        is_customer_facing=True, grouping_supported=True, photo_required=False,
    ),
    "big_move": WorkTypeCatalog(
        type_code="big_move", type_name="大额异动",
        per_customer_minutes=15,
        recommended_slots=["morning"],
        priority_level="P1", priority_weight=80,
        contact_methods=["phone"],
        is_customer_facing=True, grouping_supported=False, photo_required=False,
    ),
    "overdue": WorkTypeCatalog(
        type_code="overdue", type_name="贷款逾期",
        per_customer_minutes=15,
        recommended_slots=["afternoon"],
        priority_level="P1", priority_weight=80,
        contact_methods=["phone"],
        is_customer_facing=True, grouping_supported=False, photo_required=False,
    ),
    "opp": WorkTypeCatalog(
        type_code="opp", type_name="商机待办",
        per_customer_minutes=30,
        recommended_slots=["morning", "afternoon"],
        priority_level="P1", priority_weight=75,
        contact_methods=["visit", "phone"],
        is_customer_facing=True, grouping_supported=False, photo_required=True,
    ),
    "birthday": WorkTypeCatalog(
        type_code="birthday", type_name="生日提醒",
        per_customer_minutes=10,
        recommended_slots=["afternoon"],
        priority_level="P2", priority_weight=50,
        contact_methods=["wechat", "phone"],
        is_customer_facing=True, grouping_supported=True, photo_required=False,
    ),
    "contact_lapse": WorkTypeCatalog(
        type_code="contact_lapse", type_name="联络超期",
        per_customer_minutes=10,
        recommended_slots=["afternoon"],
        priority_level="P2", priority_weight=50,
        contact_methods=["wechat", "phone"],
        is_customer_facing=True, grouping_supported=True, photo_required=False,
    ),
    "credit_card": WorkTypeCatalog(
        type_code="credit_card", type_name="信用卡待办",
        per_customer_minutes=10,
        recommended_slots=["morning", "afternoon"],
        priority_level="P3", priority_weight=30,
        contact_methods=["wechat", "phone"],
        is_customer_facing=True, grouping_supported=True, photo_required=False,
    ),
    "post_meeting": WorkTypeCatalog(
        type_code="post_meeting", type_name="面谈后跟进",
        per_customer_minutes=15,
        recommended_slots=["afternoon"],
        priority_level="P2", priority_weight=50,
        contact_methods=["wechat", "phone"],
        is_customer_facing=True, grouping_supported=False, photo_required=False,
    ),
    "insight_alert": WorkTypeCatalog(
        type_code="insight_alert", type_name="洞察预警",
        per_customer_minutes=10,
        recommended_slots=["morning"],
        priority_level="P1", priority_weight=75,
        contact_methods=["phone"],
        is_customer_facing=True, grouping_supported=False, photo_required=False,
    ),
    # ======== 非触客型工作（2 类）========
    "report": WorkTypeCatalog(
        type_code="report", type_name="报告编写",
        per_customer_minutes=120,  # 固定 2 小时
        recommended_slots=["morning"],
        priority_level="P1", priority_weight=80,
        contact_methods=[],
        is_customer_facing=False, grouping_supported=False, photo_required=False,
    ),
    "meeting": WorkTypeCatalog(
        type_code="meeting", type_name="参加会议",
        per_customer_minutes=120,  # 固定 2 小时
        recommended_slots=["morning", "afternoon"],
        priority_level="P1", priority_weight=80,
        contact_methods=[],
        is_customer_facing=False, grouping_supported=False, photo_required=False,
    ),
    # ======== 强制工作待办（3 类）========
    "morning_meeting": WorkTypeCatalog(
        type_code="morning_meeting", type_name="早会",
        per_customer_minutes=30,
        recommended_slots=["morning"],
        priority_level="P0", priority_weight=100,
        contact_methods=[],
        is_customer_facing=False, grouping_supported=False, photo_required=False,
    ),
    "evening_meeting": WorkTypeCatalog(
        type_code="evening_meeting", type_name="晚会",
        per_customer_minutes=30,
        recommended_slots=["afternoon"],
        priority_level="P0", priority_weight=100,
        contact_methods=[],
        is_customer_facing=False, grouping_supported=False, photo_required=False,
    ),
    "report_review": WorkTypeCatalog(
        type_code="report_review", type_name="报告评审",
        per_customer_minutes=60,
        recommended_slots=["afternoon"],
        priority_level="P1", priority_weight=80,
        contact_methods=[],
        is_customer_facing=False, grouping_supported=False, photo_required=False,
    ),
}


# ============================================================
# 三卡片分组映射
# ============================================================

# 任务类型 → 卡片类型映射
CARD_GROUP_MAP: dict[str, str] = {
    # 客户待办
    "due": "customer", "big_move": "customer", "overdue": "customer",
    "birthday": "customer", "contact_lapse": "customer", "credit_card": "customer",
    "post_meeting": "customer", "insight_alert": "customer",
    # 商机待办
    "opp": "opportunity",
    # 工作待办
    "morning_meeting": "work", "evening_meeting": "work",
    "report": "work", "report_review": "work",
}

# 卡片容量上限
CARD_CAPACITY: dict[str, int] = {
    "customer": 10,
    "opportunity": 4,
    "work": 4,  # 早晚会固定占 2，其他工作 ≤ 2
}

# 客户待办卡片上下午分时上限
CUSTOMER_MORNING_MAX = 5
CUSTOMER_AFTERNOON_MAX = 5

CARD_NAMES: dict[str, str] = {
    "customer": "客户待办",
    "opportunity": "商机待办",
    "work": "工作待办",
}

# 固定工作待办（每日自动注入）
FIXED_WORK_TASKS = [
    {"type_code": "morning_meeting", "type": "早会", "assigned_slot": "morning"},
    {"type_code": "evening_meeting", "type": "晚会", "assigned_slot": "afternoon"},
]


# ============================================================
# 日程任务数据类
# ============================================================

@dataclass
class ScheduleTask:
    """日程任务 — 排入日程的待办"""
    task_id: str                 # "TK_DUE_14"
    type_code: str               # 工作分类码
    type_name: str               # "产品到期"
    cust_id: int = 0             # 主客户 ID（非触客类为 0）
    cust_name: str = ""          # 主客户名称
    summary: str = ""            # 任务摘要
    cust_count: int = 1          # 涉及客户数
    estimated_duration_min: int = 0  # 预估总耗时（分钟）
    contact_methods: list = field(default_factory=list)
    is_customer_facing: bool = True
    is_opportunity_task: bool = False
    assigned_slot: str = ""      # "morning" / "afternoon"
    order_in_slot: int = 0       # 在时段内的序号
    priority_weight: int = 30
    customer_ids: list = field(default_factory=list)  # 子客户 ID 列表
    customer_names: list = field(default_factory=list)  # 子客户名称列表
    status: str = "pending"      # pending / adjusted / completed / skipped
    # 7 日排程扩展字段
    deadline_date: str = ""      # 最晚处理日期 "2026-07-20"
    pinned_date: str = ""        # 固定排程日期（不可移动），空串表示可移动
    effective_weight: int = 0    # 动态计算的有效权重（priority_weight + urgency_boost）
    contact_prefer: str = "不限定"  # 客户联系时段偏好：上午优先/下午优先/不限定

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "type_code": self.type_code,
            "type_name": self.type_name,
            "cust_id": self.cust_id,
            "cust_name": self.cust_name,
            "summary": self.summary,
            "cust_count": self.cust_count,
            "estimated_duration_min": self.estimated_duration_min,
            "contact_methods": self.contact_methods,
            "is_customer_facing": self.is_customer_facing,
            "is_opportunity_task": self.is_opportunity_task,
            "assigned_slot": self.assigned_slot,
            "order_in_slot": self.order_in_slot,
            "priority_weight": self.priority_weight,
            "customer_ids": self.customer_ids,
            "customer_names": self.customer_names,
            "status": self.status,
            "deadline_date": self.deadline_date,
            "pinned_date": self.pinned_date,
            "contact_prefer": self.contact_prefer,
        }


# ============================================================
# 三卡片数据类
# ============================================================

@dataclass
class ScheduleCard:
    """日程卡片 — 客户待办 / 商机待办 / 工作待办"""
    card_type: str               # "customer" | "opportunity" | "work"
    card_name: str               # "客户待办" | "商机待办" | "工作待办"
    morning: list = field(default_factory=list)    # 上午任务列表
    afternoon: list = field(default_factory=list)  # 下午任务列表

    @property
    def total_count(self) -> int:
        """当前未完成任务数（不含已完成）"""
        return sum(1 for t in self.morning + self.afternoon
                   if getattr(t, 'status', 'pending') != 'completed')

    @property
    def max_capacity(self) -> int:
        caps = {"customer": 10, "opportunity": 4, "work": 4}
        return caps.get(self.card_type, 10)

    def to_dict(self) -> dict:
        return {
            "card_type": self.card_type,
            "card_name": self.card_name,
            "morning": [t.to_dict() for t in self.morning],
            "afternoon": [t.to_dict() for t in self.afternoon],
            "total_count": self.total_count,
            "max_capacity": self.max_capacity,
        }


# ============================================================
# 日排程数据类
# ============================================================

@dataclass
class DailySchedule:
    """日排程 — 某一天的完整工作日程（三卡片结构）"""
    date: str                    # "2026-07-18"
    manager_id: str
    cards: list = field(default_factory=list)       # [ScheduleCard]
    deferred_tasks: list = field(default_factory=list)  # 溢出推迟到明日的任务
    generated_at: str = ""       # 生成时间 ISO
    version: int = 0             # 版本号（重排递增）
    source: str = "rule"         # "rule" / "llm_refined"

    @property
    def total_tasks(self) -> int:
        return sum(c.total_count for c in self.cards)

    @property
    def total_minutes(self) -> int:
        return sum(
            sum(t.estimated_duration_min for t in c.morning + c.afternoon)
            for c in self.cards
        )

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "manager_id": self.manager_id,
            "cards": [c.to_dict() for c in self.cards],
            "deferred_count": len(self.deferred_tasks),
            "total_tasks": self.total_tasks,
            "total_minutes": self.total_minutes,
            "generated_at": self.generated_at,
            "version": self.version,
            "source": self.source,
        }


@dataclass
class WeeklyPlan:
    """7 日周计划 — 包含 7 天的日排程 + 溢出任务"""
    start_date: str              # 周起始日期 "2026-07-18"
    manager_id: str
    days: list                    # 7 个 DailySchedule
    overflow_tasks: list          # 溢出未排入的任务
    total_tasks: int = 0          # 7 天总任务数
    total_minutes: int = 0        # 7 天总分钟
    generated_at: str = ""        # 生成时间 ISO
    version: int = 0
    source: str = "rule"

    def to_dict(self) -> dict:
        return {
            "start_date": self.start_date,
            "manager_id": self.manager_id,
            "days": [d.to_dict() if hasattr(d, 'to_dict') else d for d in self.days],
            "overflow_tasks": [t.to_dict() if hasattr(t, 'to_dict') else t for t in self.overflow_tasks],
            "total_tasks": self.total_tasks,
            "total_minutes": self.total_minutes,
            "generated_at": self.generated_at,
            "version": self.version,
            "source": self.source,
        }


# ============================================================
# 排程常量
# ============================================================

# 时段定义（仅分上午/下午，不精确到小时）
SLOT_MORNING = "morning"
SLOT_AFTERNOON = "afternoon"

# 跨卡片约束：商机 + 工作 ≤ 6
MAX_OPP_PLUS_WORK = 6


# ============================================================
# Agent 定义
# ============================================================

@agent(
    name="日程排程智能体",
    role="scheduler",
    description="基于待办池和客户经理工作模式，智能生成每日工作日程",
    skills=[
        "classify_tasks", "allocate_slots", "optimize_sequence",
        "query_customers", "query_holdings", "query_transactions",
        "query_communications", "query_loans",
    ],
    triggers=["scheduled", "on_demand"],
    rate_limit=30,
    timeout=300,
)
class SchedulerAgent(Agent):
    """日程排程领域专家"""

    system_prompt = "prompts/scheduler.md"

    def __init__(self, adapter=None):
        super().__init__(adapter)
        self.load_prompt(self.system_prompt)

    # ================================================================
    # 工作分类目录查询
    # ================================================================

    def get_catalog(self) -> list[dict]:
        """获取完整工作分类目录"""
        return [w.to_dict() for w in WORK_TYPE_CATALOG.values()]

    def get_work_type(self, type_code: str) -> Optional[WorkTypeCatalog]:
        """获取单个工作分类"""
        return WORK_TYPE_CATALOG.get(type_code)

    # ================================================================
    # 规则引擎排程（确定性计算，毫秒级）
    # ================================================================

    def generate_daily_schedule(
        self,
        tasks: list[dict],
        manager_id: str = "",
        schedule_date: str = None,
    ) -> DailySchedule:
        """
        规则引擎生成当日日程（三卡片结构）

        Args:
            tasks: 待办列表 [{task_id, type, cust_id, cust_name, summary, cust_count, ...}]
            manager_id: 客户经理 ID
            schedule_date: 排程日期

        Returns:
            DailySchedule 排程结果（含三卡片 + deferred_tasks）
        """
        sd = schedule_date or date.today().isoformat()

        # Step 1: 将原始待办转为 ScheduleTask
        schedule_tasks = self._classify_tasks(tasks)

        # Step 2: 注入固定工作待办（早会/晚会）
        schedule_tasks = self._inject_fixed_work_tasks(schedule_tasks, sd)

        # Step 3: 按优先级排序
        schedule_tasks.sort(key=lambda t: (-t.priority_weight, -t.estimated_duration_min))

        # Step 4: 按三卡片分组
        grouped = self._group_into_cards(schedule_tasks)

        # Step 5: 容量截断 + 溢出推迟（内部已含时段分配，见 _apply_card_capacity L714）
        cards, deferred = self._apply_card_capacity(grouped, sd)

        # Step 6: 优化排序
        for card in cards:
            card.morning = self._optimize_sequence(card.morning)
            card.afternoon = self._optimize_sequence(card.afternoon)

        return DailySchedule(
            date=sd,
            manager_id=manager_id,
            cards=cards,
            deferred_tasks=deferred,
            generated_at=datetime.now().isoformat(),
            version=0,
            source="rule",
        )

    def _classify_tasks(self, tasks: list[dict]) -> list[ScheduleTask]:
        """将原始待办按工作分类目录归类，计算耗时"""
        result = []
        for t in tasks:
            task_type = t.get("type", "")
            # 优先使用 raw dict 中已有的 type_code
            type_code = t.get("type_code") or self._map_type_to_code(task_type)
            wtype = WORK_TYPE_CATALOG.get(type_code)

            # 提取 deadline 和 pinned 信息
            deadline = t.get("deadline_date", "")
            pinned = t.get("pinned_date", "")

            if not wtype:
                log.warning(f"Unknown task type: {task_type}, using defaults")
                st = ScheduleTask(
                    task_id=t.get("task_id", f"TK_UNK_{t.get('cust_id',0)}"),
                    type_code="unknown",
                    type_name=task_type,
                    cust_id=t.get("cust_id", 0),
                    cust_name=t.get("cust_name", ""),
                    summary=t.get("summary", ""),
                    cust_count=t.get("cust_count", 1),
                    estimated_duration_min=15,
                    contact_methods=["phone"],
                    priority_weight=30,
                    customer_ids=t.get("customer_ids", [t.get("cust_id", 0)]),
                    customer_names=t.get("customer_names", [t.get("cust_name", "")]),
                    deadline_date=deadline,
                    pinned_date=pinned,
                    contact_prefer=t.get("contact_prefer", "不限定"),
                )
            else:
                cust_count = t.get("cust_count", 1)
                if wtype.is_customer_facing:
                    duration = wtype.per_customer_minutes * cust_count
                else:
                    duration = wtype.per_customer_minutes

                st = ScheduleTask(
                    task_id=t.get("task_id", f"TK_{t.get('cust_id',0)}"),
                    type_code=type_code,
                    type_name=wtype.type_name,
                    cust_id=t.get("cust_id", 0),
                    cust_name=t.get("cust_name", ""),
                    summary=t.get("summary", ""),
                    cust_count=cust_count,
                    estimated_duration_min=duration,
                    contact_methods=wtype.contact_methods,
                    is_customer_facing=wtype.is_customer_facing,
                    is_opportunity_task=(type_code == "opp"),
                    priority_weight=t.get("priority_weight", wtype.priority_weight),
                    customer_ids=t.get("customer_ids", [t.get("cust_id", 0)]),
                    customer_names=t.get("customer_names", [t.get("cust_name", "")]),
                    deadline_date=deadline,
                    pinned_date=pinned,
                    contact_prefer=t.get("contact_prefer", "不限定"),
                )

            result.append(st)
        return result

    def _map_type_to_code(self, type_name: str) -> str:
        """将中文类型名映射为 type_code"""
        mapping = {
            "产品到期": "due",
            "大额异动": "big_move",
            "贷款逾期": "overdue",
            "商机待办": "opp",
            "生日提醒": "birthday",
            "联络超期": "contact_lapse",
            "信用卡待办": "credit_card",
            "面谈后跟进": "post_meeting",
            "洞察预警": "insight_alert",
            "报告编写": "report",
            "参加会议": "meeting",
            "早会": "morning_meeting",
            "晚会": "evening_meeting",
            "报告评审": "report_review",
        }
        return mapping.get(type_name, "unknown")

    # ================================================================
    # 固定工作待办注入
    # ================================================================

    def _inject_fixed_work_tasks(
        self, tasks: list[ScheduleTask], schedule_date: str
    ) -> list[ScheduleTask]:
        """为每日注入早会、晚会等固定工作待办"""
        result = list(tasks)
        for ft in FIXED_WORK_TASKS:
            wtype = WORK_TYPE_CATALOG.get(ft["type_code"])
            if not wtype:
                continue
            st = ScheduleTask(
                task_id=f"TK_{ft['type_code'].upper()}_{schedule_date}",
                type_code=ft["type_code"],
                type_name=wtype.type_name,
                cust_id=0,
                cust_name="",
                summary=wtype.type_name,
                cust_count=1,
                estimated_duration_min=wtype.per_customer_minutes,
                contact_methods=[],
                is_customer_facing=False,
                is_opportunity_task=False,
                assigned_slot=ft.get("assigned_slot", ""),
                priority_weight=wtype.priority_weight,
                deadline_date=schedule_date,
                pinned_date=schedule_date,
            )
            result.append(st)
        return result

    # ================================================================
    # 三卡片分组
    # ================================================================

    def _group_into_cards(
        self, tasks: list[ScheduleTask]
    ) -> dict[str, list[ScheduleTask]]:
        """将任务按三卡片类型分组"""
        grouped: dict[str, list[ScheduleTask]] = {
            "customer": [],
            "opportunity": [],
            "work": [],
        }
        for t in tasks:
            card_type = CARD_GROUP_MAP.get(t.type_code, "customer")
            if card_type in grouped:
                grouped[card_type].append(t)
            else:
                grouped["customer"].append(t)
        return grouped

    # ================================================================
    # 容量截断 + 溢出推迟
    # ================================================================

    def _apply_card_capacity(
        self, grouped: dict[str, list[ScheduleTask]], schedule_date: str
    ) -> tuple[list[ScheduleCard], list[ScheduleTask]]:
        """
        按卡片容量上限截断，溢出任务标记为 deferred。

        规则：
        - customer ≤ 10
        - opportunity ≤ 4
        - work: 早会(上午固定) + 晚会(下午固定) + 其他 ≤ 2
        - opportunity + work ≤ 6
        """
        deferred: list[ScheduleTask] = []

        # 1. 处理工作待办：分离固定(早晚会)和可选
        work_tasks = grouped.get("work", [])
        fixed_work = [t for t in work_tasks
                      if t.type_code in ("morning_meeting", "evening_meeting")]
        optional_work = [t for t in work_tasks
                         if t.type_code not in ("morning_meeting", "evening_meeting")]

        # 可选工作 ≤ 2
        optional_work.sort(key=lambda t: -t.priority_weight)
        kept_optional = optional_work[:2]
        deferred.extend(optional_work[2:])

        kept_work = fixed_work + kept_optional

        # 2. 处理客户待办：≤ 10
        cust_tasks = grouped.get("customer", [])
        cust_tasks.sort(key=lambda t: -t.priority_weight)
        kept_cust = cust_tasks[:CARD_CAPACITY["customer"]]
        deferred.extend(cust_tasks[CARD_CAPACITY["customer"]:])

        # 3. 处理商机待办：≤ 4
        opp_tasks = grouped.get("opportunity", [])
        opp_tasks.sort(key=lambda t: -t.priority_weight)
        kept_opp = opp_tasks[:CARD_CAPACITY["opportunity"]]
        deferred.extend(opp_tasks[CARD_CAPACITY["opportunity"]:])

        # 4. 跨卡片约束：opportunity + work ≤ 6
        if len(kept_opp) + len(kept_work) > MAX_OPP_PLUS_WORK:
            # 从 work 的非固定任务中移除
            excess = (len(kept_opp) + len(kept_work)) - MAX_OPP_PLUS_WORK
            removable = [t for t in kept_work
                         if t.type_code not in ("morning_meeting", "evening_meeting")]
            # 从低权重开始移除
            removable.sort(key=lambda t: t.priority_weight)
            to_defer = removable[:excess]
            for t in to_defer:
                kept_work.remove(t)
                deferred.append(t)

        # 5. 构建三卡片
        cards = [
            ScheduleCard(
                card_type="customer",
                card_name=CARD_NAMES["customer"],
                morning=[],
                afternoon=[],
            ),
            ScheduleCard(
                card_type="opportunity",
                card_name=CARD_NAMES["opportunity"],
                morning=[],
                afternoon=[],
            ),
            ScheduleCard(
                card_type="work",
                card_name=CARD_NAMES["work"],
                morning=[],
                afternoon=[],
            ),
        ]

        # 将 kept 任务分配到卡片中（此处只创建卡片，时段在 _allocate_slots 中分配）
        # 实际上 _allocate_slots 在 _group_into_cards 之后调用，所以这里返回的是
        # 容量内的任务列表，外面会再次调用 _allocate_slots 分配时段
        # 这里直接构建带时段的卡片
        kept_all = {
            "customer": kept_cust,
            "opportunity": kept_opp,
            "work": kept_work,
        }

        # 对每组重新分配时段
        for card in cards:
            ct = card.card_type
            slot_result = self._allocate_slots(kept_all.get(ct, []))
            card.morning = slot_result["morning"]
            card.afternoon = slot_result["afternoon"]

            # 客户待办卡片：上下午分时容量约束（上午 ≤ 5，下午 ≤ 5）
            if ct == "customer":
                for slot_name, slot_max in [("morning", CUSTOMER_MORNING_MAX),
                                            ("afternoon", CUSTOMER_AFTERNOON_MAX)]:
                    slot_tasks = card.morning if slot_name == "morning" else card.afternoon
                    if len(slot_tasks) > slot_max:
                        slot_tasks.sort(key=lambda t: -t.priority_weight)
                        overflow = slot_tasks[slot_max:]
                        if slot_name == "morning":
                            card.morning = slot_tasks[:slot_max]
                        else:
                            card.afternoon = slot_tasks[:slot_max]
                        # 溢出任务放回待办池，重置时段
                        for t in overflow:
                            t.assigned_slot = ""
                        deferred.extend(overflow)

        # 设置溢出任务的 pinned_date 为次日
        next_date = (date.fromisoformat(schedule_date) + timedelta(days=1)).isoformat()
        for t in deferred:
            t.pinned_date = next_date

        return cards, deferred

    def _allocate_slots(
        self, tasks: list[ScheduleTask]
    ) -> dict:
        """
        将任务分配到上午/下午时段。
        仅分上下午，不精确到小时；结合工作类型推荐时段和客户联系偏好。

        Returns:
            {"morning": [...], "afternoon": [...]}
        """
        morning = []
        afternoon = []
        cust_prefer_slot = {}  # cust_id -> "morning" / "afternoon"

        for t in tasks:
            wtype = WORK_TYPE_CATALOG.get(t.type_code)
            if not wtype:
                t.assigned_slot = "afternoon"
                afternoon.append(t)
                continue

            slots = list(wtype.recommended_slots)
            cp = t.contact_prefer

            # 客户偏好加权
            if cp == "上午优先" and "morning" not in slots:
                slots = ["morning"] + slots
            elif cp == "下午优先" and "afternoon" not in slots:
                slots = ["afternoon"] + slots

            # 同客户多任务统一到偏好时段
            if t.cust_id in cust_prefer_slot:
                prefer = cust_prefer_slot[t.cust_id]
                if prefer in slots:
                    slots = [prefer] + [s for s in slots if s != prefer]

            if "morning" in slots and "afternoon" in slots:
                if cp == "上午优先":
                    t.assigned_slot = "morning"
                    morning.append(t)
                    cust_prefer_slot[t.cust_id] = "morning"
                elif cp == "下午优先":
                    t.assigned_slot = "afternoon"
                    afternoon.append(t)
                    cust_prefer_slot[t.cust_id] = "afternoon"
                else:
                    t.assigned_slot = "morning"
                    morning.append(t)
            elif "morning" in slots:
                t.assigned_slot = "morning"
                morning.append(t)
                cust_prefer_slot[t.cust_id] = "morning"
            else:
                t.assigned_slot = "afternoon"
                afternoon.append(t)
                cust_prefer_slot[t.cust_id] = "afternoon"

        return {"morning": morning, "afternoon": afternoon}

    def _optimize_sequence(self, tasks: list[ScheduleTask]) -> list[ScheduleTask]:
        """优化任务排序 — 同类型相邻、短任务优先"""
        if len(tasks) <= 1:
            return tasks

        # 按 priority_weight 降序，同优先级按耗时升序（短任务优先）
        tasks.sort(key=lambda t: (-t.priority_weight, t.estimated_duration_min))

        for i, t in enumerate(tasks):
            t.order_in_slot = i + 1

        return tasks

    # ================================================================
    # 7 日周计划生成（核心）
    # ================================================================

    def generate_weekly_plan(
        self,
        tasks: list[dict],
        manager_id: str = "",
        start_date: str = None,
    ) -> WeeklyPlan:
        """
        生成 7 日周计划 — 贪心分配算法

        Args:
            tasks: 待办列表（含 deadline_date, priority_weight 等）
            manager_id: 客户经理 ID
            start_date: 周起始日期，默认今天

        Returns:
            WeeklyPlan 包含 7 个 DailySchedule + overflow_tasks
        """
        sd = start_date or date.today().isoformat()
        sd_date = date.fromisoformat(sd)

        # Step 1: 分类并计算有效权重
        schedule_tasks = self._classify_tasks(tasks)
        for t in schedule_tasks:
            if t.deadline_date:
                try:
                    dl_date = date.fromisoformat(t.deadline_date)
                    days_until = (dl_date - sd_date).days
                    urgency_boost = max(0, 7 - days_until) * 10
                except ValueError:
                    urgency_boost = 0
            else:
                urgency_boost = 0
            t.effective_weight = t.priority_weight + urgency_boost

        # Step 2: 按有效权重降序排列
        schedule_tasks.sort(key=lambda t: (-t.effective_weight, t.estimated_duration_min))

        # Step 3: 逐日填充
        days = []
        remaining = list(schedule_tasks)  # 待分配队列（可变）

        for day_offset in range(7):
            day_date = (sd_date + timedelta(days=day_offset)).isoformat()
            day_capacity = 480  # 每天总容量

            # 收集该天的任务：pinned → due → flexible
            day_tasks = []
            day_cust_ids = set()

            # 3a. 固定日期任务（pinned）
            pinned = []
            still_remaining = []
            for t in remaining:
                if t.pinned_date and t.pinned_date == day_date:
                    pinned.append(t)
                else:
                    still_remaining.append(t)
            remaining = still_remaining

            # 3b. 到期任务（deadline <= day_date）
            due_today = []
            still_remaining = []
            for t in remaining:
                if t.deadline_date:
                    try:
                        if date.fromisoformat(t.deadline_date) <= date.fromisoformat(day_date):
                            due_today.append(t)
                            continue
                    except ValueError:
                        pass
                still_remaining.append(t)
            remaining = still_remaining

            # 按有效权重排序
            pinned.sort(key=lambda t: -t.effective_weight)
            due_today.sort(key=lambda t: -t.effective_weight)

            # 3c. 灵活任务
            flexible = []
            still_remaining = []
            for t in remaining:
                if not t.pinned_date:
                    flexible.append(t)
                else:
                    still_remaining.append(t)
            remaining = still_remaining
            flexible.sort(key=lambda t: -t.effective_weight)

            # 3d. 填充：pinned → due → flexible（贪心：跳过超容量任务，继续尝试更小的）
            assigned = set()
            for t in pinned + due_today + flexible:
                if id(t) in assigned:
                    continue
                if day_capacity >= t.estimated_duration_min:
                    day_tasks.append(t)
                    day_capacity -= t.estimated_duration_min
                    day_cust_ids.add(t.cust_id)
                    assigned.add(id(t))
                # 容量不足则跳过当前任务，继续尝试后续更小的任务

            # 将未分配的任务放回 remaining（含其他天的 pinned 任务）
            unassigned = [t for t in pinned + due_today + flexible if id(t) not in assigned]
            remaining = unassigned + remaining

            # 3e. 生成日排程
            daily = self.generate_daily_schedule(
                [{"task_id": t.task_id, "type": t.type_name, "type_code": t.type_code,
                  "cust_id": t.cust_id, "cust_name": t.cust_name,
                  "summary": t.summary, "cust_count": t.cust_count,
                  "priority_weight": t.priority_weight,
                  "deadline_date": t.deadline_date, "pinned_date": t.pinned_date,
                  "customer_ids": t.customer_ids, "customer_names": t.customer_names}
                 for t in day_tasks],
                manager_id=manager_id,
                schedule_date=day_date,
            )
            days.append(daily)

        # Step 4: 溢出任务
        overflow = remaining

        # Step 5: 汇总统计
        total_tasks = sum(d.total_tasks for d in days)
        total_mins = sum(d.total_minutes for d in days)

        return WeeklyPlan(
            start_date=sd,
            manager_id=manager_id,
            days=days,
            overflow_tasks=overflow,
            total_tasks=total_tasks,
            total_minutes=total_mins,
            generated_at=datetime.now().isoformat(),
            version=0,
            source="rule",
        )

    # ================================================================
    # LLM 微调排程（按需，语义理解）
    # ================================================================

    async def ai_refine_schedule(
        self, ctx: AgentContext, base_schedule: DailySchedule
    ) -> DailySchedule:
        """
        LLM 微调日程 — 基于客户画像做智能调整

        Args:
            ctx: 执行上下文
            base_schedule: 规则引擎产出的基准日程

        Returns:
            调整后的 DailySchedule
        """
        log.info(f"ai_refine_schedule: date={base_schedule.date}")

        # 收集所有任务涉及的客户 ID（从三卡片中收集）
        all_tasks = []
        for card in base_schedule.cards:
            all_tasks.extend(card.morning)
            all_tasks.extend(card.afternoon)
        cust_ids = set()
        for t in all_tasks:
            cust_ids.update(t.customer_ids)

        # 获取客户画像摘要
        customer_summaries = []
        for cid in list(cust_ids)[:20]:  # 最多 20 人
            full = query_customer_full(cid)
            if full:
                cust = full.get("customer", {})
                customer_summaries.append({
                    "id": cid,
                    "name": cust.get("name", ""),
                    "tier": cust.get("tier", ""),
                    "aum": f"{float(cust.get('total_aum',0) or 0)/10000:.1f}万",
                    "contact_preference": cust.get("contact_prefer", "不限定"),
                })

        # 构建 user prompt
        user_prompt = self._build_refine_prompt(base_schedule, customer_summaries)

        # 调用 LLM
        try:
            resp = self.adapter.analyze_json(
                system_prompt=self.system_prompt_text,
                user_prompt=user_prompt,
                temperature=0.3,
            )
            result = resp["result"]
            adjusted = self._parse_refine_result(result, base_schedule)
            return adjusted
        except Exception as e:
            log.warning(f"LLM refine failed, using rule-based schedule: {e}")
            return base_schedule

    def _build_refine_prompt(
        self, schedule: DailySchedule, customer_summaries: list[dict]
    ) -> str:
        """构建 LLM 微调的 user prompt（三卡片结构）"""
        tasks_json = []
        for card in schedule.cards:
            for t in card.morning + card.afternoon:
                tasks_json.append({
                    "task_id": t.task_id,
                    "type": t.type_name,
                    "card_type": card.card_type,
                    "cust_name": t.cust_name,
                    "cust_count": t.cust_count,
                    "duration_min": t.estimated_duration_min,
                    "assigned_slot": t.assigned_slot,
                    "priority_weight": t.priority_weight,
                })

        return f"""请审阅以下客户经理{schedule.date}的日程排程，判断是否需要调整。

**当前日期**：{schedule.date}
**生成来源**：规则引擎自动排程
**卡片结构**：客户待办、商机待办、工作待办（仅分上下午，不精确到小时）
**总计**：{schedule.total_minutes} 分钟

**当前排程**：
```json
{json.dumps(tasks_json, ensure_ascii=False, indent=2)}
```

**相关客户画像**：
```json
{json.dumps(customer_summaries, ensure_ascii=False, indent=2)}
```

**调整建议方向**（仅当有明确依据时才调整）：
1. 同一客户有多个待办时，合并到同一时段处理
2. 高 AUM 客户的待办可适度提前
3. 商机待办优先安排在客户方便的时间
4. 长任务（≥60min）尽量不连续排布

请输出调整后的排程（JSON 格式），如果不需要调整，返回空 changes 数组。
输出格式：
{{
  "has_changes": true/false,
  "changes": [
    {{"task_id": "TK_xxx", "action": "move_to_slot", "new_slot": "morning", "reason": "..."}},
    {{"task_id": "TK_xxx", "action": "reorder", "new_order": 2, "reason": "..."}}
  ]
}}"""

    def _parse_refine_result(
        self, result: dict, base_schedule: DailySchedule
    ) -> DailySchedule:
        """解析 LLM 微调结果，应用到基准日程（三卡片结构）"""
        if not result.get("has_changes") or not result.get("changes"):
            return base_schedule

        # 深拷贝基准日程
        import copy
        adjusted = copy.deepcopy(base_schedule)
        adjusted.source = "llm_refined"
        adjusted.version = base_schedule.version + 1

        # 建立 task_id → (task, card) 映射
        task_map = {}
        for card in adjusted.cards:
            for t in card.morning:
                task_map[t.task_id] = (t, card, "morning")
            for t in card.afternoon:
                task_map[t.task_id] = (t, card, "afternoon")

        changes = result.get("changes", [])
        for ch in changes:
            tid = ch.get("task_id", "")
            action = ch.get("action", "")
            entry = task_map.get(tid)
            if not entry:
                continue

            task, card, current_slot = entry

            if action == "move_to_slot":
                new_slot = ch.get("new_slot", "")
                task.assigned_slot = new_slot
                if new_slot == "morning" and current_slot == "afternoon":
                    card.afternoon.remove(task)
                    card.morning.append(task)
                elif new_slot == "afternoon" and current_slot == "morning":
                    card.morning.remove(task)
                    card.afternoon.append(task)
                # 更新映射中的 slot 引用
                task_map[tid] = (task, card, new_slot)

            elif action == "reorder":
                new_order = ch.get("new_order", 0)
                task.order_in_slot = new_order

        # 重新排序每张卡片
        for card in adjusted.cards:
            card.morning.sort(key=lambda t: t.order_in_slot)
            card.afternoon.sort(key=lambda t: t.order_in_slot)
            for i, t in enumerate(card.morning):
                t.order_in_slot = i + 1
            for i, t in enumerate(card.afternoon):
                t.order_in_slot = i + 1

        log.info(f"LLM refined: {len(changes)} changes applied")
        return adjusted

    # ================================================================
    # 完成标记 & 手动添加
    # ================================================================

    def mark_task_complete(
        self, schedule: DailySchedule, task_id: str
    ) -> bool:
        """
        标记任务为已完成。完成后不计入卡片 total_count。

        Returns:
            True 如果找到并标记了任务，False 如果未找到
        """
        for card in schedule.cards:
            for t in card.morning + card.afternoon:
                if t.task_id == task_id:
                    t.status = "completed"
                    log.info(f"Task completed: {task_id} in card {card.card_type}")
                    return True
        return False

    def add_task_to_card(
        self,
        schedule: DailySchedule,
        task_id: str,
        card_type: str,
        pending_tasks: list,
    ) -> tuple[bool, str]:
        """
        从 pending 池手动将待办添加到指定卡片。

        Args:
            schedule: 当前日排程
            task_id: 待添加的任务 ID
            card_type: 目标卡片类型
            pending_tasks: 未安排待办列表

        Returns:
            (success, message)
        """
        # 1. 在 pending 池中查找任务
        target_task = None
        for t in pending_tasks:
            if t.task_id == task_id:
                target_task = t
                break
        if not target_task:
            return False, f"任务 {task_id} 不在未安排待办列表中"

        # 2. 查找目标卡片
        target_card = None
        for card in schedule.cards:
            if card.card_type == card_type:
                target_card = card
                break
        if not target_card:
            return False, f"未找到卡片类型: {card_type}"

        # 3. 容量校验（不含已完成的）
        if target_card.total_count >= target_card.max_capacity:
            return False, f"{target_card.card_name}已达上限({target_card.max_capacity})，无法添加"

        # 3b. 客户待办卡片：上下午分时上限校验
        if card_type == "customer":
            # 如果待办没有预设时段，自动选择有容量的时段
            if not target_task.assigned_slot:
                morning_used = sum(1 for t in target_card.morning
                                   if getattr(t, 'status', 'pending') != 'completed')
                afternoon_used = sum(1 for t in target_card.afternoon
                                     if getattr(t, 'status', 'pending') != 'completed')
                if morning_used < CUSTOMER_MORNING_MAX:
                    target_task.assigned_slot = "morning"
                elif afternoon_used < CUSTOMER_AFTERNOON_MAX:
                    target_task.assigned_slot = "afternoon"
                else:
                    return False, f"{target_card.card_name}上下午均已满({CUSTOMER_MORNING_MAX}/{CUSTOMER_AFTERNOON_MAX})，无法添加"

            target_slot = target_task.assigned_slot
            slot_tasks = target_card.morning if target_slot == "morning" else target_card.afternoon
            slot_max = CUSTOMER_MORNING_MAX if target_slot == "morning" else CUSTOMER_AFTERNOON_MAX
            slot_label = "上午" if target_slot == "morning" else "下午"
            if len(slot_tasks) >= slot_max:
                return False, f"{target_card.card_name}{slot_label}已达上限({slot_max})，无法添加"

        # 4. 跨卡片约束校验
        if card_type in ("opportunity", "work"):
            opp_card = next((c for c in schedule.cards if c.card_type == "opportunity"), None)
            work_card = next((c for c in schedule.cards if c.card_type == "work"), None)
            opp_count = opp_card.total_count if opp_card else 0
            work_count = work_card.total_count if work_card else 0
            if opp_count + work_count + 1 > MAX_OPP_PLUS_WORK:
                return False, f"商机待办+工作待办已达上限({MAX_OPP_PLUS_WORK})，无法添加"

        # 5. 添加到卡片
        target_task.status = "pending"
        if target_task.assigned_slot == "morning":
            target_card.morning.append(target_task)
        else:
            target_card.afternoon.append(target_task)

        # 6. 从 pending 池移除
        pending_tasks[:] = [t for t in pending_tasks if t.task_id != task_id]

        return True, f"已添加到{target_card.card_name}"

    def process_customer_task(
        self,
        schedule: DailySchedule,
        task_id: str,
        cust_id: int,
        cust_name: str,
        action: str,
        db,
    ) -> bool:
        """
        记录单个客户的处理方式（电话/微信），写入 processing_records 表。
        不修改 schedule 状态——由前端在所有客户处理完后调用 complete 接口。

        Args:
            action: '电话联系' | '微信联系' | '跳过'

        Returns:
            True 如果记录成功
        """
        # 查找任务所属卡片
        card_type = ""
        task = None
        for card in schedule.cards:
            for t in card.morning + card.afternoon:
                if t.task_id == task_id:
                    card_type = card.card_type
                    task = t
                    break
            if card_type:
                break

        if not task:
            log.warning(f"process_customer_task: 未找到任务 {task_id}")
            return False

        cur = db.cursor()
        now = datetime.now().isoformat()
        cur.execute(
            """INSERT INTO processing_records
               (task_type, cust_id, cust_name, action, notes, processed_at, card_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (task.type_code, cust_id, cust_name, action, "", now, card_type),
        )
        db.commit()
        log.info(f"Customer processed: {cust_name}({cust_id}) via {action} for task {task_id}")
        return True

    def return_task_to_pool(
        self, schedule: DailySchedule, task_id: str
    ) -> bool:
        """
        将日程卡片上的任务放回待办池（deferred_tasks）。

        Returns:
            True 如果找到并移除成功，False 如果未找到
        """
        for card in schedule.cards:
            for t in card.morning:
                if t.task_id == task_id:
                    t.status = "pending"
                    schedule.deferred_tasks.append(t)
                    card.morning.remove(t)
                    log.info(f"Task returned to pool: {task_id} from card {card.card_type}")
                    return True
            for t in card.afternoon:
                if t.task_id == task_id:
                    t.status = "pending"
                    schedule.deferred_tasks.append(t)
                    card.afternoon.remove(t)
                    log.info(f"Task returned to pool: {task_id} from card {card.card_type}")
                    return True
        return False

    # ================================================================
    # 日程持久化
    # ================================================================

    def save_schedule(self, schedule: DailySchedule, db) -> bool:
        """将日排程保存到数据库（三卡片结构）"""
        cur = db.cursor()
        now = datetime.now().isoformat()

        # 序列化三卡片
        cards_json = json.dumps([c.to_dict() for c in schedule.cards], ensure_ascii=False)
        deferred_json = json.dumps(
            [t.to_dict() for t in schedule.deferred_tasks], ensure_ascii=False
        )

        # 使用 UPSERT 语义：同一天同一个经理只有一份排程
        cur.execute(
            """INSERT OR REPLACE INTO daily_schedules
               (schedule_date, manager_id, morning_json, afternoon_json,
                total_minutes, generated_at, version, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                schedule.date,
                schedule.manager_id,
                cards_json,
                deferred_json,
                schedule.total_minutes,
                now,
                schedule.version,
                schedule.source,
            ),
        )
        db.commit()
        log.info(f"Schedule saved: {schedule.date} ({schedule.total_minutes}min, {schedule.total_tasks} tasks)")
        return True

    def load_schedule(self, manager_id: str, schedule_date: str, db) -> Optional[DailySchedule]:
        """从数据库加载日排程（三卡片结构）"""
        cur = db.cursor()
        row = cur.execute(
            """SELECT * FROM daily_schedules
               WHERE schedule_date = ? AND manager_id = ?""",
            (schedule_date, manager_id),
        ).fetchone()

        if not row:
            return None

        cards_json = row["morning_json"] or "[]"
        deferred_json = row["afternoon_json"] or "[]"

        is_legacy = False  # 标记是否为旧格式（任务数组而非卡片数组）

        # 解析卡片
        try:
            cards_data = json.loads(cards_json)
            # 检测新旧格式：新格式卡片有 card_type，旧格式任务有 task_id 无 card_type
            if cards_data and isinstance(cards_data, list) and "card_type" not in cards_data[0] and "task_id" in cards_data[0]:
                is_legacy = True
                cards = self._parse_legacy_schedule(cards_json, deferred_json)
            else:
                cards = []
                for cd in cards_data:
                    card = ScheduleCard(
                        card_type=cd.get("card_type", "customer"),
                        card_name=cd.get("card_name", ""),
                        morning=self._parse_tasks_from_list(cd.get("morning", [])),
                        afternoon=self._parse_tasks_from_list(cd.get("afternoon", [])),
                    )
                    cards.append(card)
        except (json.JSONDecodeError, KeyError):
            # JSON 解析失败：兼容旧格式
            is_legacy = True
            cards = self._parse_legacy_schedule(cards_json, deferred_json)

        # 解析溢出任务（旧格式无溢出概念，跳过）
        if is_legacy:
            deferred_tasks = []
        else:
            try:
                deferred_raw = json.loads(deferred_json)
                deferred_tasks = self._parse_tasks_from_list(deferred_raw) if isinstance(deferred_raw, list) else []
            except (json.JSONDecodeError, TypeError):
                deferred_tasks = []

        return DailySchedule(
            date=row["schedule_date"],
            manager_id=row["manager_id"],
            cards=cards,
            deferred_tasks=deferred_tasks,
            generated_at=row["generated_at"],
            version=row["version"] if "version" in row.keys() else 0,
            source=row["source"] if "source" in row.keys() else "rule",
        )

    def _parse_legacy_schedule(
        self, morning_json: str, afternoon_json: str
    ) -> list[ScheduleCard]:
        """兼容旧格式：将旧版 morning/afternoon 任务数组转为三卡片"""
        morning_tasks = self._parse_tasks_from_json(morning_json)
        afternoon_tasks = self._parse_tasks_from_json(afternoon_json)
        all_tasks = morning_tasks + afternoon_tasks

        # 按类型分组
        grouped: dict[str, list] = {"customer": [], "opportunity": [], "work": []}
        for t in all_tasks:
            ct = CARD_GROUP_MAP.get(t.type_code, "customer")
            if ct in grouped:
                grouped[ct].append(t)
            else:
                grouped["customer"].append(t)

        cards = []
        for ct in ["customer", "opportunity", "work"]:
            tasks = grouped[ct]
            morning = [t for t in tasks if t.assigned_slot == "morning"]
            afternoon = [t for t in tasks if t.assigned_slot == "afternoon"]

            # 工作待办卡片：补充固定早会/晚会（旧格式无这些任务）
            if ct == "work":
                from datetime import date as dt_date
                sd = dt_date.today().isoformat()
                fixed = self._inject_fixed_work_tasks([], sd)
                for ft in fixed:
                    if ft.assigned_slot == "morning":
                        morning.append(ft)
                    else:
                        afternoon.append(ft)

            cards.append(ScheduleCard(
                card_type=ct,
                card_name=CARD_NAMES[ct],
                morning=morning,
                afternoon=afternoon,
            ))
        return cards

    def _parse_tasks_from_list(self, raw: list) -> list[ScheduleTask]:
        """从 dict 列表解析任务"""
        tasks = []
        for t in raw:
            st = ScheduleTask(
                task_id=t.get("task_id", ""),
                type_code=t.get("type_code", ""),
                type_name=t.get("type_name", ""),
                cust_id=t.get("cust_id", 0),
                cust_name=t.get("cust_name", ""),
                summary=t.get("summary", ""),
                cust_count=t.get("cust_count", 1),
                estimated_duration_min=t.get("estimated_duration_min", 0),
                contact_methods=t.get("contact_methods", []),
                is_customer_facing=t.get("is_customer_facing", True),
                is_opportunity_task=t.get("is_opportunity_task", False),
                assigned_slot=t.get("assigned_slot", ""),
                order_in_slot=t.get("order_in_slot", 0),
                priority_weight=t.get("priority_weight", 30),
                customer_ids=t.get("customer_ids", []),
                customer_names=t.get("customer_names", []),
                status=t.get("status", "pending"),
                deadline_date=t.get("deadline_date", ""),
                pinned_date=t.get("pinned_date", ""),
                contact_prefer=t.get("contact_prefer", "不限定"),
            )
            tasks.append(st)
        return tasks

    def _parse_tasks_from_json(self, json_str: str) -> list[ScheduleTask]:
        """从 JSON 字符串解析任务列表"""
        if not json_str:
            return []
        try:
            raw = json.loads(json_str)
            tasks = []
            for t in raw:
                st = ScheduleTask(
                    task_id=t.get("task_id", ""),
                    type_code=t.get("type_code", ""),
                    type_name=t.get("type_name", ""),
                    cust_id=t.get("cust_id", 0),
                    cust_name=t.get("cust_name", ""),
                    summary=t.get("summary", ""),
                    cust_count=t.get("cust_count", 1),
                    estimated_duration_min=t.get("estimated_duration_min", 0),
                    contact_methods=t.get("contact_methods", []),
                    is_customer_facing=t.get("is_customer_facing", True),
                    is_opportunity_task=t.get("is_opportunity_task", False),
                    assigned_slot=t.get("assigned_slot", ""),
                    order_in_slot=t.get("order_in_slot", 0),
                    priority_weight=t.get("priority_weight", 30),
                    customer_ids=t.get("customer_ids", []),
                    customer_names=t.get("customer_names", []),
                    status=t.get("status", "pending"),
                    deadline_date=t.get("deadline_date", ""),
                    pinned_date=t.get("pinned_date", ""),
                    contact_prefer=t.get("contact_prefer", "不限定"),
                )
                tasks.append(st)
            return tasks
        except Exception as e:
            log.warning(f"Failed to parse tasks JSON: {e}")
            return []

    # ================================================================
    # 日历事件标记
    # ================================================================

    def get_month_events(
        self, manager_id: str, year: int, month: int, db
    ) -> dict[int, list[str]]:
        """
        获取指定月份的日历事件标记

        Returns:
            {day: ["normal", "opp", "report", "meeting"]}
        """
        cur = db.cursor()
        month_start = f"{year}-{month:02d}-01"
        if month == 12:
            month_end = f"{year+1}-01-01"
        else:
            month_end = f"{year}-{month+1:02d}-01"

        rows = cur.execute(
            """SELECT schedule_date, morning_json, afternoon_json
               FROM daily_schedules
               WHERE manager_id = ? AND schedule_date >= ? AND schedule_date < ?""",
            (manager_id, month_start, month_end),
        ).fetchall()

        events = {}
        for row in rows:
            day = int(row["schedule_date"].split("-")[2])
            day_events = []

            # 解析任务类型（兼容新旧格式）
            try:
                cards_raw = json.loads(row["morning_json"] or "[]")
                if isinstance(cards_raw, list) and len(cards_raw) > 0:
                    # 新格式：cards_json
                    if isinstance(cards_raw[0], dict) and "card_type" in cards_raw[0]:
                        all_tasks = []
                        for cd in cards_raw:
                            all_tasks.extend(cd.get("morning", []))
                            all_tasks.extend(cd.get("afternoon", []))
                    else:
                        # 旧格式：直接任务数组
                        all_tasks = cards_raw
                else:
                    all_tasks = []

                has_opp = any(t.get("type_code") == "opp" or t.get("card_type") == "opportunity" for t in all_tasks)
                has_work = any(t.get("type_code") in ("report", "report_review", "morning_meeting", "evening_meeting")
                              or t.get("card_type") == "work" for t in all_tasks)

                if has_opp:
                    day_events.append("opp")
                if has_work:
                    day_events.append("report")
                if not day_events:
                    day_events.append("normal")
            except (json.JSONDecodeError, KeyError, TypeError):
                day_events.append("normal")

            events[day] = day_events

        return events


# ============================================================
# 便捷函数
# ============================================================

def create_scheduler_agent() -> SchedulerAgent:
    """创建日程排程 Agent 实例（注册到全局 harness）"""
    from ..harness import harness as h
    agent = SchedulerAgent()
    h.registry.register(SchedulerAgent.meta, agent)
    return agent
