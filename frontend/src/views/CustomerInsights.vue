<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'
import { useManagerStore } from '@/stores/manager'

const route = useRoute()
const router = useRouter()
const managerStore = useManagerStore()
const loading = ref(false)

interface Insight {
  cust_id: string
  cust_name: string
  risk_level: string
  has_change: boolean
  has_risk: boolean
  change_count: number
  risk_count: number
  generated_at: string
}

const insights = ref<Insight[]>([])

/* 详情弹层 */
const detailOpen = ref(false)
const detailLoading = ref(false)
const detailName = ref('')

const detail = ref<Record<string, any> | null>(null)

const riskColorMap: Record<string, string> = { green: '#10B981', yellow: '#F59E0B', orange: '#E67E22', red: '#EF4444' }
const riskLabelMap: Record<string, string> = { green: '低风险', yellow: '关注', orange: '预警', red: '高风险' }

function fmtWan(v: any) { return v != null ? ((Number(v) / 10000).toFixed(1) + '万') : '--' }
function fmtPct(v: any) { return v != null ? Math.round(v * 100) + '%' : '--' }

onMounted(async () => {
  await loadInsights()
})

// 监听经理切换，重新加载洞察
watch(() => managerStore.currentId, () => {
  loadInsights()
})

async function loadInsights() {
  loading.value = true
  try {
    const res = await api.getCustomerInsights(managerStore.currentId)
    const list = res.data?.insights || []
    if (Array.isArray(list)) {
      insights.value = list.map((i: any) => ({
        cust_id: i.cust_id || '',
        cust_name: i.cust_name || i.name || '',
        risk_level: i.risk_level || 'green',
        has_change: i.has_change || false,
        has_risk: i.has_risk || false,
        change_count: i.change_count || 0,
        risk_count: i.risk_count || 0,
        generated_at: i.generated_at || '',
      }))
    }
  } catch (e) {
    console.warn('加载客户洞察失败', e)
  } finally {
    loading.value = false
    // 画像→洞察互跳: 如果 URL 携带 custId 参数，自动打开该客户的洞察详情
    const queryCustId = route.query.custId as string
    if (queryCustId) {
      const target = insights.value.find(i => String(i.cust_id) === queryCustId)
        || insights.value.find(i => i.cust_name === (route.query.name as string))
      if (target) {
        // 延迟打开以确保列表渲染完成
        setTimeout(() => openDetail(target), 300)
        // 清除 query 参数防止刷新时重复触发
        router.replace({ query: {} })
      }
    }
  }
}

