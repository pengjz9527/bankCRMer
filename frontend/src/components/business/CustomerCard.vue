<script setup lang="ts">
import type { Customer } from '@/stores/customer'

defineProps<{
  customer: Customer
}>()

function getLevelColor(level: string): string {
  if (level.includes('财富')) return '#f59e0b'
  if (level.includes('金卡')) return '#6C5CE7'
  return '#666'
}
</script>

<template>
  <div class="cust-card">
    <div class="cc-avatar" :style="{ background: customer.level.includes('财富') ? '#FFF7ED' : customer.level.includes('金卡') ? '#EDE9FE' : '#F5F5F5', color: getLevelColor(customer.level) }">
      {{ customer.name[0] }}
    </div>
    <div class="cc-info">
      <div class="cc-name-row">
        <span class="cc-name">{{ customer.name }}</span>
        <span class="cc-gender">{{ customer.gender }}</span>
        <span class="cc-age">{{ customer.age }}岁</span>
      </div>
      <div class="cc-meta">{{ customer.level }} · AUM {{ customer.aum }}万 · {{ customer.risk }}</div>
      <div v-if="customer.tags.length" class="cc-tags">
        <span
          v-for="t in customer.tags"
          :key="t.t"
          class="cc-tag"
          :style="{ background: t.c + '20', color: t.c }"
        >{{ t.t }}</span>
      </div>
      <div class="cc-last">最后联络：{{ customer.lastContact }}</div>
    </div>
    <span class="cc-arrow">›</span>
  </div>
</template>

<style scoped>
.cust-card {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  cursor: pointer;
}
.cust-card:active { background: #fafafa; }

.cc-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  flex-shrink: 0;
  margin-right: 12px;
}
.cc-info { flex: 1; min-width: 0; }
.cc-name-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 2px;
}
.cc-name { font-size: 15px; font-weight: 600; color: var(--color-text); }
.cc-gender { font-size: 11px; color: var(--color-text-tertiary, #999); }
.cc-age { font-size: 11px; color: var(--color-text-tertiary, #999); }
.cc-meta { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 4px; }
.cc-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 4px; }
.cc-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 999px;
}
.cc-last { font-size: 11px; color: var(--color-text-tertiary, #bbb); }
.cc-arrow {
  font-size: 22px;
  color: #ccc;
  flex-shrink: 0;
  margin-left: 8px;
}
</style>
