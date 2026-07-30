<template>
  <div class="opp-board-card">
    <!-- 目标进度区 -->
    <div class="target-section" @click="$router.push('/performance')">
      <div class="target-top">
        <div>
          <span class="target-value">{{ aumKpi?.current > 0 ? '+' + aumCurrent : '--' }}</span><span class="target-unit">{{ aumUnit }}</span>
        </div>
        <div class="target-label">本月AUM净增目标 <strong>{{ aumTarget }}{{ aumUnit }}</strong></div>
      </div>
      <div class="progress-bar">
        <div class="fill" :style="{ width: aumProgress + '%' }"></div>
      </div>
      <div class="progress-label">
        <span>完成 {{ aumProgress }}%</span><span>剩余 <strong>{{ aumRemaining }}{{ aumUnit }}</strong></span>
      </div>
      <div class="conversion-row">
        <span>转化率 {{ Math.round(conversionRate * 100) }}%</span>
        <span class="conv-formula">→</span>
        <span>需获取</span>
        <span class="conv-warn">{{ neededOpps }}个商机</span>
      </div>
    </div>

    <!-- 双页签 -->
    <div class="opp-tabs">
      <div class="opp-tab" :class="{ active: activeTab === 'current' }" @click="activeTab = 'current'">当前商机</div>
      <div class="opp-tab" :class="{ active: activeTab === 'mining' }" @click="activeTab = 'mining'">商机挖掘</div>
    </div>

    <!-- 页签1：当前商机 -->
    <div v-show="activeTab === 'current'" class="opp-tab-panel">
      <div class="pool-stats">
        <div class="pool-stat">
          <div class="val">{{ oppStore.items.length }}<span style="font-size:11px;font-weight:400">个</span></div>
          <div class="lbl">当前商机</div>
        </div>
        <div class="pool-stat">
          <div class="val">{{ totalValue }}<span style="font-size:11px;font-weight:400">万</span></div>
          <div class="lbl">预计贡献</div>
        </div>
        <div class="pool-stat pool-stat--warn">
          <div class="val danger">{{ gapValue }}<span style="font-size:11px;font-weight:400">万</span></div>
          <div class="lbl">金额缺口</div>
        </div>
      </div>

      <!-- 按类型分组展示 -->
      <div v-if="groupedOpps.length === 0" class="opp-item-row">
        <span class="opp-icon"><svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-inbox" /></svg></span>
        <div class="opp-info">
          <div class="opp-name">暂无商机数据</div>
          <div class="opp-meta">点击「商机挖掘」让AI帮您发现</div>
        </div>
      </div>

      <div
        v-for="group in groupedOpps"
        :key="group.key"
        class="opp-item-row"
        @click="goOppTab(group.key)"
      >
        <span class="opp-icon">
          <svg viewBox="0 0 24 24" class="ico ico--md"><use :href="group.icon" /></svg>
        </span>
        <div class="opp-info">
          <div class="opp-name">
            {{ group.label }}
            <span class="opp-source-tag" :class="group.tagClass">{{ group.sourceLabel }}</span>
          </div>
          <div class="opp-meta">{{ group.count }}位客户 · {{ group.summary }}</div>
        </div>
        <span class="opp-value">≈{{ group.totalVal }}万</span>
        <span class="opp-action" :class="{ 'opp-action--danger': group.key === 'liushi' }">
          {{ group.key === 'liushi' ? '紧急 ›' : '跟进 ›' }}
        </span>
      </div>
    </div>

    <!-- 页签2：商机挖掘 (§4.1 缺口>0时显示) -->
    <div v-show="activeTab === 'mining'" class="opp-tab-panel">
      <template v-if="Number(gapValue) > 0">
        <div class="mining-header">
          <span class="mining-badge mining-badge--gap">目标缺口 {{ gapValue }}万</span>
          <span v-if="miningLoading" style="font-size:12px;color:var(--color-text-tertiary)">加载中...</span>
        </div>
        <div class="mining-desc">AI已扫描全量管户客户，发现以下可挖掘方向：</div>

        <div v-if="miningLoading && miningDirections.length === 0" class="mining-item">
          <span>加载中...</span><span class="est">--</span>
        </div>
        <div v-for="(dir, i) in miningDirections" :key="i" class="mining-item">
          <span>{{ dir.label }}（{{ dir.count }}位客户中识别）</span>
          <span class="est">+{{ dir.estimated }}个商机</span>
        </div>

        <div class="mining-total">
          <span>合计可挖掘</span>
          <span style="color:var(--color-ai)">{{ miningTotalText }}</span>
        </div>
        <button class="btn-mining" :disabled="miningLoading" @click.stop="doAiMine">
          <svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-lightning" /></svg>
          {{ miningLoading ? 'AI 挖掘中...' : '一键AI挖掘' }}
        </button>
      </template>
      <template v-else>
        <div style="text-align:center;padding:30px 20px;color:#999;font-size:13px;">
          <div style="font-size:28px;margin-bottom:8px;">✅</div>
          当前商机预估贡献已覆盖目标，无需额外挖掘
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useOpportunityStore } from '../../stores/opportunity'
import { useKpiStore } from '../../stores/kpi'
import { api } from '@/api'
import { useManagerStore } from '@/stores/manager'

