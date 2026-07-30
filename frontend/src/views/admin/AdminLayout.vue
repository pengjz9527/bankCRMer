<template>
  <div class="admin-root">
    <aside class="admin-sidebar">
      <div class="admin-logo" @click="$router.push('/admin')">
        <span class="admin-logo-icon">YHB</span>
        <span class="admin-logo-text">运营管理后台</span>
      </div>
      <nav class="admin-nav">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="admin-nav-item"
          :class="{ 'admin-nav-item--active': isActive(item) }"
        >
          <span class="admin-nav-icon">{{ item.icon }}</span>
          <span class="admin-nav-label">{{ item.label }}</span>
        </router-link>
      </nav>
    </aside>
    <main class="admin-main">
      <header class="admin-header">
        <h1 class="admin-title">易会办 · AgentOS 运营管理后台</h1>
        <span class="admin-time">{{ now }}</span>
      </header>
      <div class="admin-content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const now = ref('')
let timer: number

const menuItems = [
  { path: '/admin', icon: 'D', label: '首页概览' },
  { path: '/admin/tasks', icon: 'T', label: '定时任务' },
  { path: '/admin/agents', icon: 'A', label: '智能体配置' },
  { path: '/admin/monitor', icon: 'M', label: '运行监测' },
  { path: '/admin/cost', icon: 'C', label: '费用分析' },
  { path: '/admin/models', icon: 'L', label: '模型配置' },
]

// 首页用精确匹配，其他页面用前缀匹配
function isActive(item: { path: string }): boolean {
  if (item.path === '/admin') {
    return route.path === '/admin'
  }
  return route.path.startsWith(item.path)
}

function updateTime() {
  now.value = new Date().toLocaleString('zh-CN')
}

onMounted(() => {
  updateTime()
  timer = window.setInterval(updateTime, 1000)
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<style scoped>
.admin-root {
  display: flex; width: 100%; min-height: 100vh; background: #f0f2f5;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', sans-serif;
  color: #333;
}
.admin-sidebar {
  width: 220px; background: #001529; color: #fff; flex-shrink: 0;
  display: flex; flex-direction: column;
}
.admin-logo {
  display: flex; align-items: center; gap: 10px; padding: 20px;
  border-bottom: 1px solid rgba(255,255,255,0.1); cursor: pointer;
}
.admin-logo-icon {
  width: 36px; height: 36px; border-radius: 8px; background: #ab2029;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: #fff;
}
.admin-logo-text { font-size: 14px; font-weight: 600; }
.admin-nav { flex: 1; padding: 12px 0; }
.admin-nav-item {
  display: flex; align-items: center; gap: 10px; padding: 12px 24px;
  color: rgba(255,255,255,0.65); text-decoration: none; font-size: 14px;
  transition: all 0.2s;
}
.admin-nav-item:hover { color: #fff; background: rgba(255,255,255,0.08); }
.admin-nav-item--active { color: #fff; background: #ab2029; }
.admin-nav-icon {
  width: 24px; height: 24px; border-radius: 4px; background: rgba(255,255,255,0.15);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; flex-shrink: 0;
}
.admin-nav-label { white-space: nowrap; }
.admin-main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.admin-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 24px; background: #fff; border-bottom: 1px solid #e8e8e8;
}
.admin-title { font-size: 16px; font-weight: 600; margin: 0; color: #333; }
.admin-time { font-size: 13px; color: #999; }
.admin-content { flex: 1; padding: 24px; overflow-y: scroll; min-width: 0; }
</style>
