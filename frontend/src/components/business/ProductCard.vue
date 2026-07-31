<script setup lang="ts">
import type { Product } from '@/stores/product'

const props = defineProps<{
  product: Product
  selected?: boolean
}>()

const emit = defineEmits<{
  select: [id: string]
  click: [id: string]
}>()

function minText(p: Product): string {
  if (p.minUnit === '万') return p.min + '万'
  if (p.min >= 10000) return (p.min / 10000) + '万'
  return p.min + p.minUnit
}

const riskClassMap: Record<string, string> = {
  R1: 'risk-r1', R2: 'risk-r2', R3: 'risk-r3', R4: 'risk-r4',
}
</script>

<template>
  <div class="prod-card" :class="{ selected: selected }">
    <div class="pc-select" @click.stop="emit('select', product.id)">
      <svg v-if="selected" width="18" height="18" viewBox="0 0 24 24" fill="#27ae60"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>
      <div v-else class="pc-select-empty"></div>
    </div>
    <div class="pc-body" @click="emit('click', product.id)">
      <span class="pc-icon"><svg viewBox="0 0 24 24" class="ico ico--prod"><use :href="'#' + product.icon" /></svg></span>
      <div class="pc-info">
        <div class="pc-name">{{ product.name }}</div>
        <div class="pc-sub">{{ product.type }} · {{ product.termType }} · {{ product.term }}</div>
        <div class="pc-tags">
          <span class="pc-tag" :class="riskClassMap[product.risk] || 'risk-r2'">{{ product.risk }} · {{ product.riskLabel }}</span>
          <span class="pc-tag pc-tag-min">起购 {{ minText(product) }}</span>
        </div>
        <div class="pc-desc">{{ product.benchmark }}</div>
        <div class="pc-ai" v-if="product.aiFit >= 3">
          <span class="pc-ai-star">★</span> {{ product.aiReason }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.prod-card {
  display: flex;
  align-items: flex-start;
  background: #fff;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  transition: border 0.2s;
  border: 2px solid transparent;
}
.prod-card.selected { border-color: #27ae60; }

.pc-select {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  margin-right: 8px;
  margin-top: 2px;
  cursor: pointer;
}
.pc-select-empty {
  width: 18px;
  height: 18px;
  border: 2px solid #d0d0d0;
  border-radius: 50%;
}

.pc-body {
  flex: 1;
  display: flex;
  gap: 10px;
  cursor: pointer;
  min-width: 0;
}
.pc-icon { width: 36px; height: 36px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; border-radius: 8px; background: var(--color-bg); color: var(--color-text-secondary); }
.pc-info { flex: 1; min-width: 0; }

.pc-name { font-size: 14px; font-weight: 600; color: var(--color-text); margin-bottom: 2px; }
.pc-sub { font-size: 11px; color: var(--color-text-secondary); margin-bottom: 4px; }
.pc-tags { display: flex; gap: 4px; margin-bottom: 4px; flex-wrap: wrap; }
.pc-tag {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #f5f5f5;
  color: var(--color-text-secondary);
}
.risk-r1 { background: #E8F5E9; color: #388E3C; }
.risk-r2 { background: #E3F2FD; color: #1565C0; }
.risk-r3 { background: #FFF3E0; color: #E65100; }
.risk-r4 { background: #FBE9E7; color: #BF360C; }

.pc-desc { font-size: 11px; color: var(--color-text-secondary); margin-bottom: 4px; }
.pc-ai {
  font-size: 11px;
  color: #6C5CE7;
  background: #EDE9FE;
  padding: 4px 8px;
  border-radius: 6px;
  line-height: 1.4;
}
.pc-ai-star { color: #f59e0b; }
</style>
