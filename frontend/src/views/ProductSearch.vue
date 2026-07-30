<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useProductStore, productData, useProductFilters } from '@/stores/product'
import { useManagerStore } from '@/stores/manager'
import ProductCard from '@/components/business/ProductCard.vue'

const router = useRouter()
const appStore = useAppStore()
const productStore = useProductStore()
const managerStore = useManagerStore()
const { search, typeFilter, riskFilter, sortBy, filtered, aiRecommended, selectedIds, toggleSelect } = useProductFilters()

onMounted(() => {
  productStore.loadProducts()
})

// 监听经理切换，重新加载产品数据（AI推荐基于管户画像）
watch(() => managerStore.currentId, () => {
  productStore.loadProducts()
})

const showCompare = computed(() => selectedIds.value.length >= 2)

function goDetail(id: string) {
  router.push({ name: 'product-detail', params: { id } })
}

function goCompare() {
  if (!showCompare.value) {
    appStore.showToast('请选择至少 2 款产品')
    return
  }
  router.push({ name: 'product-compare', query: { ids: selectedIds.value.join(',') } })
}

function handleToggleSelect(id: string) {
  const err = toggleSelect(id)
  if (err) appStore.showToast(err)
}

const sorts = [
  { k:'aiFit', l:'AI推荐' }, { k:'risk', l:'风险↑' }, { k:'yield', l:'收益↑' }, { k:'min', l:'起购↓' },
]
</script>

<template>
  <div class="product-search">
    <!-- Search Bar -->
    <div class="ps-search-bar">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="2">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
      <input v-model="search" class="ps-search-input" placeholder="搜索产品名称/编号/管理人" />
    </div>

    <!-- Filters + Sort + Compare -->
    <div class="ps-toolbar">
      <select v-model="typeFilter" class="ps-tool-select">
        <option v-for="t in productData.types" :key="t" :value="t">{{ t === '全部' ? '全部类型' : t }}</option>
      </select>
      <select v-model="riskFilter" class="ps-tool-select">
        <option v-for="r in productData.risks" :key="r" :value="r">{{ r === '全部' ? '全部风险' : r }}</option>
      </select>
      <select v-model="sortBy" class="ps-tool-select">
        <option v-for="s in sorts" :key="s.k" :value="s.k">{{ s.l }}</option>
      </select>
      <button class="ps-compare-btn" :class="{ ready: showCompare }" @click="goCompare">
        对比 <span class="ps-compare-count">{{ selectedIds.length }}</span>
      </button>
    </div>

    <div class="ps-result-count">共 {{ filtered.length }} 款产品</div>

    <!-- AI Recommended Section -->
    <div v-if="aiRecommended.length > 0" class="ps-ai-section">
      <div class="ps-ai-label">
        <svg viewBox="0 0 24 24" class="ico ico--sm" style="color:#f59e0b"><use href="#ico-lightbulb" /></svg> AI 推荐（基于你的管户画像）
      </div>
      <ProductCard
        v-for="p in aiRecommended"
        :key="p.id"
        :product="p"
        :selected="selectedIds.includes(p.id)"
        @select="handleToggleSelect"
        @click="goDetail"
      />
    </div>

    <!-- All Products -->
    <div class="ps-all-label">全部产品</div>
    <div v-if="filtered.length === 0" class="ps-empty">
      <div style="margin-bottom:8px"><svg viewBox="0 0 24 24" class="ico ico--xl" style="color:#ccc"><use href="#ico-inbox" /></svg></div>
      <div>暂无匹配产品</div>
      <div style="font-size:11px;color:#bbb;margin-top:4px">试试调整筛选条件</div>
    </div>
    <ProductCard
      v-for="p in filtered"
      :key="p.id"
      :product="p"
      :selected="selectedIds.includes(p.id)"
      @select="handleToggleSelect"
      @click="goDetail"
    />
  </div>
</template>

<style scoped>
.product-search {
  padding: 0 16px 80px;
  min-height: 100%;
  background: var(--color-bg);
}
.ps-search-bar {
  display: flex;
  align-items: center;
  background: #f5f5f5;
  border-radius: 20px;
  padding: 8px 14px;
  margin-bottom: 10px;
  gap: 8px;
}
.ps-search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  outline: none;
  color: var(--color-text);
}
.ps-search-input::placeholder { color: #bbb; }

.ps-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.ps-tool-select {
  flex: 1;
  min-width: 0;
  padding: 5px 6px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 11px;
  color: var(--color-text-secondary);
  background: #fff;
  outline: none;
  appearance: auto;
}
.ps-compare-btn {
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
  background: #fff;
  font-size: 12px;
  color: #999;
  cursor: pointer;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 4px;
}
.ps-compare-btn.ready {
  color: var(--color-primary);
  border-color: var(--color-primary);
  background: rgba(171,32,41,0.04);
}
.ps-compare-count {
  display: inline-flex;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 10px;
  align-items: center;
  justify-content: center;
}

.ps-result-count {
  font-size: 12px;
  color: var(--color-text-tertiary, #999);
  margin-bottom: 12px;
}

.ps-ai-section {
  margin-bottom: 16px;
}
.ps-ai-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.ps-all-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 10px;
  padding-top: 4px;
  border-top: 1px solid #f0f0f0;
}

.ps-empty {
  text-align: center;
  padding: 50px 20px;
  color: #999;
  font-size: 14px;
}
</style>
