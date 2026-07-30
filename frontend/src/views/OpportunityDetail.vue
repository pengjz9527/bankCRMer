<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'
import { useOpportunityStore } from '@/stores/opportunity'
import { useManagerStore } from '@/stores/manager'

const route = useRoute()
const router = useRouter()
const oppStore = useOpportunityStore()
const managerStore = useManagerStore()

const oppId = (route.params.id as string) || 'd1'

interface OppItem {
  id: string; name: string; meta: string; type: string; tag: string; tagClass: string
  fields?: { label: string; val: string }[]; confidence?: number; reason?: string
  estimate: string; source: string; assets: string; danger?: boolean; bp_id?: string
}

const allOpps: Record<string, OppItem> = {
  d1: { id:'d1', name:'赵明辉', meta:'男 · 52岁 · 制造业', type:'代发到账配置', tag:'系统推送', tagClass:'system', fields:[{ label:'近6月月均代发', val:'32,000元' },{ label:'最近代发日期', val:'2026-07-15' },{ label:'预计下次到账', val:'2026-07-17（2天后）' }], estimate:'≈8万', source:'系统推送·代发到账', assets:'总资产58.7万 | 财富客户 | 理财32万·基金18万·存款3.5万 | 风险偏好：稳健型' },
  d2: { id:'d2', name:'钱伟民', meta:'男 · 38岁 · IT行业', type:'代发到账配置', tag:'系统推送', tagClass:'system', fields:[{ label:'近6月月均代发', val:'28,500元' },{ label:'最近代发日期', val:'2026-07-12' },{ label:'预计下次到账', val:'2026-07-16（明天）' }], estimate:'≈6万', source:'系统推送·代发到账', assets:'总资产42.3万 | 金卡客户 | 存款28万·理财14万 | 风险偏好：保守型' },
  l1: { id:'l1', name:'吴大伟', meta:'男 · 56岁 · 餐饮业', type:'流失预警挽回', tag:'系统推送', tagClass:'system', danger:true, fields:[{ label:'资产总额', val:'210万' },{ label:'流失概率', val:'72% · 高' },{ label:'流失原因', val:'近期大额转出3笔，合计65万 · 疑似转投他行' }], estimate:'≈18万', source:'系统推送·流失预警', assets:'总资产210万 | 私行客户 | 理财95万·基金68万·存款47万 | 风险偏好：平衡型' },
  l2: { id:'l2', name:'郑美玲', meta:'女 · 42岁 · 医疗行业', type:'流失预警挽回', tag:'系统推送', tagClass:'system', fields:[{ label:'资产总额', val:'85万' },{ label:'流失概率', val:'65% · 中高' },{ label:'流失原因', val:'近2月未进行任何交易，活跃度显著下降' }], estimate:'≈8万', source:'系统推送·流失预警', assets:'总资产85万 | 财富客户 | 理财45万·基金22万·存款18万 | 风险偏好：稳健型' },
  a1: { id:'a1', name:'陈建国', meta:'男 · 35岁 · 教育行业', type:'基金购买意向', tag:'AI挖掘', tagClass:'ai', confidence:82, reason:'近3月月均非消费支出5.2万，其中3笔买入理财竞品，判断有较强理财需求但未在我行配置', estimate:'≈5万', source:'AI挖掘·基金购买意向', assets:'总资产38.5万 | 金卡客户 | 存款30万·理财8.5万 | 风险偏好：进取型' },
  m1: { id:'m1', name:'赵婷婷', meta:'女 · 30岁 · 金融行业', type:'大额配置建议', tag:'手动创建', tagClass:'manual', fields:[{ label:'意向描述', val:'客户主动咨询基金定投，希望每周定投3000元' },{ label:'发现渠道', val:'客户主动来电咨询' },{ label:'创建日期', val:'2026-07-15' }], estimate:'≈2万', source:'客户经理创建·理财配置', assets:'总资产18.2万 | 普通客户 | 存款15万·理财3.2万 | 风险偏好：平衡型' },
  m2: { id:'m2', name:'黄俊杰', meta:'男 · 45岁 · 房地产行业', type:'大额配置建议', tag:'手动创建', tagClass:'manual', fields:[{ label:'意向描述', val:'面谈时提到有闲置资金50万，考虑大额存单或稳健理财' },{ label:'发现渠道', val:'生日回访面谈' },{ label:'创建日期', val:'2026-07-13' }], estimate:'≈15万', source:'客户经理创建·大额配置', assets:'总资产162万 | 财富客户 | 存款80万·理财52万·基金30万 | 风险偏好：稳健型' },
}

const opp = ref<OppItem>(allOpps[oppId] || allOpps.d1)

/* 尝试从 API 加载商机详情 */
onMounted(async () => {
  await loadOppDetail()
})

// 监听经理切换，重新查找商机
watch(() => managerStore.currentId, () => {
  loadOppDetail()
})

