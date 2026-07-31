"""
运营智能体管理后台 — Admin API Router
在 app.py main() 中调用 register_admin_routes() 注册
"""
import json, csv, io
from datetime import date, datetime, timedelta
from fastapi import Query, HTTPException
from fastapi.responses import StreamingResponse


def register_admin_routes(app, scheduler, get_db, aq, ae, harness, reload_configs=None):
    """在 FastAPI app 上注册所有 /api/admin/* 路由"""

    # ================================================================
    # 辅助函数
    # ================================================================
    def ok(data=None, message="ok"):
        return {"code": 0, "data": data, "message": message}

    def err(code: int, message: str):
        return {"code": code, "data": None, "message": message}

    TODAY = date.today().isoformat()

    # ================================================================
    # 2.1 定时任务管理
    # ================================================================

    @app.get("/api/admin/scheduled-tasks")
    async def admin_scheduled_tasks():
        """列出所有 APScheduler 定时任务（含最近一次执行记录）"""
        job_name_map = {
            "daily_data_tick": "日增数据引擎",
            "daily_schedule_gen": "日程自动生成",
            "daily_news_fetch": "金融资讯抓取",
            "daily_digest_gen": "资讯摘要生成",
            "daily_review_gen": "昨日回顾生成",
            "weekly_insight_gen": "客户洞察生成",
        }
        jobs = scheduler.get_jobs()
        items = []
        for job in jobs:
            trigger_str = str(job.trigger) if hasattr(job, 'trigger') else ''
            # 查询最近一次执行记录
            last_run = await aq(
                "SELECT status, result_summary, error_msg, started_at, finished_at, duration_ms "
                "FROM task_execution_history WHERE job_id = ? ORDER BY started_at DESC LIMIT 1",
                (job.id,), one=True
            )
            items.append({
                "job_id": job.id,
                "job_name": job_name_map.get(job.id, job.name if hasattr(job, 'name') and job.name else job.id),
                "trigger": trigger_str,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "status": "paused" if job.next_run_time is None and getattr(job, '_paused', False) else "running",
                "last_execution": {
                    "status": last_run["status"] if last_run else None,
                    "result_summary": last_run["result_summary"] if last_run else None,
                    "error_msg": last_run["error_msg"] if last_run else None,
                    "started_at": last_run["started_at"] if last_run else None,
                    "duration_ms": last_run["duration_ms"] if last_run else None,
                } if last_run else None,
            })
        return ok({"tasks": items, "total": len(items)})

    @app.get("/api/admin/scheduled-tasks/{job_id}/history")
    async def admin_task_history(
        job_id: str,
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
    ):
        """查询定时任务执行历史"""
        offset = (page - 1) * size
        total_row = await aq(
            "SELECT COUNT(*) as cnt FROM task_execution_history WHERE job_id = ?",
            (job_id,), one=True
        )
        total = total_row["cnt"] if total_row else 0
        rows = await aq(
            "SELECT * FROM task_execution_history WHERE job_id = ? ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (job_id, size, offset)
        )
        items = []
        for r in (rows or []):
            items.append({
                "id": r["id"], "job_id": r["job_id"], "job_name": r["job_name"],
                "status": r["status"], "result_summary": r["result_summary"],
                "result_detail": r.get("result_detail", ""),
                "error_msg": r["error_msg"], "started_at": r["started_at"],
                "finished_at": r["finished_at"], "duration_ms": r["duration_ms"],
            })
        return ok({"history": items, "total": total, "page": page, "size": size})

    @app.get("/api/admin/scheduled-tasks/history/{history_id}/detail")
    async def admin_task_history_detail(history_id: int):
        """获取单条执行历史的详细结果（结构化 JSON）"""
        row = await aq(
            "SELECT * FROM task_execution_history WHERE id = ?",
            (history_id,), one=True
        )
        if not row:
            return err(404, f"历史记录 {history_id} 不存在")
        detail_str = row.get("result_detail", "")
        detail_obj = None
        if detail_str:
            try:
                detail_obj = json.loads(detail_str)
            except (json.JSONDecodeError, TypeError):
                detail_obj = {"raw": detail_str}
        return ok({
            "id": row["id"],
            "job_id": row["job_id"],
            "job_name": row["job_name"],
            "status": row["status"],
            "result_summary": row["result_summary"],
            "result_detail": detail_obj,
            "error_msg": row["error_msg"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "duration_ms": row["duration_ms"],
        })

    @app.post("/api/admin/scheduled-tasks/{job_id}/pause")
    async def admin_task_pause(job_id: str):
        """暂停定时任务"""
        try:
            scheduler.pause_job(job_id)
            # 写审计日志
            await ae(
                "INSERT INTO audit_logs (action, target_type, target_id, operator, detail, created_at) VALUES (?,?,?,?,?,?)",
                ("pause_task", "scheduled_task", job_id, "admin", f"暂停定时任务 {job_id}", datetime.now().isoformat())
            )
            return ok(message=f"任务 {job_id} 已暂停")
        except Exception as e:
            return err(500, f"暂停失败: {str(e)}")

    @app.post("/api/admin/scheduled-tasks/{job_id}/resume")
    async def admin_task_resume(job_id: str):
        """恢复定时任务"""
        try:
            scheduler.resume_job(job_id)
            await ae(
                "INSERT INTO audit_logs (action, target_type, target_id, operator, detail, created_at) VALUES (?,?,?,?,?,?)",
                ("resume_task", "scheduled_task", job_id, "admin", f"恢复定时任务 {job_id}", datetime.now().isoformat())
            )
            return ok(message=f"任务 {job_id} 已恢复")
        except Exception as e:
            return err(500, f"恢复失败: {str(e)}")

    @app.post("/api/admin/scheduled-tasks/{job_id}/trigger")
    async def admin_task_trigger(job_id: str):
        """手动触发定时任务（立即执行一次，不改变原有定时计划）"""
        import asyncio
        try:
            job = scheduler.get_job(job_id)
            if not job:
                return err(404, f"任务 {job_id} 不存在")
            now = datetime.now().isoformat()
            # 使用 asyncio.create_task 立即异步执行，不修改 next_run_time
            asyncio.create_task(job.func())
            await ae(
                "INSERT INTO audit_logs (action, target_type, target_id, operator, detail, created_at) VALUES (?,?,?,?,?,?)",
                ("trigger_task", "scheduled_task", job_id, "admin", f"手动触发任务 {job_id}", now)
            )
            return ok(message=f"任务 {job_id} 已手动触发，正在后台执行")
        except Exception as e:
            return err(500, f"触发失败: {str(e)}")

    # ================================================================
    # 2.2 智能体配置管理
    # ================================================================

    @app.get("/api/admin/agents")
    async def admin_agents():
        """所有已注册智能体清单 + 运行状态（实时数据）"""
        from agentos.model_adapter import get_adapter_info
        adapter_info = get_adapter_info()
        agents = harness.registry.list_agents()
        items = []
        for a in agents:
            role = a["role"]
            # 查询今日调用次数和最后调用时间（真实数据）
            today_stats = await aq(
                "SELECT COUNT(*) as cnt, MAX(started_at) as last_call, "
                "SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as err_cnt "
                "FROM agent_run_logs WHERE agent_role = ? AND started_at >= ?",
                (role, TODAY), one=True
            )
            # 查询平均耗时
            avg_dur = await aq(
                "SELECT AVG(duration_ms) as avg_ms FROM agent_run_logs "
                "WHERE agent_role = ? AND status='success' AND started_at >= ?",
                (role, TODAY), one=True
            )
            disabled = getattr(harness.registry, '_disabled_roles', set())
            items.append({
                "role": role,
                "name": a["name"],
                "triggers": a.get("triggers", []),
                "skills": a.get("skills", []),
                "status": "paused" if role in disabled else "active",
                "today_calls": today_stats["cnt"] if today_stats else 0,
                "today_errors": today_stats["err_cnt"] if today_stats else 0,
                "last_call_at": today_stats["last_call"] if today_stats else None,
                "avg_duration_ms": round(avg_dur["avg_ms"]) if avg_dur and avg_dur["avg_ms"] else 0,
                "model_name": adapter_info["model_name"],
                "provider": adapter_info["provider"],
            })
        return ok({"agents": items, "total": len(items), "model": adapter_info})

    # ================================================================
    # 2.3 运行监测
    # ================================================================

    @app.get("/api/admin/agents/runs")
    async def admin_agent_runs(
        agent_role: str = Query(None),
        status: str = Query(None),
        date_from: str = Query(None),
        date_to: str = Query(None),
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
    ):
        """最近调用记录查询（实时 DB 查询）"""
        where = ["1=1"]
        params = []
        if agent_role:
            where.append("agent_role = ?")
            params.append(agent_role)
        if status:
            where.append("status = ?")
            params.append(status)
        if date_from:
            where.append("started_at >= ?")
            params.append(date_from)
        if date_to:
            where.append("started_at <= ?")
            params.append(date_to + " 23:59:59")
        wc = " AND ".join(where)
        offset = (page - 1) * size
        total_row = await aq(f"SELECT COUNT(*) as cnt FROM agent_run_logs WHERE {wc}", params, one=True)
        total = total_row["cnt"] if total_row else 0
        rows = await aq(
            f"SELECT * FROM agent_run_logs WHERE {wc} ORDER BY started_at DESC LIMIT ? OFFSET ?",
            params + [size, offset]
        )
        items = []
        for r in (rows or []):
            items.append({
                "id": r["id"], "agent_role": r["agent_role"], "method": r["method"],
                "manager_id": r["manager_id"], "status": r["status"],
                "input_summary": r["input_summary"][:200] if r["input_summary"] else "",
                "started_at": r["started_at"], "finished_at": r["finished_at"],
                "duration_ms": r["duration_ms"], "error_msg": r["error_msg"][:200] if r["error_msg"] else "",
            })
        return ok({"runs": items, "total": total, "page": page, "size": size})

    @app.get("/api/admin/agents/runs/{run_id}")
    async def admin_agent_run_detail(run_id: int):
        """单次调用详情（含完整日志和 token 消耗）"""
        row = await aq("SELECT * FROM agent_run_logs WHERE id = ?", (run_id,), one=True)
        if not row:
            return err(404, f"运行记录 {run_id} 不存在")
        token_rows = await aq(
            "SELECT * FROM agent_token_usage WHERE run_log_id = ?", (run_id,)
        )
        tokens = [dict(t) for t in (token_rows or [])]
        return ok({
            "id": row["id"], "agent_role": row["agent_role"], "method": row["method"],
            "manager_id": row["manager_id"], "status": row["status"],
            "input_summary": row["input_summary"],
            "output_summary": row["output_summary"],
            "error_msg": row["error_msg"],
            "started_at": row["started_at"], "finished_at": row["finished_at"],
            "duration_ms": row["duration_ms"],
            "token_usage": tokens,
        })

    @app.get("/api/admin/audit-logs")
    async def admin_audit_logs(
        action: str = Query(None),
        target_type: str = Query(None),
        date_from: str = Query(None),
        date_to: str = Query(None),
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
    ):
        """审计日志查询（实时 DB 数据）"""
        where = ["1=1"]
        params = []
        if action:
            where.append("action = ?")
            params.append(action)
        if target_type:
            where.append("target_type = ?")
            params.append(target_type)
        if date_from:
            where.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            where.append("created_at <= ?")
            params.append(date_to + " 23:59:59")
        wc = " AND ".join(where)
        offset = (page - 1) * size
        total_row = await aq(f"SELECT COUNT(*) as cnt FROM audit_logs WHERE {wc}", params, one=True)
        total = total_row["cnt"] if total_row else 0
        rows = await aq(
            f"SELECT * FROM audit_logs WHERE {wc} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [size, offset]
        )
        items = [dict(r) for r in (rows or [])]
        return ok({"logs": items, "total": total, "page": page, "size": size})

    @app.post("/api/admin/agents/runs/export")
    async def admin_runs_export(
        agent_role: str = Query(None),
        status: str = Query(None),
        date_from: str = Query(None),
        date_to: str = Query(None),
    ):
        """导出调用记录为 CSV（实时查询）"""
        where = ["1=1"]
        params = []
        if agent_role:
            where.append("agent_role = ?")
            params.append(agent_role)
        if status:
            where.append("status = ?")
            params.append(status)
        if date_from:
            where.append("started_at >= ?")
            params.append(date_from)
        if date_to:
            where.append("started_at <= ?")
            params.append(date_to + " 23:59:59")
        wc = " AND ".join(where)
        rows = await aq(f"SELECT * FROM agent_run_logs WHERE {wc} ORDER BY started_at DESC LIMIT 2000", params)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Agent", "Method", "Manager", "Status", "Input", "Error", "Started", "Duration(ms)"])
        for r in (rows or []):
            writer.writerow([r["id"], r["agent_role"], r["method"], r["manager_id"], r["status"],
                           r["input_summary"][:300] if r["input_summary"] else "",
                           r["error_msg"][:300] if r["error_msg"] else "",
                           r["started_at"], r["duration_ms"]])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=agent_runs.csv"}
        )

    # ================================================================
    # 2.4 费用分析
    # ================================================================

    @app.get("/api/admin/agents/token-stats")
    async def admin_token_stats(period: str = Query("today")):
        """Token 消耗总览统计（实时 DB 聚合）"""
        now = date.today()
        if period == "today":
            since = now.isoformat()
        elif period == "week":
            since = (now - timedelta(days=now.weekday())).isoformat()
        elif period == "month":
            since = now.replace(day=1).isoformat()
        else:
            since = now.isoformat()

        # 总览
        total_row = await aq(
            "SELECT SUM(total_tokens) as total, AVG(total_tokens) as avg_tok, "
            "MAX(total_tokens) as max_tok, COUNT(*) as call_count "
            "FROM agent_token_usage WHERE recorded_at >= ?", (since,), one=True
        )
        # 按 agent 分组
        agent_rows = await aq(
            "SELECT agent_role, SUM(total_tokens) as total, AVG(total_tokens) as avg_tok, "
            "MAX(total_tokens) as max_tok, COUNT(*) as call_count "
            "FROM agent_token_usage WHERE recorded_at >= ? GROUP BY agent_role ORDER BY total DESC",
            (since,)
        )
        agents = []
        for r in (agent_rows or []):
            agents.append({
                "agent_role": r["agent_role"],
                "total_tokens": r["total"] or 0,
                "avg_tokens": round(r["avg_tok"] or 0, 1),
                "max_tokens": r["max_tok"] or 0,
                "call_count": r["call_count"] or 0,
            })
        return ok({
            "period": period,
            "since": since,
            "total_tokens": total_row["total"] or 0 if total_row else 0,
            "avg_tokens_per_call": round(total_row["avg_tok"] or 0, 1) if total_row else 0,
            "max_tokens_single_call": total_row["max_tok"] or 0 if total_row else 0,
            "total_calls": total_row["call_count"] or 0 if total_row else 0,
            "by_agent": agents,
        })

    @app.get("/api/admin/agents/token-ranking")
    async def admin_token_ranking(period: str = Query("today"), limit: int = Query(5, ge=1, le=20)):
        """Token 消耗 Top N 排名（实时 DB 聚合）"""
        now = date.today()
        if period == "today":
            since = now.isoformat()
        elif period == "week":
            since = (now - timedelta(days=now.weekday())).isoformat()
        elif period == "month":
            since = now.replace(day=1).isoformat()
        else:
            since = now.isoformat()

        rows = await aq(
            "SELECT agent_role, SUM(total_tokens) as total, COUNT(*) as call_count, "
            "AVG(total_tokens) as avg_tok, MAX(total_tokens) as max_tok "
            "FROM agent_token_usage WHERE recorded_at >= ? "
            "GROUP BY agent_role ORDER BY total DESC LIMIT ?",
            (since, limit)
        )
        items = []
        for i, r in enumerate(rows or []):
            items.append({
                "rank": i + 1,
                "agent_role": r["agent_role"],
                "total_tokens": r["total"] or 0,
                "call_count": r["call_count"] or 0,
                "avg_tokens": round(r["avg_tok"] or 0, 1),
                "max_tokens": r["max_tok"] or 0,
            })
        return ok({"period": period, "since": since, "ranking": items})

    @app.get("/api/admin/agents/token-trend")
    async def admin_token_trend(days: int = Query(30, ge=1, le=90)):
        """Token 消耗趋势（按日聚合，实时 DB 数据）"""
        since = (date.today() - timedelta(days=days)).isoformat()
        rows = await aq(
            "SELECT DATE(recorded_at) as day, agent_role, SUM(total_tokens) as total, COUNT(*) as call_count "
            "FROM agent_token_usage WHERE recorded_at >= ? GROUP BY day, agent_role ORDER BY day",
            (since,)
        )
        # 按日期聚合
        trend = {}
        for r in (rows or []):
            day = r["day"]
            if day not in trend:
                trend[day] = {"date": day, "total_tokens": 0, "by_agent": {}}
            trend[day]["total_tokens"] += r["total"] or 0
            trend[day]["by_agent"][r["agent_role"]] = r["total"] or 0

        # 补充缺失日期（填 0）
        result = []
        cursor = date.today() - timedelta(days=days)
        while cursor <= date.today():
            ds = cursor.isoformat()
            if ds in trend:
                result.append(trend[ds])
            else:
                result.append({"date": ds, "total_tokens": 0, "by_agent": {}})
            cursor += timedelta(days=1)
        return ok({"days": days, "since": since, "trend": result})

    @app.get("/api/admin/agents/token-details")
    async def admin_token_details(
        agent_role: str = Query(None),
        date_from: str = Query(None),
        date_to: str = Query(None),
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
    ):
        """Token 消耗明细（实时 DB 分页查询）"""
        where = ["1=1"]
        params = []
        if agent_role:
            where.append("agent_role = ?")
            params.append(agent_role)
        if date_from:
            where.append("recorded_at >= ?")
            params.append(date_from)
        if date_to:
            where.append("recorded_at <= ?")
            params.append(date_to + " 23:59:59")
        wc = " AND ".join(where)
        offset = (page - 1) * size
        total_row = await aq(f"SELECT COUNT(*) as cnt FROM agent_token_usage WHERE {wc}", params, one=True)
        total = total_row["cnt"] if total_row else 0
        rows = await aq(
            f"SELECT * FROM agent_token_usage WHERE {wc} ORDER BY recorded_at DESC LIMIT ? OFFSET ?",
            params + [size, offset]
        )
        items = [dict(r) for r in (rows or [])]
        return ok({"details": items, "total": total, "page": page, "size": size})

    # ================================================================
    # 2.4 智能体配置（含 {role} 通配路由，必须在具体路由之后注册）
    # ================================================================

    @app.get("/api/admin/agents/{role}")
    async def admin_agent_detail(role: str):
        """单个智能体详情"""
        from agentos.model_adapter import get_adapter_info
        adapter_info = get_adapter_info()
        meta = harness.registry.get_meta(role)
        if not meta:
            return err(404, f"智能体 {role} 不存在")
        # 参数
        params_rows = await aq(
            "SELECT param_key, param_value, param_type, description, updated_at FROM agent_configs WHERE agent_role = ?",
            (role,)
        )
        params = [dict(r) for r in (params_rows or [])]
        # 最近 10 次运行
        runs = await aq(
            "SELECT id, method, manager_id, status, input_summary, output_summary, error_msg, "
            "started_at, finished_at, duration_ms FROM agent_run_logs "
            "WHERE agent_role = ? ORDER BY started_at DESC LIMIT 10",
            (role,)
        )
        run_items = [dict(r) for r in (runs or [])]
        disabled = getattr(harness.registry, '_disabled_roles', set())
        return ok({
            "role": meta.role,
            "name": meta.name,
            "description": meta.description,
            "model_name": adapter_info["model_name"],
            "provider": adapter_info["provider"],
            "triggers": meta.triggers,
            "skills": meta.skills,
            "rate_limit": meta.rate_limit,
            "timeout": meta.timeout,
            "status": "paused" if role in disabled else "active",
            "params": params,
            "recent_runs": run_items,
        })

    @app.post("/api/admin/agents/{role}/pause")
    async def admin_agent_pause(role: str):
        """暂停智能体"""
        meta = harness.registry.get_meta(role)
        if not meta:
            return err(404, f"智能体 {role} 不存在")
        if not hasattr(harness.registry, '_disabled_roles'):
            harness.registry._disabled_roles = set()
        harness.registry._disabled_roles.add(role)
        await ae(
            "INSERT INTO audit_logs (action, target_type, target_id, operator, detail, created_at) VALUES (?,?,?,?,?,?)",
            ("pause_agent", "agent", role, "admin", f"暂停智能体 {role}", datetime.now().isoformat())
        )
        return ok(message=f"智能体 {role} 已暂停")

    @app.post("/api/admin/agents/{role}/resume")
    async def admin_agent_resume(role: str):
        """恢复智能体"""
        meta = harness.registry.get_meta(role)
        if not meta:
            return err(404, f"智能体 {role} 不存在")
        if hasattr(harness.registry, '_disabled_roles'):
            harness.registry._disabled_roles.discard(role)
        await ae(
            "INSERT INTO audit_logs (action, target_type, target_id, operator, detail, created_at) VALUES (?,?,?,?,?,?)",
            ("resume_agent", "agent", role, "admin", f"恢复智能体 {role}", datetime.now().isoformat())
        )
        return ok(message=f"智能体 {role} 已恢复")

    @app.get("/api/admin/agents/{role}/params")
    async def admin_agent_params(role: str):
        """获取智能体可配置参数（实时 DB 查询）"""
        rows = await aq(
            "SELECT id, param_key, param_value, param_type, description, updated_at FROM agent_configs WHERE agent_role = ?",
            (role,)
        )
        items = [dict(r) for r in (rows or [])]
        return ok({"params": items, "agent_role": role})

    @app.put("/api/admin/agents/{role}/params")
    async def admin_agent_params_update(role: str, body: dict):
        """更新智能体可配置参数"""
        params = body.get("params", [])
        if not params:
            return err(400, "缺少 params")
        now = datetime.now().isoformat()
        for p in params:
            await ae(
                "INSERT INTO agent_configs (agent_role, param_key, param_value, param_type, description, updated_at) "
                "VALUES (?,?,?,?,?,?) ON CONFLICT(agent_role, param_key) DO UPDATE SET "
                "param_value=excluded.param_value, param_type=excluded.param_type, "
                "description=excluded.description, updated_at=excluded.updated_at",
                (role, p.get("param_key", ""), str(p.get("param_value", "")),
                 p.get("param_type", "string"), p.get("description", ""), now)
            )
        await ae(
            "INSERT INTO audit_logs (action, target_type, target_id, operator, detail, created_at) VALUES (?,?,?,?,?,?)",
            ("update_params", "agent", role, "admin", f"更新参数: {json.dumps([p.get('param_key','') for p in params])}", now)
        )
        return ok(message=f"已更新 {len(params)} 个参数")

    @app.get("/api/admin/agents/{role}/results")
    async def admin_agent_results(
        role: str,
        status: str = Query(None),
        date_from: str = Query(None),
        date_to: str = Query(None),
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
    ):
        """智能体运行结果查询和对比"""
        where = ["agent_role = ?"]
        params = [role]
        if status:
            where.append("status = ?")
            params.append(status)
        if date_from:
            where.append("started_at >= ?")
            params.append(date_from)
        if date_to:
            where.append("started_at <= ?")
            params.append(date_to + " 23:59:59")

        wc = " AND ".join(where)
        offset = (page - 1) * size
        total_row = await aq(f"SELECT COUNT(*) as cnt FROM agent_run_logs WHERE {wc}", params, one=True)
        total = total_row["cnt"] if total_row else 0
        rows = await aq(
            f"SELECT * FROM agent_run_logs WHERE {wc} ORDER BY started_at DESC LIMIT ? OFFSET ?",
            params + [size, offset]
        )
        items = []
        for r in (rows or []):
            # 查询关联的 token 消耗
            token_rows = await aq(
                "SELECT model_name, prompt_tokens, completion_tokens, total_tokens FROM agent_token_usage WHERE run_log_id = ?",
                (r["id"],)
            )
            tokens = [dict(t) for t in (token_rows or [])]
            items.append({
                "id": r["id"], "agent_role": r["agent_role"], "method": r["method"],
                "manager_id": r["manager_id"], "status": r["status"],
                "input_summary": r["input_summary"], "output_summary": r["output_summary"],
                "error_msg": r["error_msg"], "started_at": r["started_at"],
                "finished_at": r["finished_at"], "duration_ms": r["duration_ms"],
                "token_usage": tokens,
            })
        return ok({"results": items, "total": total, "page": page, "size": size})

    @app.post("/api/admin/agents/{role}/results/export")
    async def admin_agent_results_export(
        role: str,
        date_from: str = Query(None),
        date_to: str = Query(None),
    ):
        """导出智能体运行结果为 CSV（实时查询）"""
        where = ["agent_role = ?"]
        params = [role]
        if date_from:
            where.append("started_at >= ?")
            params.append(date_from)
        if date_to:
            where.append("started_at <= ?")
            params.append(date_to + " 23:59:59")
        wc = " AND ".join(where)
        rows = await aq(f"SELECT * FROM agent_run_logs WHERE {wc} ORDER BY started_at DESC LIMIT 1000", params)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Method", "Manager", "Status", "Input", "Output", "Error", "Started", "Finished", "Duration(ms)"])
        for r in (rows or []):
            writer.writerow([r["id"], r["method"], r["manager_id"], r["status"],
                           r["input_summary"], r["output_summary"], r["error_msg"],
                           r["started_at"], r["finished_at"], r["duration_ms"]])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={role}_results.csv"}
        )

    # ================================================================
    # 2.5 大模型配置管理
    # ================================================================

    @app.get("/api/admin/models")
    async def admin_models():
        """所有大模型配置（实时 DB 查询）"""
        rows = await aq("SELECT * FROM model_configs ORDER BY is_active DESC, updated_at DESC")
        items = [dict(r) for r in (rows or [])]
        # 查询当前激活模型信息
        active = await aq("SELECT * FROM model_configs WHERE is_active = 1 LIMIT 1", one=True)
        return ok({
            "models": items,
            "active": dict(active) if active else None,
            "total": len(items),
        })

    @app.post("/api/admin/models")
    async def admin_models_create(body: dict):
        """新增大模型配置"""
        config_key = body.get("config_key", "").strip()
        if not config_key:
            return err(400, "缺少 config_key")
        # 检查唯一性
        exist = await aq("SELECT config_key FROM model_configs WHERE config_key = ?", (config_key,), one=True)
        if exist:
            return err(409, f"配置 {config_key} 已存在")
        now = datetime.now().isoformat()
        await ae(
            "INSERT INTO model_configs (config_key, provider, model_name, api_base, api_key, is_active, purpose, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (config_key, body.get("provider", "deepseek"), body.get("model_name", ""),
             body.get("api_base", ""), body.get("api_key", ""),
             body.get("is_active", 0), body.get("purpose", "general"), now, now)
        )
        await ae(
            "INSERT INTO audit_logs (action, target_type, target_id, operator, detail, created_at) VALUES (?,?,?,?,?,?)",
            ("create_model", "model_config", config_key, "admin", f"新增模型配置 {config_key}", now)
        )
        return ok(message=f"模型配置 {config_key} 已创建")

    @app.put("/api/admin/models/{config_key}")
    async def admin_models_update(config_key: str, body: dict):
        """更新大模型配置"""
        exist = await aq("SELECT config_key FROM model_configs WHERE config_key = ?", (config_key,), one=True)
        if not exist:
            return err(404, f"配置 {config_key} 不存在")
        now = datetime.now().isoformat()
        await ae(
            "UPDATE model_configs SET provider=?, model_name=?, api_base=?, api_key=?, purpose=?, updated_at=? WHERE config_key=?",
            (body.get("provider", "deepseek"), body.get("model_name", ""),
             body.get("api_base", ""), body.get("api_key", ""),
             body.get("purpose", "general"), now, config_key)
        )
        await ae(
            "INSERT INTO audit_logs (action, target_type, target_id, operator, detail, created_at) VALUES (?,?,?,?,?,?)",
            ("update_model", "model_config", config_key, "admin", f"更新模型配置 {config_key}", now)
        )
        return ok(message=f"模型配置 {config_key} 已更新")

    @app.delete("/api/admin/models/{config_key}")
    async def admin_models_delete(config_key: str):
        """删除大模型配置（不允许删除当前激活的）"""
        exist = await aq("SELECT is_active FROM model_configs WHERE config_key = ?", (config_key,), one=True)
        if not exist:
            return err(404, f"配置 {config_key} 不存在")
        if exist["is_active"]:
            return err(400, "无法删除当前激活的模型配置，请先激活其他配置")
        await ae("DELETE FROM model_configs WHERE config_key = ?", (config_key,))
        await ae(
            "INSERT INTO audit_logs (action, target_type, target_id, operator, detail, created_at) VALUES (?,?,?,?,?,?)",
            ("delete_model", "model_config", config_key, "admin", f"删除模型配置 {config_key}", datetime.now().isoformat())
        )
        return ok(message=f"模型配置 {config_key} 已删除")

    @app.post("/api/admin/models/{config_key}/activate")
    async def admin_models_activate(config_key: str):
        """激活大模型配置（其他配置 is_active 置 0，热切换全局 adapter）"""
        exist = await aq("SELECT * FROM model_configs WHERE config_key = ?", (config_key,), one=True)
        if not exist:
            return err(404, f"配置 {config_key} 不存在")
        now = datetime.now().isoformat()
        # 全部置 0
        await ae("UPDATE model_configs SET is_active = 0, updated_at = ?", (now,))
        # 激活目标
        await ae("UPDATE model_configs SET is_active = 1, updated_at = ? WHERE config_key = ?", (now, config_key))
        # 热切换全局 ModelAdapter
        try:
            from agentos.model_adapter import reload_adapter, ModelConfig
            new_config = ModelConfig(
                provider=exist["provider"],
                model_name=exist["model_name"],
                api_key=exist["api_key"],
                base_url=exist["api_base"],
            )
            reload_adapter(new_config)
        except Exception as e:
            return err(500, f"模型热切换失败: {str(e)}")
        await ae(
            "INSERT INTO audit_logs (action, target_type, target_id, operator, detail, created_at) VALUES (?,?,?,?,?,?)",
            ("activate_model", "model_config", config_key, "admin",
             f"激活模型 {exist['provider']}/{exist['model_name']}", now)
        )
        return ok({
            "message": f"已切换到 {exist['provider']}/{exist['model_name']}",
            "provider": exist["provider"],
            "model_name": exist["model_name"],
        })

    # ================================================================
    # 2.6 平台环境配置管理
    # ================================================================

    @app.get("/api/admin/platform-configs")
    async def admin_platform_configs():
        """获取所有平台环境配置"""
        rows = await aq("SELECT * FROM platform_configs ORDER BY category, config_key")
        return ok({"configs": [dict(r) for r in (rows or [])], "count": len(rows or [])})

    @app.post("/api/admin/platform-configs")
    async def admin_platform_config_create(body: dict):
        """新增平台配置项"""
        key = body.get("config_key", "").strip()
        if not key:
            return err(400, "缺少 config_key")
        exist = await aq("SELECT config_key FROM platform_configs WHERE config_key = ?", (key,), one=True)
        if exist:
            return err(409, f"配置 {key} 已存在")
        now = datetime.now().isoformat()
        await ae(
            "INSERT INTO platform_configs (config_key, config_value, category, description, updated_at, created_at) VALUES (?,?,?,?,?,?)",
            (key, body.get("config_value", ""), body.get("category", "general"), body.get("description", ""), now, now))
        await ae(
            "INSERT INTO audit_logs (action, target_type, target_id, operator, detail, created_at) VALUES (?,?,?,?,?,?)",
            ("create_config", "platform_config", key, "admin", f"新增配置 {key}", now))
        if reload_configs:
            reload_configs()
        return ok(message=f"配置 {key} 已创建")

    @app.put("/api/admin/platform-configs/{config_key:path}")
    async def admin_platform_config_update(config_key: str, body: dict):
        """更新平台配置项"""
        exist = await aq("SELECT * FROM platform_configs WHERE config_key = ?", (config_key,), one=True)
        if not exist:
            return err(404, f"配置 {config_key} 不存在")
        now = datetime.now().isoformat()
        new_val = body.get("config_value", exist["config_value"])
        new_cat = body.get("category", exist["category"])
        new_desc = body.get("description", exist.get("description", ""))
        await ae(
            "UPDATE platform_configs SET config_value=?, category=?, description=?, updated_at=? WHERE config_key=?",
            (new_val, new_cat, new_desc, now, config_key))
        await ae(
            "INSERT INTO audit_logs (action, target_type, target_id, operator, detail, created_at) VALUES (?,?,?,?,?,?)",
            ("update_config", "platform_config", config_key, "admin", f"更新配置 {config_key}", now))
        if reload_configs:
            reload_configs()
        return ok(message=f"配置 {config_key} 已更新")

    @app.delete("/api/admin/platform-configs/{config_key:path}")
    async def admin_platform_config_delete(config_key: str):
        """删除平台配置项"""
        exist = await aq("SELECT * FROM platform_configs WHERE config_key = ?", (config_key,), one=True)
        if not exist:
            return err(404, f"配置 {config_key} 不存在")
        await ae("DELETE FROM platform_configs WHERE config_key = ?", (config_key,))
        now = datetime.now().isoformat()
        await ae(
            "INSERT INTO audit_logs (action, target_type, target_id, operator, detail, created_at) VALUES (?,?,?,?,?,?)",
            ("delete_config", "platform_config", config_key, "admin", f"删除配置 {config_key}", now))
        if reload_configs:
            reload_configs()
        return ok(message=f"配置 {config_key} 已删除")

    print(f"[Admin API] {30} 个管理端点已注册")
