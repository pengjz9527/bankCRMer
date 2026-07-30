<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const stats = ref([
  { label:'今日面谈', value:'2场', sub:'王建国、赵明辉' },
  { label:'新增商机', value:'3个', sub:'代发×2、AI挖掘×1' },
  { label:'作战包生成', value:'1个', sub:'王建国·定存到期' },
  { label:'待办完成', value:'4/6', sub:'完成率 67%' },
])

const highlights = ref([
  '赵明辉代发到账已配置 20 万理财，签约完成',
  '王建国定存到期承接方案已生成作战包',
  'AI 挖掘到陈建国基金购买意向商机（置信度 82%）',
])

function goBack() { router.back() }
</script>

<template>
  <div class="yr-page">
    <div class="yr-header">
      <span class="yr-back" @click="goBack">←</span>
      <span class="yr-title">昨日回顾</span>
    </div>
    <div class="yr-body">
      <div class="yr-date-badge"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-calendar" /></svg> 7月15日 周二</div>

      <div class="yr-stats-grid">
        <div v-for="s in stats" :key="s.label" class="yr-stat-card">
          <div class="yr-stat-val">{{ s.value }}</div>
          <div class="yr-stat-label">{{ s.label }}</div>
          <div class="yr-stat-sub">{{ s.sub }}</div>
        </div>
      </div>

      <div class="yr-section">
        <div class="yr-section-title"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-star" /></svg> 重点成果</div>
        <div v-for="h in highlights" :key="h" class="yr-highlight">
          <span class="yr-highlight-dot"></span> {{ h }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.yr-page { min-height: 100%; background: #f8f8f8; padding-bottom: 40px; }
.yr-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.yr-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.yr-title { font-size: 16px; font-weight: 600; }
.yr-body { padding: 12px 16px; }
.yr-date-badge { text-align: center; font-size: 13px; color: var(--color-text-secondary); margin-bottom: 12px; display: flex; align-items: center; justify-content: center; gap: 6px; }

.yr-stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
.yr-stat-card { background: #fff; border-radius: 10px; padding: 14px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.yr-stat-val { font-size: 24px; font-weight: 700; color: var(--color-primary); }
.yr-stat-label { font-size: 12px; color: var(--color-text-secondary); margin-top: 2px; }
.yr-stat-sub { font-size: 10px; color: #bbb; margin-top: 2px; }

.yr-section { background: #fff; border-radius: 10px; padding: 14px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.yr-section-title { font-size: 14px; font-weight: 600; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
.yr-highlight { font-size: 13px; padding: 6px 0; color: var(--color-text); display: flex; align-items: flex-start; gap: 8px; line-height: 1.5; }
.yr-highlight-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-primary); margin-top: 6px; flex-shrink: 0; }
</style>
