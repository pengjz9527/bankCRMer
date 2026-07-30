"""
AgentOS — 易会办 AI 智能体运行时
轻量级 Agent 框架，支持声明式注册、技能共享、批量编排
"""

from .model_adapter import ModelAdapter, ModelConfig
from .harness import Harness, Agent, AgentRegistry, SkillExecutor, AgentContext, agent, skill, get_harness

__version__ = "0.1.0"
