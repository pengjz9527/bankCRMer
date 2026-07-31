<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProductStore, productData } from '@/stores/product'

const route = useRoute()
const router = useRouter()
const productStore = useProductStore()
const prodId = (route.params.id as string) || 'P001'

const p = computed(() => productData.all.find(x => x.id === prodId) || productData.all[0])

const minText = computed(() => {
  if (!p.value) return ''
  if (p.value.minUnit === '万') return p.value.min + '万'
  if (p.value.min >= 10000) return (p.value.min / 10000) + '万'
  return p.value.min + p.value.minUnit
})

onMounted(() => {
  // 直接导航到详情页时，store 可能尚未加载
  productStore.loadProducts()
})

function goBack() { router.back() }
function goCompare() { router.push({ name: 'product-compare', query: { ids: prodId } }) }
</script>

<template>
  <div class="pd-page">
    <div class="pd-header">
      <span class="pd-back" @click="goBack">←</span>
      <span class="pd-title">{{ p.name }}</span>
      <span class="pd-compare" @click="goCompare">对比</span>
    </div>
    <div class="pd-body">
      <div class="pd-icon-row">
        <span class="pd-icon"><svg viewBox="0 0 24 24" class="ico ico--xl"><use :href="'#' + p.icon" /></svg></span>
        <div>
          <div class="pd-type">{{ p.type }} · {{ p.risk }} · {{ p.riskLabel }}</div>
        </div>
      </div>

      <div class="pd-section">
        <div class="pd-section-title"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-clipboard" /></svg> 基本信息</div>
        <div class="pd-row"><span class="pd-label">产品编号</span><span class="pd-value">{{ p.id }}</span></div>
        <div class="pd-row"><span class="pd-label">产品类型</span><span class="pd-value">{{ p.type }}</span></div>
        <div class="pd-row"><span class="pd-label">期限类型</span><span class="pd-value">{{ p.termType }} · {{ p.term }}</span></div>
        <div class="pd-row"><span class="pd-label">风险等级</span><span class="pd-value">{{ p.risk }} · {{ p.riskLabel }}</span></div>
        <div class="pd-row"><span class="pd-label">起购金额</span><span class="pd-value">{{ minText }}</span></div>
      </div>

      <div class="pd-section">
        <div class="pd-section-title"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-lightbulb" /></svg> 收益参考</div>
        <div class="pd-row"><span class="pd-label">业绩基准</span><span class="pd-value">{{ p.benchmark }}</span></div>
      </div>

      <div v-if="p.aiFit >= 3" class="pd-section pd-ai">
        <div class="pd-section-title"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-robot" /></svg> AI 推荐理由</div>
        <p style="font-size:13px;color:#6C5CE7;line-height:1.6;margin:0">{{ p.aiReason }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pd-page { min-height: 100%; background: #f8f8f8; padding-bottom: 40px; }
.pd-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.pd-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.pd-title { flex: 1; font-size: 16px; font-weight: 600; }
.pd-compare { font-size: 13px; color: var(--color-primary); cursor: pointer; }
.pd-body { padding: 12px 16px; }
.pd-icon-row { display: flex; align-items: center; gap: 12px; padding: 16px; background: #fff; border-radius: 10px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.pd-icon { width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; background: var(--color-bg); border-radius: 10px; color: var(--color-text-secondary); flex-shrink: 0; }
.pd-type { font-size: 13px; color: var(--color-text-secondary); }
.pd-section { background: #fff; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.pd-section.pd-ai { background: #F8F5FF; border-left: 3px solid #6C5CE7; }
.pd-section-title { font-size: 14px; font-weight: 600; margin-bottom: 10px; }
.pd-row { display: flex; padding: 6px 0; border-bottom: 1px solid #f5f5f5; font-size: 13px; }
.pd-row:last-child { border-bottom: none; }
.pd-label { width: 80px; flex-shrink: 0; color: #999; font-size: 12px; }
.pd-value { flex: 1; color: var(--color-text); }
</style>
