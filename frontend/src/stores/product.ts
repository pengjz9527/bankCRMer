import { defineStore } from 'pinia'
import { ref, reactive, computed } from 'vue'
import { api } from '../api'

export interface Product {
  id: string
  name: string
  icon: string
  type: string
  termType: string
  term: string
  risk: string
  riskLabel: string
  min: number
  minUnit: string
  benchmark: string
  aiReason: string
  aiFit: number
  manager?: string
}

/* 静态回落数据 */
const staticProducts: Product[] = [
  { id:'P001', name:'悦享稳健理财 A 款', icon:'ico-chart', type:'理财', termType:'开放式', term:'灵活申赎', risk:'R2', riskLabel:'中低', min:10000, minUnit:'元', benchmark:'业绩比较基准 3.2%-3.6%', aiReason:'与你的 3 位财富客户风险偏好匹配，定存到期承接优选', aiFit:5 },
  { id:'P002', name:'XX 混合基金优选', icon:'ico-trend-up', type:'基金', termType:'开放式', term:'T+1到账', risk:'R3', riskLabel:'中', min:1000, minUnit:'元', benchmark:'近1年收益 +8.5%，同类排名前20%', aiReason:'你的客户王建国近3月浏览基金频道 15 次，推荐对接', aiFit:4 },
  { id:'P003', name:'安心存大额存单', icon:'ico-bank', type:'存款', termType:'固定期限', term:'3年', risk:'R1', riskLabel:'低', min:200000, minUnit:'元', benchmark:'年利率 2.85%，可转让', aiReason:'孙丽有大额定存标签，可推荐大额存单', aiFit:4 },
  { id:'P004', name:'稳健增利 180 天', icon:'ico-chart', type:'理财', termType:'封闭式', term:'180天', risk:'R2', riskLabel:'中低', min:10000, minUnit:'元', benchmark:'业绩比较基准 3.5%-4.0%', aiReason:'中期配置，适合 AUM 20-60 万客户', aiFit:4 },
  { id:'P005', name:'智选成长基金', icon:'ico-trend-up', type:'基金', termType:'开放式', term:'T+2到账', risk:'R4', riskLabel:'中高', min:1000, minUnit:'元', benchmark:'近1年收益 +15.2%，科技主题', aiReason:'李强为进取型客户，适合中高风险投资', aiFit:3 },
  { id:'P006', name:'鑫享年金保险', icon:'ico-check-circle', type:'保险', termType:'长期', term:'10年缴', risk:'R2', riskLabel:'中低', min:50000, minUnit:'元', benchmark:'保证收益 + 分红，年化约 3.8%', aiReason:'赵明辉有代发工资，适合年金规划', aiFit:3 },
  { id:'P007', name:'e 钱包货基', icon:'ico-wallet', type:'基金', termType:'开放式', term:'快速赎回', risk:'R1', riskLabel:'低', min:1, minUnit:'元', benchmark:'七日年化 2.15%', aiReason:'流动性管理优选，适合闲置资金存放', aiFit:3 },
  { id:'P008', name:'稳利宝 7 天通知', icon:'ico-bank', type:'存款', termType:'通知存款', term:'7天', risk:'R1', riskLabel:'低', min:50000, minUnit:'元', benchmark:'年利率 1.55%', aiReason:'短期资金管理，适合近期有资金周转需求的客户', aiFit:2 },
  { id:'P009', name:'黄金积存计划', icon:'ico-trophy', type:'理财', termType:'定投', term:'每月', risk:'R3', riskLabel:'中', min:500, minUnit:'元', benchmark:'挂钩国际金价', aiReason:'孙丽有贵金属标签，适合黄金定投', aiFit:4 },
  { id:'P010', name:'安心稳利 365 天', icon:'ico-chart', type:'理财', termType:'封闭式', term:'365天', risk:'R2', riskLabel:'中低', min:50000, minUnit:'元', benchmark:'业绩比较基准 3.8%-4.2%', aiReason:'长期稳健配置，适合50万以上AUM客户', aiFit:3 },
  { id:'P011', name:'科技先锋 ETF 联接', icon:'ico-laptop', type:'基金', termType:'开放式', term:'T+1到账', risk:'R4', riskLabel:'中高', min:100, minUnit:'元', benchmark:'跟踪中证科技指数', aiReason:'适合进取型客户，配置科技赛道', aiFit:2 },
  { id:'P012', name:'教育金储备计划', icon:'ico-star', type:'保险', termType:'长期', term:'至18岁', risk:'R2', riskLabel:'中低', min:30000, minUnit:'元', benchmark:'年化约 3.5% + 教育金领取', aiReason:'陈晓燕子女教育需求', aiFit:3 },
]

