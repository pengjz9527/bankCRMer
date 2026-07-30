<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productData } from '@/stores/product'
import type { Product } from '@/stores/product'

const route = useRoute()
const router = useRouter()
const ids = computed(() => ((route.query.ids as string) || '').split(',').filter(Boolean))
const products = computed<Product[]>(() => ids.value.map(id => productData.all.find(p => p.id === id)).filter(Boolean) as Product[])

function goBack() { router.back() }

const fields: { label: string; key: keyof Product | 'minText' }[] = [
  { label: '名称', key: 'name' },
  { label: '类型', key: 'type' },
  { label: '期限', key: 'term' },
  { label: '风险等级', key: 'riskLabel' },
  { label: '起购', key: 'minText' },
  { label: '基准', key: 'benchmark' },
]
function val(p: Product, key: string): string {
  if (key === 'minText') return p.min >= 10000 ? (p.min/10000)+'万' : p.min+p.minUnit
  if (key === 'riskLabel') return p.risk + ' · ' + p.riskLabel + '风险'
  return String((p as any)[key] || '-')
}
</script>

<template>
  <div class="pc-page">
    <div class="pc-header">
      <span class="pc-back" @click="goBack">←</span>
      <span class="pc-title">产品对比（{{ products.length }}）</span>
    </div>
    <div class="pc-body">
      <div v-if="products.length < 2" class="pc-empty">请选择至少 2 款产品进行对比</div>
      <template v-else>
        <div class="pc-table">
          <div class="pc-row pc-row-header">
            <div class="pc-cell-label"></div>
            <div v-for="p in products" :key="p.id" class="pc-cell">
              <div class="pc-cell-name">{{ p.name }}</div>
            </div>
          </div>
          <div v-for="f in fields" :key="f.label" class="pc-row">
            <div class="pc-cell-label">{{ f.label }}</div>
            <div v-for="p in products" :key="p.id" class="pc-cell">
              {{ val(p, f.key) }}
            </div>
          </div>
        </div>
        <div class="pc-ai">
          <svg viewBox="0 0 24 24" class="ico ico--sm" style="color:#6C5CE7;vertical-align:middle"><use href="#ico-robot" /></svg> <strong>AI 推荐：</strong>{{ products[0].name }} 更适合你的当前管户结构，匹配度最高。
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.pc-page { min-height: 100%; background: #f8f8f8; padding-bottom: 40px; }
.pc-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.pc-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.pc-title { font-size: 16px; font-weight: 600; }
.pc-body { padding: 12px 16px; }
.pc-empty { text-align: center; padding: 60px 20px; color: #999; }
.pc-table { background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.pc-row { display: flex; border-bottom: 1px solid #f0f0f0; }
.pc-row:last-child { border-bottom: none; }
.pc-row-header { background: #fafafa; font-weight: 600; }
.pc-cell-label { width: 70px; flex-shrink: 0; padding: 10px 8px; font-size: 11px; color: #999; background: #fafafa; }
.pc-cell { flex: 1; padding: 10px 8px; font-size: 12px; color: var(--color-text); min-width: 0; }
.pc-cell-name { font-size: 13px; font-weight: 600; }
.pc-ai { margin-top: 16px; background: #F8F5FF; border-radius: 10px; padding: 12px 14px; font-size: 13px; color: #6C5CE7; line-height: 1.6; }
</style>
