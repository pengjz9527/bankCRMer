<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'

const route = useRoute()
const router = useRouter()
const customerName = ref((route.params.id as string) || '')
const loading = ref(false)
const custApiId = ref('')

// 预设安全默认结构，防止模板访问 undefined 属性导致空白
const defaultProfile = () => ({
  base: { name: '加载中...', gender: '', age: 0, occupation: '', industry: '', city: '', education: '', level: '', manager: '', tenure: '', risk: '' },
  family: { marriage: '', children: '', childStage: '' },
  business: null as any,
  wealth: { totalAssets: 0, aum: 0, wealthScore: { score: 0, time: '', dims: [] as string[] }, cashflow: { yearIn: '0', inDesc: '', yearOut: '0', outDist: '', retain: '' }, holdings: { total: '0', cumReturn: '0', annualYield: '', peakMonth: '', detail: { deposit: 0, finance: 0, fund: 0, metal: 0, insurance: 0 } } },
  credit: { loans: [] as any[], housingFund: { base: 0, period: '' }, socialSecurity: { base: 0, period: '' } },
  behavior: { finPrefs: [] as any[], liquidity: '', risk: { test: '', browseDist: '' }, marketing: { channels: [] as string[], activityCount: 0, bestTime: '' }, payroll: { monthAmount: '0', date: '', avg6m: '0', peak: '0', level: '', retain3d: '', retain7d: '' }, otherOpp: { loanIntent: false, wealthIntent: false } },
  interactions: [] as string[],
  holdings: [] as string[],
  benefits: { unclaimed: [] as any[], available: [] as any[], eligible: [] as any[] },
})
const p = ref<Record<string, any>>(defaultProfile())
const customerOpps = ref<any[]>([])  // 从 API 加载的真实商机列表
const oppsLoading = ref(false)

