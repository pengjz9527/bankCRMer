<template>
  <svg xmlns="http://www.w3.org/2000/svg" id="iconSprite" viewBox="0 0 24 24" style="position:absolute;width:0;height:0;overflow:hidden">
    <defs></defs>
  </svg>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'

onMounted(() => {
  // Vue 挂载后 #iconSprite 才存在于 DOM，此时调用 IconManager.init() 注入图标
  const win = window as any
  if (win.IconManager && typeof win.IconManager.init === 'function') {
    win.IconManager.init()
  }
})
</script>