const emit = defineEmits<{ aiMine: [] }>()
const router = useRouter()
const oppStore = useOpportunityStore()
const kpiStore = useKpiStore()
const managerStore = useManagerStore()

const activeTab = ref('current')

/* ===== 目标进度区：对接 kpiStore AUM 指标 + oppStore 商机数据 ===== */
// AUM 新增 KPI（kpiStore.items[0] = "新增AUM"）
const aumKpi = computed(() => kpiStore.items[0])
const aumCurrent = computed(() => aumKpi.value?.current ?? 0)
const aumTarget = computed(() => aumKpi.value?.target ?? 0)
const aumUnit = computed(() => aumKpi.value?.unit || '万')
const aumProgress = computed(() => aumKpi.value?.progress ?? 0)
const aumRemaining = computed(() => parseFloat((Math.max(0, aumTarget.value - aumCurrent.value)).toFixed(1)))

// 转化率（基于历史数据或默认 15%）
const conversionRate = ref(0.15)

// 平均商机价值（万）
const avgOppValue = computed(() => {
  if (oppStore.items.length === 0) return 6
  const total = oppStore.items.reduce((s, o) => s + (o.estimatedValue || 0), 0)
  return Math.max(1, Math.round((total / oppStore.items.length) / 10000))
})

// 达成目标所需商机总数 = 缺口 / 转化率 / 平均商机价值
const neededOpps = computed(() => {
  if (aumRemaining.value <= 0 || aumTarget.value <= 0) return 0
  const raw = aumRemaining.value / (conversionRate.value * avgOppValue.value)
  return Math.max(0, Math.ceil(raw))
})

// 当前已有商机数量
const currentOppCount = computed(() => oppStore.items.length)

// 商机缺口
const oppGap = computed(() => Math.max(0, neededOpps.value - currentOppCount.value))

/* 按类型分组 */
interface OppGroup {
  key: string
  label: string
  icon: string
  sourceLabel: string
  tagClass: string
  count: number
  summary: string
  totalVal: string
}

const groupedOpps = computed<OppGroup[]>(() => {
  const items = oppStore.items
  if (!items.length) return []

  const groups: OppGroup[] = []

  // 代发到账
  const daifa = items.filter(o => o.type.includes('代发'))
  if (daifa.length) {
    const avg = daifa.reduce((s, o) => s + (o.estimatedValue || 0), 0)
    groups.push({
      key: 'daifa', label: '代发即将到账', icon: '#ico-inbox',
      sourceLabel: '系统推送', tagClass: 'opp-source-tag--system',
      count: daifa.length,
      summary: `近6月月均代发${(daifa[0].estimatedValue / 10000).toFixed(1)}万`,
      totalVal: (avg / 10000).toFixed(0),
    })
  }

  // 流失预警
  const liushi = items.filter(o => o.type.includes('预警') || o.type.includes('流失'))
  if (liushi.length) {
    const avg = liushi.reduce((s, o) => s + (o.estimatedValue || 0), 0)
    groups.push({
      key: 'liushi', label: '流失预警挽回', icon: '#ico-warning',
      sourceLabel: '系统推送', tagClass: 'opp-source-tag--system',
      count: liushi.length,
      summary: `AI识别流失概率>60%`,
      totalVal: (avg / 10000).toFixed(0),
    })
  }

  // AI挖掘
  const ai = items.filter(o => o.source === 'AI挖掘' && !o.type.includes('代发') && !o.type.includes('预警'))
  if (ai.length) {
    const avg = ai.reduce((s, o) => s + (o.estimatedValue || 0), 0)
    const avgConf = ai.reduce((s, o) => s + (o.confidence || 0), 0) / ai.length
    groups.push({
      key: 'ai', label: 'AI 智能挖掘', icon: '#ico-ai',
      sourceLabel: 'AI挖掘', tagClass: 'opp-source-tag--ai',
      count: ai.length,
      summary: `置信度 ${Math.round(avgConf * 100)}% · ${ai[0].type || '挖掘商机'}`,
      totalVal: (avg / 10000).toFixed(0),
    })
  }

  // 我的商机
  const mine = items.filter(o => o.source === '手动创建')
  if (mine.length) {
    const avg = mine.reduce((s, o) => s + (o.estimatedValue || 0), 0)
    groups.push({
      key: 'mine', label: '我的商机', icon: '#ico-pencil',
      sourceLabel: '手动创建', tagClass: 'opp-source-tag--manual',
      count: mine.length,
      summary: `${mine[0].description || '客户经理创建'}`,
      totalVal: (avg / 10000).toFixed(0),
    })
  }

  return groups.sort((a, b) => parseFloat(b.totalVal) - parseFloat(a.totalVal))
})