/* 从 API 并行加载客户画像 + 子模块数据（参照 workbench.html） */
onMounted(async () => {
  loading.value = true
  try {
    const routeId = route.params.id as string
    let match: any = null
    let fastPathCid = ''  // 数字 ID 快路径已获取到的客户 ID

    // 优先：如果 routeId 是纯数字，直接按 ID 查询
    if (/^\d+$/.test(routeId)) {
      try {
        const basicRes = await api.getCustomerBasic(routeId)
        if (basicRes?.data?.id) {
          match = basicRes.data
          customerName.value = match.name || routeId
          fastPathCid = String(match.id)
        }
      } catch { /* 数字 ID 也未匹配，继续列表查找 */ }
    }

    // 回退：通过客户列表匹配（仅当快路径未命中时）
    if (!match?.id) {
      const res = await api.getCustomers('', 100)
      const list = res.data?.customers || res.data || []
      match = list.find((c: any) => c.name === routeId)
        || list.find((c: any) => String(c.id) === routeId)
        || list.find((c: any) => c.cust_no === routeId)
        || list.find((c: any) => c.name?.includes(routeId) || routeId.includes(c.name))
    }

    if (match?.id) {
      const cid = fastPathCid || String(match.id)
      custApiId.value = cid
      if (match.name && !customerName.value) customerName.value = match.name
      const safeCall = (fn: () => Promise<any>) => fn().catch(() => null)
      const [profRes, holdsRes, loansRes, prefsRes, flowRes, salaryRes, benefitsRes, activitiesRes] = await Promise.all([
        safeCall(() => api.getCustomerProfile(cid)),
        safeCall(() => api.getCustomerHoldings(cid)),
        safeCall(() => api.getCustomerLoans(cid)),
        safeCall(() => api.getCustomerBehavior(cid)),
        safeCall(() => api.getCustomerFundFlow(cid)),
        safeCall(() => api.getCustomerSalary(cid)),
        safeCall(() => api.getCustomerBenefits(cid)),
        safeCall(() => api.getCustomerActivities(cid)),
      ])

      const d = profRes?.data
      if (d?.basic) {
        const b = d.basic || {}
        const fam = d.family || {}
        const biz = d.business || null
        const ws = d.wealth_summary || {}
        const cs = d.credit_summary || {}
        const bs = d.behavior_summary || {}
        const flow = flowRes?.data
        const salary = salaryRes?.data
        const holds = holdsRes?.data
        const flowIn = flow ? (flow.yearly_inflow || 0) / 10000 : 0
        const flowOut = flow ? (flow.yearly_outflow || 0) / 10000 : 0
        const salMonth = salary ? (salary.current_month_amount || 0) / 10000 : 0
        const salAvg = salary ? (salary.avg_6m || 0) / 10000 : 0
        const hd = holds?.distribution || {}
        const hTotal = holds ? (holds.total_scale || 0) / 10000 : (ws.total_aum || 0) / 10000
        const holdingDetails = holds?.details?.slice(0, 5).map((h: any) =>
          `${h.product_name || '产品'} · ${(h.amount / 10000).toFixed(1)}万${h.maturity_date ? ' · 到期 ' + h.maturity_date : ''}`
        ) || []
        const loans = loansRes?.data
        const loanList = Array.isArray(loans) ? loans : (loans?.loans || [])
        const benefits = benefitsRes?.data
        const benefitList = Array.isArray(benefits) ? benefits : (benefits?.benefits || [])
        const actList = activitiesRes?.data
        const activityItems = Array.isArray(actList) ? actList : (actList?.activities || [])

        p.value = {
          base: {
            name: b.name || customerName.value, gender: b.gender || '男', age: b.age || 30,
            occupation: b.occupation || '', industry: b.industry || '', city: b.city || '',
            education: b.education || '—', level: (b.tier || '普通') + '客户',
            manager: b.manager || '—', tenure: '—',
            risk: (bs.risk_result || '稳健型') + ' R2',
          },
          family: {
            marriage: fam.marriage ? '已婚' : '未婚',
            children: fam.children ? '已育' : '未育',
            childStage: fam.child_education || (fam.children ? '有子女' : '无子女'),
          },
          business: biz ? {
            entity: biz.business_name || biz.entity || '', duration: (biz.duration_years || biz.duration || '') + '年',
            share: biz.share_ratio || biz.share || '', capital: biz.reg_capital || biz.capital || '',
            address: biz.address || b.city || '', scope: biz.scope || '', active: biz.verified !== false,
          } : null,
          wealth: {
            totalAssets: (ws.total_aum || 0) / 10000, aum: (ws.total_aum || 0) / 10000,
            wealthScore: {
              score: ws.wealth_score || 50, time: '本月',
              dims: ws.wealth_score > 70 ? ['资产配置合理','收入稳定','社会资源丰富'] : ['资产配置','收入水平'],
            },
            cashflow: {
              yearIn: flowIn.toFixed(0), inDesc: flow?.inflow_desc || '经营回款+代发工资',
              yearOut: flowOut.toFixed(0), outDist: flow?.outflow_desc || '转账 · 消费 · 其他',
              retain: flow?.retention_desc || '资金留存正常',
            },
            holdings: {
              total: hTotal.toFixed(1), cumReturn: ((ws.total_aum || 0) / 10000 * 0.05).toFixed(1),
              annualYield: '4.1%', peakMonth: '本年',
              detail: {
                deposit: (hd.deposit || 0) / 10000, finance: (hd.wealth_mgmt || 0) / 10000,
                fund: (hd.fund || 0) / 10000, metal: (hd.precious_metal || 0) / 10000,
                insurance: (hd.insurance || 0) / 10000,
              },
            },
          },
          credit: {
            loans: loanList, housingFund: { base: 6800, period: '本年' }, socialSecurity: { base: 8200, period: '本年' },
          },
          behavior: {
            finPrefs: (bs.fin_prefs || []).map((f: any) => ({ label: f.label || f, basis: f.basis || '近3月行为分析' })),
            liquidity: bs.liquidity || '中',
            risk: { test: (bs.risk_result || '稳健型') + ' R2', browseDist: 'R1-R3为主' },
            marketing: { channels: ['电话','微信'], activityCount: activityItems.length || 1, bestTime: '上午9:00-11:00' },
            payroll: {
              monthAmount: salMonth.toFixed(1), date: '每月发薪日', avg6m: salAvg.toFixed(1),
              peak: salMonth.toFixed(1) + '万', level: salary?.salary_level || '中等',
              retain3d: '70%', retain7d: '45%',
            },
            otherOpp: { loanIntent: (cs?.loan_count || 0) > 0, wealthIntent: true },
          },
          interactions: ['最近交互记录'],
          holdings: holdingDetails.length > 0 ? holdingDetails : [],
          benefits: { unclaimed: [], available: benefitList.slice(0, 3).map((b: any) => ({ name: b.benefit_name || b.name, detail: b.benefit_value || b.detail, status: b.status || '可用' })), eligible: activityItems.slice(0, 3).map((a: any) => ({ name: a.activity_name || a.name, detail: a.reward || a.detail, status: '可参与' })) },
        }

        // 加载该客户的商机列表
        loadCustomerOpps(cid)
      }
    }
  } catch (e) {
    console.warn('加载客户画像失败，使用静态数据', e)
  } finally {
    loading.value = false
  }
})

