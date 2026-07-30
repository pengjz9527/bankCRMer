<template>
  <div class="page">
    <h2 class="page-title">定时任务管理</h2>

    <div class="panel">
      <table class="data-table">
        <thead>
          <tr>
            <th>任务名称</th>
            <th>执行规则</th>
            <th>调度状态</th>
            <th>最近执行</th>
            <th>执行结果</th>
            <th>下次运行</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tasks" :key="t.job_id">
            <td><strong>{{ friendlyName(t.job_id) }}</strong></td>
            <td class="mono">{{ friendlyTrigger(t.trigger) }}</td>
            <td><span class="badge" :class="t.status">{{ t.status === 'running' ? '运行中' : '已暂停' }}</span></td>
            <td>
              <span v-if="t.last_execution" class="badge" :class="t.last_execution.status === 'success' ? 'exec-ok' : 'exec-fail'">
                {{ t.last_execution.status === 'success' ? '成功' : '失败' }}
              </span>
              <span v-else class="no-log">-</span>
            </td>
            <td class="summary-cell" :title="t.last_execution?.result_summary || t.last_execution?.error_msg || ''">
              {{ lastExecSummary(t) }}
            </td>
            <td>{{ t.next_run_time ? formatTime(t.next_run_time) : '-' }}</td>
            <td>
              <button v-if="t.status === 'running'" class="btn btn-sm btn-warn" @click="pauseTask(t)">暂停</button>
              <button v-else class="btn btn-sm btn-primary" @click="resumeTask(t)">恢复</button>
              <button class="btn btn-sm" @click="triggerTask(t)">立即执行</button>
              <button class="btn btn-sm btn-link" @click="toggleHistory(t)">历史</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!tasks.length" class="empty">暂无定时任务数据</div>
    </div>

    <!-- 执行历史面板 -->
    <div v-if="historyJobId" class="panel history-panel">
      <h3 class="panel-title">
        执行历史 — {{ historyJobId }}
        <button class="btn btn-sm btn-link" @click="historyJobId = ''">收起</button>
      </h3>
      <table class="data-table" v-if="history.length">
        <thead>
          <tr><th>时间</th><th>状态</th><th>耗时</th><th>结果摘要</th><th>错误信息</th></tr>
        </thead>
        <tbody>
          <tr v-for="h in history" :key="h.id">
            <td class="time-cell">{{ formatTime(h.started_at) }}</td>
            <td><span class="badge" :class="h.status === 'success' ? 'success' : 'error'">{{ h.status }}</span></td>
            <td>{{ h.duration_ms ? (h.duration_ms / 1000).toFixed(1) + 's' : '-' }}</td>
            <td>{{ (h.result_summary || '').slice(0, 60) }}</td>
            <td class="err-cell">{{ (h.error_msg || '').slice(0, 80) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无执行历史</div>
      <div class="pagination" v-if="historyTotal > historySize">
        <button class="btn btn-sm" :disabled="historyPage <= 1" @click="loadHistory(historyPage - 1)">上一页</button>
        <span class="page-info">{{ historyPage }} / {{ Math.ceil(historyTotal / historySize) }}</span>
        <button class="btn btn-sm" :disabled="historyPage * historySize >= historyTotal" @click="loadHistory(historyPage + 1)">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminApi } from '../../api'

interface TaskInfo { job_id: string; job_name: string; trigger: string; status: string; next_run_time: string; last_execution?: { status: string; result_summary: string; error_msg: string; started_at: string; duration_ms: number } | null }
interface HistoryItem { id: number; status: string; result_summary: string; error_msg: string; started_at: string; finished_at: string; duration_ms: number }

const tasks = ref<TaskInfo[]>([])
const historyJobId = ref('')
const history = ref<HistoryItem[]>([])
const historyPage = ref(1)
const historySize = ref(20)
const historyTotal = ref(0)

function formatTime(iso: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN')
}

const taskNameMap: Record<string, string> = {
  daily_data_tick: '日增数据引擎',
  daily_schedule_gen: '日程自动生成',
  daily_news_fetch: '金融资讯抓取',
  daily_digest_gen: '资讯摘要生成',
  daily_review_gen: '昨日回顾生成',
  weekly_insight_gen: '客户洞察生成',
}

function friendlyName(jobId: string): string {
  return taskNameMap[jobId] || jobId
}

function friendlyTrigger(trigger: string): string {
  if (!trigger) return '-'
  // 解析 cron[hour='7', minute='30'] 格式
  const hour = trigger.match(/hour='?(\d+)'?/)
  const minute = trigger.match(/minute='?(\d+)'?/)
  const dow = trigger.match(/day_of_week='?(\w+)'?/)
  if (dow) {
    const dayMap: Record<string, string> = { sun: '周日', mon: '周一', tue: '周二', wed: '周三', thu: '周四', fri: '周五', sat: '周六' }
    return `每${dayMap[dow[1]] || dow[1]} ${hour?.[1] || '00'}:${minute?.[1] || '00'}`
  }
  if (hour) return `每日 ${hour[1]}:${minute?.[1] || '00'}`
  return trigger
}

function lastExecSummary(t: TaskInfo): string {
  const le = t.last_execution
  if (!le) return '-'
  if (le.status === 'success') {
    // 尝试美化 result_summary：如 {"transactions":5} → 交易5笔
    const s = le.result_summary || ''
    // 如果看起来是 dict 字符串，尝试解析
    try {
      const obj = JSON.parse(s.replace(/'/g, '"'))
      const parts: string[] = []
      const nameMap: Record<string, string> = {
        transactions: '交易', behaviors: '行为', communications: '沟通',
        holding_updates: '持仓更新', events: '事件',
      }
      for (const [k, v] of Object.entries(obj)) {
        if (typeof v === 'number' && v > 0) parts.push(`${nameMap[k] || k}${v}`)
      }
      if (parts.length) return parts.join('，')
    } catch {}
    return s.slice(0, 40) || '完成'
  }
  return (le.error_msg || '未知错误').slice(0, 40)
}

async function loadTasks() {
  try {
    const res = await adminApi.getScheduledTasks()
    tasks.value = res.data?.tasks || []
  } catch (e) { console.error('load tasks error:', e) }
}

async function loadHistory(page = 1) {
  if (!historyJobId.value) return
  try {
    historyPage.value = page
    const res = await adminApi.getTaskHistory(historyJobId.value, page, historySize.value)
    history.value = res.data?.history || []
    historyTotal.value = res.data?.total || 0
  } catch (e) { console.error('load history error:', e) }
}

function toggleHistory(t: TaskInfo) {
  if (historyJobId.value === t.job_id) {
    historyJobId.value = ''
    history.value = []
  } else {
    historyJobId.value = t.job_id
    loadHistory(1)
  }
}

async function pauseTask(t: TaskInfo) {
  try {
    await adminApi.pauseTask(t.job_id)
    await loadTasks()
  } catch (e) { console.error('pause error:', e) }
}

async function resumeTask(t: TaskInfo) {
  try {
    await adminApi.resumeTask(t.job_id)
    await loadTasks()
  } catch (e) { console.error('resume error:', e) }
}

async function triggerTask(t: TaskInfo) {
  try {
    await adminApi.triggerTask(t.job_id)
    // 等待一下再刷新
    setTimeout(() => loadTasks(), 1000)
  } catch (e) { console.error('trigger error:', e) }
}

onMounted(() => { loadTasks() })
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.page-title { font-size: 18px; font-weight: 700; color: #333; margin: 0; }
.panel { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.panel-title { font-size: 15px; font-weight: 600; margin: 0 0 16px; display: flex; align-items: center; gap: 12px; }

.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 8px 12px; background: #fafafa; color: #666; font-weight: 600; border-bottom: 2px solid #e8e8e8; white-space: nowrap; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; color: #333; }
.mono { font-family: 'SF Mono', monospace; font-size: 12px; color: #666; }
.time-cell { white-space: nowrap; color: #888; font-size: 12px; }
.err-cell { color: #ab2029; font-size: 12px; max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 500; }
.badge.running { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
.badge.paused { background: #fff7e6; color: #faad14; border: 1px solid #ffd591; }
.badge.success { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
.badge.error { background: #fff2f0; color: #ab2029; border: 1px solid #ffccc7; }

/* 最近执行状态徽章 */
.badge.exec-ok { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
.badge.exec-fail { background: #fff2f0; color: #ab2029; border: 1px solid #ffccc7; }
.no-log { font-size: 12px; color: #bbb; }
.summary-cell { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; color: #666; cursor: default; }

.btn { display: inline-flex; align-items: center; padding: 4px 12px; border: 1px solid #d9d9d9; border-radius: 4px; background: #fff; color: #333; font-size: 12px; cursor: pointer; white-space: nowrap; gap: 4px; transition: all 0.2s; }
.btn:hover { border-color: #ab2029; color: #ab2029; }
.btn-sm { padding: 2px 8px; font-size: 12px; }
.btn-primary { background: #ab2029; color: #fff; border-color: #ab2029; }
.btn-primary:hover { background: #8b1a22; }
.btn-warn { background: #faad14; color: #fff; border-color: #faad14; }
.btn-warn:hover { background: #d48806; }
.btn-link { color: #1890ff; border: none; background: none; padding: 2px 4px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.history-panel { margin-top: 0; background: #fafafa; }
.pagination { display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 16px; }
.page-info { font-size: 13px; color: #666; }

.empty { padding: 32px; text-align: center; color: #999; font-size: 14px; }
</style>