async function loadOppDetail() {
  // 确保商机列表已加载
  if (oppStore.items.length === 0) {
    await oppStore.loadOpportunities(managerStore.currentId)
  }
  // 从 store 查找当前商机
  const apiOpp = oppStore.items.find(o => o.id === oppId || o.opp_id === oppId)
  if (apiOpp) {
    opp.value = {
      id: apiOpp.id || apiOpp.opp_id || oppId,
      name: apiOpp.customerName || apiOpp.cust_name || '',
      meta: apiOpp.customerName || '',
      type: apiOpp.type || '',
      tag: apiOpp.source || '',
      tagClass: apiOpp.source === 'AI挖掘' ? 'ai' : apiOpp.source === '手动创建' ? 'manual' : 'system',
      reason: apiOpp.reasoning || apiOpp.description || '',
      confidence: apiOpp.confidence ? Math.round(apiOpp.confidence * 100) : undefined,
      estimate: formatVal(apiOpp.estimatedValue || 0),
      source: apiOpp.source || '',
      assets: '',
      bp_id: apiOpp.bp_id,
      fields: apiOpp.reasoning ? [{ label:'AI分析', val: apiOpp.reasoning }] : undefined,
    }
  }
}

function formatVal(v: number) {
  if (v >= 10000) return `≈${(v/10000).toFixed(0)}万`
  return `≈${(v/10000).toFixed(1)}万`
}

const sourceIcons: Record<string, string> = {
  '系统推送·代发到账': 'ico-inbox-arrow',
  '系统推送·流失预警': 'ico-warning',
  'AI挖掘·基金购买意向': 'ico-robot',
  '客户经理创建·理财配置': 'ico-edit',
  '客户经理创建·大额配置': 'ico-edit',
}

function goBack() { router.back() }
function goCustomerProfile() { router.push({ name: 'customer-detail', params: { id: opp.value.name } }) }
function goBattlePackage() {
  if (opp.value.bp_id) {
    router.push({ name: 'battle-package', query: { id: opp.value.bp_id } })
  } else {
    router.push({ name: 'battle-package-mode', query: { oppId: opp.value.id } })
  }
}
</script>

<template>
  <div class="od-page">
    <div class="od-header">
      <span class="od-back" @click="goBack">←</span>
      <span class="od-title">{{ opp.name }} · {{ opp.meta }}</span>
    </div>

    <div class="od-body">
      <!-- Source -->
      <div class="od-section">
        <div class="od-section-title">
          <svg viewBox="0 0 24 24" class="ico ico--sm"><use :href="'#' + (sourceIcons[opp.source] || 'ico-clipboard')" /></svg> {{ opp.source }}
        </div>
        <template v-if="opp.fields">
          <div v-for="f in opp.fields" :key="f.label" class="od-row">
            <span class="od-label">{{ f.label }}</span>
            <span class="od-value">{{ f.val }}</span>
          </div>
        </template>
        <template v-if="opp.confidence !== undefined">
          <div class="od-row">
            <span class="od-label">置信度</span>
            <span class="od-value" style="color:#6C5CE7;font-weight:600">{{ opp.confidence }}%</span>
          </div>
          <div v-if="opp.reason" class="od-row">
            <span class="od-label">推理说明</span>
            <span class="od-value" style="font-size:12px;text-align:left;flex:1">{{ opp.reason }}</span>
          </div>
        </template>
        <div class="od-row">
          <span class="od-label">预估贡献</span>
          <span class="od-value" style="color:var(--color-primary);font-weight:600">{{ opp.estimate }}</span>
        </div>
      </div>

      <!-- Customer Overview -->
      <div class="od-section">
        <div class="od-section-title"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-chart" /></svg> 客户速览</div>
        <div class="od-row">
          <span class="od-label">资产概况</span>
          <span class="od-value" style="font-size:12px">{{ opp.assets }}</span>
        </div>
        <div class="od-link" @click="goCustomerProfile()">查看完整客户画像 →</div>
      </div>

      <!-- Action -->
      <div class="od-section">
        <div class="od-action-card" @click="goBattlePackage()">
          <div class="od-action-icon"><svg viewBox="0 0 24 24" class="ico ico--lg"><use href="#ico-clipboard" /></svg></div>
          <div class="od-action-info">
            <div class="od-action-title">{{ opp.bp_id ? '已生成作战包' : '生成作战包' }}</div>
            <div class="od-action-desc">{{ opp.bp_id ? '点击查看已生成的作战包' : '基于客户画像和商机信息，AI生成面谈作战包' }}</div>
          </div>
          <div class="od-action-arrow">›</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.od-page { min-height: 100%; background: #f8f8f8; padding-bottom: 40px; }
.od-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.od-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); flex-shrink: 0; }
.od-title { font-size: 15px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.od-body { padding: 12px 16px; }

.od-section {
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.od-section-title { font-size: 14px; font-weight: 600; margin-bottom: 10px; display: flex; align-items: center; gap: 4px; }

.od-row {
  display: flex;
  padding: 6px 0;
  border-bottom: 1px solid #f5f5f5;
  font-size: 13px;
}
.od-row:last-child { border-bottom: none; }
.od-label { width: 80px; flex-shrink: 0; color: #999; font-size: 12px; }
.od-value { flex: 1; color: var(--color-text); }

.od-link {
  font-size: 13px;
  color: var(--color-primary);
  text-align: right;
  margin-top: 8px;
  cursor: pointer;
}

.od-action-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  border-left: 3px solid var(--color-primary);
  background: rgba(171,32,41,0.03);
  cursor: pointer;
}
.od-action-icon { width: 36px; height: 36px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; border-radius: 8px; background: var(--color-bg); color: var(--color-text-secondary); }
.od-action-info { flex: 1; }
.od-action-title { font-size: 14px; font-weight: 600; margin-bottom: 2px; }
.od-action-desc { font-size: 11px; color: var(--color-text-secondary); }
.od-action-arrow { font-size: 20px; color: #ccc; }
</style>
