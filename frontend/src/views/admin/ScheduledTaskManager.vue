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
            <td class="summary-cell">
              <a v-if="t.last_execution?.status === 'success'" class="summary-link" @click="openDetail(t.last_execution)">
                {{ lastExecSummary(t) }}
              </a>
              <span v-else-if="t.last_execution" class="summary-err">{{ (t.last_execution.error_msg || '未知错误').slice(0, 40) }}</span>
              <span v-else>-</span>
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
        执行历史 — {{ friendlyName(historyJobId) }}
        <button class="btn btn-sm btn-link" @click="historyJobId = ''">收起</button>
      </h3>
      <table class="data-table" v-if="history.length">
        <thead>
          <tr><th>时间</th><th>状态</th><th>耗时</th><th>结果摘要</th><th>错误信息</th></tr>
        </thead>
        <tbody>
          <tr v-for="h in history" :key="h.id">
            <td class="time-cell">{{ formatTime(h.started_at) }}</td>
            <td><span class="badge" :class="h.status === 'success' ? 'success' : 'error'">{{ h.status === 'success' ? '成功' : '失败' }}</span></td>
            <td>{{ h.duration_ms ? (h.duration_ms / 1000).toFixed(1) + 's' : '-' }}</td>
            <td class="summary-cell">
              <a v-if="h.status === 'success'" class="summary-link" @click="openDetail(h)">
                {{ (h.result_summary || '完成').slice(0, 60) }}
              </a>
              <span v-else class="summary-err">{{ (h.error_msg || '').slice(0, 60) }}</span>
            </td>
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

    <!-- 详情弹窗 -->
    <div v-if="detailVisible" class="modal-overlay" @click.self="detailVisible = false">
      <div class="modal modal-lg">
        <div class="modal-header">
          <h3>执行详情</h3>
          <button class="btn btn-sm" @click="detailVisible = false">关闭</button>
        </div>
        <div class="modal-body">
          <!-- 加载中 -->
          <div v-if="detailLoading" class="detail-loading">加载中...</div>

          <!-- 无详情数据 -->
          <div v-else-if="!detailData" class="empty">暂无详情数据</div>

          <!-- 日增数据引擎 -->
          <div v-else-if="detailJobId === 'daily_data_tick'" class="detail-content">
            <div class="detail-meta">
              <span class="detail-label">执行日期：</span>{{ detailData.date || '-' }}
            </div>
            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-num">{{ detailData.transactions || 0 }}</div>
                <div class="stat-label">交易记录</div>
              </div>
              <div class="stat-card">
                <div class="stat-num">{{ detailData.behaviors || 0 }}</div>
                <div class="stat-label">行为记录</div>
              </div>
              <div class="stat-card">
                <div class="stat-num">{{ detailData.communications || 0 }}</div>
                <div class="stat-label">沟通记录</div>
              </div>
              <div class="stat-card">
                <div class="stat-num">{{ detailData.holding_updates || 0 }}</div>
                <div class="stat-label">持仓更新</div>
              </div>
              <div class="stat-card">
                <div class="stat-num">{{ detailData.events || 0 }}</div>
                <div class="stat-label">特殊事件</div>
              </div>
              <div class="stat-card">
                <div class="stat-num">{{ detailData.product_updates || 0 }}</div>
                <div class="stat-label">产品变更</div>
              </div>
              <div class="stat-card">
                <div class="stat-num">{{ detailData.announcements || 0 }}</div>
                <div class="stat-label">行内公告</div>
              </div>
            </div>
          </div>

          <!-- 日程自动生成 -->
          <div v-else-if="detailJobId === 'daily_schedule_gen'" class="detail-content">
            <div class="detail-meta">
              <span class="detail-label">排程日期：</span>{{ detailData.date || '-' }}
              &emsp;<span class="detail-label">涉及经理：</span>{{ detailData.manager_count || 0 }} 位
            </div>
            <table class="data-table" v-if="detailData.managers?.length">
              <thead><tr><th>经理</th><th>待办数</th><th>排程槽位数</th></tr></thead>
              <tbody>
                <tr v-for="m in detailData.managers" :key="m.manager_id">
                  <td>{{ m.manager_id }}</td>
                  <td>{{ m.task_count || 0 }}</td>
                  <td>{{ m.slot_count || 0 }}</td>
                </tr>
              </tbody>
            </table>
            <div v-else class="empty">暂无经理详情</div>
          </div>

          <!-- 金融资讯抓取 -->
          <div v-else-if="detailJobId === 'daily_news_fetch'" class="detail-content">
            <div class="detail-meta">
              <span class="detail-label">抓取日期：</span>{{ detailData.date || '-' }}
              &emsp;<span class="detail-label">总计：</span>{{ detailData.count || 0 }} 条
            </div>
            <div class="source-badges" v-if="detailData.sources">
              <span class="source-badge" v-for="(cnt, src) in detailData.sources" :key="src">
                {{ srcMap[src] || src }}：{{ cnt }} 条
              </span>
            </div>
            <ul class="headline-list" v-if="detailData.headlines?.length">
              <li v-for="(h, i) in detailData.headlines" :key="i" class="headline-item">
                <span class="headline-source">{{ srcMap[h.source] || h.source }}</span>
                <span class="headline-title">{{ h.title }}</span>
              </li>
            </ul>
            <div v-else class="empty">暂无资讯标题</div>
          </div>

          <!-- 资讯摘要生成 -->
          <div v-else-if="detailJobId === 'daily_digest_gen'" class="detail-content">
            <div class="detail-meta">
              <span class="detail-label">生成日期：</span>{{ detailData.date || '-' }}
              &emsp;<span class="detail-label">要闻数：</span>{{ detailData.headline_count || 0 }} 条
            </div>
            <ul class="headline-list" v-if="detailData.headlines?.length">
              <li v-for="(h, i) in detailData.headlines" :key="i" class="headline-item">
                <span class="headline-index">{{ i + 1 }}.</span>
                <span class="headline-title" v-if="typeof h === 'string'">{{ h }}</span>
                <span class="headline-title" v-else>{{ h.title || h.headline || JSON.stringify(h) }}</span>
              </li>
            </ul>
            <div v-else class="empty">暂无需闻详情</div>
          </div>

          <!-- 昨日回顾生成 -->
          <div v-else-if="detailJobId === 'daily_review_gen'" class="detail-content">
            <div class="detail-meta">
              <span class="detail-label">回顾日期：</span>{{ detailData.date || '-' }}
              &emsp;<span class="detail-label">成功：</span>{{ detailData.success_count || 0 }} / {{ detailData.total_count || 0 }} 位经理
            </div>
            <table class="data-table" v-if="detailData.managers?.length">
              <thead><tr><th>经理</th><th>生成结果</th></tr></thead>
              <tbody>
                <tr v-for="m in detailData.managers" :key="m.manager_id">
                  <td>{{ m.manager_id }}</td>
                  <td>
                    <span class="badge" :class="m.saved ? 'success' : 'error'">{{ m.saved ? '成功' : '失败' }}</span>
                    <span v-if="m.error" class="err-hint">{{ m.error }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="empty">暂无经理详情</div>
          </div>

          <!-- 客户洞察生成 -->
          <div v-else-if="detailJobId === 'weekly_insight_gen'" class="detail-content">
            <div class="detail-meta">
              <span class="detail-label">执行日期：</span>{{ detailData.date || '-' }}
              &emsp;<span class="detail-label">生成数量：</span>{{ detailData.generated_count || 0 }}
            </div>
            <ul class="headline-list" v-if="detailData.customers?.length">
              <li v-for="(c, i) in detailData.customers" :key="i" class="headline-item">
                <span v-if="typeof c === 'object'">{{ c.name || c.cust_id || c.cust_name || JSON.stringify(c) }}</span>
                <span v-else>{{ c }}</span>
              </li>
            </ul>
            <div v-else class="empty">暂无客户详情</div>
          </div>

          <!-- 其他 / 通用 JSON 展示 -->
          <div v-else class="detail-content">
            <pre class="detail-json">{{ JSON.stringify(detailData, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminApi } from '../../api'

interface TaskInfo { job_id: string; job_name: string; trigger: string; status: string; next_run_time: string; last_execution?: { status: string; result_summary: string; error_msg: string; started_at: string; duration_ms: number; id?: number } | null }
interface HistoryItem { id: number; status: string; result_summary: string; result_detail?: string; error_msg: string; started_at: string; finished_at: string; duration_ms: number }

const tasks = ref<TaskInfo[]>([])
const historyJobId = ref('')
const history = ref<HistoryItem[]>([])
const historyPage = ref(1)
const historySize = ref(20)
const historyTotal = ref(0)

// 详情弹窗
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref<any>(null)
const detailJobId = ref('')

const srcMap: Record<string, string> = { tushare: 'Tushare', sina: '新浪财经', eastmoney: '东方财富' }

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
    const s = le.result_summary || ''
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

async function openDetail(record: { id?: number; result_summary?: string; result_detail?: string }) {
  detailVisible.value = true
  detailLoading.value = true
  detailData.value = null
  detailJobId.value = ''

  try {
    // 优先用已加载的 detail（历史列表已包含）
    if (record.result_detail) {
      try {
        detailData.value = JSON.parse(record.result_detail)
      } catch {
        detailData.value = { raw: record.result_detail }
      }
      detailJobId.value = historyJobId.value
      detailLoading.value = false
      return
    }

    // 否则从 API 获取（主列表点击时，last_execution 没有 id）
    if (!record.id) {
      detailLoading.value = false
      detailData.value = { _note: '该记录尚未产生详情数据，请通过历史列表查看' }
      return
    }

    const res = await adminApi.getTaskHistoryDetail(record.id)
    if (res.data?.result_detail) {
      detailData.value = res.data.result_detail
    }
    detailJobId.value = res.data?.job_id || ''
  } catch (e) {
    console.error('load detail error:', e)
    detailData.value = null
  } finally {
    detailLoading.value = false
  }
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
.badge.exec-ok { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
.badge.exec-fail { background: #fff2f0; color: #ab2029; border: 1px solid #ffccc7; }
.no-log { font-size: 12px; color: #bbb; }
.summary-cell { max-width: 160px; font-size: 12px; color: #666; }
.summary-err { color: #ab2029; font-size: 12px; }
.summary-link { color: #1890ff; cursor: pointer; text-decoration: none; }
.summary-link:hover { text-decoration: underline; color: #40a9ff; }
.err-hint { color: #ab2029; font-size: 11px; margin-left: 8px; }

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

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center; z-index: 2000; }
.modal { background: #fff; border-radius: 8px; width: 560px; max-width: 90vw; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 4px 24px rgba(0,0,0,.15); }
.modal-sm { width: 380px; }
.modal-lg { width: 720px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #f0f0f0; flex-shrink: 0; }
.modal-header h3 { margin: 0; font-size: 16px; }
.modal-body { padding: 20px; overflow-y: auto; flex: 1; }

/* Detail */
.detail-loading { text-align: center; padding: 40px; color: #999; }
.detail-content { font-size: 13px; }
.detail-meta { margin-bottom: 16px; padding: 10px 14px; background: #fafafa; border-radius: 6px; font-size: 13px; color: #555; }
.detail-label { font-weight: 600; color: #333; }

/* Stats Grid */
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat-card { background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 8px; padding: 16px 12px; text-align: center; }
.stat-num { font-size: 26px; font-weight: 700; color: #52c41a; }
.stat-label { font-size: 12px; color: #888; margin-top: 4px; }

/* Headlines */
.headline-list { list-style: none; padding: 0; margin: 0; }
.headline-item { padding: 8px 12px; border-bottom: 1px solid #f5f5f5; display: flex; align-items: flex-start; gap: 8px; }
.headline-item:last-child { border-bottom: none; }
.headline-index { color: #999; font-weight: 600; min-width: 24px; }
.headline-source { display: inline-block; padding: 1px 8px; border-radius: 3px; font-size: 11px; background: #e6f7ff; color: #1890ff; white-space: nowrap; flex-shrink: 0; }
.headline-title { flex: 1; line-height: 1.5; }

/* Source badges */
.source-badges { display: flex; gap: 10px; margin-bottom: 16px; }
.source-badge { padding: 3px 12px; border-radius: 12px; font-size: 12px; background: #f0f5ff; color: #2f54eb; }

/* JSON fallback */
.detail-json { background: #fafafa; border: 1px solid #e8e8e8; border-radius: 6px; padding: 14px; font-size: 12px; white-space: pre-wrap; word-break: break-all; max-height: 50vh; overflow-y: auto; margin: 0; }
</style>
