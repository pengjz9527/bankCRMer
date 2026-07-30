<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const customer = ref((route.query.customer as string) || '王建国')
const date = ref((route.query.date as string) || '2026-07-15')
const type = ref('面谈')

const detail = ref({
  topics: ['定存到期承接', '基金偏好挖掘'],
  duration: '45分钟',
  location: '合肥分行营业部 · 客户接待室',
  notes: '客户持有25万定存7月18日到期，需尽快对接。近3月浏览基金频道15次，可切入基金推荐。风险偏好稳健型，避免推荐高风险产品。',
  outcome: '客户同意定存转理财，基金待进一步了解。约定下次面谈时间下周。',
  actionItems: ['发送悦享稳健理财产品资料', '准备基金对比材料', '跟进定存到期日（7/18）'],
})

function goBack() { router.back() }
</script>

<template>
  <div class="md-page">
    <div class="md-header">
      <span class="md-back" @click="goBack">←</span>
      <span class="md-title">会议详情</span>
    </div>
    <div class="md-body">
      <div class="md-section">
        <div class="md-row"><span class="md-label">客户</span><span class="md-value">{{ customer }}</span></div>
        <div class="md-row"><span class="md-label">日期</span><span class="md-value">{{ date }}</span></div>
        <div class="md-row"><span class="md-label">类型</span><span class="md-value">{{ type }}</span></div>
        <div class="md-row"><span class="md-label">时长</span><span class="md-value">{{ detail.duration }}</span></div>
        <div class="md-row"><span class="md-label">地点</span><span class="md-value">{{ detail.location }}</span></div>
      </div>

      <div class="md-section">
        <div class="md-section-title"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-edit" /></svg> 议题</div>
        <div v-for="t in detail.topics" :key="t" class="md-topic">· {{ t }}</div>
      </div>

      <div class="md-section">
        <div class="md-section-title"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-file-text" /></svg> 纪要</div>
        <p class="md-notes">{{ detail.notes }}</p>
      </div>

      <div class="md-section">
        <div class="md-section-title"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-check-circle" /></svg> 成果</div>
        <p class="md-outcome">{{ detail.outcome }}</p>
      </div>

      <div class="md-section">
        <div class="md-section-title"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-clipboard" /></svg> 待办事项</div>
        <div v-for="(item, idx) in detail.actionItems" :key="idx" class="md-action-item">
          <span class="md-action-check">☐</span> {{ item }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.md-page { min-height: 100%; background: #f8f8f8; padding-bottom: 40px; }
.md-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.md-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.md-title { font-size: 16px; font-weight: 600; }
.md-body { padding: 12px 16px; }

.md-section { background: #fff; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.md-section-title { font-size: 14px; font-weight: 600; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; color: var(--color-text-primary); }
.md-row { display: flex; padding: 5px 0; font-size: 13px; border-bottom: 1px solid #f5f5f5; }
.md-row:last-child { border-bottom: none; }
.md-label { width: 50px; color: #999; font-size: 12px; }
.md-value { flex: 1; color: var(--color-text); }
.md-topic { font-size: 13px; padding: 4px 0; color: var(--color-text); }
.md-notes { font-size: 13px; line-height: 1.7; color: var(--color-text); margin: 0; }
.md-outcome { font-size: 13px; line-height: 1.7; color: #27ae60; margin: 0; }
.md-action-item { font-size: 13px; padding: 4px 0; color: var(--color-text); display: flex; align-items: flex-start; gap: 6px; }
.md-action-check { color: var(--color-primary); flex-shrink: 0; }
</style>
