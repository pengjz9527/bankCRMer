<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useOpportunityStore } from '@/stores/opportunity'
import { useManagerStore } from '@/stores/manager'
import { api } from '@/api'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const oppStore = useOpportunityStore()
const managerStore = useManagerStore()

type TabKey = 'system' | 'ai' | 'mine'

const tabs: { key: TabKey; label: string; sourceFilter: (o: any) => boolean }[] = [
  { key: 'system', label: '系统推送', sourceFilter: o => o.source === '规则匹配' },
  { key: 'ai', label: 'AI挖掘', sourceFilter: o => o.source === 'AI挖掘' },
  { key: 'mine', label: '自建商机', sourceFilter: o => o.source === '手动创建' },
]

const activeTab = ref<TabKey>('system')

/* Tab 数据 */
const tabItems = computed(() => {
  const tab = tabs.find(t => t.key === activeTab.value)
  if (!tab) return []
  return oppStore.items.filter(tab.sourceFilter)
})

const tabCounts = computed(() => {
  const counts: Record<string, number> = {}
  tabs.forEach(t => {
    counts[t.key] = oppStore.items.filter(t.sourceFilter).length
  })
  return counts
})

/* 系统推送 Tab 内分子分组 */
const systemGroups = computed(() => {
  const items = tabItems.value
  const groups: { key: string; label: string; icon: string; items: any[] }[] = []
  const daifa = items.filter(o => o.type?.includes('代发') || o.type?.includes('到期') || o.type?.includes('产品') || o.type?.includes('大额'))
  const liushi = items.filter(o => o.type?.includes('预警') || o.type?.includes('流失'))
  // 未分类的放入代发组
  const categorized = new Set([...daifa, ...liushi].map(o => o.id))
  const other = items.filter(o => !categorized.has(o.id))
  if (daifa.length || other.length) {
    groups.push({ key: 'daifa', label: '代发到账 / 产品到期', icon: '#ico-inbox', items: [...daifa, ...other] })
  }
  if (liushi.length) {
    groups.push({ key: 'liushi', label: '流失预警', icon: '#ico-warning', items: liushi })
  }
  return groups
})

/* Block3 query 参数定位 Tab */
const tabKeyMap: Record<string, TabKey> = { daifa: 'system', liushi: 'system', ai: 'ai', mine: 'mine' }
onMounted(async () => {
  await oppStore.loadOpportunities(managerStore.currentId)
  const qTab = route.query.tab as string
  if (qTab && tabKeyMap[qTab]) {
    activeTab.value = tabKeyMap[qTab]
  }
})
watch(() => route.query.tab, (v) => {
  if (v && tabKeyMap[v as string]) activeTab.value = tabKeyMap[v as string]
})

// 监听经理切换，重新加载商机数据
watch(() => managerStore.currentId, (newId) => {
  oppStore.loadOpportunities(newId)
})

/* 来源图标 */
function oppIcon(opp: any) {
  if (opp.source === 'AI挖掘') return '#ico-ai'
  if (opp.source === '手动创建') return '#ico-pencil'
  if (opp.type?.includes('预警') || opp.type?.includes('流失')) return '#ico-warning'
  return '#ico-inbox'
}

/* 来源标签 */
function oppTagClass(opp: any) {
  if (opp.source === 'AI挖掘') return 'opp-tag--ai'
  if (opp.source === '手动创建') return 'opp-tag--manual'
  return 'opp-tag--system'
}
function oppTagLabel(opp: any) {
  if (opp.source === 'AI挖掘') return 'AI挖掘'
  if (opp.source === '手动创建') return '手动创建'
  return '系统推送'
}

/* 状态标签 */
function statusLabel(opp: any) {
  return opp.status || '待跟进'
}
function statusClass(opp: any) {
  const s = opp.status || ''
  if (s.includes('已生成') || s.includes('已触达')) return 'ws-status--done'
  if (s.includes('流失')) return 'ws-status--danger'
  return 'ws-status--pending'
}

/* 格式化金额 */
function fmtVal(v: number) {
  if (v >= 10000) return `≈${(v / 10000).toFixed(0)}万`
  return `≈${(v / 10000).toFixed(1)}万`
}

