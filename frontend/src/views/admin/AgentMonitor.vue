<template>
  <div class="page">
    <h2 class="page-title">运行监测</h2>

    <!-- 筛选栏 -->
    <div class="filters">
      <select v-model="filterAgentRole" class="filter-input">
        <option value="">全部智能体</option>
        <option v-for="a in agentOptions" :key="a.role" :value="a.role">{{ a.name || a.role }}</option>
      </select>
      <select v-model="filterStatus" class="filter-input">
        <option value="">全部状态</option>
        <option value="success">成功</option>
        <option value="error">异常</option>
      </select>
      <input type="date" v-model="filterDateFrom" class="filter-input" />
      <input type="date" v-model="filterDateTo" class="filter-input" />
      <button class="btn btn-primary" @click="search">查询</button>
      <button class="btn" @click="exportCSV">导出 CSV</button>
    </div>

    <!-- 调用记录表格 -->
    <div class="panel">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>智能体</th>
            <th>方法</th>
            <th>状态</th>
            <th>输入摘要</th>
            <th>时间</th>
            <th>耗时</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in runs" :key="r.id" @click="toggleDetail(r)" class="clickable-row">
            <td>{{ r.id }}</td>
            <td>{{ r.agent_role }}</td>
            <td class="mono">{{ r.method }}</td>
            <td><span class="badge" :class="r.status">{{ r.status }}</span></td>
            <td class="summary-cell">{{ (r.input_summary || '').slice(0, 60) }}</td>
            <td class="time-cell">{{ formatTime(r.started_at) }}</td>
            <td>{{ r.duration_ms ? (r.duration_ms / 1000).toFixed(1) + 's' : '-' }}</td>
            <td><button class="btn btn-sm btn-link" @click.stop="toggleDetail(r)">详情</button></td>
          </tr>
        </tbody>
      </table>
      <div v-if="!runs.length" class="empty">暂无调用记录</div>

      <!-- 分页 -->
      <div class="pagination" v-if="total > pageSize">
        <button class="btn btn-sm" :disabled="page <= 1" @click="loadPage(page - 1)">上一页</button>
        <span class="page-info">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
        <button class="btn btn-sm" :disabled="page * pageSize >= total" @click="loadPage(page + 1)">下一页</button>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="detailRun" class="modal-overlay" @click.self="detailRun = null">
      <div class="modal">
        <div class="modal-header">
          <h3>运行详情 #{{ detailRun.id }}</h3>
          <button class="btn btn-sm" @click="detailRun = null">关闭</button>
        </div>
        <div class="modal-body">
          <div class="detail-grid">
            <div class="detail-row"><span class="dl">智能体</span><span>{{ detailRun.agent_role }}</span></div>
            <div class="detail-row"><span class="dl">方法</span><span class="mono">{{ detailRun.method }}</span></div>
            <div class="detail-row"><span class="dl">状态</span><span class="badge" :class="detailRun.status">{{ detailRun.status }}</span></div>
            <div class="detail-row"><span class="dl">开始时间</span><span>{{ formatTime(detailRun.started_at) }}</span></div>
            <div class="detail-row"><span class="dl">结束时间</span><span>{{ formatTime(detailRun.finished_at) }}</span></div>
            <div class="detail-row"><span class="dl">耗时</span><span>{{ detailRun.duration_ms ? (detailRun.duration_ms / 1000).toFixed(1) + 's' : '-' }}</span></div>
          </div>
          <div class="detail-section" v-if="detailRun.input_summary">
            <h4>输入摘要</h4>
            <pre class="detail-pre">{{ detailRun.input_summary }}</pre>
          </div>
          <div class="detail-section" v-if="detailRun.output_summary">
            <h4>输出摘要</h4>
            <pre class="detail-pre">{{ detailRun.output_summary }}</pre>
          </div>
          <div class="detail-section" v-if="detailRun.error_msg">
            <h4 class="text-red">错误信息</h4>
            <pre class="detail-pre error-pre">{{ detailRun.error_msg }}</pre>
          </div>
          <div class="detail-section" v-if="detailTokens.length">
            <h4>Token 消耗</h4>
            <table class="data-table">
              <thead><tr><th>模型</th><th>Prompt Tokens</th><th>Completion Tokens</th><th>Total Tokens</th></tr></thead>
              <tbody>
                <tr v-for="t in detailTokens" :key="t.model_name">
                  <td class="mono">{{ t.model_name }}</td>
                  <td>{{ t.prompt_tokens?.toLocaleString() }}</td>
                  <td>{{ t.completion_tokens?.toLocaleString() }}</td>
                  <td><strong>{{ t.total_tokens?.toLocaleString() }}</strong></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminApi } from '../../api'

