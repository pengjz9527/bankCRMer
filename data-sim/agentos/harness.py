"""
Agent Harness — AgentOS 运行时框架
Agent 注册 · 技能调度 · 生命周期 · 上下文管理
"""

import os
import json
import time
import logging
import asyncio
from datetime import datetime
from typing import Any, Callable, Optional
from dataclasses import dataclass, field
from pathlib import Path

from .model_adapter import ModelAdapter, ModelConfig, get_adapter

log = logging.getLogger("agentos.harness")

# Prompt 文件基础路径
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


# ============================================================
# AgentContext — 执行上下文
# ============================================================

@dataclass
class AgentContext:
    """Agent 执行上下文，携带请求元信息"""
    manager_id: str = ""
    branch: str = ""
    scope: str = "scheduled"          # scheduled | on_demand
    request_id: str = ""
    extra: dict = field(default_factory=dict)

    def override(self, **kwargs) -> "AgentContext":
        """创建派生上下文（用于并行子任务）"""
        new = AgentContext(
            manager_id=kwargs.get("manager_id", self.manager_id),
            branch=kwargs.get("branch", self.branch),
            scope=kwargs.get("scope", self.scope),
            request_id=self.request_id,
            extra={**self.extra, **kwargs.get("extra", {})},
        )
        return new


# ============================================================
# AgentRegistry — Agent 注册中心
# ============================================================

@dataclass
class AgentMeta:
    """Agent 元数据"""
    name: str
    role: str
    description: str
    agent_class: type
    skills: list[str] = field(default_factory=list)
    model_name: str = "deepseek-chat"
    triggers: list[str] = field(default_factory=list)   # scheduled, on_demand
    rate_limit: int = 100
    timeout: int = 600


class AgentRegistry:
    """Agent 注册中心，维护所有已注册 Agent 的元数据"""

    def __init__(self):
        self._agents: dict[str, AgentMeta] = {}
        self._instances: dict[str, Any] = {}

    def register(self, meta: AgentMeta, instance: Any = None):
        self._agents[meta.role] = meta
        if instance:
            self._instances[meta.role] = instance
        log.info(f"Agent registered: {meta.name} (role={meta.role})")

    def get_meta(self, role: str) -> Optional[AgentMeta]:
        return self._agents.get(role)

    def get_instance(self, role: str) -> Optional[Any]:
        return self._instances.get(role)

    def list_agents(self) -> list[dict]:
        return [
            {"role": m.role, "name": m.name, "triggers": m.triggers, "skills": m.skills}
            for m in self._agents.values()
        ]


# ============================================================
# SkillExecutor — 技能调度器
# ============================================================

class SkillExecutor:
    """技能调度器，安全执行预注册函数，带限流/日志"""

    def __init__(self):
        self._skills: dict[str, Callable] = {}
        self._call_counts: dict[str, list[float]] = {}  # 用于限流

    def register(self, name: str, func: Callable):
        self._skills[name] = func
        log.debug(f"Skill registered: {name}")

    async def execute(self, name: str, *args, **kwargs) -> Any:
        """执行技能（同步函数包装为异步）"""
        if name not in self._skills:
            raise ValueError(f"Skill not found: {name}")

        # 限流检查（简单滑动窗口）
        now = time.time()
        if name not in self._call_counts:
            self._call_counts[name] = []
        self._call_counts[name] = [t for t in self._call_counts[name] if now - t < 60]

        func = self._skills[name]
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        return result

    def list_skills(self) -> list[str]:
        return list(self._skills.keys())


# ============================================================
# Agent 基类
# ============================================================

class Agent:
    """Agent 基类，所有领域智能体继承此类"""

    meta: AgentMeta

    def __init__(self, adapter: ModelAdapter = None):
        self.adapter = adapter or get_adapter()
        self.system_prompt_text: str = ""

    def load_prompt(self, prompt_file: str):
        """从文件加载 system prompt"""
        path = PROMPTS_DIR / prompt_file
        if not path.exists():
            # 尝试相对于项目根
            alt_path = Path(__file__).parent.parent / prompt_file
            if alt_path.exists():
                path = alt_path

        if path.exists():
            self.system_prompt_text = path.read_text(encoding="utf-8")
            log.info(f"Prompt loaded: {path} ({len(self.system_prompt_text)} chars)")
        else:
            log.warning(f"Prompt file not found: {path} (searched: {path}, {alt_path if 'alt_path' in dir() else 'N/A'})")

    def chunk(self, items: list, size: int = 50) -> list[list]:
        """将列表分块"""
        return [items[i:i + size] for i in range(0, len(items), size)]


# ============================================================
# 声明式装饰器
# ============================================================

_global_registry = AgentRegistry()
_global_skills = SkillExecutor()


def agent(
    name: str,
    role: str,
    description: str = "",
    skills: list[str] = None,
    model: str = None,
    triggers: list[str] = None,
    rate_limit: int = 100,
    timeout: int = 600,
):
    """
    声明式 Agent 注册装饰器
    """
    def decorator(cls):
        meta = AgentMeta(
            name=name,
            role=role,
            description=description,
            agent_class=cls,
            skills=skills or [],
            model_name=model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            triggers=triggers or [],
            rate_limit=rate_limit,
            timeout=timeout,
        )
        cls.meta = meta
        _global_registry.register(meta)
        return cls
    return decorator