/* ===== 半屏详情面板 ===== */
const showDetail = ref(false)
const detailOpp = ref<any>(null)
const detailProfile = ref<any>(null)

async function openDetail(opp: any) {
  detailOpp.value = opp
  detailProfile.value = null
  showDetail.value = true
  // 异步加载客户速览数据
  const cid = opp.cust_id
  if (cid) {
    try {
      const [basicRes, wealthRes] = await Promise.all([
        api.getCustomerBasic(String(cid)),
        api.getCustomerWealth(String(cid)),
      ])
      const b = basicRes.data || {}
      const w = wealthRes.data || {}
      detailProfile.value = {
        totalAssets: w.total_assets || b.total_assets || '--',
        level: b.customer_level || b.level || '--',
        holdings: w.holdings_summary || b.holdings || '--',
        riskPref: b.risk_preference || b.risk_appetite || '--',
      }
    } catch { /* ignore */ }
  }
}
function closeDetail() { showDetail.value = false }

/* 详情面板操作 */
function markFollowed() { appStore.showToast('已标记为已跟进'); closeDetail() }
function markSkip() { appStore.showToast('已标记暂不处理'); closeDetail() }
function markInvalid() { appStore.showToast('已标记为无效商机'); closeDetail() }

/* 跳转 */
function goCustomerProfile(name: string) {
  closeDetail()
  router.push({ name: 'customer-detail', params: { id: name } })
}
/* ===== 作战包生成 ===== */
const bpGenerating = ref(false)
const bpPhase = ref('')

async function goBattlePackage(opp: any) {
  closeDetail()
  // 已有作战包，直接查看
  if (opp.bp_id) {
    router.push({ name: 'battle-package', params: { id: opp.bp_id } })
    return
  }

  // 直接开始生成标准版作战包
  bpGenerating.value = true
  bpPhase.value = 'AI 正在加载客户数据...'

  const custId = opp.cust_id || ''
  const oppId = opp.id || opp.opp_id || ''

  // 构建 opportunity_info
  const opportunity_info: Record<string, any> = {}
  if (opp.type) opportunity_info.type = opp.type
  if (opp.description) opportunity_info.title = opp.description
  if (opp.reasoning) opportunity_info.reasoning = opp.reasoning
  if (opp.estimatedValue) opportunity_info.estimated_value = opp.estimatedValue
  if (opp.confidence) opportunity_info.confidence = opp.confidence

  try {
    setTimeout(() => { bpPhase.value = 'AI 正在匹配产品...' }, 3000)
    setTimeout(() => { bpPhase.value = 'AI 正在生成作战包（约15-25秒）...' }, 6000)

    const res = await api.generateBattlePackage({
      cust_id: custId,
      mode: '标准版',
      opp_id: oppId,
      opportunity_info: Object.keys(opportunity_info).length > 0 ? opportunity_info : undefined,
    })

    const bpId = res?.data?.bp_id
    if (bpId) {
      bpPhase.value = '作战包生成成功！'
      appStore.showToast('作战包生成成功！')
      router.push({ name: 'battle-package', params: { id: bpId } })
    } else {
      const errMsg = res?.message || '未知错误'
      appStore.showToast('作战包生成失败: ' + errMsg)
    }
  } catch (e: any) {
    console.warn('生成作战包失败', e?.message || e)
    appStore.showToast('生成失败: ' + (e?.message || '未知错误'))
  } finally {
    bpGenerating.value = false
    bpPhase.value = ''
  }
}

function goBack() { router.back() }
</script>

