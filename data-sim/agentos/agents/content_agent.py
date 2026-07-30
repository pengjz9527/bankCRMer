"""
ContentAgent — 内容生成智能体
"信息秘书"角色，负责从日常数据中提炼关键信息，生成精炼内容报告。

四项核心技能：
  gen_review       — 昨日回顾（每日 20:00 定时）
  gen_digest       — 资讯摘要（每日 08:30 定时）
  gen_summary      — 周报（每周一 08:00 定时）
  transcribe_dictation — 面谈口述转写（面访后按需触发）

触发方式：定时 + 按需 + 事件触发
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

from ..harness import Agent, AgentContext, agent, skill
from ..model_adapter import get_adapter

log = logging.getLogger("agentos.content_agent")

# ============================================================
# 数据库路径
# ============================================================

DB_PATH = str(Path(__file__).parent.parent.parent / "yihuiban_sim.db")

# ============================================================
# 数据查询辅助函数
# ============================================================

def _query_db(sql: str, params: tuple = ()) -> list[dict]:
    """通用数据库查询"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _get_managers() -> list[str]:
    """获取所有在职客户经理 ID"""
    rows = _query_db("SELECT DISTINCT manager_id FROM cust_manager_rel")
    mgrs = [r["manager_id"] for r in rows]
    return mgrs if mgrs else ["M001"]


def _get_manager_name(mgr_id: str) -> str:
    """获取客户经理姓名（从 customers 表中 manager 或 默认）"""
    # 尝试从 agent 配置中获取
    return f"客户经理{mgr_id}"


# ============================================================
# gen_review 数据收集
# ============================================================

def _collect_review_data(mgr_id: str, target_date: str) -> dict:
    """
    收集指定日期的回顾数据。

    Returns:
        {
            "processing": [...],     # 处理记录
            "communications": [...], # 沟通记录
            "big_transactions": [...], # 大额交易
            "product_updates": [...], # 产品变更
            "announcements": [...],  # 行内公告
            "schedule_completed": int, # 日程完成数
        }
    """
    # 1. 处理记录（processing_records）
    processing = _query_db(
        """SELECT task_type, cust_name, action, notes, processed_at
           FROM processing_records
           WHERE date(processed_at) = ?
           ORDER BY processed_at DESC""",
        (target_date,),
    )

    # 2. 沟通记录（communications）
    communications = _query_db(
        """SELECT cm.cust_id, c.name as cust_name, cm.channel,
                  cm.duration_min, cm.summary, cm.key_topics, cm.comm_date
           FROM communications cm
           JOIN cust_manager_rel cmr ON cm.cust_id = cmr.cust_id
           JOIN customers c ON cm.cust_id = c.id
           WHERE cmr.manager_id = ? AND cm.comm_date = ?
           ORDER BY cm.comm_date DESC""",
        (mgr_id, target_date),
    )

    # 3. 大额交易（>3万）
    big_transactions = _query_db(
        """SELECT t.cust_id, c.name as cust_name, t.txn_type, t.amount,
                  t.summary, t.txn_date
           FROM transactions t
           JOIN cust_manager_rel cmr ON t.cust_id = cmr.cust_id
           JOIN customers c ON t.cust_id = c.id
           WHERE cmr.manager_id = ? AND t.txn_date = ? AND t.amount > 30000
           ORDER BY t.amount DESC""",
        (mgr_id, target_date),
    )

    # 4. 产品变更
    product_updates = _query_db(
        """SELECT product_code, change_type, old_value, new_value, changed_at
           FROM product_updates
           WHERE date(changed_at) = ?
           ORDER BY changed_at DESC""",
        (target_date,),
    )

    # 5. 行内公告
    announcements = _query_db(
        """SELECT title, content, ann_type, published_at
           FROM internal_announcements
           WHERE date(published_at) = ?
           ORDER BY published_at DESC""",
        (target_date,),
    )

    # 6. 日程完成数（从 daily_schedules 中统计 completed 状态）
    # 注：简化处理，以 processing_records 数量作为参考
    schedule_completed = len(processing)

    return {
        "processing": processing,
        "communications": communications,
        "big_transactions": big_transactions,
        "product_updates": product_updates,
        "announcements": announcements,
        "schedule_completed": schedule_completed,
    }


# ============================================================
# gen_digest 数据收集
# ============================================================

