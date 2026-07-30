<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface Meeting { date: string; customer: string; type: string; summary: string; result: string }
const meetings = ref<Meeting[]>([
  { date:'2026-07-15', customer:'王建国', type:'面谈', summary:'定存到期承接 + 基金推荐', result:'客户同意定存转理财，基金待进一步了解' },
  { date:'2026-07-14', customer:'赵明辉', type:'面谈', summary:'代发到账配置', result:'已签约20万理财配置' },
  { date:'2026-07-10', customer:'张丽华', type:'电话', summary:'生日回访 + 产品推荐', result:'客户表示考虑中' },
  { date:'2026-07-09', customer:'李强', type:'微信', summary:'新客回访', result:'已添加微信，约定下次面谈' },
  { date:'2026-07-08', customer:'孙丽', type:'面谈', summary:'大额定存 + 保险规划', result:'已推荐年金保险，客户有意向' },
])

function goBack() { router.back() }
function goDetail(meeting: Meeting) {
  router.push({ name: 'meeting-detail', query: { customer: meeting.customer, date: meeting.date } })
}
</script>

<template>
  <div class="mr-page">
    <div class="mr-header">
      <span class="mr-back" @click="goBack">←</span>
      <span class="mr-title">会议记录</span>
    </div>
    <div class="mr-body">
      <div v-for="m in meetings" :key="m.date + m.customer" class="mr-card" @click="goDetail(m)">
        <div class="mr-card-date">{{ m.date }}</div>
        <div class="mr-card-info">
          <div class="mr-card-name">{{ m.customer }} · {{ m.type }}</div>
          <div class="mr-card-summary">{{ m.summary }}</div>
          <div class="mr-card-result">{{ m.result }}</div>
        </div>
        <span class="mr-card-arrow">›</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mr-page { min-height: 100%; background: #f8f8f8; padding-bottom: 40px; }
.mr-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.mr-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.mr-title { font-size: 16px; font-weight: 600; }
.mr-body { padding: 12px 16px; }
.mr-card {
  display: flex;
  align-items: flex-start;
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  cursor: pointer;
  gap: 12px;
}
.mr-card-date {
  font-size: 12px;
  color: var(--color-primary);
  font-weight: 600;
  white-space: nowrap;
  padding-top: 2px;
}
.mr-card-info { flex: 1; min-width: 0; }
.mr-card-name { font-size: 14px; font-weight: 600; margin-bottom: 2px; }
.mr-card-summary { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 2px; }
.mr-card-result { font-size: 11px; color: #27ae60; }
.mr-card-arrow { font-size: 20px; color: #ccc; flex-shrink: 0; }
</style>