<template>
  <div class="w3-page">
    <!-- 页面头 -->
    <div class="w3-header">
      <span class="w3-back" @click="goBack">←</span>
      <span class="w3-title">商机管理</span>
      <span class="w3-filter">筛选▼</span>
    </div>

    <!-- 三 Tab (§5.3) -->
    <div class="w3-tabs">
      <div
        v-for="tab in tabs"
        :key="tab.key"
        class="w3-tab"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
        <span class="w3-tab-badge">{{ tabCounts[tab.key] }}</span>
      </div>
    </div>

    <!-- 商机卡片列表 -->
    <div class="w3-body">
      <!-- ===== 系统推送 Tab：分子分组 ===== -->
      <template v-if="activeTab === 'system'">
        <template v-if="systemGroups.length === 0">
          <div class="w3-empty">暂无商机</div>
        </template>
        <template v-for="group in systemGroups" :key="group.key">
          <div class="w3-group-title">
            <svg viewBox="0 0 24 24" class="ico ico--sm"><use :href="group.icon" /></svg>
            {{ group.label }} · {{ group.items.length }}个商机
          </div>
          <div
            v-for="opp in group.items"
            :key="opp.id || opp.opp_id"
            class="w3-card"
            :class="{ 'w3-card--danger': opp.type?.includes('预警') || opp.type?.includes('流失') }"
            @click="openDetail(opp)"
          >
            <div class="w3-card-header">
              <span class="w3-card-name">{{ opp.customerName || opp.cust_name }}</span>
              <div class="w3-card-tags">
                <span class="w3-card-status" :class="statusClass(opp)">{{ statusLabel(opp) }}</span>
                <span class="w3-card-tag" :class="oppTagClass(opp)">{{ oppTagLabel(opp) }}</span>
              </div>
            </div>
            <div class="w3-card-type">
              <svg viewBox="0 0 24 24" class="ico ico--sm"><use :href="oppIcon(opp)" /></svg>
              {{ opp.type }}
            </div>
            <div class="w3-card-meta">
              <div v-if="opp.reasoning" class="w3-meta-reason">{{ opp.reasoning }}</div>
            </div>
            <div class="w3-card-value">预估贡献：{{ fmtVal(opp.estimatedValue || 0) }}</div>
            <div class="w3-card-footer">
              <button class="w3-btn" @click.stop="goCustomerProfile(opp.customerName || opp.cust_name)">查看画像</button>
              <button class="w3-btn w3-btn--primary" @click.stop="goBattlePackage(opp)">
                {{ opp.bp_id ? '查看作战包' : '生成作战包' }}
              </button>
            </div>
          </div>
        </template>
      </template>

      <!-- ===== AI挖掘 / 自建商机 Tab ===== -->
      <template v-else>
        <div class="w3-group-title">
          {{ tabs.find(t => t.key === activeTab)?.label }} · {{ tabItems.length }}个商机
        </div>
        <div v-if="tabItems.length === 0" class="w3-empty">暂无商机</div>
        <div
          v-for="opp in tabItems"
          :key="opp.id || opp.opp_id"
          class="w3-card"
          @click="openDetail(opp)"
        >
          <div class="w3-card-header">
            <span class="w3-card-name">{{ opp.customerName || opp.cust_name }}</span>
            <div class="w3-card-tags">
              <span class="w3-card-status" :class="statusClass(opp)">{{ statusLabel(opp) }}</span>
              <span class="w3-card-tag" :class="oppTagClass(opp)">{{ oppTagLabel(opp) }}</span>
            </div>
          </div>
          <div class="w3-card-type">
            <svg viewBox="0 0 24 24" class="ico ico--sm"><use :href="oppIcon(opp)" /></svg>
            {{ opp.type }}
          </div>
          <div class="w3-card-meta">
            <div v-if="opp.reasoning" class="w3-meta-reason">{{ opp.reasoning }}</div>
            <div v-if="opp.confidence" class="w3-confidence">
              置信度
              <span class="w3-conf-bar"><span class="w3-conf-fill" :style="{ width: (opp.confidence * 100) + '%' }"></span></span>
              {{ Math.round(opp.confidence * 100) }}%
            </div>
          </div>
          <div class="w3-card-value">预估贡献：{{ fmtVal(opp.estimatedValue || 0) }}</div>
          <div class="w3-card-footer">
            <button class="w3-btn" @click.stop="goCustomerProfile(opp.customerName || opp.cust_name)">查看画像</button>
            <button class="w3-btn w3-btn--primary" @click.stop="goBattlePackage(opp)">
              {{ opp.bp_id ? '查看作战包' : '生成作战包' }}
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- ===== 半屏详情面板 (§5.6) ===== -->
    <Transition name="sheet-fade">
      <div v-if="showDetail" class="w3-overlay" @click.self="closeDetail">
        <Transition name="sheet-slide">
          <div v-if="showDetail && detailOpp" class="w3-sheet">
            <div class="w3-sheet-header">
              <span class="w3-sheet-title">商机详情</span>
              <span class="w3-sheet-close" @click="closeDetail">✕</span>
            </div>
            <div class="w3-sheet-body">
              <!-- 客户信息 -->
              <div class="ws-customer">
                {{ detailOpp.customerName || detailOpp.cust_name }}
                <span class="ws-status-tag" :class="statusClass(detailOpp)">{{ statusLabel(detailOpp) }}</span>
              </div>

              <!-- 来源 + 字段 -->
              <div class="ws-section">
                <div class="ws-section-title">
                  <svg viewBox="0 0 24 24" class="ico ico--sm"><use :href="oppIcon(detailOpp)" /></svg>
                  {{ detailOpp.type }}（来源：{{ oppTagLabel(detailOpp) }}）
                </div>
                <template v-if="detailOpp.confidence">
                  <div class="ws-row">
                    <span class="ws-label">置信度</span>
                    <span class="ws-val" style="color:#6C5CE7;font-weight:600">{{ Math.round(detailOpp.confidence * 100) }}%</span>
                  </div>
                  <div v-if="detailOpp.reasoning" class="ws-row">
                    <span class="ws-label">推理说明</span>
                    <span class="ws-val" style="font-size:12px">{{ detailOpp.reasoning }}</span>
                  </div>
                </template>
                <template v-if="!detailOpp.confidence && detailOpp.reasoning">
                  <div class="ws-row">
                    <span class="ws-label">商机描述</span>
                    <span class="ws-val" style="font-size:12px">{{ detailOpp.reasoning }}</span>
                  </div>
                </template>
                <div class="ws-row">
                  <span class="ws-label">预估贡献</span>
                  <span class="ws-val" style="color:var(--color-primary);font-weight:600">{{ fmtVal(detailOpp.estimatedValue || 0) }}</span>
                </div>
              </div>

              <!-- 客户速览 (§5.6 含资产/等级/持仓/风险偏好) -->
              <div class="ws-section">
                <div class="ws-section-title">── 客户速览 ──</div>
                <template v-if="detailProfile">
                  <div class="ws-quick-info">
                    总资产：{{ detailProfile.totalAssets }}万 | 客户等级：{{ detailProfile.level }}
                  </div>
                  <div class="ws-quick-info">
                    持仓：{{ detailProfile.holdings }}
                  </div>
                  <div class="ws-quick-info">
                    风险偏好：{{ detailProfile.riskPref }}
                  </div>
                </template>
                <template v-else>
                  <div class="ws-quick-info" style="color:#999">加载中...</div>
                </template>
                <div class="ws-link" @click="goCustomerProfile(detailOpp.customerName || detailOpp.cust_name)">
                  查看完整客户画像 →
                </div>
              </div>

              <!-- 主操作：生成作战包 (§6.1) -->
              <div class="ws-section">
                <div class="ws-action-card" @click="goBattlePackage(detailOpp)">
                  <div class="ws-action-icon">⚡</div>
                  <div class="ws-action-info">
                    <div class="ws-action-title">{{ detailOpp.bp_id ? '查看作战包' : '生成作战包' }}</div>
                    <div class="ws-action-desc">
                      {{ detailOpp.bp_id ? '点击查看已生成的作战包' : '为该客户生成标准版作战包' }}
                      <span v-if="!detailOpp.bp_id">，生成后将同步创建商机待办 🟣</span>
                    </div>
                  </div>
                  <div class="ws-action-arrow">›</div>
                </div>
              </div>

              <!-- 底部操作 -->
              <div class="ws-bottom-actions">
                <button class="ws-bottom-btn" @click="markFollowed">标记为已跟进</button>
                <button class="ws-bottom-btn" @click="markSkip">暂不处理</button>
                <button class="ws-bottom-btn ws-bottom-btn--danger" @click="markInvalid">标记无效</button>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>

    <!-- ===== 作战包生成加载遮罩 ===== -->
    <Transition name="sheet-fade">
      <div v-if="bpGenerating" class="bp-generating-overlay">
        <div class="bp-gen-card">
          <div class="bp-gen-spinner"></div>
          <div class="bp-gen-title">AI 作战包生成中</div>
          <div class="bp-gen-phase">{{ bpPhase }}</div>
          <div class="bp-gen-hint">智能体正在加载客户数据、匹配产品、生成话术...</div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.w3-page { min-height: 100%; background: var(--color-bg); }