interface RunItem { id: number; agent_role: string; method: string; status: string; input_summary: string; output_summary?: string; error_msg?: string; started_at: string; finished_at?: string; duration_ms: number; token_usage?: TokenItem[] }
interface TokenItem { model_name: string; prompt_tokens: number; completion_tokens: number; total_tokens: number }
interface AgentOpt { role: string; name?: string }

const runs = ref<RunItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const agentOptions = ref<AgentOpt[]>([])

const filterAgentRole = ref('')
const filterStatus = ref('')
const filterDateFrom = ref('')
const filterDateTo = ref('')

const detailRun = ref<RunItem | null>(null)
const detailTokens = ref<TokenItem[]>([])

function formatTime(iso: string): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

async function loadAgents() {
  try {
    const res = await adminApi.getAgents()
    agentOptions.value = res.data?.agents || []
  } catch (e) { console.error('load agents error:', e) }
}

async function search() { loadPage(1) }

async function loadPage(p: number) {
  page.value = p
  try {
    const params: Record<string, any> = { page: p, size: pageSize.value }
    if (filterAgentRole.value) params.agent_role = filterAgentRole.value
    if (filterStatus.value) params.status = filterStatus.value
    if (filterDateFrom.value) params.date_from = filterDateFrom.value
    if (filterDateTo.value) params.date_to = filterDateTo.value
    const res = await adminApi.getAgentRuns(params)
    runs.value = res.data?.runs || []
    total.value = res.data?.total || 0
  } catch (e) { console.error('load runs error:', e) }
}

async function toggleDetail(r: RunItem) {
  if (detailRun.value?.id === r.id) {
    detailRun.value = null
    detailTokens.value = []
    return
  }
  try {
    const res = await adminApi.getAgentRunDetail(r.id)
    detailRun.value = res.data as RunItem
    detailTokens.value = (res.data as any)?.token_usage || []
  } catch (e) { console.error('load run detail error:', e) }
}

function exportCSV() {
  adminApi.exportAgentRuns(
    filterAgentRole.value || undefined,
    filterStatus.value || undefined,
    filterDateFrom.value || undefined,
    filterDateTo.value || undefined
  ).catch(e => console.error('export error:', e))
}

onMounted(() => { loadAgents(); loadPage(1) })
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.page-title { font-size: 18px; font-weight: 700; color: #333; margin: 0; }

.filters { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.filter-input { padding: 6px 12px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 13px; background: #fff; }

.panel { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }

.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 8px 12px; background: #fafafa; color: #666; font-weight: 600; border-bottom: 2px solid #e8e8e8; white-space: nowrap; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; color: #333; }
.mono { font-family: 'SF Mono', monospace; font-size: 12px; color: #666; }
.time-cell { white-space: nowrap; color: #888; font-size: 12px; }
.summary-cell { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.clickable-row { cursor: pointer; transition: background 0.15s; }
.clickable-row:hover { background: #fafafa; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 500; text-transform: uppercase; }
.badge.success { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
.badge.error { background: #fff2f0; color: #ab2029; border: 1px solid #ffccc7; }

.btn { display: inline-flex; align-items: center; padding: 4px 12px; border: 1px solid #d9d9d9; border-radius: 4px; background: #fff; color: #333; font-size: 12px; cursor: pointer; white-space: nowrap; gap: 4px; transition: all 0.2s; }
.btn:hover { border-color: #ab2029; color: #ab2029; }
.btn-sm { padding: 2px 8px; font-size: 12px; }
.btn-primary { background: #ab2029; color: #fff; border-color: #ab2029; }
.btn-primary:hover { background: #8b1a22; }
.btn-link { color: #1890ff; border: none; background: none; padding: 2px 4px; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.pagination { display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 16px; }
.page-info { font-size: 13px; color: #666; }

/* 弹窗 */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: flex-start; justify-content: center; z-index: 1000; padding-top: 60px; }
.modal { background: #fff; border-radius: 12px; width: 700px; max-height: 80vh; display: flex; flex-direction: column; box-shadow: 0 8px 40px rgba(0,0,0,0.15); }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; border-bottom: 1px solid #e8e8e8; }
.modal-header h3 { margin: 0; font-size: 16px; }
.modal-body { padding: 24px; overflow-y: auto; flex: 1; }

.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 20px; margin-bottom: 20px; }
.detail-row { display: flex; gap: 8px; font-size: 13px; }
.dl { color: #888; flex-shrink: 0; min-width: 60px; }

.detail-section { margin-top: 16px; }
.detail-section h4 { font-size: 13px; font-weight: 600; color: #555; margin: 0 0 8px; }
.detail-pre { background: #f5f5f5; border-radius: 6px; padding: 12px; font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-break: break-all; margin: 0; max-height: 200px; overflow-y: auto; }
.error-pre { background: #fff2f0; color: #ab2029; }

.text-red { color: #ab2029; }

.empty { padding: 32px; text-align: center; color: #999; font-size: 14px; }
</style>