def _collect_digest_data(target_date: str) -> list[dict]:
    """获取当日金融资讯"""
    rows = _query_db(
        """SELECT title, content, source, category, news_url, fetched_at
           FROM daily_news
           WHERE date(fetched_at) = ?
           ORDER BY fetched_at DESC
           LIMIT 30""",
        (target_date,),
    )
    return rows


# ============================================================
# gen_summary 数据收集
# ============================================================

def _collect_summary_data(mgr_id: str, week_start: str, week_end: str) -> dict:
    """收集本周汇总数据"""
    # 本周处理记录
    processing = _query_db(
        """SELECT task_type, cust_name, action, processed_at
           FROM processing_records
           WHERE date(processed_at) BETWEEN ? AND ?
           ORDER BY processed_at DESC""",
        (week_start, week_end),
    )

    # 本周沟通
    communications = _query_db(
        """SELECT cm.channel, cm.summary, cm.key_topics, cm.comm_date,
                  c.name as cust_name
           FROM communications cm
           JOIN cust_manager_rel cmr ON cm.cust_id = cmr.cust_id
           JOIN customers c ON cm.cust_id = c.id
           WHERE cmr.manager_id = ? AND cm.comm_date BETWEEN ? AND ?
           ORDER BY cm.comm_date DESC""",
        (mgr_id, week_start, week_end),
    )

    # 本周商机
    opportunities = _query_db(
        """SELECT title, priority, status, cust_name, generated_at
           FROM opportunities
           WHERE manager_id = ? AND generated_at BETWEEN ? AND ?
           ORDER BY priority DESC""",
        (mgr_id, week_start, week_end),
    )

    return {
        "processing": processing,
        "communications": communications,
        "opportunities": opportunities,
    }


# ============================================================
# Agent 定义
# ============================================================