/* Header */
.w3-header {
  display: flex; align-items: center; padding: 12px 16px;
  background: #fff; position: sticky; top: 0; z-index: 5;
  border-bottom: 1px solid #eee;
}
.w3-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.w3-title { flex: 1; font-size: 16px; font-weight: 600; }
.w3-filter { font-size: 12px; color: var(--color-text-secondary); cursor: pointer; }

/* Tabs — 三 Tab */
.w3-tabs {
  display: flex; background: #fff; border-bottom: 1px solid #eee;
  position: sticky; top: 45px; z-index: 4;
}
.w3-tab {
  flex: 1; text-align: center; padding: 12px 4px;
  font-size: 13px; color: var(--color-text-secondary);
  cursor: pointer; position: relative;
  display: flex; align-items: center; justify-content: center; gap: 4px;
}
.w3-tab.active { color: var(--color-primary); font-weight: 600; }
.w3-tab.active::after {
  content: ''; position: absolute; bottom: 0; left: 50%;
  transform: translateX(-50%); width: 24px; height: 3px;
  background: var(--color-primary); border-radius: 2px;
}
.w3-tab-badge {
  font-size: 10px; padding: 1px 6px;
  background: #f0f0f0; border-radius: 999px;
}
.w3-tab.active .w3-tab-badge { background: rgba(171,32,41,0.1); color: var(--color-primary); }