/* 统计 */
const totalValue = computed(() => {
  const sum = oppStore.items.reduce((s, o) => s + (o.estimatedValue || 0), 0)
  return (sum / 10000).toFixed(0)
})
const gapValue = computed(() => Math.max(0, aumTarget.value - Number(totalValue.value)))

/* 商机挖掘数据 */
const miningDirections = ref<{ label: string; count: number; estimated: number }[]>([])
const miningLoading = ref(false)
const miningTotalText = computed(() => {
  if (!miningDirections.value.length) return '--'
  const total = miningDirections.value.reduce((s, d) => s + d.estimated, 0)
  return `+${total}个商机`
})

onMounted(async () => {
  // 确保 KPI 数据已加载
  if (kpiStore.items.length === 0 || kpiStore.items[0]?.current === 0) {
    await kpiStore.loadKpi(managerStore.currentId)
  }
  // 加载AI挖掘方向
  try {
    const res = await api.aiGetOpportunityList(managerStore.currentId)
    const list = res.data?.opportunities || res.data || []
    if (Array.isArray(list) && list.length) {
      // 按 opportunity_type 分组
      const typeMap: Record<string, number> = {}
      list.forEach((o: any) => {
        const t = o.opportunity_type || o.type || '其他'
        typeMap[t] = (typeMap[t] || 0) + 1
      })
      miningDirections.value = Object.entries(typeMap).map(([label, count]) => ({
        label, count, estimated: Math.max(1, Math.round(count * 0.6)),
      }))
    }
  } catch { /* ignore */ }
})

function doAiMine() {
  miningLoading.value = true
  emit('aiMine')
  // 延迟恢复
  setTimeout(() => { miningLoading.value = false }, 8000)
}

function goOppTab(tab: string) {
  // 映射到 W3 三 Tab: 代发/流失 → system, ai → ai, mine → mine
  const w3Tab = tab === 'daifa' || tab === 'liushi' ? 'system' : tab
  router.push({ name: 'opportunity', query: { tab: w3Tab } })
}
</script>

