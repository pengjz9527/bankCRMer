"""
Model Adapter — 大模型适配层
统一接口，一行配置切换 DeepSeek / OpenAI / Claude / 本地模型
"""

import os
import json
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

# 加载 .env
from dotenv import load_dotenv
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)

log = logging.getLogger("agentos.model")


@dataclass
class ModelConfig:
    """模型配置，按 Agent 粒度可独立指定"""
    provider: str = "deepseek"        # deepseek | openai | anthropic
    model_name: str = "deepseek-v4-flash"  # Flash: 速度优先，适合批量结构化提取
    api_key: str = ""
    base_url: str = "https://api.deepseek.com/v1"
    temperature: float = 0.3           # 商机挖掘偏确定性，低温度
    max_tokens: int = 8192             # Flash 无推理链开销，8K 足够
    timeout: int = 180                 # 批量挖掘可能较慢

    @classmethod
    def from_env(cls, provider: str = None, model_name: str = None):
        """从环境变量创建默认配置"""
        provider = provider or os.getenv("DEFAULT_MODEL_PROVIDER", "deepseek")

        if provider == "deepseek":
            return cls(
                provider="deepseek",
                model_name=model_name or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            )
        elif provider == "openai":
            import openai
            return cls(
                provider="openai",
                model_name=model_name or os.getenv("OPENAI_MODEL", "gpt-4o"),
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url="https://api.openai.com/v1",
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

    @classmethod
    def from_db_row(cls, row: dict):
        """从数据库 model_configs 行创建配置"""
        return cls(
            provider=row.get("provider", "deepseek"),
            model_name=row.get("model_name", ""),
            api_key=row.get("api_key", ""),
            base_url=row.get("api_base", ""),
        )


class ModelAdapter:
    """
    大模型适配器，封装 OpenAI-compatible API 调用
    支持 DeepSeek / OpenAI / 任何兼容接口
    """

    def __init__(self, config: ModelConfig = None):
        self.config = config or ModelConfig.from_env()
        self._client = None
        self.last_usage: dict = {}  # 最近一次 chat() 的 token 消耗
        log.info(f"ModelAdapter init: provider={self.config.provider}, model={self.config.model_name}")

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
        return self._client

    def chat(
        self,
        messages: list[dict],
        temperature: float = None,
        max_tokens: int = None,
        response_format: dict = None,
    ) -> dict:
        """
        发送对话请求，返回 {"content": str, "usage": dict}

        Args:
            messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
            temperature: 覆盖默认温度
            max_tokens: 覆盖默认 token 数
            response_format: 如 {"type": "json_object"} 强制 JSON 输出

        Returns:
            {"content": 模型文本响应, "usage": {prompt_tokens, completion_tokens, total_tokens, model_name}}
        """
        kwargs = dict(
            model=self.config.model_name,
            messages=messages,
            temperature=temperature if temperature is not None else self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
        )
        if response_format:
            kwargs["response_format"] = response_format

        # Flash 模型：禁用思考模式，加速结构化输出
        if "flash" in self.config.model_name:
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

        log.debug(f"Chat request: model={self.config.model_name}, msgs={len(messages)}, tokens={kwargs['max_tokens']}")

        try:
            response = self.client.chat.completions.create(**kwargs)
            msg = response.choices[0].message
            content = msg.content or ""
            usage_info = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
                "model_name": self.config.model_name,
            }
            # V4 Pro 推理模型：记录思考链长度用于调试
            reasoning = getattr(msg, "reasoning_content", None)
            if reasoning:
                log.debug(f"Chat response: reasoning={len(reasoning)} chars, content={len(content)} chars, tokens={usage_info['total_tokens']}")
            else:
                log.debug(f"Chat response: {len(content)} chars, tokens_used={usage_info['total_tokens']}")
            # 如果 content 为空但 finish_reason 为 length，提示 token 不足
            if not content and response.choices[0].finish_reason == "length":
                log.warning("Chat response: content is empty (token limit reached before model finished reasoning). Increase max_tokens.")
            self.last_usage = usage_info
            return {"content": content, "usage": usage_info}
        except Exception as e:
            log.error(f"Chat failed: {e}")
            raise

    def analyze_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = None,
    ) -> dict:
        """
        调用 LLM 并强制返回 JSON 对象（含 usage 信息）

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入（含数据上下文）
            temperature: 温度参数

        Returns:
            {"result": 解析后的 JSON dict, "usage": {prompt_tokens, completion_tokens, total_tokens, model_name}}
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        resp = self.chat(
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        raw = resp["content"]
        usage = resp["usage"]

        # 清理可能的 markdown 代码块包装
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

        # 尝试多种方式解析
        errors = []
        for attempt in range(3):
            try:
                return {"result": json.loads(raw), "usage": usage}
            except json.JSONDecodeError as e:
                errors.append(str(e))
                if attempt == 0:
                    # 尝试修复：移除尾随逗号
                    import re
                    raw = re.sub(r',\s*}', '}', raw)
                    raw = re.sub(r',\s*]', ']', raw)
                elif attempt == 1:
                    # 尝试修复：截断到最后一个完整的对象
                    # 找到最后一个 }
                    last_brace = raw.rfind('}')
                    if last_brace > 0:
                        raw = raw[:last_brace + 1]

        log.error(f"JSON parse failed after 3 attempts. Errors: {errors}")
        log.error(f"Raw response (first 1000 chars): {raw[:1000]}")
        raise ValueError(f"LLM returned invalid JSON: {errors[-1]}") from Exception(errors[-1])


# 全局单例
_default_adapter: Optional[ModelAdapter] = None


def get_adapter(config: ModelConfig = None) -> ModelAdapter:
    """获取全局模型适配器（懒初始化）"""
    global _default_adapter
    if config:
        return ModelAdapter(config)
    if _default_adapter is None:
        _default_adapter = ModelAdapter()
    return _default_adapter


def reload_adapter(config: ModelConfig):
    """热切换全局 ModelAdapter 单例（用于管理后台模型切换）"""
    global _default_adapter
    _default_adapter = ModelAdapter(config)
    # 同步更新 harness 的 adapter 引用
    try:
        from .harness import harness
        harness.adapter = _default_adapter
    except ImportError:
        pass
    log.info(f"ModelAdapter reloaded: provider={config.provider}, model={config.model_name}")
    return _default_adapter


def get_active_model_name() -> str:
    """获取当前激活的模型名称"""
    if _default_adapter and _default_adapter.config:
        return _default_adapter.config.model_name
    return "unknown"


def get_adapter_info() -> dict:
    """获取当前 adapter 的完整配置信息"""
    if _default_adapter and _default_adapter.config:
        c = _default_adapter.config
        return {
            "provider": c.provider,
            "model_name": c.model_name,
            "base_url": c.base_url,
        }
    return {"provider": "", "model_name": "unknown", "base_url": ""}


def seed_model_config_from_env(db_execute, db_query):
    """
    启动时：如果 model_configs 表为空，从 .env 初始化一条激活配置。
    之后直接从 DB 读取活跃模型配置来初始化 adapter。

    Args:
        db_execute: async execute 函数 (sql, params)
        db_query: async query 函数 (sql, params) -> list[dict]
    """
    import asyncio

    async def _seed():
        # 检查是否已有激活配置
        active = await db_query(
            "SELECT * FROM model_configs WHERE is_active = 1 LIMIT 1", one=True
        )
        if active:
            log.info(f"Seed: 已有激活模型 {active['provider']}/{active['model_name']} (config_key={active['config_key']})")
            return ModelConfig.from_db_row(active)

        # 无激活配置，从 .env 初始化
        config = ModelConfig.from_env()
        now = datetime.now().isoformat()
        await db_execute(
            "INSERT OR REPLACE INTO model_configs (config_key, provider, model_name, api_base, api_key, is_active, purpose, created_at, updated_at) "
            "VALUES (?,?,?,?,?,1,'general',?,?)",
            ("deepseek-default", config.provider, config.model_name, config.base_url, config.api_key, now, now)
        )
        log.info(f"Seed: 从 .env 初始化模型配置 deepseek-default ({config.provider}/{config.model_name})")
        return config

    # 同步执行异步函数
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 已有事件循环，创建 task 等待
            import concurrent.futures
            future = asyncio.run_coroutine_threadsafe(_seed(), loop)
            return future.result(timeout=10)
        else:
            return asyncio.run(_seed())
    except RuntimeError:
        return asyncio.run(_seed())


def init_adapter_from_db(db_execute, db_query):
    """
    启动时从 DB 初始化全局 ModelAdapter。
    如果 DB 中无激活配置，先从 .env seed 一条。
    """
    global _default_adapter
    config = seed_model_config_from_env(db_execute, db_query)
    _default_adapter = ModelAdapter(config)
    log.info(f"ModelAdapter 从 DB 初始化: provider={config.provider}, model={config.model_name}")
    return _default_adapter
