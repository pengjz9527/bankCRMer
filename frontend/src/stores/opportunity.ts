import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api'

export interface Opportunity {
  id: string
  type: string
  source: string
  sourceTag: string
  customerName: string
  description: string
  estimatedValue: number
  status: string
  /* raw API fields */
  opp_id?: string
  cust_id?: string
  confidence?: number
  reasoning?: string
  bp_id?: string
}

export const useOpportunityStore = defineStore('opportunity', () => {
  const items = ref<Opportunity[]>([])
  const loading = ref(false)
  const currentTab = ref<string>('current')

  async function loadOpportunities(mgrId: string) {
    loading.value = true
    try {
      const res = await api.getOpportunities(mgrId)
      const list = res.data?.opportunities || res.data
      if (Array.isArray(list) && list.length > 0) {
        items.value = list.map((o: any) => ({
          id: o.opp_id || o.id || '',
          opp_id: o.opp_id,
          type: o.type || '',
          source: o.source || '',
          sourceTag: o.source === 'AI挖掘' ? 'AI' : o.source === '手动创建' ? '手动' : '系统',
          customerName: o.cust_name || o.customerName || '',
          cust_id: o.cust_id,
          description: o.reasoning || o.description || '',
          estimatedValue: o.estimated_value || o.estimatedValue || 0,
          status: o.status || '待跟进',
          confidence: o.confidence,
          reasoning: o.reasoning,
          bp_id: o.bp_id,
        }))
      }
    } catch (e) {
      console.warn('加载商机失败', e)
    } finally {
      loading.value = false
    }
  }

  function setTab(tab: string) {
    currentTab.value = tab
  }

  const currentItems = computed(() => {
    if (currentTab.value === 'current') return items.value
    return items.value.filter((o) => o.source === currentTab.value)
  })

  return { items, loading, currentTab, setTab, currentItems, loadOpportunities }
})
