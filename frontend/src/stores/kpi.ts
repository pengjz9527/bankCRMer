import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api'

export interface KpiItem {
  label: string
  current: number
  target: number
  unit: string
  progress: number
  trend: string
}

/* 静态回落 */
const staticKpi: KpiItem[] = [
  { label:'新增AUM', current: 280, target: 500, unit:'万', progress: 56, trend:'↑ 8%' },
  { label:'新客拓展', current: 9, target: 20, unit:'户', progress: 45, trend:'↑ 2户' },
  { label:'理财销售', current: 320, target: 600, unit:'万', progress: 53, trend:'→ 持平' },
  { label:'基金销售', current: 120, target: 300, unit:'万', progress: 40, trend:'↓ 3%' },
  { label:'保险销售', current: 55, target: 120, unit:'万', progress: 46, trend:'↑ 5%' },
  { label:'客户满意度', current: 3.8, target: 5, unit:'分', progress: 76, trend:'→ 稳定' },
]

export const useKpiStore = defineStore('kpi', () => {
  const items = ref<KpiItem[]>(staticKpi)
  const rank = ref({ current: 3, total: 12, label: '分行排名' })
  const loading = ref(false)

  async function loadKpi(managerId: string) {
    loading.value = true
    try {
      const [snapRes, tgtRes, rankRes] = await Promise.all([
        api.getKpiSnapshot(managerId),
        api.getKpiTargets(managerId),
        api.getKpiRanking(managerId),
      ])

      /* ---- 排名 ---- */
      const rd = rankRes.data
      if (rd?.my_rank) {
        rank.value = { current: rd.my_rank, total: rd.total || 12, label: '分行排名' }
      }

      /* ---- KPI 指标 ---- */
      const byKpi = snapRes.data?.by_kpi || []
      const targets = tgtRes.data?.targets || []

      if (byKpi.length > 0 && targets.length > 0) {
        // 目标值 map: kpi_code -> target_value
        const tgtMap: Record<string, number> = {}
        const unitMap: Record<string, string> = {}
        for (const t of targets) {
          tgtMap[t.kpi_code] = t.target_value
          unitMap[t.kpi_code] = t.unit || ''
        }

        items.value = byKpi.map((k: any) => {
          const target = tgtMap[k.kpi_code] || 1
          const snaps = k.snapshots || []
          const latest = snaps.length > 0 ? snaps[0] : null
          const current = latest?.actual_value ?? 0
          const progress = Math.min(100, Math.round((current / Math.max(target, 0.01)) * 100))

          // 趋势计算
          const prev = snaps.length > 1 ? snaps[1] : null
          let trend = '→ 持平'
          if (prev && latest) {
            const diff = latest.actual_value - prev.actual_value
            if (diff > 0) trend = `↑ ${((diff / Math.max(prev.actual_value, 0.01)) * 100).toFixed(0)}%`
            else if (diff < 0) trend = `↓ ${Math.abs(((diff / Math.max(prev.actual_value, 0.01)) * 100)).toFixed(0)}%`
          }

          return {
            label: k.kpi_name,
            current: Number(current.toFixed(1)),
            target: Number(target.toFixed(1)),
            unit: unitMap[k.kpi_code] || k.unit || '',
            progress,
            trend,
          }
        })
      }
    } catch (e) {
      console.warn('加载KPI数据失败，使用静态数据', e)
    } finally {
      loading.value = false
    }
  }

  return { items, rank, loading, loadKpi }
})
