<template>
  <div class="page">
    <h2 class="page-title">智能体配置管理</h2>
    <div class="layout">
      <!-- 左侧智能体列表 -->
      <div class="agent-list">
        <div
          v-for="a in agents"
          :key="a.role"
          class="agent-card"
          :class="{ selected: selectedRole === a.role }"
          @click="selectAgent(a.role)"
        >
          <div class="agent-card-header">
            <span class="agent-card-role">{{ a.role }}</span>
            <span class="badge" :class="a.status">{{ a.status === 'active' ? '运行中' : '已暂停' }}</span>
          </div>
          <div class="agent-card-name">{{ a.name }}</div>
          <div class="agent-card-stats">
            <span>今日调用: {{ a.today_calls ?? 0 }}</span>
            <span v-if="a.today_errors" class="text-red">异常: {{ a.today_errors }}</span>
          </div>
        </div>
      </div>

      <!-- 右侧详情面板 -->
      <div class="detail-panel" v-if="detail">
        <div class="detail-header">
          <h3>{{ detail.name }} ({{ detail.role }})</h3>
          <button
            class="btn"
            :class="detail.status === 'active' ? 'btn-warn' : 'btn-primary'"
            @click="togglePause"
          >
            {{ detail.status === 'active' ? '暂停' : '恢复' }}
          </button>
        </div>

        <div class="detail-meta">
          <div class="meta-row"><span class="meta-label">描述</span><span>{{ detail.description || '-' }}</span></div>
          <div class="meta-row"><span class="meta-label">模型</span><span>{{ detail.model_name }}</span></div>
          <div class="meta-row"><span class="meta-label">触发器</span><span>{{ detail.triggers?.join(', ') || '-' }}</span></div>
          <div class="meta-row"><span class="meta-label">技能</span><span>{{ detail.skills?.join(', ') || '-' }}</span></div>
          <div class="meta-row"><span class="meta-label">限流</span><span>{{ detail.rate_limit }} 次/分钟</span></div>
          <div class="meta-row"><span class="meta-label">超时</span><span>{{ detail.timeout }}s</span></div>
        </div>

        <!-- 可配置参数 -->
        <div class="section">
          <h4 class="section-title">可配置参数</h4>
          <table class="data-table" v-if="params.length">
            <thead><tr><th>参数键</th><th>值</th><th>类型</th><th>说明</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="(p, i) in params" :key="p.param_key">
                <td class="mono">{{ p.param_key }}</td>
                <td>
                  <input v-if="editingIdx === i" v-model="editForm.param_value" class="input-sm" />
                  <span v-else>{{ p.param_value }}</span>
                </td>
                <td>
                  <select v-if="editingIdx === i" v-model="editForm.param_type" class="input-sm">
                    <option value="string">string</option>
                    <option value="number">number</option>
                    <option value="boolean">boolean</option>
                  </select>
                  <span v-else class="mono">{{ p.param_type }}</span>
                </td>
                <td>
                  <input v-if="editingIdx === i" v-model="editForm.description" class="input-sm" />
                  <span v-else>{{ p.description || '-' }}</span>
                </td>
                <td>
                  <template v-if="editingIdx === i">
                    <button class="btn btn-sm btn-primary" @click="saveParam(i)">保存</button>
                    <button class="btn btn-sm" @click="editingIdx = -1">取消</button>
                  </template>
                  <button v-else class="btn btn-sm btn-link" @click="editParam(i)">编辑</button>
                </td>
              </tr>
            </tbody>
          </table>
          <button class="btn btn-sm" @click="addParam" v-if="editingIdx === -1">+ 新增参数</button>
          <div v-if="!params.length && editingIdx === -1" class="empty">暂无参数，点击"新增参数"添加</div>
        </div>

        <!-- 最近运行结果 -->
        <div class="section">
          <div class="section-header">
            <h4 class="section-title">最近运行结果</h4>
            <div>
              <button class="btn btn-sm" @click="exportResults">导出 CSV</button>
            </div>
          </div>
          <table class="data-table" v-if="runs.length">
            <thead><tr><th>时间</th><th>方法</th><th>状态</th><th>耗时</th><th>输入 / 输出摘要</th></tr></thead>
            <tbody>
              <tr v-for="r in runs" :key="r.id">
                <td class="time-cell">{{ formatTime(r.started_at) }}</td>
                <td class="mono">{{ r.method }}</td>
                <td><span class="badge" :class="r.status">{{ r.status }}</span></td>
                <td>{{ r.duration_ms ? (r.duration_ms / 1000).toFixed(1) + 's' : '-' }}</td>
                <td>
                  <div class="summary-line">{{ (r.input_summary || '').slice(0, 60) }}</div>
                  <div class="summary-line text-muted">{{ (r.output_summary || '').slice(0, 60) }}</div>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="empty">暂无运行记录</div>
        </div>
      </div>

      <div class="detail-panel detail-empty" v-else>
        <div class="empty">← 请选择一个智能体查看详情</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminApi } from '../../api'

interface AgentItem { role: string; name: string; status: string; today_calls: number; today_errors: number }
interface AgentDetail { role: string; name: string; description: string; model_name: string; triggers: string[]; skills: string[]; rate_limit: number; timeout: number; status: string; params: ParamItem[]; recent_runs: RunItem[] }
interface ParamItem { param_key: string; param_value: string; param_type: string; description: string }
interface RunItem { id: number; method: string; status: string; input_summary: string; output_summary: string; started_at: string; duration_ms: number }

