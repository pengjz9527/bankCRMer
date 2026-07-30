<template>
  <div class="page">
    <h2 class="page-title">费用分析</h2>

    <!-- 统计概览卡片 -->
    <div class="stat-cards">
      <div class="stat-card" v-for="c in statCards" :key="c.label">
        <div class="stat-card-val">{{ c.value.toLocaleString() }}</div>
        <div class="stat-card-lbl">{{ c.label }}</div>
        <div class="stat-card-sub">{{ c.sub }}</div>
      </div>
    </div>

    <div class="charts-row">
      <!-- Token Top5 柱状图 -->
      <div class="panel chart-panel">
        <div class="panel-header">
          <h3 class="panel-title">Token 消耗 Top5</h3>
          <select v-model="rankPeriod" @change="loadRanking" class="filter-input">
            <option value="today">今日</option>
            <option value="week">本周</option>
            <option value="month">本月</option>
          </select>
        </div>
        <div v-if="ranking.length" class="bar-chart">
          <div v-for="r in ranking" :key="r.agent_role" class="bar-row">
            <span class="bar-label">{{ r.agent_role }}</span>
            <span class="bar-track">
              <span class="bar-fill" :style="{ width: barPct(r.total_tokens) + '%' }">
                <span class="bar-val">{{ r.total_tokens.toLocaleString() }}</span>
              </span>
            </span>
          </div>
        </div>
        <div v-else class="empty">暂无数据</div>
      </div>

      <!-- 30 天趋势线图 -->
      <div class="panel chart-panel">
        <div class="panel-header">
          <h3 class="panel-title">30 天 Token 消耗趋势</h3>
        </div>
        <div v-if="trend.length" class="line-chart">
          <div class="line-chart-svg-wrapper">
            <svg viewBox="0 0 600 160" class="line-svg">
              <polyline
                :points="trendLinePoints"
                fill="none"
                stroke="#ab2029"
                stroke-width="2"
                stroke-linejoin="round"
              />
              <template v-for="(p, i) in trendPoints" :key="i">
                <circle :cx="p.x" :cy="p.y" r="3" fill="#ab2029" />
              </template>
            </svg>
          </div>
          <div class="line-labels">
            <span v-for="(t, i) in trendLabelSamples" :key="i" class="line-label">{{ t }}</span>
          </div>
        </div>
        <div v-else class="empty">暂无数据</div>
      </div>
    </div>

    <!-- 明细表格 -->
    <div class="panel">
      <div class="panel-header">
        <h3 class="panel-title">Token 消耗明细</h3>
        <div class="filter-row">
          <select v-model="detailAgentRole" class="filter-input">
            <option value="">全部智能体</option>
            <option v-for="a in agentOptions" :key="a.role" :value="a.role">{{ a.name || a.role }}</option>
          </select>
          <input type="date" v-model="detailDateFrom" class="filter-input" />
          <input type="date" v-model="detailDateTo" class="filter-input" />
          <button class="btn btn-primary" @click="loadDetails(1)">查询</button>
        </div>
      </div>
      <table class="data-table" v-if="details.length">
        <thead>
          <tr><th>ID</th><th>智能体</th><th>模型</th><th>Prompt Tokens</th><th>Completion</th><th>Total</th><th>时间</th></tr>
        </thead>
        <tbody>
          <tr v-for="d in details" :key="d.id">
            <td>{{ d.id }}</td>
            <td>{{ d.agent_role }}</td>
            <td class="mono">{{ d.model_name }}</td>
            <td>{{ (d.prompt_tokens || 0).toLocaleString() }}</td>
            <td>{{ (d.completion_tokens || 0).toLocaleString() }}</td>
            <td><strong>{{ (d.total_tokens || 0).toLocaleString() }}</strong></td>
            <td class="time-cell">{{ formatTime(d.recorded_at) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!details.length" class="empty">暂无 Token 消耗明细</div>
      <div class="pagination" v-if="detailTotal > detailSize">
        <button class="btn btn-sm" :disabled="detailPage <= 1" @click="loadDetails(detailPage - 1)">上一页</button>
        <span class="page-info">{{ detailPage }} / {{ Math.ceil(detailTotal / detailSize) }}</span>
        <button class="btn btn-sm" :disabled="detailPage * detailSize >= detailTotal" @click="loadDetails(detailPage + 1)">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { adminApi } from '../../api'

interface RankItem { agent_role: string; total_tokens: number; call_count: number }
interface TrendDay { date: string; total_tokens: number; by_agent: Record<string, number> }
interface DetailItem { id: number; agent_role: string; model_name: string; prompt_tokens: number; completion_tokens: number; total_tokens: number; recorded_at: string }
interface AgentOpt { role: string; name?: string }

const statCards = ref([
  { label: '今日总量', value: 0, sub: 'tokens' },
  { label: '本周总量', value: 0, sub: 'tokens' },
  { label: '本月总量', value: 0, sub: 'tokens' },
  { label: '平均每次', value: 0, sub: 'tokens/call' },
])

const rankPeriod = ref('today')
const ranking = ref<RankItem[]>([])
const trend = ref<TrendDay[]>([])
const details = ref<DetailItem[]>([])
const detailPage = ref(1)
const detailSize = ref(20)
const detailTotal = ref(0)
const detailAgentRole = ref('')
const detailDateFrom = ref('')
const detailDateTo = ref('')
const agentOptions = ref<AgentOpt[]>([])

function formatTime(iso: string): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

function barPct(v: number): number {
  const maxV = ranking.value.length > 0 ? ranking.value[0].total_tokens : 1
  return maxV > 0 ? Math.round((v / maxV) * 100) : 0
}

// 趋势图计算
const trendPoints = computed(() => {
  if (!trend.value.length) return []
  const maxV = Math.max(...trend.value.map(t => t.total_tokens), 1)
  const w = 600; const h = 160; const padX = 10; const padY = 10
  const usableW = w - padX * 2; const usableH = h - padY * 2
  return trend.value.map((t, i) => ({
    x: padX + (i / Math.max(trend.value.length - 1, 1)) * usableW,
    y: h - padY - (t.total_tokens / maxV) * usableH,
  }))
})

const trendLinePoints = computed(() => {
  return trendPoints.value.map(p => `${p.x},${p.y}`).join(' ')
})

const trendLabelSamples = computed(() => {
  if (!trend.value.length) return []
  const n = trend.value.length
  const step = Math.max(1, Math.floor(n / 5))
  const indices = []
  for (let i = 0; i < n; i += step) indices.push(i)
  if (indices[indices.length - 1] !== n - 1) indices.push(n - 1)
  return indices.map(i => trend.value[i].date.slice(5)) // MM-DD
})

async function loadStats() {
  try {
    const [todayRes, weekRes, monthRes] = await Promise.all([
      adminApi.getTokenStats('today'),
      adminApi.getTokenStats('week'),
      adminApi.getTokenStats('month'),
    ])
    const today = todayRes.data || {}
    const week = weekRes.data || {}
    const month = monthRes.data || {}
    statCards.value = [
      { label: '今日总量', value: today.total_tokens || 0, sub: 'tokens' },
      { label: '本周总量', value: week.total_tokens || 0, sub: 'tokens' },
      { label: '本月总量', value: month.total_tokens || 0, sub: 'tokens' },
      { label: '平均每次', value: today.avg_tokens_per_call || 0, sub: 'tokens/call' },
    ]
  } catch (e) { console.error('load stats error:', e) }
}

async function loadRanking() {
  try {
    const res = await adminApi.getTokenRanking(rankPeriod.value, 5)
    ranking.value = res.data?.ranking || []
  } catch (e) { console.error('load ranking error:', e) }
}

async function loadTrend() {
  try {
    const res = await adminApi.getTokenTrend(30)
    trend.value = res.data?.trend || []
  } catch (e) { console.error('load trend error:', e) }
}

async function loadDetails(p: number) {
  detailPage.value = p
  try {
    const params: Record<string, any> = { page: p, size: detailSize.value }
    if (detailAgentRole.value) params.agent_role = detailAgentRole.value
    if (detailDateFrom.value) params.date_from = detailDateFrom.value
    if (detailDateTo.value) params.date_to = detailDateTo.value
    const res = await adminApi.getTokenDetails(params)
    details.value = res.data?.details || []
    detailTotal.value = res.data?.total || 0
  } catch (e) { console.error('load details error:', e) }
}

async function loadAgentOptions() {
  try {
    const res = await adminApi.getAgents()
    agentOptions.value = res.data?.agents || []
  } catch (e) { console.error('load agents error:', e) }
}

onMounted(() => {
  loadStats(); loadRanking(); loadTrend(); loadDetails(1); loadAgentOptions()
})
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.page-title { font-size: 18px; font-weight: 700; color: #333; margin: 0; }

/* 统计卡片 */
.stat-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.stat-card { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); text-align: center; }
.stat-card-val { font-size: 28px; font-weight: 700; color: #333; }
.stat-card-lbl { font-size: 13px; color: #666; margin-top: 4px; }
.stat-card-sub { font-size: 11px; color: #999; }

/* Charts row */
.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.chart-panel { min-height: 260px; }

.panel { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.panel-title { font-size: 15px; font-weight: 600; margin: 0; color: #333; }

.filter-input { padding: 4px 10px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 13px; background: #fff; }
.filter-row { display: flex; align-items: center; gap: 8px; }

/* 柱状图 */
.bar-chart { display: flex; flex-direction: column; gap: 10px; }
.bar-row { display: flex; align-items: center; gap: 10px; }
.bar-label { width: 120px; font-size: 12px; color: #555; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex-shrink: 0; }
.bar-track { flex: 1; height: 24px; background: #f0f0f0; border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; background: linear-gradient(90deg, #ab2029, #e8555f); border-radius: 4px; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; min-width: 40px; transition: width 0.5s; }
.bar-val { font-size: 11px; color: #fff; font-weight: 600; white-space: nowrap; }

/* 折线图 */
.line-chart { position: relative; }
.line-chart-svg-wrapper { width: 100%; }
.line-svg { width: 100%; height: auto; display: block; }
.line-labels { display: flex; justify-content: space-between; padding: 0 2%; }
.line-label { font-size: 10px; color: #999; }

/* 表格 */
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 8px 12px; background: #fafafa; color: #666; font-weight: 600; border-bottom: 2px solid #e8e8e8; white-space: nowrap; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; color: #333; }
.mono { font-family: 'SF Mono', monospace; font-size: 12px; color: #666; }
.time-cell { white-space: nowrap; color: #888; font-size: 12px; }

.btn { display: inline-flex; align-items: center; padding: 4px 12px; border: 1px solid #d9d9d9; border-radius: 4px; background: #fff; color: #333; font-size: 12px; cursor: pointer; white-space: nowrap; gap: 4px; transition: all 0.2s; }
.btn:hover { border-color: #ab2029; color: #ab2029; }
.btn-sm { padding: 2px 8px; font-size: 12px; }
.btn-primary { background: #ab2029; color: #fff; border-color: #ab2029; }
.btn-primary:hover { background: #8b1a22; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.pagination { display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 16px; }
.page-info { font-size: 13px; color: #666; }

.empty { padding: 40px; text-align: center; color: #999; font-size: 14px; }
</style>
