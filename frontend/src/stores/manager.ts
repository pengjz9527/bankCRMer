import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Manager {
  id: string
  name: string
}

export const useManagerStore = defineStore('manager', () => {
  const managers: Manager[] = [
    { id: 'M001', name: '李建国' },
    { id: 'M002', name: '王芳' },
    { id: 'M003', name: '张伟' },
  ]
  const currentId = ref('M001')

  const currentName = computed(() => {
    return managers.find((m) => m.id === currentId.value)?.name ?? ''
  })

  const greeting = computed(() => {
    const hour = new Date().getHours()
    const prefix = hour < 12 ? '上午好' : hour < 18 ? '下午好' : '晚上好'
    return `${prefix}，${currentName.value}经理`
  })

  function setManager(id: string) {
    currentId.value = id
  }

  return { managers, currentId, currentName, greeting, setManager }
})