const agents = ref<AgentItem[]>([])
const selectedRole = ref('')
const detail = ref<AgentDetail | null>(null)
const params = ref<ParamItem[]>([])
const runs = ref<RunItem[]>([])
const editingIdx = ref(-1)
const editForm = ref({ param_key: '', param_value: '', param_type: 'string', description: '' })

function formatTime(iso: string): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

async function loadAgents() {
  try {
    const res = await adminApi.getAgents()
    agents.value = res.data?.agents || []
    // 初次进入时默认选中第一个智能体
    if (agents.value.length > 0 && !selectedRole.value) {
      await selectAgent(agents.value[0].role)
    }
  } catch (e) { console.error('load agents error:', e) }
}

async function selectAgent(role: string) {
  selectedRole.value = role
  editingIdx.value = -1
  try {
    const res = await adminApi.getAgentDetail(role)
    const d = res.data as AgentDetail
    detail.value = d
    params.value = d?.params || []
    runs.value = d?.recent_runs || []
  } catch (e) { console.error('load agent detail error:', e) }
}

async function togglePause() {
  if (!detail.value) return
  const role = detail.value.role
  try {
    if (detail.value.status === 'active') {
      await adminApi.pauseAgent(role)
    } else {
      await adminApi.resumeAgent(role)
    }
    // 刷新
    await loadAgents()
    await selectAgent(role)
  } catch (e) { console.error('toggle pause error:', e) }
}

function editParam(idx: number) {
  editingIdx.value = idx
  const p = params.value[idx]
  editForm.value = { param_key: p.param_key, param_value: p.param_value, param_type: p.param_type, description: p.description || '' }
}

function addParam() {
  editingIdx.value = params.value.length
  editForm.value = { param_key: '', param_value: '', param_type: 'string', description: '' }
  params.value.push({ param_key: '', param_value: '', param_type: 'string', description: '' })
}

async function saveParam(idx: number) {
  const p = editForm.value
  if (!p.param_key) return
  params.value[idx] = { ...p }
  editingIdx.value = -1
  try {
    await adminApi.updateAgentParams(selectedRole.value, params.value)
  } catch (e) { console.error('save params error:', e) }
}

function exportResults() {
  if (!selectedRole.value) return
  adminApi.exportAgentResults(selectedRole.value).catch(e => console.error('export error:', e))
}

onMounted(() => { loadAgents() })
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.page-title { font-size: 18px; font-weight: 700; color: #333; margin: 0; }

.layout { display: flex; gap: 20px; align-items: flex-start; }

/* 左侧列表 */
.agent-list { width: 260px; flex-shrink: 0; display: flex; flex-direction: column; gap: 12px; }
.agent-card { background: #fff; border-radius: 8px; padding: 14px; cursor: pointer; border: 2px solid transparent; box-shadow: 0 1px 4px rgba(0,0,0,0.06); transition: all 0.2s; }
.agent-card:hover { border-color: #ddd; }
.agent-card.selected { border-color: #ab2029; }
.agent-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.agent-card-role { font-size: 13px; font-weight: 600; color: #333; }
.agent-card-name { font-size: 12px; color: #888; margin-bottom: 8px; }
.agent-card-stats { display: flex; gap: 12px; font-size: 12px; color: #999; }

/* 右侧详情 */
.detail-panel { flex: 1; background: #fff; border-radius: 8px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); min-height: 400px; }
.detail-empty { display: flex; align-items: center; justify-content: center; }
.detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.detail-header h3 { font-size: 16px; font-weight: 700; color: #333; margin: 0; }

.detail-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; margin-bottom: 24px; padding: 16px; background: #fafafa; border-radius: 6px; }
.meta-row { display: flex; gap: 8px; font-size: 13px; }
.meta-label { color: #888; flex-shrink: 0; }

.section { margin-top: 20px; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.section-title { font-size: 14px; font-weight: 600; color: #333; margin: 0 0 12px; }
.section-header .section-title { margin-bottom: 0; }

.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 8px 12px; background: #fafafa; color: #666; font-weight: 600; border-bottom: 2px solid #e8e8e8; white-space: nowrap; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; color: #333; }
.mono { font-family: 'SF Mono', monospace; font-size: 12px; color: #666; }
.time-cell { white-space: nowrap; color: #888; font-size: 12px; }
.summary-line { font-size: 12px; color: #333; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.text-muted { color: #999; }
.text-red { color: #ab2029; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 500; }
.badge.active { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
.badge.paused { background: #fff7e6; color: #faad14; border: 1px solid #ffd591; }
.badge.success { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
.badge.error { background: #fff2f0; color: #ab2029; border: 1px solid #ffccc7; }

.btn { display: inline-flex; align-items: center; padding: 4px 12px; border: 1px solid #d9d9d9; border-radius: 4px; background: #fff; color: #333; font-size: 12px; cursor: pointer; white-space: nowrap; gap: 4px; transition: all 0.2s; }
.btn:hover { border-color: #ab2029; color: #ab2029; }
.btn-sm { padding: 2px 8px; font-size: 12px; }
.btn-primary { background: #ab2029; color: #fff; border-color: #ab2029; }
.btn-primary:hover { background: #8b1a22; }
.btn-warn { background: #faad14; color: #fff; border-color: #faad14; }
.btn-warn:hover { background: #d48806; }
.btn-link { color: #1890ff; border: none; background: none; padding: 2px 4px; }

.input-sm { padding: 3px 8px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 12px; width: 100%; box-sizing: border-box; }
select.input-sm { width: auto; }

.empty { padding: 32px; text-align: center; color: #999; font-size: 14px; }
</style>