// Section expand states — per spec: basic, wealth, opps, benefits default open
const expanded = ref<Record<string, boolean>>({
  basic: true, family: false, business: false,
  wealth: true, credit: false, behavior: false,
  opps: true, interactions: false, holdings: false,
  benefits: true,
})
function toggle(key: string) { expanded.value[key] = !expanded.value[key] }
function goBack() { router.back() }
function goInsight() {
  // 画像→洞察: 传递 custId (洞察 API 专用 ID) 和客户姓名
  router.push({ name: 'customer-insights', query: { custId: custApiId.value || '', name: customerName.value } })
}
function goAiChat() {
  router.push({ name: 'ai-chat', query: { from: 'w8detail', customer: customerName.value } })
}
function goBattlePackage(bpId: string) {
  if (bpId) router.push({ name: 'battle-package', query: { id: bpId } })
}

// 面谈记录
const meetingRecords = ref<any[]>([])
const meetingRecordsLoaded = ref(false)
async function loadMeetingRecords() {
  try {
    const res = await api.getMeetingRecords({ cust_name: customerName.value, page_size: 10 })
    if (res.code === 0) {
      meetingRecords.value = res.data.items || []
    }
  } catch (e) {
    console.warn('加载面谈记录失败', e)
  } finally {
    meetingRecordsLoaded.value = true
  }
}

// 商机列表
async function loadCustomerOpps(custId: string) {
  oppsLoading.value = true
  try {
    const res = await api.aiGetOpportunityList(undefined, Number(custId))
    const list = res.data?.opportunities || res.data || []
    if (Array.isArray(list)) {
      customerOpps.value = list.map((o: any) => ({
        opp_id: o.opp_id,
        title: o.title || o.opportunity_type || '',
        type: o.opportunity_type || o.type || '',
        priority: o.priority === '高' ? 'red' : 'yellow',
        label: `${o.opportunity_type || o.type}（${o.status || '待跟进'}）`,
        detail: o.reasoning || '',
        estimated_value: o.estimated_value || 0,
        confidence: o.confidence || 0,
        status: o.status || '待跟进',
        bpReady: !!o.bp_id,
        bp_id: o.bp_id || '',
      }))
    }
  } catch (e) {
    console.warn('加载商机列表失败', e)
  } finally {
    oppsLoading.value = false
  }
}

onMounted(() => { loadMeetingRecords() })
</script>

