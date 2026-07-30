<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useCustomerStore, customerData, useCustomerFilters } from '@/stores/customer'
import { useManagerStore } from '@/stores/manager'
import CustomerCard from '@/components/business/CustomerCard.vue'
import NewCustomerCard from '@/components/business/NewCustomerCard.vue'
import type { Customer } from '@/stores/customer'

const router = useRouter()
const appStore = useAppStore()
const customerStore = useCustomerStore()
const managerStore = useManagerStore()

const mode = ref<'list' | 'new'>('list')
const { search, levelFilter, riskFilter, insightFilter, sortBy, applyFilters } = useCustomerFilters()

const filteredCustomers = computed<Customer[]>(() => applyFilters(customerStore.customers as Customer[]))

const title = computed(() => {
  if (mode.value === 'new') return 'AI 推荐新客'
  return `我的客户 (${filteredCustomers.value.length})`
})

function goDetail(name: string) {
  router.push({ name: 'customer-detail', params: { id: name } })
}

function goAiChat() {
  router.push({ name: 'ai-chat', query: { from: 'w8' } })
}

function claimCustomer(name: string) {
  appStore.showToast(`已认领客户：${name}`)
}

onMounted(() => {
  customerStore.loadCustomers(managerStore.currentId)
})

// 监听经理切换，重新加载客户数据
watch(() => managerStore.currentId, (newId) => {
  customerStore.loadCustomers(newId)
})

const sorts = [
  { k:'default', l:'默认排序' }, { k:'aum_desc', l:'AUM ↓' }, { k:'aum_asc', l:'AUM ↑' },
  { k:'age_desc', l:'年龄 ↓' }, { k:'age_asc', l:'年龄 ↑' }, { k:'recent', l:'最近联系' },
]
</script>

<template>
  <div class="customer-list" :class="{ 'is-new-mode': mode === 'new' }">
    <!-- Search Bar -->
    <div class="cl-search-bar">
      <svg class="cl-search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
      <input
        v-model="search"
        class="cl-search-input"
        placeholder="搜索姓名/手机号"
        @input="() => {}"
      />
      <span class="cl-insight-link" @click="$router.push('/customer-insights')">洞察</span>
    </div>

    <!-- Desktop Filter & Sort Rows (hidden on mobile overlay) -->
    <div class="cl-filters">
      <select v-model="levelFilter" class="cl-filter-select">
        <option v-for="f in customerData.filters" :key="f" :value="f">{{ f }}</option>
      </select>
      <select v-model="riskFilter" class="cl-filter-select">
        <option v-for="f in customerData.riskFilters" :key="f" :value="f">{{ f }}</option>
      </select>
    </div>
    <div class="cl-sort-row">
      <select v-model="sortBy" class="cl-sort-select">
        <option v-for="s in sorts" :key="s.k" :value="s.k">{{ s.l }}</option>
      </select>
    </div>

    <!-- Result Summary -->
    <div class="cl-result-summary">
      共 <strong>{{ filteredCustomers.length }}</strong> 位客户
    </div>

    <!-- List Mode -->
    <template v-if="mode === 'list'">
      <div v-if="filteredCustomers.length === 0" class="cl-empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="1.5">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <div class="cl-empty-text">没有找到匹配的客户</div>
        <div class="cl-empty-hint">试试调整筛选条件</div>
      </div>
      <CustomerCard
        v-for="(c, idx) in filteredCustomers"
        :key="c.id || (c.name + idx)"
        :customer="c"
        @click="goDetail(c.name)"
      />
    </template>

    <!-- New Customer Mode -->
    <template v-else>
      <div class="cl-ai-tip">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="#7b1fa2"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15v-6h2v6h-2zm1-8c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1z"/></svg>
        <span>AI 基于你的商机缺口和管户画像，从分行客户池中推荐 {{ customerData.newCustomers.length }} 户潜在客户。</span>
      </div>
      <div v-for="c in customerData.newCustomers" :key="c.name" class="cl-new-card">
        <div class="cl-nc-match">
          <span v-for="i in 3" :key="i">★</span> 匹配度 {{ c.match }}%
        </div>
        <div class="cl-nc-info">{{ c.name }} · {{ c.gender }} · {{ c.age }}岁 · AUM {{ c.aum }}万 · 无客户经理 · 距支行 {{ c.distance }}</div>
        <div class="cl-nc-reason">AI 分析：{{ c.reason }}</div>
        <div class="cl-nc-actions">
          <button class="cl-nc-btn claim" @click="claimCustomer(c.name)">认领为客户</button>
          <button class="cl-nc-btn ignore">忽略</button>
        </div>
      </div>
      <button class="cl-batch-claim" @click="appStore.showToast('已认领 3 户新客')">一键认领全部匹配度 ≥ 85% 的客户 (3户)</button>
    </template>

    <!-- Mode Toggle FAB -->
    <button class="cl-mode-fab" @click="mode = mode === 'list' ? 'new' : 'list'">
      <svg v-if="mode === 'list'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15v-6h2v6h-2zm1-8c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1z"/>
      </svg>
      <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
      </svg>
    </button>
  </div>