/* 后端产品映射到前端 Product */
function mapApiProduct(p: any): Product {
  const riskLabels: Record<string, string> = { R1:'低', R2:'中低', R3:'中', R4:'中高', R5:'高' }
  const iconMap: Record<string, string> = { '理财':'ico-chart', '基金':'ico-trend-up', '存款':'ico-bank', '保险':'ico-check-circle' }
  return {
    id: p.id || p.product_id || '',
    name: p.name || p.product_name || '',
    icon: iconMap[p.type] || iconMap[p.category] || 'ico-chart',
    type: p.type || p.category || '',
    termType: p.term_type || p.termType || '',
    term: p.term || p.duration || '',
    risk: p.risk_level || p.risk || 'R2',
    riskLabel: riskLabels[p.risk_level] || p.risk_label || p.riskLabel || '中低',
    min: p.min_invest || p.min || 1000,
    minUnit: p.minUnit || '元',
    benchmark: p.benchmark || p.expected_return || '',
    aiReason: p.ai_reason || p.selling_points_text || '',
    aiFit: p.ai_fit || p.recommendation_score || 3,
    manager: p.manager || '',
  }
}

export const useProductStore = defineStore('product', () => {
  const products = ref<Product[]>(staticProducts)
  const loading = ref(false)
  const loaded = ref(false)

  async function loadProducts() {
    loading.value = true
    try {
      const res = await api.getProducts()
      const list = res.data?.products || res.data
      if (Array.isArray(list) && list.length > 0) {
        products.value = list.map(mapApiProduct)
        // 同步到 productData.all 保持向后兼容
        productData.all = products.value
        loaded.value = true
      }
    } catch (e) {
      console.warn('加载产品列表失败，使用静态数据', e)
    } finally {
      loading.value = false
    }
  }

  return { products, loading, loaded, loadProducts }
})

/* ── 保持向后兼容的 reactive 导出 ── */
export const productData = reactive({
  types: ['全部', '理财', '基金', '存款', '保险'],
  risks: ['全部', 'R1', 'R2', 'R3', 'R4'],
  all: staticProducts as Product[],
})

export function useProductFilters() {
  const search = ref('')
  const typeFilter = ref('全部')
  const riskFilter = ref('全部')
  const sortBy = ref<'aiFit' | 'risk' | 'yield' | 'min'>('aiFit')
  const selectedIds = ref<string[]>([])

  const filtered = computed(() => {
    let list = productData.all.slice()
    const keyword = search.value.toLowerCase()

    if (typeFilter.value !== '全部') {
      list = list.filter(p => p.type === typeFilter.value)
    }

    const riskMap: Record<string, string[]> = {
      '全部': [], 'R1': ['R1'], 'R2': ['R2'], 'R3': ['R3'], 'R4': ['R4'],
    }
    const riskVals = riskMap[riskFilter.value]
    if (riskVals && riskVals.length > 0) {
      list = list.filter(p => riskVals.includes(p.risk))
    }

    if (keyword) {
      list = list.filter(p =>
        p.name.toLowerCase().includes(keyword) ||
        p.id.toLowerCase().includes(keyword) ||
        (p.manager || '').toLowerCase().includes(keyword)
      )
    }

    if (sortBy.value === 'risk') {
      list.sort((a, b) => a.risk.localeCompare(b.risk))
    } else if (sortBy.value === 'yield' || sortBy.value === 'aiFit') {
      list.sort((a, b) => b.aiFit - a.aiFit)
    } else if (sortBy.value === 'min') {
      list.sort((a, b) => a.min - b.min)
    }

    return list
  })

  const aiRecommended = computed(() => filtered.value.filter(p => p.aiFit >= 4).slice(0, 4))

  function toggleSelect(id: string) {
    const idx = selectedIds.value.indexOf(id)
    if (idx >= 0) { selectedIds.value.splice(idx, 1); return }
    if (selectedIds.value.length >= 3) return '最多选择3款产品'
    const p = productData.all.find(x => x.id === id)
    if (!p) return
    if (selectedIds.value.length > 0) {
      const first = productData.all.find(x => x.id === selectedIds.value[0])
      if (first && p.type !== first.type) return `仅支持同类型对比，当前为 ${first.type} 类`
    }
    selectedIds.value.push(id)
    return null
  }

  return { search, typeFilter, riskFilter, sortBy, filtered, aiRecommended, selectedIds, toggleSelect }
}