<template>
  <div class="cust-detail">
    <div class="cd-header">
      <span class="cd-back" @click="goBack">←</span>
      <span class="cd-title">客户画像 · {{ customerName }}</span>
      <span class="cd-edit" @click="goAiChat">编辑</span>
    </div>

    <div class="cd-body">
      <!-- §1 基础信息 (default open) -->
      <div class="ps-section">
        <div class="ps-header" :class="{ expanded: expanded.basic }" @click="toggle('basic')">
          <span class="ps-title">📋 基础信息</span>
          <span class="ps-arrow" :class="{ open: expanded.basic }">▾</span>
        </div>
        <div class="ps-body" :class="{ open: expanded.basic }">
          <div class="pf-row"><span class="pf-label">姓名</span><span class="pf-value">{{ p.base.name }} · {{ p.base.gender }} · {{ p.base.age }}岁</span></div>
          <div class="pf-row"><span class="pf-label">职业</span><span class="pf-value">{{ p.base.occupation }}</span></div>
          <div class="pf-row"><span class="pf-label">行业</span><span class="pf-value">{{ p.base.industry }}</span></div>
          <div class="pf-row"><span class="pf-label">城市</span><span class="pf-value">{{ p.base.city }}</span></div>
          <div class="pf-row"><span class="pf-label">学历</span><span class="pf-value">{{ p.base.education }}</span></div>
          <div class="pf-row"><span class="pf-label">客户等级</span><span class="pf-value">{{ p.base.level }}</span></div>
          <div class="pf-row"><span class="pf-label">风险评级</span><span class="pf-value">{{ p.base.risk }}</span></div>
          <div class="pf-row"><span class="pf-label">客户经理</span><span class="pf-value">{{ p.base.manager }} · 管户{{ p.base.tenure }}</span></div>
        </div>
      </div>

      <!-- §2 家庭结构 -->
      <div class="ps-section">
        <div class="ps-header" :class="{ expanded: expanded.family }" @click="toggle('family')">
          <span class="ps-title">👨‍👩‍👧 家庭结构</span>
          <span class="ps-arrow" :class="{ open: expanded.family }">▾</span>
        </div>
        <div class="ps-body" :class="{ open: expanded.family }">
          <div class="pf-row"><span class="pf-label">婚姻状况</span><span class="pf-value">{{ p.family.marriage }}</span></div>
          <div class="pf-row"><span class="pf-label">子女情况</span><span class="pf-value">{{ p.family.children }}</span></div>
          <div class="pf-row"><span class="pf-label">子女阶段</span><span class="pf-value">{{ p.family.childStage }}</span></div>
        </div>
      </div>

      <!-- §3 经营信息 (only for business owners) -->
      <div class="ps-section" v-if="p.business">
        <div class="ps-header" :class="{ expanded: expanded.business }" @click="toggle('business')">
          <span class="ps-title">🏭 经营信息</span>
          <span class="ps-arrow" :class="{ open: expanded.business }">▾</span>
        </div>
        <div class="ps-body" :class="{ open: expanded.business }">
          <div class="pf-row"><span class="pf-label">经营主体</span><span class="pf-value">{{ p.business.entity }}</span></div>
          <div class="pf-row"><span class="pf-label">经营时长</span><span class="pf-value">{{ p.business.duration }}</span></div>
          <div class="pf-row"><span class="pf-label">持股比例</span><span class="pf-value">{{ p.business.share }}</span></div>
          <div class="pf-row"><span class="pf-label">注册资金</span><span class="pf-value">{{ p.business.capital }}</span></div>
          <div class="pf-row"><span class="pf-label">经营地址</span><span class="pf-value">{{ p.business.address }}</span></div>
          <div class="pf-row"><span class="pf-label">经营范围</span><span class="pf-value">{{ p.business.scope }}</span></div>
          <div class="pf-row"><span class="pf-label">经营持续性</span><span class="pf-value"><span v-if="p.business.active" class="pf-ok">✓ 近3月交易正常</span><span v-else class="pf-warn">⚠ 需关注</span></span></div>
        </div>
      </div>

      <!-- §4 财富解读 (default open) -->
      <div class="ps-section">
        <div class="ps-header" :class="{ expanded: expanded.wealth }" @click="toggle('wealth')">
          <span class="ps-title">💎 财富解读</span>
          <span class="ps-arrow" :class="{ open: expanded.wealth }">▾</span>
        </div>
        <div class="ps-body" :class="{ open: expanded.wealth }">
          <!-- 净值分层 -->
          <div class="pf-sub-card">
            <div class="psc-title">📊 净值分层</div>
            <div class="pf-row"><span class="pf-label">总资产</span><span class="pf-value">{{ p.wealth.totalAssets }}万</span></div>
            <div class="pf-row"><span class="pf-label">客户等级</span><span class="pf-value">{{ p.base.level }}</span></div>
            <div class="pf-row"><span class="pf-label">客群标签</span><span class="pf-value">代发客群</span></div>
          </div>
          <!-- 资金解读 -->
          <div class="pf-sub-card">
            <div class="psc-title">💰 资金解读</div>
            <div class="pf-row"><span class="pf-label">近一年入金</span><span class="pf-value">{{ p.wealth.cashflow.yearIn }}万</span></div>
            <div class="pf-row"><span class="pf-label">入金来源</span><span class="pf-value">{{ p.wealth.cashflow.inDesc }}</span></div>
            <div class="pf-row"><span class="pf-label">近一年出金</span><span class="pf-value">{{ p.wealth.cashflow.yearOut }}万</span></div>
            <div class="pf-row"><span class="pf-label">出金分布</span><span class="pf-value">{{ p.wealth.cashflow.outDist }}</span></div>
          </div>
          <!-- 持仓解读 -->
          <div class="pf-sub-card">
            <div class="psc-title">📦 持仓解读</div>
            <div class="pf-row"><span class="pf-label">持仓总规模</span><span class="pf-value">{{ p.wealth.holdings.total }}万</span></div>
            <div class="pf-row"><span class="pf-label">累计收益</span><span class="pf-value">+{{ p.wealth.holdings.cumReturn }}万</span></div>
            <div class="pf-row"><span class="pf-label">年化收益率</span><span class="pf-value">{{ p.wealth.holdings.annualYield }}</span></div>
            <div class="pf-row"><span class="pf-label">近一年峰值</span><span class="pf-value">{{ p.wealth.holdings.peakMonth }}</span></div>
          </div>
          <!-- 资产网格 -->
          <div class="pf-asset-grid">
            <div class="pa-item"><div class="pa-val">{{ p.wealth.holdings.detail.deposit }}万</div><div class="pa-label">存款</div></div>
            <div class="pa-item"><div class="pa-val">{{ p.wealth.holdings.detail.finance }}万</div><div class="pa-label">理财</div></div>
            <div class="pa-item"><div class="pa-val">{{ p.wealth.holdings.detail.fund }}万</div><div class="pa-label">基金</div></div>
            <div class="pa-item"><div class="pa-val">{{ p.wealth.holdings.detail.metal }}万</div><div class="pa-label">贵金属</div></div>
            <div class="pa-item"><div class="pa-val">{{ p.wealth.holdings.detail.insurance }}万</div><div class="pa-label">保险</div></div>
          </div>
        </div>
      </div>

      <!-- §5 信贷解读 -->
      <div class="ps-section">
        <div class="ps-header" :class="{ expanded: expanded.credit }" @click="toggle('credit')">
          <span class="ps-title">🏦 信贷解读</span>
          <span class="ps-arrow" :class="{ open: expanded.credit }">▾</span>
        </div>
        <div class="ps-body" :class="{ open: expanded.credit }">
          <div class="pf-sub-card">
            <div class="psc-title">📋 贷款记录</div>
            <div v-if="p.credit.loans?.length === 0" class="pf-empty">无当前贷款记录</div>
            <div v-for="loan in p.credit.loans" :key="loan.id || loan.type" class="pf-row">
              <span class="pf-label">{{ loan.type || '贷款' }}</span>
              <span class="pf-value">{{ loan.amount || '--' }}</span>
            </div>
          </div>
          <div class="pf-sub-card">
            <div class="psc-title">🚫 历史被拒</div>
            <div class="pf-empty">无被拒记录</div>
          </div>
          <div class="pf-sub-card">
            <div class="psc-title">📋 社保/公积金</div>
            <div class="pf-row"><span class="pf-label">公积金基数</span><span class="pf-value">{{ p.credit.housingFund.base }}元 · {{ p.credit.housingFund.period }}</span></div>
            <div class="pf-row"><span class="pf-label">社保基数</span><span class="pf-value">{{ p.credit.socialSecurity.base }}元 · {{ p.credit.socialSecurity.period }}</span></div>
          </div>
        </div>
      </div>

      <!-- §6 行为标签 (事实数据) -->
      <div class="ps-section">
        <div class="ps-header" :class="{ expanded: expanded.behavior }" @click="toggle('behavior')">
          <span class="ps-title">🧠 行为标签</span>
          <span class="ps-arrow" :class="{ open: expanded.behavior }">▾</span>
        </div>
        <div class="ps-body" :class="{ open: expanded.behavior }">
          <div class="pf-sub-card">
            <div class="psc-title">⚖️ 风险测评</div>
            <div class="pf-row"><span class="pf-label">风测结果</span><span class="pf-value">{{ p.behavior.risk.test }}</span></div>
          </div>
          <div class="pf-sub-card">
            <div class="psc-title">📱 营销偏好</div>
            <div class="pf-row"><span class="pf-label">渠道偏好</span><span class="pf-value">{{ p.behavior.marketing.channels.join(' / ') }}</span></div>
            <div class="pf-row"><span class="pf-label">近3月活动</span><span class="pf-value">{{ p.behavior.marketing.activityCount }}次</span></div>
            <div class="pf-row"><span class="pf-label">最佳联系</span><span class="pf-value">{{ p.behavior.marketing.bestTime }}</span></div>
          </div>
          <div class="pf-sub-card">
            <div class="psc-title">💳 工资代发</div>
            <div class="pf-row"><span class="pf-label">当月代发</span><span class="pf-value">{{ p.behavior.payroll.monthAmount }}万 · {{ p.behavior.payroll.date }}</span></div>
            <div class="pf-row"><span class="pf-label">近6月月均</span><span class="pf-value">{{ p.behavior.payroll.avg6m }}万</span></div>
            <div class="pf-row"><span class="pf-label">峰值</span><span class="pf-value">{{ p.behavior.payroll.peak }}</span></div>
            <div class="pf-row"><span class="pf-label">薪资等级</span><span class="pf-value">{{ p.behavior.payroll.level }}</span></div>
            <div class="pf-row"><span class="pf-label">3日留存</span><span class="pf-value">{{ p.behavior.payroll.retain3d }}</span></div>
            <div class="pf-row"><span class="pf-label">7日留存</span><span class="pf-value">{{ p.behavior.payroll.retain7d }}</span></div>
          </div>
        </div>
      </div>

      <!-- §7 商机与待办 (default open) -->
      <div class="ps-section">
        <div class="ps-header" :class="{ expanded: expanded.opps }" @click="toggle('opps')">
          <span class="ps-title">🎯 商机与待办</span>
          <span class="ps-arrow" :class="{ open: expanded.opps }">▾</span>
        </div>
        <div class="ps-body" :class="{ open: expanded.opps }">
          <div v-if="oppsLoading" class="pf-empty">加载中...</div>
          <div v-for="op in customerOpps" :key="op.opp_id" class="ps-opp-card">
            <div class="ps-opp-priority" :class="{ red: op.priority === 'red', yellow: op.priority === 'yellow' }">
              {{ op.priority === 'red' ? '高优' : '关注' }}
            </div>
            <div class="ps-opp-content">
              <div class="ps-opp-title">{{ op.label }}</div>
              <div class="ps-opp-detail">{{ op.detail }}</div>
              <button v-if="op.bpReady" class="ps-opp-btn ps-opp-btn--outline" @click="goBattlePackage(op.bp_id)">
                📋 关联的作战包
              </button>
            </div>
          </div>
          <div v-if="!oppsLoading && customerOpps.length === 0" class="pf-empty">暂无关联商机</div>
        </div>
      </div>

      <!-- §8 最近交互 -->
      <div class="ps-section">
        <div class="ps-header" :class="{ expanded: expanded.interactions }" @click="toggle('interactions')">
          <span class="ps-title">📝 最近交互</span>
          <span class="ps-arrow" :class="{ open: expanded.interactions }">▾</span>
        </div>
        <div class="ps-body" :class="{ open: expanded.interactions }">
          <div v-for="it in p.interactions" :key="it" class="pf-interact-row">{{ it }}</div>

          <!-- 面谈记录入口 -->
          <div v-if="meetingRecords.length > 0" class="meeting-records-inline">
            <div class="meeting-records-inline-title">📋 面谈记录</div>
            <div v-for="mr in meetingRecords" :key="mr.id" class="meeting-records-inline-item">
              <div class="mri-header">
                <span class="mri-date">{{ mr.meeting_date }}</span>
                <span class="mri-status" :class="mr.meeting_status === 'completed' ? 'mri-done' : 'mri-draft'">
                  {{ mr.meeting_status === 'completed' ? '已完成' : '口述中' }}
                </span>
                <span class="mri-count">{{ mr.dictation_count }}次录音</span>
              </div>
              <div v-if="mr.summary" class="mri-summary">{{ mr.summary.slice(0, 80) }}{{ mr.summary.length > 80 ? '...' : '' }}</div>
            </div>
          </div>
          <div v-else-if="meetingRecordsLoaded" class="pf-empty" style="font-size:12px;color:#999;">暂无面谈记录</div>

          <div class="pf-link-more">查看全部交互记录 &gt;</div>
        </div>
      </div>

      <!-- §9 持有产品 -->
      <div class="ps-section">
        <div class="ps-header" :class="{ expanded: expanded.holdings }" @click="toggle('holdings')">
          <span class="ps-title">📦 持有产品</span>
          <span class="ps-arrow" :class="{ open: expanded.holdings }">▾</span>
        </div>
        <div class="ps-body" :class="{ open: expanded.holdings }">
          <div v-for="h in p.holdings" :key="h" class="pf-holding-row">{{ h }}</div>
          <div v-if="p.holdings.length === 0" class="pf-empty">暂无持有产品</div>
        </div>
      </div>

      <!-- §10 权益与活动 (default open) -->
      <div class="ps-section">
        <div class="ps-header" :class="{ expanded: expanded.benefits }" @click="toggle('benefits')">
          <span class="ps-title">🎁 权益与活动</span>
          <span class="ps-arrow" :class="{ open: expanded.benefits }">▾</span>
        </div>
        <div class="ps-body" :class="{ open: expanded.benefits }">
          <!-- 待领取奖励 -->
          <div v-if="p.benefits?.unclaimed?.length" class="pf-benefit-block pf-benefit-block--warn">
            <div class="pfb-title">待领取奖励</div>
            <div v-for="item in p.benefits.unclaimed" :key="item.name" class="pfb-item">
              <span class="pfb-dot pfb-dot--red"></span>
              <strong>{{ item.name }}</strong> · {{ item.detail }}
              <span class="pfb-tag pfb-tag--red">未领取</span>
            </div>
          </div>
          <!-- 可用权益 -->
          <div v-if="p.benefits?.available?.length" class="pf-benefit-block pf-benefit-block--purple">
            <div class="pfb-title">可用权益</div>
            <div v-for="item in p.benefits.available" :key="item.name" class="pfb-item">
              <span class="pfb-dot pfb-dot--purple"></span>
              <strong>{{ item.name }}</strong> · {{ item.detail }}
              <span class="pfb-tag pfb-tag--purple">{{ item.status }}</span>
            </div>
          </div>
          <!-- 可参与活动 -->
          <div v-if="p.benefits?.eligible?.length" class="pf-benefit-block pf-benefit-block--green">
            <div class="pfb-title">可参与活动</div>
            <div v-for="item in p.benefits.eligible" :key="item.name" class="pfb-item">
              <span class="pfb-dot pfb-dot--green"></span>
              <strong>{{ item.name }}</strong> · {{ item.detail }}
            </div>
          </div>
          <div v-if="!p.benefits?.unclaimed?.length && !p.benefits?.available?.length && !p.benefits?.eligible?.length" class="pf-empty">暂无权益与活动数据</div>
        </div>
      </div>
    </div>

    <!-- Bottom Action Bar -->
    <div class="cd-actions">
      <button class="cd-action-btn" @click="$el">📞 拨号</button>
      <button class="cd-action-btn" @click="$el">💬 微信</button>
      <button class="cd-action-btn cd-action-btn--primary">创建商机</button>
      <button class="cd-action-btn cd-action-btn--ai" @click="goInsight">🧠 AI 洞察</button>
    </div>
  </div>
