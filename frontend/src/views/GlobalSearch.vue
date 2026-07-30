<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const query = ref('')

interface SearchItem { type: string; name: string; sub: string }
const searchData = ref<SearchItem[]>([
  { type:'客户', name:'王建国', sub:'财富客户 · AUM 58.7万' },
  { type:'客户', name:'赵明辉', sub:'财富客户 · AUM 185.2万' },
  { type:'客户', name:'孙丽', sub:'财富客户 · AUM 210.5万' },
  { type:'客户', name:'张丽华', sub:'金卡客户 · AUM 42.3万' },
  { type:'客户', name:'陈晓燕', sub:'金卡客户 · AUM 32.8万' },
  { type:'客户', name:'李强', sub:'普通客户 · AUM 18.5万' },
  { type:'客户', name:'周强', sub:'普通客户 · AUM 3.2万' },
  { type:'产品', name:'悦享稳健理财 A 款', sub:'理财 · R2中低风险' },
  { type:'产品', name:'XX 混合基金优选', sub:'基金 · R3中风险' },
  { type:'产品', name:'安心存大额存单', sub:'存款 · R1低风险' },
])

const results = computed(() => {
  if (!query.value.trim()) return searchData.value
  const q = query.value.toLowerCase()
  return searchData.value.filter(s =>
    s.name.toLowerCase().includes(q) || s.sub.toLowerCase().includes(q) || s.type.includes(q)
  )
})

function goBack() { router.back() }
function goItem(item: SearchItem) {
  if (item.type === '客户') {
    router.push({ name: 'customer-detail', params: { id: item.name } })
  } else {
    router.push({ name: 'product-search' })
  }
}
</script>

<template>
  <div class="gs-page">
    <div class="gs-header">
      <span class="gs-back" @click="goBack">←</span>
      <div class="gs-search-bar">
        <svg viewBox="0 0 24 24" class="ico ico--sm" style="color:#999"><use href="#ico-search" /></svg>
        <input v-model="query" class="gs-search-input" placeholder="搜索客户、产品..." autofocus />
      </div>
    </div>
    <div class="gs-body">
      <div v-if="results.length === 0" class="gs-empty">无匹配结果</div>
      <div v-for="item in results" :key="item.name" class="gs-item" @click="goItem(item)">
        <span class="gs-item-type"><svg viewBox="0 0 24 24" class="ico ico--md"><use :href="item.type === '客户' ? '#ico-user' : '#ico-chart'" /></svg></span>
        <div class="gs-item-info">
          <div class="gs-item-name">{{ item.name }}</div>
          <div class="gs-item-sub">{{ item.sub }}</div>
        </div>
        <span class="gs-item-arrow">›</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.gs-page { min-height: 100%; background: var(--color-bg); }
.gs-header { display: flex; align-items: center; padding: 10px 16px; background: #fff; border-bottom: 1px solid #eee; gap: 10px; }
.gs-back { font-size: 20px; cursor: pointer; color: var(--color-primary); flex-shrink: 0; }
.gs-search-bar { flex: 1; display: flex; align-items: center; gap: 6px; background: #f5f5f5; border-radius: 16px; padding: 8px 12px; }
.gs-search-input { flex: 1; border: none; background: transparent; font-size: 14px; outline: none; }
.gs-body { padding: 8px 16px; }
.gs-empty { text-align: center; padding: 40px; color: #999; font-size: 14px; }
.gs-item { display: flex; align-items: center; padding: 12px 0; border-bottom: 1px solid #f5f5f5; cursor: pointer; gap: 10px; }
.gs-item-type { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: 8px; background: var(--color-bg); color: var(--color-text-secondary); flex-shrink: 0; }
.gs-item-info { flex: 1; }
.gs-item-name { font-size: 14px; font-weight: 500; }
.gs-item-sub { font-size: 11px; color: var(--color-text-secondary); }
.gs-item-arrow { font-size: 18px; color: #ccc; }
</style>