/* Body */
.w3-body { padding: 12px 16px 80px; }
.w3-group-title {
  font-size: 13px; font-weight: 600; color: var(--color-text-secondary);
  margin-bottom: 10px; display: flex; align-items: center; gap: 4px;
}
.w3-empty { text-align: center; padding: 60px 20px; color: #999; font-size: 14px; }

/* Card */
.w3-card {
  background: #fff; border-radius: 10px; padding: 14px;
  margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  cursor: pointer; border-left: 3px solid transparent;
}
.w3-card--danger { border-left-color: #e74c3c; }
.w3-card-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;
}
.w3-card-name { font-size: 15px; font-weight: 600; }
.w3-card-tags { display: flex; gap: 6px; align-items: center; }
.w3-card-tag { font-size: 10px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.opp-tag--system { background: #f0f0f0; color: #666; }
.opp-tag--ai { background: rgba(108,92,231,0.1); color: #6C5CE7; }
.opp-tag--manual { background: rgba(39,174,96,0.1); color: #27ae60; }

/* Status badge */
.w3-card-status {
  font-size: 10px; padding: 2px 6px; border-radius: 3px; font-weight: 500;
}
.ws-status--pending { background: #FFF3CD; color: #856404; }
.ws-status--done { background: #D4EDDA; color: #155724; }
.ws-status--danger { background: #F8D7DA; color: #721C24; }
.ws-status-tag { margin-left: 8px; }

.w3-card-type {
  font-size: 12px; color: var(--color-text-secondary); margin-bottom: 6px;
  display: flex; align-items: center; gap: 4px;
}
.w3-card-meta { margin-bottom: 6px; }
.w3-meta-reason { font-size: 11px; color: #6C5CE7; line-height: 1.5; }
.w3-confidence {
  font-size: 12px; color: var(--color-text-secondary);
  display: flex; align-items: center; gap: 6px; margin-top: 4px;
}
.w3-conf-bar { width: 60px; height: 4px; background: #eee; border-radius: 2px; overflow: hidden; }
.w3-conf-fill { height: 100%; background: #6C5CE7; border-radius: 2px; }
.w3-card-value { font-size: 13px; color: var(--color-primary); font-weight: 500; margin-bottom: 8px; }
.w3-card-footer { display: flex; gap: 8px; }
.w3-btn {
  flex: 1; padding: 8px; border-radius: 6px; border: 1px solid #e0e0e0;
  background: #fff; font-size: 12px; cursor: pointer; text-align: center;
}
.w3-btn--primary { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }

/* ===== 半屏详情面板 ===== */
.w3-overlay {
  position: absolute; inset: 0; background: rgba(0,0,0,0.4);
  z-index: 100; display: flex; align-items: flex-end;
}
.w3-sheet {
  background: #fff; width: 100%; max-height: 85%;
  border-radius: 16px 16px 0 0; overflow-y: auto;
}
.w3-sheet-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px; border-bottom: 1px solid #f0f0f0;
  position: sticky; top: 0; background: #fff; z-index: 1;
}
.w3-sheet-title { font-size: 16px; font-weight: 600; }
.w3-sheet-close { font-size: 18px; cursor: pointer; color: #999; padding: 4px; }
.w3-sheet-body { padding: 16px; }
.ws-customer { font-size: 15px; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; }
.ws-status-tag { font-size: 10px; padding: 2px 8px; border-radius: 4px; }
.ws-section {
  background: #fafafa; border-radius: 10px; padding: 12px 14px;
  margin-bottom: 10px;
}
.ws-section-title {
  font-size: 13px; font-weight: 600; margin-bottom: 8px;
  display: flex; align-items: center; gap: 4px;
}
.ws-row { display: flex; padding: 5px 0; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
.ws-row:last-child { border-bottom: none; }
.ws-label { width: 70px; flex-shrink: 0; color: #999; font-size: 12px; }
.ws-val { flex: 1; color: var(--color-text); }
.ws-quick-info { font-size: 12px; color: var(--color-text-secondary); line-height: 1.8; }
.ws-link {
  font-size: 13px; color: var(--color-primary); text-align: right;
  margin-top: 8px; cursor: pointer;
}

/* Action card */
.ws-action-card {
  display: flex; align-items: center; gap: 12px;
  padding: 12px; border-radius: 8px;
  border-left: 3px solid var(--color-primary);
  background: rgba(171,32,41,0.03); cursor: pointer;
}
.ws-action-icon { font-size: 20px; flex-shrink: 0; }
.ws-action-info { flex: 1; }
.ws-action-title { font-size: 14px; font-weight: 600; margin-bottom: 2px; }
.ws-action-desc { font-size: 11px; color: var(--color-text-secondary); line-height: 1.5; }
.ws-action-arrow { font-size: 20px; color: #ccc; }

/* Bottom actions */
.ws-bottom-actions {
  display: flex; gap: 8px; margin-top: 16px; padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
.ws-bottom-btn {
  flex: 1; padding: 10px 8px; border-radius: 8px;
  border: 1px solid #e0e0e0; background: #fff;
  font-size: 12px; cursor: pointer; text-align: center;
}
.ws-bottom-btn--danger { color: #e74c3c; border-color: #e74c3c33; }

/* BP Generating Overlay */
.bp-generating-overlay {
  position: absolute; inset: 0; z-index: 100;
  background: rgba(0,0,0,0.45); display: flex;
  align-items: center; justify-content: center;
}
.bp-gen-card {
  background: #fff; border-radius: 16px; padding: 32px 28px;
  text-align: center; max-width: 280px; width: 85%;
  box-shadow: 0 8px 32px rgba(0,0,0,0.15);
}
.bp-gen-spinner {
  width: 40px; height: 40px; margin: 0 auto 16px;
  border: 3px solid #eee; border-top-color: var(--color-primary);
  border-radius: 50%; animation: bp-spin 0.8s linear infinite;
}
@keyframes bp-spin { to { transform: rotate(360deg); } }
.bp-gen-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.bp-gen-phase { font-size: 13px; color: var(--color-primary); margin-bottom: 12px; min-height: 18px; }
.bp-gen-hint { font-size: 11px; color: #999; line-height: 1.5; }

/* Transitions */
.sheet-fade-enter-active, .sheet-fade-leave-active { transition: opacity 0.3s; }
.sheet-fade-enter-from, .sheet-fade-leave-to { opacity: 0; }
.sheet-slide-enter-active, .sheet-slide-leave-active { transition: transform 0.3s ease; }
.sheet-slide-enter-from, .sheet-slide-leave-to { transform: translateY(100%); }
</style>
