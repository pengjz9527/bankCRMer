import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const toastVisible = ref(false)
  const toastMessage = ref('')
  const apiAvailable = ref(true)
  const useApi = ref(true)

  let toastTimer: ReturnType<typeof setTimeout> | null = null

  function showToast(msg: string, duration = 1800) {
    toastMessage.value = msg
    toastVisible.value = true
    if (toastTimer) clearTimeout(toastTimer)
    toastTimer = setTimeout(() => {
      toastVisible.value = false
    }, duration)
  }

  return { toastVisible, toastMessage, apiAvailable, useApi, showToast }
})
