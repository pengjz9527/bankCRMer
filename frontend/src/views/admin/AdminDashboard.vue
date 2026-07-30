<template>
  <div class="dashboard">
    <!-- 4 统计卡片 -->
    <div class="stat-cards">
      <div class="stat-card">
        <div class="stat-card-icon agents">A</div>
        <div class="stat-card-body">
          <div class="stat-card-value">{{ stats.agentTotal }}</div>
          <div class="stat-card-label">智能体总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card-icon running">R</div>
        <div class="stat-card-body">
          <div class="stat-card-value">{{ stats.agentActive }}</div>
          <div class="stat-card-label">运行中</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card-icon calls">C</div>
        <div class="stat-card-body">
          <div class="stat-card-value">{{ stats.todayCalls }}</div>
          <div class="stat-card-label">今日调用</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-card-icon errors">E</div>
        <div class="stat-card-body">
          <div class="stat-card-value" :class="{ 'text-red': stats.todayErrors > 0 }">{{ stats.todayErrors }}</div>
          <div class="stat-card-label">异常数</div>
        </div>
      </div>
    </div>

    <div class="dashboard-grid">
      <!-- 智能体运行概览 -->
      <div class="panel">
        <h3 class="panel-title">智能体运行概览</h3>
        <table class="data-table" v-if="agents.length">
          <thead>
            <tr><th>智能体</th><th>状态</th><th>今日调用</th><th>平均耗时</th><th>健康</th></tr>
          </thead>
          <tbody>
            <tr v-for="a in agents" :key="a.role">
              <td><strong>{{ a.name || a.role }}</strong></td>
              <td><span class="badge" :class="a.status">{{ a.status === 'active' ? '运行中' : '已暂停' }}</span></td>
              <td>{{ a.today_calls ?? 0 }}</td>
              <td>{{ a.avg_duration_ms ? (a.avg_duration_ms / 1000).toFixed(1) + 's' : '-' }}</td>
              <td><span class="health-dot" :class="a.today_errors > 0 ? 'bad' : 'good'"></span></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">暂无智能体数据</div>
      </div>

      <!-- Token Top5 -->
      <div class="panel">
        <h3 class="panel-title">Token 消耗 Top5（今日）</h3>
        <div v-if="tokenRanking.length" class="rank-list">
          <div v-for="(r, i) in tokenRanking" :key="r.agent_role" class="rank-item">
            <span class="rank-num" :class="'num-' + (i + 1)">{{ i + 1 }}</span>
            <span class="rank-name">{{ r.agent_role }}</span>
            <span class="rank-val">{{ r.total_tokens.toLocaleString() }} tokens</span>
            <span class="rank-bar-wrap"><span class="rank-bar" :style="{ width: rankBarWidth(r.total_tokens, tokenRanking[0].total_tokens) + '%' }"></span></span>
          </div>
        </div>
        <div v-else class="empty">暂无 Token 消耗数据</div>
      </div>

      <!-- 定时任务状态 -->
      <div class="panel">
        <h3 class="panel-title">定时任务状态</h3>
        <table class="data-table" v-if="tasks.length">
          <thead>
            <tr><th>任务名</th><th>调度状态</th><th>最近执行</th><th>执行结果</th><th>下次运行</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in tasks" :key="t.job_id">
              <td>{{ t.job_name }}</td>
              <td><span class="badge" :class="t.status">{{ t.status === 'running' ? '运行中' : '已暂停' }}</span></td>
              <td>
                <span v-if="t.last_execution" class="badge" :class="t.last_execution.status === 'success' ? 'exec-ok' : 'exec-fail'">
                  {{ t.last_execution.status === 'success' ? '成功' : '失败' }}
                </span>
                <span v-else class="no-exec">暂无记录</span>
              </td>
              <td class="summary-cell">{{ t.last_execution?.result_summary || t.last_execution?.error_msg || '-' }}</td>
              <td>{{ t.next_run_time ? formatTime(t.next_run_time) : '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">暂无定时任务数据</div>
      </div>

      <!-- 最近告警 -->
      <div class="panel">
        <h3 class="panel-title">最近异常记录</h3>
        <table class="data-table" v-if="errorRuns.length">
          <thead>
            <tr><th>时间</th><th>智能体</th><th>错误信息</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in errorRuns" :key="r.id">
              <td class="time-cell">{{ formatTime(r.started_at) }}</td>
              <td>{{ r.agent_role }}</td>
              <td class="err-cell">{{ (r.error_msg || '').slice(0, 80) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty">暂无异常记录 👍</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminApi } from '../../api'

interface StatInfo { agentTotal: number; agentActive: number; todayCalls: number; todayErrors: number }
interface AgentInfo { role: string; name?: string; status: string; today_calls: number; today_errors: number; avg_duration_ms: number }
interface TaskInfo { job_id: string; job_name: string; status: string; next_run_time: string; last_execution?: { status: string; result_summary: string; error_msg: string; started_at: string; duration_ms: number } | null }
interface RankInfo { agent_role: string; total_tokens: number }
interface ErrorRun { id: number; agent_role: string; error_msg: string; started_at: string }

const stats = ref<StatInfo>({ agentTotal: 0, agentActive: 0, todayCalls: 0, todayErrors: 0 })
const agents = ref<AgentInfo[]>([])
const tasks = ref<TaskInfo[]>([])
const tokenRanking = ref<RankInfo[]>([])
const errorRuns = ref<ErrorRun[]>([])

function formatTime(iso: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function rankBarWidth(v: number, maxV: number): number {
  return maxV > 0 ? Math.round((v / maxV) * 100) : 0
}

onMounted(async () => {
  try {
    // 并行加载所有数据
    const [agentsRes, tasksRes, rankingRes, errorRunsRes] = await Promise.all([
      adminApi.getAgents(),
      adminApi.getScheduledTasks(),
      adminApi.getTokenRanking('today', 5),
      adminApi.getAgentRuns({ status: 'error', size: 10 }),
    ])

    // 解析智能体数据
    const agentList: AgentInfo[] = agentsRes.data?.agents || []
    agents.value = agentList
    stats.value.agentTotal = agentList.length
    stats.value.agentActive = agentList.filter(a => a.status === 'active').length
    stats.value.todayCalls = agentList.reduce((s, a) => s + (a.today_calls || 0), 0)
    stats.value.todayErrors = agentList.reduce((s, a) => s + (a.today_errors || 0), 0)

    // 解析定时任务
    tasks.value = tasksRes.data?.tasks || []

    // 解析 Token 排名
    tokenRanking.value = rankingRes.data?.ranking || []

    // 解析错误记录
    errorRuns.value = errorRunsRes.data?.runs || []
  } catch (e) {
    console.error('Dashboard load error:', e)
  }
})
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 24px; }

/* 统计卡片 */
.stat-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat-card { background: #fff; border-radius: 8px; padding: 20px; display: flex; align-items: center; gap: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.stat-card-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 700; color: #fff; flex-shrink: 0; }
.stat-card-icon.agents { background: #1890ff; }
.stat-card-icon.running { background: #52c41a; }
.stat-card-icon.calls { background: #722ed1; }
.stat-card-icon.errors { background: #faad14; }
.stat-card-body { flex: 1; }
.stat-card-value { font-size: 28px; font-weight: 700; color: #333; line-height: 1.2; }
.stat-card-value.text-red { color: #ab2029; }
.stat-card-label { font-size: 13px; color: #999; margin-top: 4px; }

/* 网格 */
.dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.panel { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.panel-title { font-size: 15px; font-weight: 600; margin: 0 0 16px; color: #333; }

/* 通用表格 */
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 8px 12px; background: #fafafa; color: #666; font-weight: 600; border-bottom: 2px solid #e8e8e8; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; color: #333; }
.time-cell { white-space: nowrap; color: #888; font-size: 12px; }
.err-cell { color: #ab2029; font-size: 12px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 徽章 */
.badge { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 500; }
.badge.active { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
.badge.paused { background: #fff7e6; color: #faad14; border: 1px solid #ffd591; }
.badge.running { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }

/* 执行状态徽章 */
.badge.exec-ok { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
.badge.exec-fail { background: #fff2f0; color: #ab2029; border: 1px solid #ffccc7; }
.no-exec { font-size: 12px; color: #bbb; }
.summary-cell { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; color: #666; }

/* 健康指示灯 */
.health-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
.health-dot.good { background: #52c41a; }
.health-dot.bad { background: #ab2029; }

/* 排名列表 */
.rank-list { display: flex; flex-direction: column; gap: 8px; }
.rank-item { display: flex; align-items: center; gap: 10px; padding: 6px 0; }
.rank-num { width: 22px; height: 22px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; color: #fff; flex-shrink: 0; }
.rank-num.num-1 { background: #ab2029; }
.rank-num.num-2 { background: #fa8c16; }
.rank-num.num-3 { background: #fadb14; color: #333; }
.rank-num.num-4, .rank-num.num-5 { background: #d9d9d9; color: #666; }
.rank-name { flex: 0 0 120px; font-size: 13px; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-val { flex: 0 0 100px; font-size: 12px; color: #888; text-align: right; }
.rank-bar-wrap { flex: 1; height: 6px; background: #f0f0f0; border-radius: 3px; overflow: hidden; }
.rank-bar { height: 100%; background: #1890ff; border-radius: 3px; transition: width 0.5s; }

.empty { padding: 32px; text-align: center; color: #999; font-size: 14px; }
</style>
