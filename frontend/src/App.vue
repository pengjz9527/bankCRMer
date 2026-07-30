<template>
  <!-- 管理后台：桌面端独立布局，无 phone-frame / TabBar -->
  <template v-if="isAdminRoute">
    <router-view />
  </template>

  <!-- 手机端 APP：phone-frame 布局 -->
  <div v-else class="phone-frame">
    <AppHeader />
    <div class="workspace">
      <router-view v-slot="{ Component }">
        <transition name="page-fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
    <TabBar />
    <!-- Toast -->
    <Transition name="toast-fade">
      <div v-if="appStore.toastVisible" class="toast" :class="{ 'toast--show': appStore.toastVisible }">
        {{ appStore.toastMessage }}
      </div>
    </Transition>
    <!-- 图标精灵 -->
    <IconSprite />
  </div>
</template>

<script setup lang="ts">
import { computed, watch, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from './stores/app'
import AppHeader from './components/common/AppHeader.vue'
import TabBar from './components/common/TabBar.vue'
import IconSprite from './components/common/IconSprite.vue'

const appStore = useAppStore()
const route = useRoute()

const isAdminRoute = computed(() => route.path.startsWith('/admin'))

// admin 路由时取消 body 的居中 flex 布局，使桌面端填满视口
watch(isAdminRoute, (val) => {
  document.body.classList.toggle('admin-mode', val)
}, { immediate: true })

onUnmounted(() => {
  document.body.classList.remove('admin-mode')
})
</script>

<style scoped>
/* 页面切换动画 */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.2s ease;
}
.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}

/* Toast */
.toast {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  background: rgba(0,0,0,0.78); color: #fff; padding: 10px 20px;
  border-radius: var(--radius-md); font-size: var(--fs-body);
  z-index: 9999; white-space: nowrap;
  pointer-events: none;
}
.toast--show { display: block; }
.toast-fade-enter-active, .toast-fade-leave-active { transition: opacity 0.25s; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; }
</style>