<style scoped>
.opp-board-card {
  background: var(--color-card); border-radius: var(--radius-md);
  box-shadow: var(--shadow-card); overflow: hidden;
  margin-bottom: var(--sp-sm);
}
.target-section { padding: var(--sp-md); cursor: pointer; }
.target-top {
  display: flex; justify-content: space-between; align-items: flex-start;
  margin-bottom: var(--sp-sm);
}
.target-value {
  font-family: var(--font-number); font-size: var(--fs-num-lg);
  font-weight: var(--fw-bold); color: var(--color-text-primary); line-height: 1;
}
.target-unit { font-size: var(--fs-body); font-weight: var(--fw-medium); color: var(--color-text-secondary); margin-left: 2px; }
.target-label { font-size: var(--fs-caption); color: var(--color-text-tertiary); text-align: right; }
.target-label strong { color: var(--color-text-primary); }
.progress-bar {
  height: 8px; background: var(--color-divider); border-radius: 4px; overflow: hidden;
  margin-bottom: var(--sp-xs); cursor: pointer; position: relative;
}
.progress-bar .fill {
  height: 100%; border-radius: 4px;
  background: linear-gradient(90deg, #3B82F6, #60A5FA);
  transition: width 800ms var(--ease-default);
}
.progress-label {
  display: flex; justify-content: space-between;
  font-size: var(--fs-caption); color: var(--color-text-tertiary);
  margin-bottom: var(--sp-xs);
}
.progress-label strong { color: var(--color-warning); }
.conversion-row {
  display: flex; align-items: center; gap: var(--sp-xs);
  padding: var(--sp-xs) var(--sp-sm);
  background: var(--color-bg); border-radius: var(--radius-sm);
  font-size: var(--fs-caption); color: var(--color-text-secondary);
}
.conv-formula { font-family: var(--font-number); color: var(--color-text-primary); font-weight: var(--fw-bold); }
.conv-warn { color: var(--color-danger); font-weight: var(--fw-bold); margin-left: auto; }

/* Tabs */
.opp-tabs {
  display: flex; border-bottom: 1px solid var(--color-divider);
  padding: 0 var(--sp-md);
}
.opp-tab {
  flex: 1; text-align: center; padding: 10px 0;
  font-size: var(--fs-body); color: var(--color-text-tertiary);
  cursor: pointer; position: relative;
}
.opp-tab.active {
  color: var(--color-primary); font-weight: var(--fw-bold);
}
.opp-tab.active::after {
  content: ''; position: absolute; bottom: 0; left: 50%;
  transform: translateX(-50%); width: 24px; height: 3px;
  background: var(--color-primary); border-radius: 2px;
}
.opp-tab-panel { padding: var(--sp-sm) var(--sp-md) var(--sp-md); }

.pool-stats { display: flex; gap: var(--sp-sm); margin-bottom: var(--sp-sm); }
.pool-stat {
  flex: 1; padding: var(--sp-sm) var(--sp-xs);
  background: var(--color-bg); border: 1px solid var(--color-border);
  border-radius: var(--radius-sm); text-align: center;
}
.pool-stat--warn { background: var(--color-warning-light); border-color: #F5C842; }
.pool-stat .val {
  font-family: var(--font-number); font-size: var(--fs-num-sm);
  font-weight: var(--fw-bold); color: var(--color-text-primary);
}
.pool-stat .val.danger { color: var(--color-danger); }
.pool-stat .lbl { font-size: var(--fs-small); color: var(--color-text-tertiary); margin-top: 2px; }

.opp-item-row {
  display: flex; align-items: center; padding: 10px 0;
  border-bottom: 1px solid var(--color-divider); cursor: pointer;
}
.opp-item-row:last-child { border-bottom: none; }
.opp-icon { font-size: 18px; margin-right: var(--sp-sm); flex-shrink: 0; }
.opp-info { flex: 1; min-width: 0; }
.opp-name { font-size: var(--fs-body); font-weight: var(--fw-medium); }
.opp-meta { font-size: var(--fs-caption); color: var(--color-text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.opp-value { font-family: var(--font-number); font-size: var(--fs-caption); color: var(--color-text-secondary); margin-right: var(--sp-sm); flex-shrink: 0; }
.opp-action { font-size: var(--fs-caption); color: var(--color-primary); font-weight: var(--fw-medium); flex-shrink: 0; }
.opp-action--danger { color: var(--color-danger); }
.opp-source-tag {
  font-size: 10px; font-weight: var(--fw-bold);
  padding: 1px 6px; border-radius: 3px; margin-left: 4px;
}
.opp-source-tag--system { background: var(--color-bg); color: var(--color-text-tertiary); }
.opp-source-tag--ai { background: var(--color-ai-light); color: var(--color-ai); }
.opp-source-tag--manual { background: var(--color-success-light); color: #009A59; }

/* Mining */
.mining-header { display: flex; align-items: center; gap: var(--sp-sm); margin-bottom: var(--sp-sm); }
.mining-badge {
  font-size: var(--fs-caption); font-weight: var(--fw-bold);
  padding: 4px 12px; border-radius: var(--radius-full);
}
.mining-badge--gap { background: var(--color-warning-light); color: #B8600C; }
.mining-desc { font-size: var(--fs-caption); color: var(--color-text-secondary); margin-bottom: var(--sp-sm); }
.mining-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 0; font-size: var(--fs-caption); color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-divider);
}
.mining-item:last-child { border-bottom: none; }
.mining-item .est { font-size: var(--fs-small); color: var(--color-text-tertiary); }
.mining-total {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 0 0; margin-top: var(--sp-xs);
  border-top: 1px dashed var(--color-divider);
  font-weight: var(--fw-bold); color: var(--color-ai);
  font-size: var(--fs-body);
}
.btn-mining {
  width: 100%; height: 38px; margin-top: var(--sp-sm);
  background: var(--color-ai); color: #fff; border: none;
  border-radius: var(--radius-sm); font-size: var(--fs-body); font-weight: var(--fw-bold);
  cursor: pointer; transition: all var(--duration-fast);
  -webkit-tap-highlight-color: transparent;
}
.btn-mining:active { opacity: 0.85; transform: scale(0.98); }
.btn-mining:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