@agent(
    name="内容生成智能体",
    role="content_gen",
    description="信息秘书：生成昨日回顾/资讯摘要/周报/面谈口述转写",
    skills=[
        "gen_review", "gen_digest", "gen_summary", "transcribe_dictation",
    ],
    triggers=["scheduled", "on_demand", "event"],
    rate_limit=30,
    timeout=300,
)
class ContentAgent(Agent):
    """内容生成领域专家 — 客户经理的"信息秘书" """

    system_prompt = "prompts/content_agent.md"

    def __init__(self, adapter=None):
        super().__init__(adapter)
        self.load_prompt(self.system_prompt)

    # ================================================================
    # gen_review — 昨日回顾
    # ================================================================

    async def gen_review(self, ctx: AgentContext, manager_id: str = "", target_date: str = "") -> dict:
        """
        生成昨日回顾。

        Args:
            manager_id: 客户经理 ID（为空则遍历全部经理）
            target_date: 目标日期，默认为昨天

        Returns:
            {"manager_id": str, "review": dict, "saved": bool}
        """
        if not target_date:
            target_date = (date.today() - timedelta(days=1)).isoformat()

        manager_id = manager_id or ctx.manager_id
        if not manager_id:
            return {"error": "manager_id 为空，无法生成回顾"}

        log.info(f"gen_review: manager={manager_id}, date={target_date}")

        # 收集数据
        data = _collect_review_data(manager_id, target_date)

        # 检查是否有数据
        total_items = (
            len(data["processing"]) + len(data["communications"]) +
            len(data["big_transactions"]) + len(data["product_updates"]) +
            len(data["announcements"])
        )
        if total_items == 0:
            # 无数据时生成空回顾
            review = {
                "date": target_date,
                "manager_id": manager_id,
                "sections": [
                    {"title": "今日概要", "content": f"{target_date} 无工作记录。"},
                    {"title": "工作完成", "content": "昨日无处理记录。"},
                    {"title": "客户动态", "content": "昨日无异动或沟通记录。"},
                    {"title": "产品/公告", "content": "昨日无产品变更或行内公告。"},
                    {"title": "明日关注", "content": "建议关注近期到期产品和待跟进商机。"},
                ],
            }
            self._save_review(manager_id, target_date, review)
            return {"manager_id": manager_id, "review": review, "saved": True, "empty": True}

        # 构建 LLM prompt
        user_prompt = self._build_review_prompt(manager_id, target_date, data)

        # 调用 LLM
        try:
            resp = self.adapter.analyze_json(
                system_prompt=self.system_prompt_text,
                user_prompt=user_prompt,
                temperature=0.3,
            )
            review = resp["result"]
            log.info(f"gen_review done: {resp['usage']['total_tokens']} tokens")
        except Exception as e:
            log.error(f"gen_review LLM failed: {e}")
            # 降级：返回规则生成的基础回顾
            review = self._fallback_review(target_date, data)

        # 保存到数据库
        saved = self._save_review(manager_id, target_date, review)
        return {"manager_id": manager_id, "review": review, "saved": saved}

    def _build_review_prompt(self, mgr_id: str, target_date: str, data: dict) -> str:
        """构建 gen_review 的 LLM prompt"""
        return f"""请为客户经理 {mgr_id} 生成 {target_date} 的昨日回顾。

**处理记录（{len(data['processing'])} 条）**：
```json
{json.dumps(data['processing'], ensure_ascii=False, indent=2)}
```

**沟通记录（{len(data['communications'])} 条）**：
```json
{json.dumps(data['communications'], ensure_ascii=False, indent=2)}
```

**大额交易（{len(data['big_transactions'])} 笔）**：
```json
{json.dumps(data['big_transactions'], ensure_ascii=False, indent=2)}
```

**产品变更（{len(data['product_updates'])} 条）**：
```json
{json.dumps(data['product_updates'], ensure_ascii=False, indent=2)}
```

**行内公告（{len(data['announcements'])} 条）**：
```json
{json.dumps(data['announcements'], ensure_ascii=False, indent=2)}
```

请严格按照 system prompt 中定义的 gen_review 格式输出 JSON。"""

    def _fallback_review(self, target_date: str, data: dict) -> dict:
        """规则生成的降级回顾（LLM 不可用时）"""
        sections = []

        # 概要
        proc_count = len(data["processing"])
        comm_count = len(data["communications"])
        big_count = len(data["big_transactions"])
        sections.append({
            "title": "今日概要",
            "content": f"{target_date} 完成客户触达 {proc_count} 项，沟通 {comm_count} 次，大额异动 {big_count} 笔。"
        })

        # 工作完成
        if data["processing"]:
            items = [f"{p['cust_name']}: {p['action']}({p['task_type']})" for p in data["processing"][:5]]
            sections.append({"title": "工作完成", "content": "；".join(items)})
        else:
            sections.append({"title": "工作完成", "content": f"{target_date} 无处理记录。"})

        # 客户动态
        if data["communications"]:
            items = [f"{c['cust_name']}: {c['summary'] or c['key_topics'] or c['channel']}" for c in data["communications"][:5]]
            sections.append({"title": "客户动态", "content": "；".join(items)})
        elif data["big_transactions"]:
            items = [f"{t['cust_name']} {t['txn_type']} {float(t['amount'])/10000:.1f}万" for t in data["big_transactions"][:3]]
            sections.append({"title": "客户动态", "content": "大额交易：" + "；".join(items)})
        else:
            sections.append({"title": "客户动态", "content": "昨日无异动或沟通记录。"})

        # 产品/公告
        prod_items = [f"{p['change_type']}: {p['product_code']}" for p in data["product_updates"][:3]]
        ann_items = [a["title"] for a in data["announcements"][:3]]
        combined = "; ".join(prod_items + ann_items)
        sections.append({"title": "产品/公告", "content": combined or "昨日无产品变更或行内公告。"})

        # 明日关注
        sections.append({"title": "明日关注", "content": "建议关注近期到期产品、待跟进商机及高优先级待办。"})

        return {"date": target_date, "manager_id": "", "sections": sections}

    def _save_review(self, mgr_id: str, target_date: str, review: dict) -> bool:
        """保存回顾到 daily_reviews 表"""
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        try:
            content = json.dumps(review, ensure_ascii=False)
            now = datetime.now().isoformat()
            conn.execute(
                """INSERT OR REPLACE INTO daily_reviews
                   (manager_id, review_date, content, generated_at, is_read)
                   VALUES (?, ?, ?, ?, 0)""",
                (mgr_id, target_date, content, now),
            )
            conn.commit()
            return True
        except Exception as e:
            log.error(f"Failed to save review for {mgr_id}/{target_date}: {e}")
            return False
        finally:
            conn.close()

    # ================================================================
    # gen_digest — 资讯摘要
    # ================================================================

    async def gen_digest(self, ctx: AgentContext, target_date: str = "") -> dict:
        """
        生成当日资讯摘要。

        Args:
            target_date: 目标日期，默认为今天

        Returns:
            {"date": str, "headlines": [...], "briefing": str}
        """
        if not target_date:
            target_date = date.today().isoformat()

        log.info(f"gen_digest: date={target_date}")

        news = _collect_digest_data(target_date)

        if not news:
            return {
                "date": target_date,
                "headlines": [],
                "briefing": f"{target_date} 暂无金融资讯。可能数据源暂不可用。",
                "empty": True,
            }

        # 构建 LLM prompt
        news_json = json.dumps(news[:20], ensure_ascii=False, indent=2)
        user_prompt = f"""请从以下 {len(news)} 条当日金融资讯中，提炼 5-8 条最值得客户经理关注的要闻。

**资讯列表**：
```json
{news_json}
```

请严格按照 system prompt 中定义的 gen_digest 格式输出 JSON。
要点：
- 优先选择与银行业务相关的资讯（利率、理财、监管、房贷、基金、保险等）
- 每条要闻 summary 控制在 30 字以内
- briefing 给出 50-100 字的综合解读
"""

        try:
            resp = self.adapter.analyze_json(
                system_prompt=self.system_prompt_text,
                user_prompt=user_prompt,
                temperature=0.3,
            )
            result = resp["result"]
            result["date"] = target_date
            log.info(f"gen_digest done: {resp['usage']['total_tokens']} tokens")
            return result
        except Exception as e:
            log.error(f"gen_digest LLM failed: {e}")
            # 降级：返回原始标题列表
            headlines = [{"title": n["title"], "summary": n.get("content", "")[:50], "category": n.get("category", "金融"), "source": n.get("source", "")} for n in news[:8]]
            return {
                "date": target_date,
                "headlines": headlines,
                "briefing": f"今日共获取 {len(news)} 条资讯（AI 摘要生成失败，显示原始标题）。",
            }

    # ================================================================
    # gen_summary — 周报
    # ================================================================

    async def gen_summary(self, ctx: AgentContext, manager_id: str = "") -> dict:
        """
        生成本周工作周报。

        Args:
            manager_id: 客户经理 ID

        Returns:
            {"week": str, "overview": str, "highlights": [...], "stats": {...}, "next_week_focus": [...]}
        """
        today = date.today()
        # 本周一
        week_start = (today - timedelta(days=today.weekday())).isoformat()
        week_end = today.isoformat()
        week_label = f"{week_start} 至 {week_end}"

        manager_id = manager_id or ctx.manager_id
        if not manager_id:
            return {"error": "manager_id 为空，无法生成周报"}

        log.info(f"gen_summary: manager={manager_id}, week={week_label}")

        data = _collect_summary_data(manager_id, week_start, week_end)

        if not data["processing"] and not data["communications"] and not data["opportunities"]:
            return {
                "week": week_label,
                "overview": "本周无工作记录。",
                "highlights": [],
                "stats": {},
                "next_week_focus": ["建议本周保持客户触达频率"],
                "empty": True,
            }

        user_prompt = f"""请为客户经理 {manager_id} 生成本周工作周报。

**时间范围**：{week_label}

**处理记录（{len(data['processing'])} 条）**：
```json
{json.dumps(data['processing'][:30], ensure_ascii=False, indent=2)}
```

**沟通记录（{len(data['communications'])} 条）**：
```json
{json.dumps(data['communications'][:30], ensure_ascii=False, indent=2)}
```

**商机记录（{len(data['opportunities'])} 条）**：
```json
{json.dumps(data['opportunities'][:20], ensure_ascii=False, indent=2)}
```

请严格按照 system prompt 中定义的 gen_summary 格式输出 JSON。
要点：
- overview 控制在 100 字以内
- highlights 列出 3 个亮点，不要编造
- stats 统计要有数字依据
- next_week_focus 给出 2-3 条具体建议
"""

        try:
            resp = self.adapter.analyze_json(
                system_prompt=self.system_prompt_text,
                user_prompt=user_prompt,
                temperature=0.3,
            )
            result = resp["result"]
            result["week"] = week_label
            log.info(f"gen_summary done: {resp['usage']['total_tokens']} tokens")
            return result
        except Exception as e:
            log.error(f"gen_summary LLM failed: {e}")
            # 降级
            return {
                "week": week_label,
                "overview": f"本周共处理 {len(data['processing'])} 项客户触达，完成 {len(data['communications'])} 次沟通，跟进 {len(data['opportunities'])} 个商机。",
                "highlights": [],
                "stats": {
                    "客户触达": f"{len(data['processing'])}次",
                    "沟通次数": f"{len(data['communications'])}次",
                    "商机跟进": f"{len(data['opportunities'])}个",
                },
                "next_week_focus": ["保持客户触达频率", "关注到期产品", "跟进待处理商机"],
            }

    # ================================================================
    # transcribe_dictation — 面谈口述转写
    # ================================================================

    async def transcribe_dictation(self, ctx: AgentContext, audio_path: str = "", audio_bytes: bytes = None) -> dict:
        """
        面谈口述AI转写回填。客户经理面访结束后口述 1-2 分钟，AI 转写提取，
        回填 PDCA 字段、更新画像（变更标红）、生成待办。

        Args:
            audio_path: 音频文件路径
            audio_bytes: 音频字节流

        Returns:
            {"transcript": str, "pdc": {...}, "profile_changes": [...], "todos": [...]}
        """
        log.info(f"transcribe_dictation: audio_path={bool(audio_path)}, audio_bytes={bool(audio_bytes)}")

        # Step 1: ASR 转写
        if not audio_path and not audio_bytes:
            return {"error": "请提供 audio_path 或 audio_bytes"}

        try:
            from ..asr_client import AlibabaASRClient
            asr = AlibabaASRClient()
            if audio_bytes:
                transcript = asr.transcribe_bytes(audio_bytes)
            else:
                transcript = asr.transcribe(audio_path)
        except ImportError:
            return {"error": "ASR 客户端不可用，请安装 alibabacloud-nls-cloud-meta20180518"}
        except Exception as e:
            log.error(f"ASR failed: {e}")
            return {"error": f"语音转写失败: {e}"}

        if not transcript:
            return {"error": "语音转写结果为空"}

        # Step 2: LLM 提取 PDCA + 待办 + 画像变更
        user_prompt = f"""客户经理面访结束后口述了以下内容，请提取关键信息。

**口述转写文本**：
```
{transcript}
```

请完成以下任务并以 JSON 格式返回：
1. **PDCA 提取**：
   - P (计划目的): 本次面谈的目标是否达成
   - D (执行偏离): 实际执行与计划有无偏差
   - C (客户反馈): 客户的态度/意见/新需求
   - A (后续动作): 需要跟进的具体行动

2. **画像变更** (如有)：
   - 列出在面谈中发现的客户画像变化（如：职业变更、家庭情况、投资偏好、联系方式等）
   - 每条变更包含 field(字段), old_value, new_value, confidence(确信度: high/medium/low)

3. **待办生成**：
   - 列出需要跟进的待办事项
   - 每条包含 title, priority(高/中/低), deadline(建议截止日期)

输出格式：
```json
{{
  "pdc": {{
    "plan": "面谈目的",
    "do": "执行情况",
    "check": "客户反馈",
    "act": "后续动作"
  }},
  "profile_changes": [
    {{"field": "字段名", "old_value": "原值", "new_value": "新值", "confidence": "high"}}
  ],
  "todos": [
    {{"title": "待办内容", "priority": "高", "deadline": "YYYY-MM-DD"}}
  ]
}}
```"""

        try:
            resp = self.adapter.analyze_json(
                system_prompt=self.system_prompt_text,
                user_prompt=user_prompt,
                temperature=0.2,
            )
            result = resp["result"]
            result["transcript"] = transcript
            log.info(f"transcribe_dictation done: {resp['usage']['total_tokens']} tokens")
            return result
        except Exception as e:
            log.error(f"transcribe_dictation LLM failed: {e}")
            return {
                "transcript": transcript,
                "pdc": {"plan": "", "do": "", "check": "", "act": ""},
                "profile_changes": [],
                "todos": [],
                "error": f"AI 提取失败: {e}",
            }

    # ================================================================
    # 批量生成 — 供定时任务调用
    # ================================================================

    async def batch_gen_review(self, ctx: AgentContext, target_date: str = "") -> list[dict]:
        """
        为所有客户经理批量生成昨日回顾。
        """
        managers = _get_managers()
        results = []
        for mgr_id in managers:
            try:
                r = await self.gen_review(ctx, manager_id=mgr_id, target_date=target_date)
                results.append(r)
            except Exception as e:
                log.error(f"batch_gen_review failed for {mgr_id}: {e}")
                results.append({"manager_id": mgr_id, "error": str(e)})
        return results


# ============================================================
# 便捷函数
# ============================================================

def create_content_agent() -> ContentAgent:
    """创建内容生成 Agent 实例（注册到全局 harness）"""
    from ..harness import harness as h
    agent = ContentAgent()
    h.registry.register(ContentAgent.meta, agent)
    return agent
