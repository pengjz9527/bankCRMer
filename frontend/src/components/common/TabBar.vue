<template>
  <nav class="tab-bar">
    <div
      v-for="tab in tabs"
      :key="tab.key"
      class="tab-item"
      :class="{ 'tab-item--active': activeTab === tab.key }"
      @click="navigate(tab)"
    >
      <span class="tab-icon">
        <svg viewBox="0 0 24 24" class="ico ico--md"><use :href="'#' + tab.icon" /></svg>
      </span>
      <span class="tab-label">{{ tab.label }}</span>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const tabs = [
  { key: 'home', label: '工作台', icon: 'ico-home', path: '/' },
  { key: 'customer', label: '客户', icon: 'ico-people', path: '/customer' },
  { key: 'product', label: '产品', icon: 'ico-package', path: '/product' },
  { key: 'me', label: '我的', icon: 'ico-user', path: '/profile' },
]

const activeTab = computed(() => {
  const path = route.path
  if (path === '/') return 'home'
  if (path.startsWith('/customer')) return 'customer'
  if (path.startsWith('/product')) return 'product'
  if (path.startsWith('/profile')) return 'me'
  return 'home'
})

function navigate(tab: (typeof tabs)[0]) {
  router.push(tab.path)
}
</script>

<style scoped>
/* 复用 global.css 中的 .tab-bar / .tab-item 样式 */
</style>
