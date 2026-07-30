import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api'

export interface Customer {
  name: string
  gender: string
  age: number
  phone: string
  level: string
  aum: number
  risk: string
  products: string[]
  tags: { t: string; c: string }[]
  lastContact: string
  lastContactDays: number
  /* extra fields from API */
  id?: string
  cust_no?: string
  city?: string
  employment_status?: string
}

/* 后端 tier -> 前端 level 映射 */
function tierToLevel(tier: string): string {
  if (!tier) return '普通客户'
  if (tier.includes('财富') || tier === '高端财富') return '财富客户'
  if (tier.includes('金卡') || tier === '金卡') return '金卡客户'
  if (tier.includes('钻石') || tier === '钻石') return '钻石客户'
  return '普通客户'
}

/* 静态回落数据 */
const staticCustomers: Customer[] = [
  { name:'王建国', gender:'男', age:45, phone:'138****6789', level:'财富客户', aum:58.7, risk:'稳健型', products:['定存','理财','基金'], tags:[{t:'定存到期(3天后)',c:'#e74c3c'},{t:'基金偏好',c:'#e67e22'}], lastContact:'7月15日 · 面谈', lastContactDays:0 },
  { name:'张丽华', gender:'女', age:38, phone:'139****8901', level:'金卡客户', aum:42.3, risk:'成长型', products:['理财'], tags:[], lastContact:'7月15日 · 电话', lastContactDays:0 },
  { name:'赵明辉', gender:'男', age:52, phone:'136****2345', level:'财富客户', aum:185.2, risk:'稳健型', products:['代发','定存','理财'], tags:[{t:'代发到账·已签约20万',c:'#27ae60'}], lastContact:'7月14日 · 面谈', lastContactDays:1 },
  { name:'陈晓燕', gender:'女', age:41, phone:'137****3456', level:'金卡客户', aum:32.8, risk:'成长型', products:['理财','基金'], tags:[], lastContact:'7月10日 · 电话', lastContactDays:5 },
  { name:'李强', gender:'男', age:36, phone:'135****4567', level:'普通客户', aum:18.5, risk:'进取型', products:['定存'], tags:[], lastContact:'7月9日 · 微信', lastContactDays:6 },
  { name:'孙丽', gender:'女', age:55, phone:'133****7890', level:'财富客户', aum:210.5, risk:'稳健型', products:['定存','理财','保险','贵金属'], tags:[{t:'保险意向',c:'#9b59b6'},{t:'大额定存',c:'#2980b9'}], lastContact:'7月8日 · 面谈', lastContactDays:7 },
  { name:'周强', gender:'男', age:29, phone:'131****0123', level:'普通客户', aum:3.2, risk:'成长型', products:[], tags:[{t:'新开户·7天',c:'#95a5a6'}], lastContact:'7月14日 · 微信', lastContactDays:1 },
]

export const useCustomerStore = defineStore('customer', () => {
  const customers = ref<Customer[]>(staticCustomers)
  const loading = ref(false)
  const loaded = ref(false)  // 是否已从API加载过

  async function loadCustomers(managerId: string) {
    loading.value = true
    try {
      const res = await api.getCustomers(managerId)
      const list = res.data?.customers || res.data
      if (Array.isArray(list) && list.length > 0) {
        customers.value = list.map((c: any) => ({
          id: String(c.id),
          cust_no: c.cust_no,
          name: c.name,
          gender: c.gender,
          age: c.age,
          phone: c.phone_masked || c.phone || '',
          level: tierToLevel(c.tier || ''),
          aum: Number((c.total_aum / 10000).toFixed(1)) || c.total_aum || 0,
          risk: c.risk || '稳健型',
          products: c.products || [],
          tags: c.tags || [],
          lastContact: c.last_contact || '',
          lastContactDays: c.last_contact_days ?? 99,
          city: c.city,
          employment_status: c.employment_status,
        }))
        loaded.value = true
      }
    } catch (e) {
      console.warn('加载客户列表失败，使用静态数据', e)
    } finally {
      loading.value = false
    }
  }

  return { customers, loading, loaded, loadCustomers }
})

/* ── 保持向后兼容的 reactive 导出 ── */
import { reactive } from 'vue'

export const customerData = reactive({
  filters: ['全部', '财富', '金卡', '普通'],
  riskFilters: ['全部风险', '稳健型', '成长型', '进取型'],
  insightFilters: ['客户洞察', '变化信号', '预警信号'],
  customers: staticCustomers,
  newCustomers: [
    { name:'周建国', gender:'男', age:48, aum:72, match:92, distance:'1.2km', reason:'定存到期+基金偏好，与你的管户结构高度互补' },
    { name:'吴芳', gender:'女', age:35, aum:45, match:87, distance:'0.8km', reason:'代发客户+理财需求，近期浏览理财产品12次' },
    { name:'郑伟', gender:'男', age:55, aum:98, match:85, distance:'1.5km', reason:'财富客户+AUM成长性强，子女教育金需求' },
  ],
})

export function useCustomerFilters() {
  const search = ref('')
  const levelFilter = ref('全部')
  const riskFilter = ref('全部风险')
  const insightFilter = ref('客户洞察')
  const sortBy = ref('default')

  function applyFilters(list: Customer[]): Customer[] {
    let filtered = list.slice()

    if (search.value) {
      const q = search.value.toLowerCase()
      filtered = filtered.filter(c => c.name.includes(q) || c.phone.includes(q))
    }

    if (levelFilter.value !== '全部') {
      filtered = filtered.filter(c => c.level === levelFilter.value)
    }

    if (riskFilter.value !== '全部风险') {
      filtered = filtered.filter(c => c.risk === riskFilter.value)
    }

    switch (sortBy.value) {
      case 'aum_desc': filtered.sort((a, b) => b.aum - a.aum); break
      case 'aum_asc': filtered.sort((a, b) => a.aum - b.aum); break
      case 'age_desc': filtered.sort((a, b) => b.age - a.age); break
      case 'age_asc': filtered.sort((a, b) => a.age - b.age); break
      case 'recent': filtered.sort((a, b) => a.lastContactDays - b.lastContactDays); break
    }

    return filtered
  }

  return { search, levelFilter, riskFilter, insightFilter, sortBy, applyFilters }
}
