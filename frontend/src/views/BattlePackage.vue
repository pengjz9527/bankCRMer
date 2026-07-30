<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const bpId = (route.params.id as string) || (route.query.id as string)
const loading = ref(true)
const bpData = ref<any>(null)
const expandedSections = ref<Record<string, boolean>>({ overview: true, agenda: true, clues: true, benefit: false, risk: false, actions: false })

function goBack() { router.back() }
function toggleSection(key: string) {
  expandedSections.value[key] = !expandedSections.value[key]
}

onMounted(async () => {
  if (!bpId) { loading.value = false; return }
  try {
    const res = await api.getBattlePackageDetail(bpId)
    bpData.value = res.data
  } catch (e) {
    console.warn('加载作战包失败', e)
    appStore.showToast('加载作战包失败')
  } finally {
    loading.value = false
  }
})

function fmtDate(d: string) {
  if (!d) return '--'
  return d.replace('T', ' ').slice(0, 16)
}

function startMeeting() {
  if (!bpId) return
  router.push({ name: 'meeting', params: { id: bpId } })
}
function editPackage() { appStore.showToast('编辑功能开发中') }
function copyText(text: string) {
  navigator.clipboard?.writeText(text).then(() => appStore.showToast('已复制'))
}
</script>

<template>
  <div class="bp-page">
    <div class="bp-header">
      <span class="bp-back" @click="goBack">←</span>
      <span class="bp-title">作战包</span>
      <span v-if="bpData" class="bp-mode-badge">{{ bpData.mode }}</span>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="bp-loading">
      <div class="bp-spinner"></div>
      <div>加载作战包中...</div>
    </div>

    <!-- Empty -->
    <div v-else-if="!bpData" class="bp-empty">
      <div style="font-size:36px;margin-bottom:12px">📋</div>
      <div>未找到作战包数据</div>
    </div>

    <!-- Content -->
    <div v-else class="bp-body">
      <!-- Meta info -->
      <div class="bp-meta-card">
        <div class="bp-meta-row">
          <span class="bp-meta-label">客户</span>
          <span class="bp-meta-value">{{ bpData.cust_name }}</span>
        </div>
        <div class="bp-meta-row">
          <span class="bp-meta-label">模式</span>
          <span class="bp-meta-value">{{ bpData.mode }}</span>
        </div>
        <div class="bp-meta-row">
          <span class="bp-meta-label">状态</span>
          <span class="bp-meta-value bp-status" :class="bpData.status === '未使用' ? 'bp-status--unused' : 'bp-status--used'">{{ bpData.status }}</span>
        </div>
        <div class="bp-meta-row">
          <span class="bp-meta-label">生成时间</span>
          <span class="bp-meta-value">{{ fmtDate(bpData.generated_at) }}</span>
        </div>
        <div class="bp-meta-row">
          <span class="bp-meta-label">有效期至</span>
          <span class="bp-meta-value">{{ bpData.expires_at || '--' }}</span>
        </div>
      </div>

      <!-- 客户速览 -->
      <div class="bp-section">
        <div class="bp-section-header" @click="toggleSection('overview')">
          <span class="bp-section-title">👤 客户速览</span>
          <span class="bp-arrow" :class="{ open: expandedSections.overview }">▾</span>
        </div>
        <div v-show="expandedSections.overview" class="bp-section-body">
          <!-- Agent生成的丰富结构 -->
          <template v-if="bpData.customer_overview?.one_liner || bpData.customer_overview?.profile_summary">
            <div v-if="bpData.customer_overview.one_liner" class="bp-ov-oneliner">{{ bpData.customer_overview.one_liner }}</div>
            <div v-if="bpData.customer_overview.profile_summary" class="bp-ov-summary">{{ bpData.customer_overview.profile_summary }}</div>
            <div v-if="bpData.customer_overview.visit_purpose" class="bp-ov-purpose">
              <span class="bp-ov-label">拜访目的：</span>{{ bpData.customer_overview.visit_purpose }}
            </div>
            <div v-if="bpData.customer_overview.name" class="bp-ov-name">客户：{{ bpData.customer_overview.name }}</div>
          </template>
          <!-- 简化版结构 (age/gender/tier) -->
          <template v-else>
            <div class="bp-overview-grid">
              <div class="bp-ov-item">
                <div class="bp-ov-label">姓名</div>
                <div class="bp-ov-val">{{ bpData.customer_overview?.name || '--' }}</div>
              </div>
              <div class="bp-ov-item">
                <div class="bp-ov-label">年龄</div>
                <div class="bp-ov-val">{{ bpData.customer_overview?.age || '--' }}岁</div>
              </div>
              <div class="bp-ov-item">
                <div class="bp-ov-label">性别</div>
                <div class="bp-ov-val">{{ bpData.customer_overview?.gender || '--' }}</div>
              </div>
              <div class="bp-ov-item">
                <div class="bp-ov-label">客户等级</div>
                <div class="bp-ov-val">{{ bpData.customer_overview?.tier || '--' }}</div>
              </div>
              <div class="bp-ov-item">
                <div class="bp-ov-label">总资产</div>
                <div class="bp-ov-val">{{ bpData.customer_overview?.total_aum ? (bpData.customer_overview.total_aum >= 10000 ? (bpData.customer_overview.total_aum / 10000).toFixed(1) + '万' : bpData.customer_overview.total_aum + '元') : '--' }}</div>
              </div>
              <div class="bp-ov-item">
                <div class="bp-ov-label">拜访目的</div>
                <div class="bp-ov-val">{{ bpData.customer_overview?.visit_purpose || '--' }}</div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- 面谈议程 -->
      <div v-if="bpData.agenda?.length" class="bp-section">
        <div class="bp-section-header" @click="toggleSection('agenda')">
          <span class="bp-section-title">📋 面谈议程（{{ bpData.agenda.length }}）</span>
          <span class="bp-arrow" :class="{ open: expandedSections.agenda }">▾</span>
        </div>
        <div v-show="expandedSections.agenda" class="bp-section-body">
          <div v-for="(item, i) in bpData.agenda" :key="i" class="bp-agenda-item">
            <div class="bp-agenda-step">
              <span class="bp-agenda-num">{{ item.step || i + 1 }}</span>
              {{ item.topic || item.name || `环节${i + 1}` }}
            </div>
            <div v-if="item.duration" class="bp-agenda-time">{{ item.duration }}</div>
            <div v-if="item.key_points?.length" class="bp-agenda-points">
              <div v-for="(kp, ki) in item.key_points" :key="ki" class="bp-agenda-point">· {{ kp }}</div>
            </div>
            <div v-else-if="item.desc || item.description" class="bp-agenda-desc">{{ item.desc || item.description }}</div>
          </div>
        </div>
      </div>

      <!-- 营销线索 -->
      <div class="bp-section">
        <div class="bp-section-header" @click="toggleSection('clues')">
          <span class="bp-section-title">💡 营销线索（{{ bpData.clues?.length || 0 }}）</span>
          <span class="bp-arrow" :class="{ open: expandedSections.clues }">▾</span>
        </div>
        <div v-show="expandedSections.clues" class="bp-section-body">
          <div v-if="!bpData.clues?.length" class="bp-no-data">暂无线索</div>
          <div v-for="clue in (bpData.clues || [])" :key="clue.clue_id || clue.title" class="bp-clue">
            <div class="bp-clue-header">
              <span class="bp-clue-title">{{ clue.title }}</span>
              <span class="bp-clue-priority" :class="'bp-priority--' + (clue.priority === '高' ? 'high' : clue.priority === '中' ? 'mid' : 'low')">
                {{ clue.priority }}
              </span>
            </div>
            <div v-if="clue.discovery_basis" class="bp-clue-row">
              <span class="bp-clue-label">发现依据</span>
              <span class="bp-clue-val">{{ clue.discovery_basis }}</span>
            </div>
            <div v-if="clue.strategy" class="bp-clue-row">
              <span class="bp-clue-label">营销策略</span>
              <span class="bp-clue-val">{{ clue.strategy }}</span>
            </div>
            <div v-if="clue.opening_script" class="bp-clue-row">
              <span class="bp-clue-label">切入话术</span>
              <span class="bp-clue-val bp-clue-script">{{ clue.opening_script }}</span>
            </div>
            <div v-if="clue.products?.length" class="bp-clue-products">
              <div class="bp-clue-label">推荐产品</div>
              <div v-for="(p, pi) in clue.products" :key="pi" class="bp-product">
                <div class="bp-product-name">{{ p.name }}</div>
                <div class="bp-product-meta">
                  <span v-if="p.type">{{ p.type }}</span>
                  <span v-if="p.risk">风险 {{ p.risk }}</span>
                  <span v-if="p.yield">收益 {{ p.yield }}%</span>
                  <span v-if="p.expected_return">{{ p.expected_return }}</span>
                </div>
                <div v-if="p.reason" class="bp-product-reason">推荐理由：{{ p.reason }}</div>
                <div v-if="p.script" class="bp-product-script">「{{ p.script }}」</div>
              </div>
            </div>
            <div v-if="clue.deviation_branches?.length" class="bp-clue-deviations">
              <div class="bp-clue-label">偏离应对</div>
              <div v-for="(db, di) in clue.deviation_branches" :key="di" class="bp-deviation">
                <div v-if="db.scenario" class="bp-dev-scenario">客户说：「{{ db.scenario }}」</div>
                <div v-if="db.response" class="bp-dev-response">应对：{{ db.response }}</div>
                <div v-if="db.suggested_products?.length" class="bp-dev-products">
                  备选产品：{{ db.suggested_products.join('、') }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 营销切入点 -->
      <div v-if="bpData.benefit_entries" class="bp-section">
        <div class="bp-section-header" @click="toggleSection('benefit')">
          <span class="bp-section-title">🎯 营销切入点</span>
          <span class="bp-arrow" :class="{ open: expandedSections.benefit }">▾</span>
        </div>
        <div v-show="expandedSections.benefit" class="bp-section-body">
          <div v-if="bpData.benefit_entries.default_entry" class="bp-benefit-default">
            <div class="bp-benefit-title">{{ bpData.benefit_entries.default_entry.title }}</div>
            <div v-if="bpData.benefit_entries.default_entry.description" class="bp-benefit-desc">{{ bpData.benefit_entries.default_entry.description }}</div>
          </div>
          <div v-if="bpData.benefit_entries.quick_hooks?.length" class="bp-benefit-hooks">
            <div class="bp-clue-label">快速切入</div>
            <div v-for="(h, hi) in bpData.benefit_entries.quick_hooks" :key="hi" class="bp-hook-item">· {{ typeof h === 'string' ? h : h.title || h.text || '' }}</div>
          </div>
        </div>
      </div>

      <!-- 风险提示 -->
      <div v-if="bpData.risk_warnings?.length" class="bp-section">
        <div class="bp-section-header" @click="toggleSection('risk')">
          <span class="bp-section-title">⚠️ 风险提示（{{ bpData.risk_warnings.length }}）</span>
          <span class="bp-arrow" :class="{ open: expandedSections.risk }">▾</span>
        </div>
        <div v-show="expandedSections.risk" class="bp-section-body">
          <div v-for="(w, i) in bpData.risk_warnings" :key="i" class="bp-risk-item">
            ⚠️ {{ typeof w === 'string' ? w : w.text || w.warning || '' }}
          </div>
        </div>
      </div>

      <!-- 访后动作 -->
      <div v-if="bpData.post_visit_actions?.length" class="bp-section">
        <div class="bp-section-header" @click="toggleSection('actions')">
          <span class="bp-section-title">✅ 访后动作（{{ bpData.post_visit_actions.length }}）</span>
          <span class="bp-arrow" :class="{ open: expandedSections.actions }">▾</span>
        </div>
        <div v-show="expandedSections.actions" class="bp-section-body">
          <div v-for="(a, i) in bpData.post_visit_actions" :key="i" class="bp-action-item">
            ☐ {{ typeof a === 'string' ? a : a.action || a.text || '' }}
          </div>
        </div>
      </div>
    </div>

    <!-- P1 底部操作栏 -->
    <div v-if="bpData" class="bp-bottom-bar">
      <button class="bp-btn bp-btn--primary" @click="startMeeting">
        <svg viewBox="0 0 24 24" class="ico ico--sm" style="vertical-align:middle;margin-right:4px"><use href="#ico-target" /></svg>
        开始面谈
      </button>
      <button class="bp-btn bp-btn--outline" @click="editPackage">
        <svg viewBox="0 0 24 24" class="ico ico--sm" style="vertical-align:middle;margin-right:4px"><use href="#ico-edit" /></svg>
        编辑
      </button>
      <button class="bp-btn bp-btn--ghost" @click="goBack">返回</button>
    </div>
  </div>
</template>

<style scoped>
.bp-page { min-height: 100%; background: var(--color-bg); }
.bp-header {
  display: flex; align-items: center; padding: 12px 16px;
  background: #fff; position: sticky; top: 0; z-index: 5;
  border-bottom: 1px solid #eee;
}
.bp-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.bp-title { flex: 1; font-size: 16px; font-weight: 600; }
.bp-mode-badge {
  font-size: 11px; padding: 3px 10px; border-radius: 999px;
  background: rgba(171,32,41,0.08); color: var(--color-primary); font-weight: 500;
}

/* Loading & Empty */
.bp-loading { text-align: center; padding: 80px 20px; color: #999; font-size: 14px; }
.bp-spinner {
  width: 32px; height: 32px; border: 3px solid #eee; border-top-color: var(--color-primary);
  border-radius: 50%; margin: 0 auto 12px; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.bp-empty { text-align: center; padding: 80px 20px; color: #999; font-size: 14px; }

/* Body */
.bp-body { padding: 12px 16px 80px; }

/* Meta card */
.bp-meta-card {
  background: #fff; border-radius: 10px; padding: 14px 16px;
  margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.bp-meta-row { display: flex; padding: 4px 0; font-size: 13px; }
.bp-meta-label { width: 70px; color: #999; font-size: 12px; flex-shrink: 0; }
.bp-meta-value { color: var(--color-text); font-weight: 500; }
.bp-status { font-size: 11px; padding: 1px 8px; border-radius: 4px; }
.bp-status--unused { background: #FFF3CD; color: #856404; }
.bp-status--used { background: #D4EDDA; color: #155724; }

/* Sections */
.bp-section {
  background: #fff; border-radius: 10px; margin-bottom: 10px;
  overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.bp-section-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; cursor: pointer; user-select: none;
}
.bp-section-header:active { background: #fafafa; }
.bp-section-title { font-size: 14px; font-weight: 600; }
.bp-arrow { font-size: 12px; color: #999; transition: transform 0.2s; }
.bp-arrow.open { transform: rotate(180deg); }
.bp-section-body { padding: 0 16px 14px; }
.bp-no-data { text-align: center; padding: 20px; color: #999; font-size: 13px; }

/* Customer overview - agent format */
.bp-ov-oneliner {
  font-size: 15px; font-weight: 600; color: var(--color-text);
  margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #f0f0f0;
}
.bp-ov-summary {
  font-size: 13px; color: var(--color-text); line-height: 1.7;
  margin-bottom: 8px;
}
.bp-ov-purpose {
  font-size: 12px; color: var(--color-primary);
  background: rgba(171,32,41,0.04); padding: 8px 10px; border-radius: 6px;
  margin-bottom: 4px;
}
.bp-ov-purpose .bp-ov-label { color: #999; font-size: 11px; }
.bp-ov-name { font-size: 12px; color: #999; margin-top: 4px; }

/* Customer overview - simple format */
.bp-overview-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
}
.bp-ov-item { }
.bp-ov-label { font-size: 11px; color: #999; margin-bottom: 2px; }
.bp-ov-val { font-size: 14px; font-weight: 500; color: var(--color-text); }

/* Agenda */
.bp-agenda-item {
  padding: 10px 0; border-bottom: 1px solid #f0f0f0;
}
.bp-agenda-item:last-child { border-bottom: none; }
.bp-agenda-step { font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.bp-agenda-num {
  width: 22px; height: 22px; border-radius: 50%;
  background: var(--color-primary); color: #fff; font-size: 11px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.bp-agenda-time { font-size: 11px; color: var(--color-primary); margin-bottom: 4px; }
.bp-agenda-points { padding-left: 30px; }
.bp-agenda-point { font-size: 12px; color: var(--color-text-secondary); padding: 2px 0; }
.bp-agenda-desc { font-size: 12px; color: var(--color-text-secondary); padding-left: 30px; }

/* Clues */
.bp-clue {
  padding: 12px 0; border-bottom: 1px solid #f0f0f0;
}
.bp-clue:last-child { border-bottom: none; }
.bp-clue-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.bp-clue-title { font-size: 14px; font-weight: 600; }
.bp-clue-priority { font-size: 10px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.bp-priority--high { background: #F8D7DA; color: #721C24; }
.bp-priority--mid { background: #FFF3CD; color: #856404; }
.bp-priority--low { background: #D4EDDA; color: #155724; }
.bp-clue-row { display: flex; gap: 8px; padding: 4px 0; font-size: 12px; }
.bp-clue-label { width: 56px; flex-shrink: 0; color: #999; font-size: 11px; padding-top: 2px; }
.bp-clue-val { flex: 1; color: var(--color-text); line-height: 1.6; }
.bp-clue-script {
  background: #f8f8f8; padding: 8px 10px; border-radius: 6px;
  border-left: 3px solid var(--color-primary); line-height: 1.6;
  font-style: italic;
}

/* Products */
.bp-clue-products { margin-top: 10px; }
.bp-clue-products .bp-clue-label { font-size: 11px; color: #999; margin-bottom: 6px; }
.bp-product {
  background: #f8f8f8; border-radius: 8px; padding: 10px 12px;
  margin-bottom: 6px;
}
.bp-product-name { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.bp-product-meta { display: flex; gap: 10px; font-size: 11px; color: var(--color-text-secondary); flex-wrap: wrap; }
.bp-product-reason { font-size: 11px; color: #666; margin-top: 4px; }
.bp-product-script { font-size: 12px; color: var(--color-primary); margin-top: 4px; font-style: italic; }

/* Deviations */
.bp-clue-deviations { margin-top: 10px; }
.bp-clue-deviations .bp-clue-label { font-size: 11px; color: #999; margin-bottom: 6px; }
.bp-deviation {
  background: #fff8f0; border-radius: 6px; padding: 8px 10px;
  margin-bottom: 6px; border-left: 3px solid #f0a020;
}
.bp-dev-scenario { font-size: 12px; color: #856404; margin-bottom: 2px; }
.bp-dev-response { font-size: 12px; color: var(--color-text); }
.bp-dev-products { font-size: 11px; color: var(--color-text-secondary); margin-top: 2px; }

/* Benefit entries */
.bp-benefit-default { margin-bottom: 10px; }
.bp-benefit-title { font-size: 14px; font-weight: 600; margin-bottom: 4px; }
.bp-benefit-desc { font-size: 12px; color: var(--color-text-secondary); }
.bp-benefit-hooks { margin-top: 8px; }
.bp-benefit-hooks .bp-clue-label { margin-bottom: 4px; }
.bp-hook-item { font-size: 12px; color: var(--color-text-secondary); padding: 2px 0; }

/* Risks */
.bp-risk-item {
  font-size: 13px; color: #B8600C; padding: 6px 0;
  border-bottom: 1px solid #f5f5f5;
}
.bp-risk-item:last-child { border-bottom: none; }

/* Actions */
.bp-action-item {
  font-size: 13px; padding: 6px 0;
  border-bottom: 1px solid #f5f5f5;
}
.bp-action-item:last-child { border-bottom: none; }

/* P1 Bottom Bar */
.bp-bottom-bar {
  position: sticky; bottom: 0; z-index: 10;
  display: flex; gap: 10px; padding: 10px 16px;
  background: #fff; border-top: 1px solid #eee;
  box-shadow: 0 -2px 8px rgba(0,0,0,0.04);
}
.bp-btn {
  flex: 1; padding: 12px 0; border-radius: 8px;
  font-size: 14px; font-weight: 600; cursor: pointer;
  border: none; display: flex; align-items: center; justify-content: center;
}
.bp-btn--primary { background: var(--color-primary); color: #fff; }
.bp-btn--outline { background: #fff; color: var(--color-primary); border: 1px solid var(--color-primary); }
.bp-btn--ghost { background: transparent; color: #999; flex: 0.6; }
</style>