</template>

<style scoped>
.cust-detail { min-height: 100%; background: #f8f8f8; padding-bottom: 80px; }
.cd-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.cd-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.cd-title { flex: 1; font-size: 17px; font-weight: 600; }
.cd-edit { font-size: 13px; cursor: pointer; color: var(--color-primary); }
.cd-body { padding: 12px 16px; }

/* Collapsible Section */
.ps-section { background: #fff; border-radius: 10px; margin-bottom: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.ps-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; cursor: pointer; user-select: none; }
.ps-header:active { background: #fafafa; }
.ps-title { font-size: 15px; font-weight: 600; color: var(--color-text); }
.ps-arrow { font-size: 12px; color: #999; transition: transform 0.2s; }
.ps-arrow.open { transform: rotate(180deg); }
.ps-body { display: none; padding: 0 16px 14px; }
.ps-body.open { display: block; }

/* Field Rows */
.pf-row { display: flex; padding: 6px 0; border-bottom: 1px solid #f5f5f5; font-size: 13px; }
.pf-row:last-child { border-bottom: none; }
.pf-label { width: 80px; flex-shrink: 0; color: #999; font-size: 12px; }
.pf-value { flex: 1; color: var(--color-text); word-break: break-all; }
.pf-ok { color: #10B981; }
.pf-warn { color: #F59E0B; }
.pf-empty { font-size: 12px; color: #bbb; text-align: center; padding: 8px; }

/* Sub-cards inside sections */
.pf-sub-card { background: #f9f9f9; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }
.psc-title { font-size: 13px; font-weight: 600; color: var(--color-primary); margin-bottom: 6px; }

/* Asset grid (5 items) */
.pf-asset-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin-top: 8px; }
.pa-item { background: #f5f5f5; border-radius: 8px; padding: 8px 4px; text-align: center; }
.pa-val { font-size: 14px; font-weight: 700; color: var(--color-text); }
.pa-label { font-size: 10px; color: #999; margin-top: 2px; }

/* Interactions */
.pf-interact-row { font-size: 13px; color: var(--color-text-secondary); padding: 5px 0; border-bottom: 1px solid #f5f5f5; }
.pf-interact-row:last-of-type { border-bottom: none; }
.pf-link-more { font-size: 12px; color: var(--color-primary); text-align: right; cursor: pointer; padding-top: 6px; }

/* Holdings */
.pf-holding-row { font-size: 12px; color: var(--color-text-secondary); padding: 4px 0; }

/* Benefit blocks */
.pf-benefit-block { border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }
.pf-benefit-block--warn { background: #FFF5F5; border: 1px solid #FECACA; }
.pf-benefit-block--purple { background: #F5F3FF; border: 1px solid #DDD6FE; }
.pf-benefit-block--green { background: #F0FDF4; border: 1px solid #BBF7D0; }
.pfb-title { font-size: 13px; font-weight: 600; margin-bottom: 6px; }
.pf-benefit-block--warn .pfb-title { color: #DC2626; }
.pf-benefit-block--purple .pfb-title { color: #6C5CE7; }
.pf-benefit-block--green .pfb-title { color: #00B578; }
.pfb-item { font-size: 12px; padding: 4px 0; border-bottom: 1px solid rgba(0,0,0,0.05); display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.pfb-item:last-child { border-bottom: none; }
.pfb-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.pfb-dot--red { background: #DC2626; }
.pfb-dot--purple { background: #6C5CE7; }
.pfb-dot--green { background: #00B578; }
.pfb-tag { font-size: 10px; padding: 1px 6px; border-radius: 3px; }
.pfb-tag--red { background: #FEE2E2; color: #DC2626; }
.pfb-tag--purple { background: #EDE9FE; color: #6C5CE7; }

/* Opp cards */
.ps-opp-card { display: flex; gap: 10px; padding: 10px 0; border-bottom: 1px solid #f5f5f5; }
.ps-opp-card:last-child { border-bottom: none; }
.ps-opp-priority { padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; height: fit-content; white-space: nowrap; }
.ps-opp-priority.red { background: #FEE2E2; color: #DC2626; }
.ps-opp-priority.yellow { background: #FEF3C7; color: #D97706; }
.ps-opp-content { flex: 1; }
.ps-opp-title { font-size: 13px; font-weight: 500; margin-bottom: 2px; }
.ps-opp-detail { font-size: 11px; color: var(--color-text-secondary); margin-bottom: 6px; }
.ps-opp-btn { font-size: 11px; padding: 4px 12px; border-radius: 4px; cursor: pointer; border: none; }
.ps-opp-btn--primary { background: var(--color-primary); color: #fff; }
.ps-opp-btn--outline { background: transparent; color: var(--color-primary); border: 1px solid var(--color-primary); }

/* Bottom Action Bar */
.cd-actions { position: sticky; bottom: 0; display: flex; gap: 6px; padding: 10px 12px; background: #fff; border-top: 1px solid #eee; z-index: 10; flex-wrap: wrap; justify-content: center; }
.cd-action-btn { font-size: 11px; padding: 6px 10px; border-radius: 6px; border: 1px solid #ddd; background: #fff; color: var(--color-text); cursor: pointer; white-space: nowrap; }
.cd-action-btn:active { background: #f5f5f5; }
.cd-action-btn--primary { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.cd-action-btn--ai { color: #7C5CE7; border-color: #7C5CE7; font-weight: 600; }

/* ── 面谈记录行内展示 ── */
.meeting-records-inline {
  margin-top: 10px; padding-top: 10px;
  border-top: 1px dashed #e5e7eb;
}
.meeting-records-inline-title {
  font-size: 12px; font-weight: 600; color: #6b7280; margin-bottom: 8px;
}
.meeting-records-inline-item {
  padding: 8px 10px; margin-bottom: 6px;
  background: #f9fafb; border-radius: 8px; border: 1px solid #f3f4f6;
}
.mri-header {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 4px;
}
.mri-date { font-size: 12px; color: #374151; font-weight: 500; }
.mri-status {
  font-size: 10px; padding: 1px 6px; border-radius: 6px; font-weight: 600;
}
.mri-done { background: #d1fae5; color: #065f46; }
.mri-draft { background: #fef3c7; color: #92400e; }
.mri-count { font-size: 10px; color: #9ca3af; margin-left: auto; }
.mri-summary {
  font-size: 12px; color: #6b7280; line-height: 1.5;
}
</style>