</template>

<style scoped>
.customer-list {
  padding: 0 16px 80px;
  min-height: 100%;
  background: var(--color-bg);
}
.cl-search-bar {
  display: flex;
  align-items: center;
  background: #f5f5f5;
  border-radius: 20px;
  padding: 8px 14px;
  margin-bottom: 10px;
}
.cl-search-icon { color: #999; flex-shrink: 0; margin-right: 8px; }
.cl-search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  outline: none;
  color: var(--color-text);
}
.cl-search-input::placeholder { color: #bbb; }
.cl-insight-link {
  font-size: 12px; color: var(--color-primary); cursor: pointer; white-space: nowrap;
  padding: 2px 8px; border: 1px solid var(--color-primary); border-radius: 4px; flex-shrink: 0;
}
.cl-filters {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.cl-filter-select,
.cl-sort-select {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 12px;
  color: var(--color-text-secondary);
  background: #fff;
  outline: none;
  appearance: auto;
}
.cl-sort-row { margin-bottom: 8px; }
.cl-result-summary {
  font-size: 12px;
  color: var(--color-text-tertiary, #999);
  margin-bottom: 12px;
}
.cl-result-summary strong { color: var(--color-primary); }

/* Empty State */
.cl-empty {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}
.cl-empty-text { font-size: 15px; margin-top: 12px; font-weight: 500; }
.cl-empty-hint { font-size: 12px; margin-top: 4px; color: #bbb; }

/* New Customer Mode */
.cl-ai-tip {
  background: #f0fdf4;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 16px;
  font-size: 12px;
  color: var(--color-text-secondary);
  display: flex;
  align-items: flex-start;
  gap: 6px;
  line-height: 1.6;
}
.cl-new-card {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.cl-nc-match { font-size: 12px; color: #f59e0b; margin-bottom: 6px; font-weight: 600; }
.cl-nc-info { font-size: 13px; color: var(--color-text); margin-bottom: 4px; }
.cl-nc-reason { font-size: 11px; color: var(--color-text-secondary); margin-bottom: 10px; line-height: 1.5; }
.cl-nc-actions { display: flex; gap: 8px; }
.cl-nc-btn {
  flex: 1;
  padding: 8px;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
  font-size: 13px;
  cursor: pointer;
  background: #fff;
  text-align: center;
}
.cl-nc-btn.claim {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}
.cl-batch-claim {
  width: 100%;
  padding: 12px;
  margin-top: 4px;
  border: 1px dashed var(--color-primary);
  border-radius: 8px;
  font-size: 13px;
  color: var(--color-primary);
  background: rgba(171, 32, 41, 0.04);
  cursor: pointer;
}

/* Mode FAB */
.cl-mode-fab {
  position: sticky;
  bottom: 16px;
  float: right;
  margin-right: 4px;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--color-primary);
  border: none;
  box-shadow: 0 4px 12px rgba(171,32,41,0.35);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  transition: transform 0.2s;
}
.cl-mode-fab:active { transform: scale(0.92); }
</style>