def skill(name: str = None, description: str = ""):
    """
    声明式 Skill 注册装饰器
    可用于 Agent 方法或独立函数
    """
    def decorator(func):
        skill_name = name or func.__name__
        _global_skills.register(skill_name, func)
        func._skill_name = skill_name
        return func
    return decorator


# ============================================================
# Harness 主类
# ============================================================

class Harness:
    """
    AgentOS 主入口
    统一管理 Agent 注册、技能调度、上下文传递
    """

    def __init__(self):
        self.registry = _global_registry
        self.skills = _global_skills
        self.adapter = get_adapter()
        self._db_execute = None  # 回调函数 (sql: str, params: tuple) -> None

    def set_db_callback(self, execute_fn):
        """设置数据库写回调（用于运行日志和 token 记录）"""
        self._db_execute = execute_fn

    def _log_run(self, agent_role: str, method: str, manager_id: str,
                 status: str, input_summary: str, output_summary: str,
                 error_msg: str, started_at: str, finished_at: str, duration_ms: int):
        """写运行日志到 agent_run_logs 表"""
        if not self._db_execute:
            return
        try:
            self._db_execute(
                "INSERT INTO agent_run_logs (agent_role, method, manager_id, status, "
                "input_summary, output_summary, error_msg, started_at, finished_at, duration_ms, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (agent_role, method, manager_id, status, input_summary, output_summary,
                 error_msg, started_at, finished_at, duration_ms, started_at)
            )
        except Exception as e:
            log.warning(f"Failed to write run log: {e}")

    def _log_token(self, agent_role: str, model_name: str,
                   prompt_tokens: int, completion_tokens: int, total_tokens: int):
        """写 Token 消耗记录到 agent_token_usage 表"""
        if not self._db_execute or total_tokens <= 0:
            return
        try:
            now = datetime.now().isoformat()
            self._db_execute(
                "INSERT INTO agent_token_usage (agent_role, run_log_id, model_name, "
                "prompt_tokens, completion_tokens, total_tokens, recorded_at) "
                "VALUES (?, (SELECT MAX(id) FROM agent_run_logs), ?,?,?,?,?)",
                (agent_role, model_name, prompt_tokens, completion_tokens, total_tokens, now)
            )
        except Exception as e:
            log.warning(f"Failed to write token usage: {e}")

    async def invoke(
        self,
        agent_role: str,
        method: str,
        ctx: AgentContext = None,
        **kwargs,
    ) -> Any:
        """
        调用 Agent 方法（含运行日志和 Token 记录）

        Args:
            agent_role: Agent 角色名（如 "opportunity_miner"）
            method: 方法名（如 "mine_on_demand"）
            ctx: 执行上下文
            **kwargs: 传递给方法的额外参数

        Returns:
            Agent 方法返回值
        """
        ctx = ctx or AgentContext()

        # 检查是否被暂停
        disabled = getattr(self.registry, '_disabled_roles', set())
        if agent_role in disabled:
            raise RuntimeError(f"Agent {agent_role} is paused")

        instance = self.registry.get_instance(agent_role)

        if instance is None:
            meta = self.registry.get_meta(agent_role)
            if meta is None:
                raise ValueError(f"Agent not found: {agent_role}")
            # 懒实例化
            instance = meta.agent_class(adapter=self.adapter)
            # 加载 prompt
            prompt_file = getattr(instance, "system_prompt", None)
            if prompt_file:
                instance.load_prompt(prompt_file)
            self.registry.register(meta, instance)

        func = getattr(instance, method, None)
        if func is None:
            raise ValueError(f"Method not found: {agent_role}.{method}")

        # 截取输入摘要
        input_summary = json.dumps(kwargs, ensure_ascii=False, default=str)[:500] if kwargs else ""

        log.info(f"Invoke: {agent_role}.{method} (scope={ctx.scope})")
        start = time.time()
        started_at = datetime.now().isoformat()
        manager_id = ctx.manager_id or kwargs.get("manager_id", "")

        # 写 pending 日志
        self._log_run(agent_role, method, str(manager_id), "pending",
                      input_summary, "", "", started_at, None, 0)

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(ctx, **kwargs)
            else:
                result = func(ctx, **kwargs)
            elapsed = time.time() - start
            finished_at = datetime.now().isoformat()
            duration_ms = int(elapsed * 1000)

            # 截取输出摘要
            output_summary = json.dumps(result, ensure_ascii=False, default=str)[:500]

            # 更新日志为 success
            self._log_run(agent_role, method, str(manager_id), "success",
                          input_summary, output_summary, "", started_at, finished_at, duration_ms)

            # 记录 Token 消耗
            usage = getattr(self.adapter, 'last_usage', {})
            if usage and usage.get('total_tokens', 0) > 0:
                self._log_token(agent_role, usage.get('model_name', ''),
                               usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0),
                               usage.get('total_tokens', 0))

            log.info(f"Invoke done: {agent_role}.{method} ({elapsed:.1f}s, tokens={usage.get('total_tokens', 'N/A')})")
            return result
        except Exception as e:
            elapsed = time.time() - start
            finished_at = datetime.now().isoformat()
            duration_ms = int(elapsed * 1000)
            error_msg = f"{type(e).__name__}: {str(e)}"

            # 更新日志为 error
            self._log_run(agent_role, method, str(manager_id), "error",
                          input_summary, "", error_msg[:500], started_at, finished_at, duration_ms)

            log.error(f"Invoke failed: {agent_role}.{method} ({elapsed:.1f}s): {e}")
            raise


# 全局 Harness 单例
harness = Harness()


def get_harness() -> Harness:
    return harness
