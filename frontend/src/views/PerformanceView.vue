<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useKpiStore } from '@/stores/kpi'
import { useManagerStore } from '@/stores/manager'

const router = useRouter()
const kpiStore = useKpiStore()
const managerStore = useManagerStore()

onMounted(() => {
  kpiStore.loadKpi(managerStore.currentId)
})

// 监听经理切换，刷新业绩数据
watch(() => managerStore.currentId, (newId) => {
  kpiStore.loadKpi(newId)
})

function goBack() { router.back() }
</script>

<template>
  <div class="perf-page">
    <div class="perf-header">
      <span class="perf-back" @click="goBack">←</span>
      <span class="perf-title">业绩看板</span>
    </div>
    <div class="perf-body">
      <!-- Rank Card -->
      <div class="perf-rank-card">
        <div class="perf-rank-num">#{{ kpiStore.rank.current }}</div>
        <div class="perf-rank-label">{{ kpiStore.rank.label }} · 共 {{ kpiStore.rank.total }} 人</div>
        <div class="perf-rank-bar-wrap">
          <div class="perf-rank-bar" :style="{ width: ((kpiStore.rank.total - kpiStore.rank.current + 1) / kpiStore.rank.total * 100) + '%' }"></div>
        </div>
        <div class="perf-rank-desc">超过 {{ kpiStore.rank.total - kpiStore.rank.current }} 位同事</div>
      </div>

      <!-- KPI Cards -->
      <div v-for="k in kpiStore.items" :key="k.label" class="perf-kpi-card">
        <div class="perf-kpi-header">
          <span class="perf-kpi-label">{{ k.label }}</span>
          <span class="perf-kpi-trend" :style="{ color: k.trend.startsWith('↑') ? '#27ae60' : k.trend.startsWith('↓') ? '#e74c3c' : '#999' }">{{ k.trend }}</span>
        </div>
        <div class="perf-kpi-values">
          <span class="perf-kpi-current">{{ k.current }}{{ k.unit }}</span>
          <span class="perf-kpi-target">/ {{ k.target }}{{ k.unit }}</span>
        </div>
        <div class="perf-kpi-bar">
          <div class="perf-kpi-fill" :style="{ width: k.progress + '%' }"></div>
        </div>
        <div class="perf-kpi-progress">{{ k.progress }}%</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.perf-page { min-height: 100%; background: #f8f8f8; padding-bottom: 40px; }
.perf-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.perf-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.perf-title { font-size: 16px; font-weight: 600; }
.perf-body { padding: 12px 16px; }

.perf-rank-card {
  background: linear-gradient(135deg, #6C5CE7, #8b7ae8);
  border-radius: 10px;
  padding: 20px;
  color: #fff;
  text-align: center;
  margin-bottom: 12px;
}
.perf-rank-num { font-size: 48px; font-weight: 800; line-height: 1; }
.perf-rank-label { font-size: 14px; opacity: 0.85; margin: 4px 0 12px; }
.perf-rank-bar-wrap { height: 6px; background: rgba(255,255,255,0.2); border-radius: 3px; margin-bottom: 6px; }
.perf-rank-bar { height: 100%; background: #fff; border-radius: 3px; }
.perf-rank-desc { font-size: 12px; opacity: 0.7; }

.perf-kpi-card {
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.perf-kpi-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
.perf-kpi-label { font-size: 14px; font-weight: 600; }
.perf-kpi-trend { font-size: 11px; font-weight: 600; }
.perf-kpi-values { margin-bottom: 6px; }
.perf-kpi-current { font-size: 26px; font-weight: 700; color: var(--color-text); }
.perf-kpi-target { font-size: 13px; color: #999; }
.perf-kpi-bar { height: 6px; background: #eee; border-radius: 3px; margin-bottom: 4px; }
.perf-kpi-fill { height: 100%; background: var(--color-primary); border-radius: 3px; }
.perf-kpi-progress { font-size: 11px; color: var(--color-text-secondary); text-align: right; }
</style>