async function openDetail(ins: Insight) {
  detailName.value = ins.cust_name
  detailOpen.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const res = await api.getCustomerInsightDetail(ins.cust_id)
    if (res.data) detail.value = res.data
  } catch (e) {
    console.warn('加载洞察详情失败', e)
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() { detailOpen.value = false }
function goBack() { router.back() }
function goCustomerProfile() {
  // 洞察→画像: name = basic.name || custName (按规范优先使用 API 返回的 basic.name)
  const name = detail.value?.overview?.basic?.name || detailName.value
  closeDetail()
  router.push({ name: 'customer-detail', params: { id: name } })
}

function sevClass(s: string) {
  if (s === '高' || s === 'high') return 'high'
  if (s === '中' || s === 'medium') return 'medium'
  return 'low'
}
</script>

<template>
  <div class="ci-page">
    <div class="ci-header">
      <span class="ci-back" @click="goBack">←</span>
      <span class="ci-title">客户洞察</span>
      <span class="ci-count">{{ insights.length }}条</span>
    </div>

    <div class="ci-body">
      <div v-if="loading" class="ci-loading">加载中...</div>
      <div v-else-if="insights.length === 0" class="ci-empty">暂无客户洞察数据</div>

      <div v-for="ins in insights" :key="ins.cust_id" class="ci-card" @click="openDetail(ins)">
        <div class="ci-card-header">
          <span class="ci-card-name">{{ ins.cust_name }}</span>
          <span class="ci-risk-tag" :style="{ background: (riskColorMap[ins.risk_level] || '#10B981') + '18', color: riskColorMap[ins.risk_level] || '#10B981' }">
            {{ riskLabelMap[ins.risk_level] || ins.risk_level }}
          </span>
        </div>
        <div class="ci-card-signals">
          <span v-if="ins.has_change" class="ci-signal ci-signal--change">🔔 {{ ins.change_count }}个变化信号</span>
          <span v-if="ins.has_risk" class="ci-signal ci-signal--risk">⚠️ {{ ins.risk_count }}个预警信号</span>
          <span v-if="!ins.has_change && !ins.has_risk" class="ci-signal ci-signal--ok">✅ 状态稳定</span>
        </div>
        <div v-if="ins.generated_at" class="ci-card-time">生成于 {{ ins.generated_at.slice(0, 10) }}</div>
      </div>
    </div>

    <!-- Detail Overlay -->
    <div v-if="detailOpen" class="ci-overlay" @click.self="closeDetail">
      <div class="ci-sheet">
        <div class="ci-sheet-header">
          <span class="ci-sheet-title">{{ detailName }} · 洞察详情</span>
          <span class="ci-sheet-close" @click="closeDetail">✕</span>
        </div>

        <div v-if="detailLoading" class="ci-loading">加载中...</div>

        <div v-else-if="detail" class="ci-sheet-body">
          <!-- Card 1: Hero 卡片 -->
          <div class="ci-hero">
            <div class="ci-hero-name">{{ detail.overview?.basic?.name || detailName }}</div>
            <div class="ci-hero-badges">
              <span class="ci-hero-risk" :style="{ background: riskColorMap[detail.risk_level] || '#10B981', color: '#fff' }">
                {{ riskLabelMap[detail.risk_level] || detail.risk_level }}
              </span>
              <span v-if="detail.overview?.asset_structure?.style_tag" class="ci-hero-tier">
                {{ detail.overview.asset_structure.style_tag }}
              </span>
            </div>
            <div v-if="detail.overview?.basic?.summary" class="ci-hero-summary">
              {{ detail.overview.basic.summary }}
            </div>
          </div>

          <!-- Card 2: 核心指标四宫格 -->
          <div class="ci-metrics">
            <div class="ci-metric">
              <div class="ci-metric-icon">💰</div>
              <div class="ci-metric-value">{{ fmtWan(detail.overview?.basic?.total_aum) }}</div>
              <div class="ci-metric-label">总资产 (AUM)</div>
            </div>
            <div class="ci-metric">
              <div class="ci-metric-icon">📱</div>
              <div class="ci-metric-value">{{ detail.overview?.engagement?.recent_30d_logins || 0 }}<span class="ci-metric-unit">次</span></div>
              <div class="ci-metric-label">近30天活跃</div>
              <div class="ci-metric-sub">{{ detail.overview?.engagement?.engagement_tag || '--' }}<span v-if="detail.overview?.engagement?.last_contact_days != null"> · 上次联络{{ detail.overview.engagement.last_contact_days }}天前</span></div>
            </div>
            <div class="ci-metric">
              <div class="ci-metric-icon">🛡️</div>
              <div class="ci-metric-value">{{ detail.overview?.risk_profile?.risk_level || '--' }}</div>
              <div class="ci-metric-label">风险评级</div>
              <div class="ci-metric-sub">{{ detail.overview?.risk_profile?.match_status || '--' }}</div>
            </div>
            <div class="ci-metric">
              <div class="ci-metric-icon">🎯</div>
              <div class="ci-metric-value">{{ detail.overview?.existing_opportunities?.count || 0 }}<span class="ci-metric-unit">个</span></div>
              <div class="ci-metric-label">关联商机</div>
              <div class="ci-metric-sub">估值 {{ fmtWan(detail.overview?.existing_opportunities?.total_value) }}</div>
            </div>
          </div>

          <!-- Card 3: 资产配置面板 -->
          <div v-if="detail.overview?.asset_structure" class="ci-panel">
            <div class="ci-panel-header">
              <span class="ci-panel-icon">📊</span>
              <span class="ci-panel-title">资产配置</span>
              <span class="ci-panel-tag">{{ fmtWan(detail.overview.asset_structure.total_holdings) }}</span>
            </div>
            <div v-for="item in [
              { label: '存款', pct: detail.overview.asset_structure.deposit_ratio, cls: 'deposit' },
              { label: '理财', pct: detail.overview.asset_structure.wealth_ratio, cls: 'wealth' },
              { label: '基金', pct: detail.overview.asset_structure.fund_ratio, cls: 'fund' },
              { label: '保险', pct: detail.overview.asset_structure.insurance_ratio, cls: 'insurance' },
            ]" :key="item.label" class="ci-asset-row">
              <span class="ci-asset-label">{{ item.label }}</span>
              <div class="ci-asset-track">
                <div class="ci-asset-fill" :class="'ci-asset-fill--' + item.cls" :style="{ width: Math.max((item.pct || 0) * 100, 4) + '%' }"></div>
              </div>
              <span class="ci-asset-val">{{ Math.round((item.pct || 0) * 100) }}%</span>
            </div>
            <div v-if="detail.overview.asset_structure.near_maturity_count > 0" class="ci-maturity-alert">
              ⏰ {{ detail.overview.asset_structure.near_maturity_count }} 笔产品近期到期，合计 {{ fmtWan(detail.overview.asset_structure.near_maturity_total) }}
            </div>
          </div>

          <!-- Card 4: 家庭 + 收入双栏 -->
          <div v-if="detail.overview?.family_lifecycle || detail.overview?.income_pattern" class="ci-dual-col">
            <div v-if="detail.overview?.family_lifecycle" class="ci-panel ci-panel--half">
              <div class="ci-panel-header"><span class="ci-panel-icon">👨‍👩‍👧</span><span class="ci-panel-title">家庭</span></div>
              <div class="ci-info-row"><span class="ci-info-label">阶段</span><span class="ci-info-val">{{ detail.overview.family_lifecycle.lifecycle_tag || '--' }}</span></div>
              <div v-if="detail.overview.family_lifecycle.marriage !== undefined" class="ci-info-row"><span class="ci-info-label">婚姻</span><span class="ci-info-val">{{ detail.overview.family_lifecycle.marriage ? '已婚' : '未婚' }}</span></div>
              <div v-if="detail.overview.family_lifecycle.children !== undefined" class="ci-info-row"><span class="ci-info-label">子女</span><span class="ci-info-val">{{ detail.overview.family_lifecycle.children ? (detail.overview.family_lifecycle.child_stage || '有') : '无' }}</span></div>
              <div v-if="detail.overview.family_lifecycle.financial_needs?.length" class="ci-tags">
                <span v-for="n in detail.overview.family_lifecycle.financial_needs" :key="n" class="ci-tag">{{ n }}</span>
              </div>
            </div>
            <div v-if="detail.overview?.income_pattern" class="ci-panel ci-panel--half">
              <div class="ci-panel-header"><span class="ci-panel-icon">💳</span><span class="ci-panel-title">收入</span></div>
              <div class="ci-info-row"><span class="ci-info-label">月均入账</span><span class="ci-info-val">{{ fmtWan(detail.overview.income_pattern.monthly_avg_in) }}</span></div>
              <div class="ci-info-row"><span class="ci-info-label">月均支出</span><span class="ci-info-val">{{ fmtWan(detail.overview.income_pattern.monthly_avg_out) }}</span></div>
              <div class="ci-info-row"><span class="ci-info-label">模式</span><span class="ci-info-val">{{ detail.overview.income_pattern.pattern_tag || '--' }}</span></div>
              <span v-if="detail.overview.income_pattern.has_salary_in" class="ci-tag ci-tag--purple">代发工资</span>
              <span v-if="detail.overview.income_pattern.recent_large_txn" class="ci-tag">近期大额交易</span>
            </div>
          </div>

          <!-- Card 5: 行为偏好 -->
          <div v-if="detail.overview?.engagement?.top_page_types?.length || detail.overview?.engagement?.product_interest?.length" class="ci-panel">
            <div class="ci-panel-header"><span class="ci-panel-icon">🔍</span><span class="ci-panel-title">行为偏好</span></div>
            <div v-if="detail.overview.engagement.top_page_types?.length">
              <div class="ci-sub-label">浏览偏好</div>
              <div class="ci-tags"><span v-for="t in detail.overview.engagement.top_page_types" :key="t" class="ci-tag ci-tag--purple">{{ t }}</span></div>
            </div>
            <div v-if="detail.overview.engagement.product_interest?.length" style="margin-top:8px">
              <div class="ci-sub-label">产品兴趣</div>
              <div class="ci-tags"><span v-for="t in detail.overview.engagement.product_interest" :key="t" class="ci-tag">{{ t }}</span></div>
            </div>
          </div>

          <!-- Card 6: 变化信号 🔔 -->
          <div class="ci-signals">
            <div class="ci-signals-header">
              <span>🔔</span>
              <span class="ci-panel-title">变化信号</span>
              <span class="ci-signals-count">{{ (detail.change_signals || []).length }} 条</span>
            </div>
            <div v-if="!detail.change_signals?.length" class="ci-signals-empty">📭 近期无显著行为变化信号</div>
            <div v-for="(sig, i) in (detail.change_signals || [])" :key="i" class="ci-signal-card" :class="'ci-signal-card--' + sevClass(sig.severity)">
              <span class="ci-signal-type" :class="'ci-signal-type--' + sevClass(sig.severity)">{{ sig.type || sig.severity || '信号' }}</span>
              <div class="ci-signal-title">{{ sig.title }}</div>
              <div v-if="sig.detail" class="ci-signal-detail">{{ sig.detail }}</div>
              <div v-if="sig.suggested_action" class="ci-signal-action">💡 {{ sig.suggested_action }}</div>
            </div>
          </div>

          <!-- Card 7: 风险提示 ⚠️ -->
          <div class="ci-signals">
            <div class="ci-signals-header">
              <span>⚠️</span>
              <span class="ci-panel-title">风险提示</span>
              <span class="ci-signals-count">{{ (detail.risk_signals || []).length }} 条</span>
            </div>
            <div v-if="!detail.risk_signals?.length" class="ci-signals-empty">✅ 暂未检测到显著风险信号</div>
            <div v-for="(sig, i) in (detail.risk_signals || [])" :key="i" class="ci-signal-card" :class="'ci-signal-card--' + sevClass(sig.level)">
              <span class="ci-signal-type" :class="'ci-signal-type--' + sevClass(sig.level)">{{ sig.type || sig.level || '风险' }}</span>
              <div class="ci-signal-title">{{ sig.title }}</div>
              <div v-if="sig.detail" class="ci-signal-detail">{{ sig.detail }}</div>
              <div v-if="sig.suggested_action" class="ci-signal-action">💡 {{ sig.suggested_action }}</div>
            </div>
          </div>

          <!-- Card 8: 底部 -->
          <button class="ci-view-profile-btn" @click="goCustomerProfile">📋 查看完整画像</button>
          <div class="ci-footer-meta">
            <span>生成时间：{{ detail.generated_at ? detail.generated_at.slice(0, 10) : '--' }}</span>
            <span v-if="detail.expires_at">有效期至 {{ detail.expires_at }}</span>
          </div>
        </div>

        <div v-else class="ci-empty">该客户暂无洞察快照</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ci-page { min-height: 100%; background: #f8f8f8; padding-bottom: 40px; }
.ci-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.ci-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.ci-title { flex: 1; font-size: 17px; font-weight: 600; }
.ci-count { font-size: 12px; color: var(--color-text-secondary); background: #f0f0f0; padding: 2px 10px; border-radius: 999px; }
.ci-body { padding: 12px 16px; }
.ci-loading { text-align: center; padding: 40px; color: #999; font-size: 14px; }
.ci-empty { text-align: center; padding: 60px 20px; color: #999; font-size: 14px; }

/* List cards */
.ci-card { background: #fff; border-radius: 10px; padding: 14px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); cursor: pointer; }
.ci-card:active { background: #fafafa; }
.ci-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.ci-card-name { font-size: 15px; font-weight: 600; }
.ci-risk-tag { font-size: 10px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.ci-card-signals { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
.ci-signal { font-size: 11px; padding: 2px 8px; border-radius: 4px; }
.ci-signal--change { background: #FEF3C7; color: #D97706; }
.ci-signal--risk { background: #FEE2E2; color: #DC2626; }
.ci-signal--ok { background: #D1FAE5; color: #059669; }
.ci-card-time { font-size: 11px; color: #999; }

/* Overlay & Sheet */
.ci-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0.4); z-index: 100; display: flex; align-items: flex-end; }
.ci-sheet { background: #fff; width: 100%; max-height: 88%; border-radius: 16px 16px 0 0; overflow-y: auto; }
.ci-sheet::-webkit-scrollbar { display: none; }
.ci-sheet-header { display: flex; align-items: center; justify-content: space-between; padding: 16px; border-bottom: 1px solid #eee; position: sticky; top: 0; background: #fff; z-index: 1; }
.ci-sheet-title { font-size: 16px; font-weight: 600; }
.ci-sheet-close { font-size: 18px; cursor: pointer; color: #999; padding: 4px; }
.ci-sheet-body { padding: 16px; }

/* Card 1: Hero */
.ci-hero { margin-bottom: 16px; }
.ci-hero-name { font-size: 18px; font-weight: 700; margin-bottom: 8px; }
.ci-hero-badges { display: flex; gap: 8px; margin-bottom: 8px; }
.ci-hero-risk { font-size: 11px; padding: 2px 10px; border-radius: 4px; font-weight: 500; }
.ci-hero-tier { font-size: 11px; padding: 2px 10px; border-radius: 4px; background: #EDE9FE; color: #6C5CE7; }
.ci-hero-summary { font-size: 13px; color: var(--color-text-secondary); line-height: 1.6; }

/* Card 2: Metrics */
.ci-metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 16px; }
.ci-metric { background: #f9f9f9; border-radius: 8px; padding: 12px; text-align: center; }
.ci-metric-icon { font-size: 16px; margin-bottom: 4px; }
.ci-metric-value { font-size: 18px; font-weight: 700; color: var(--color-text); }
.ci-metric-unit { font-size: 12px; font-weight: 400; }
.ci-metric-label { font-size: 11px; color: #999; margin-top: 2px; }
.ci-metric-sub { font-size: 10px; color: #bbb; margin-top: 2px; }

/* Card 3: Asset allocation */
.ci-panel { background: #f9f9f9; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.ci-panel-header { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; }
.ci-panel-icon { font-size: 14px; }
.ci-panel-title { font-size: 14px; font-weight: 600; flex: 1; }
.ci-panel-tag { font-size: 11px; color: var(--color-primary); background: rgba(171,32,41,0.08); padding: 2px 8px; border-radius: 4px; }

.ci-asset-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.ci-asset-label { width: 32px; font-size: 12px; color: #666; flex-shrink: 0; }
.ci-asset-track { flex: 1; height: 6px; background: #eee; border-radius: 3px; overflow: hidden; }
.ci-asset-fill { height: 100%; border-radius: 3px; }
.ci-asset-fill--deposit { background: #3B82F6; }
.ci-asset-fill--wealth { background: #8B5CF6; }
.ci-asset-fill--fund { background: #F59E0B; }
.ci-asset-fill--insurance { background: #10B981; }
.ci-asset-val { width: 32px; font-size: 12px; color: #666; text-align: right; flex-shrink: 0; }
.ci-maturity-alert { margin-top: 8px; font-size: 12px; color: #D97706; display: flex; align-items: center; gap: 4px; }

/* Card 4: Dual column */
.ci-dual-col { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }
.ci-panel--half { margin-bottom: 0; }
.ci-info-row { display: flex; justify-content: space-between; font-size: 12px; padding: 3px 0; }
.ci-info-label { color: #999; }
.ci-info-val { color: var(--color-text); font-weight: 500; }
.ci-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.ci-tag { font-size: 10px; padding: 2px 8px; border-radius: 4px; background: #f0f0f0; color: #666; }
.ci-tag--purple { background: #EDE9FE; color: #6C5CE7; }

/* Card 5: Behavior */
.ci-sub-label { font-size: 11px; color: #999; margin-bottom: 4px; }

/* Card 6 & 7: Signals */
.ci-signals { margin-bottom: 12px; }
.ci-signals-header { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; }
.ci-signals-count { font-size: 11px; color: #999; margin-left: auto; }
.ci-signals-empty { text-align: center; padding: 12px; font-size: 13px; color: #bbb; background: #f9f9f9; border-radius: 8px; }

.ci-signal-card { padding: 10px 12px; border-radius: 8px; margin-bottom: 8px; }
.ci-signal-card--high { background: #FEF2F2; border-left: 3px solid #EF4444; }
.ci-signal-card--medium { background: #FFFBEB; border-left: 3px solid #F59E0B; }
.ci-signal-card--low { background: #F0FDF4; border-left: 3px solid #10B981; }
.ci-signal-type { font-size: 10px; padding: 1px 6px; border-radius: 3px; font-weight: 500; }
.ci-signal-type--high { background: #FEE2E2; color: #DC2626; }
.ci-signal-type--medium { background: #FEF3C7; color: #D97706; }
.ci-signal-type--low { background: #D1FAE5; color: #059669; }
.ci-signal-title { font-size: 13px; font-weight: 600; margin-top: 4px; color: var(--color-text); }
.ci-signal-detail { font-size: 12px; color: var(--color-text-secondary); margin-top: 2px; line-height: 1.5; }
.ci-signal-action { font-size: 12px; color: var(--color-primary); margin-top: 6px; font-weight: 500; }

/* Card 8: Footer */
.ci-view-profile-btn { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--color-primary); background: transparent; color: var(--color-primary); font-size: 14px; font-weight: 500; cursor: pointer; margin-top: 4px; }
.ci-view-profile-btn:active { background: rgba(171,32,41,0.04); }
.ci-footer-meta { display: flex; justify-content: space-between; font-size: 11px; color: #bbb; margin-top: 8px; padding-bottom: 16px; }
</style>
