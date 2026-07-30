<template>
  <header class="app-header">
    <span class="greeting">{{ managerStore.greeting }}</span>
    <select
      class="manager-selector"
      :value="managerStore.currentId"
      @change="onManagerChange(($event.target as HTMLSelectElement).value)"
    >
      <option v-for="m in managerStore.managers" :key="m.id" :value="m.id">
        {{ m.name }}
      </option>
    </select>
    <div class="header-actions">
      <button class="icon-btn" @click="$router.push('/search')">
        <svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-search" /></svg>
      </button>
      <button class="icon-btn" @click="$router.push('/messages')">
        <svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-bell" /></svg>
        <span v-if="unreadCount > 0" class="badge">{{ unreadCount }}</span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useManagerStore } from '../../stores/manager'
import { useAppStore } from '../../stores/app'

const managerStore = useManagerStore()
const appStore = useAppStore()
const unreadCount = ref(3)

function onManagerChange(mgrId: string) {
  managerStore.setManager(mgrId)
  appStore.showToast(`已切换至: ${managerStore.currentName}经理`)
}
</script>

<style scoped>
.app-header {
  background: var(--color-card); flex-shrink: 0;
  padding: 10px 15px 12px;
  display: flex; justify-content: space-between; align-items: center;
  box-shadow: 0 1px 0 var(--color-divider);
  position: relative; z-index: 300;
}
.greeting {
  font-size: var(--fs-h2); font-weight: var(--fw-bold);
  color: var(--color-text-primary);
}
.manager-selector {
  font-size: 11px; padding: 4px 8px; border-radius: 6px;
  border: 1px solid #d0d5dd; background: #fff; color: #333;
  margin-left: 8px; max-width: 110px; cursor: pointer;
}
.header-actions {
  display: flex; gap: var(--sp-sm); align-items: center;
}
.icon-btn {
  width: 36px; height: 36px; border-radius: 50%;
  background: var(--color-bg); border: none; font-size: 18px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; position: relative;
  transition: background var(--duration-fast);
  -webkit-tap-highlight-color: transparent;
}
.icon-btn:active { background: var(--color-divider); }
.badge {
  position: absolute; top: -3px; right: -3px;
  min-width: 16px; height: 16px; padding: 0 4px;
  background: var(--color-danger); color: #fff;
  font-size: 10px; border-radius: var(--radius-full);
  display: flex; align-items: center; justify-content: center;
  font-weight: var(--fw-bold); border: 2px solid #fff;
}
</style>
