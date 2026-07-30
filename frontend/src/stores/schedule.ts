import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api'

export interface TaskItem {
  taskId: string
  typeCode: string
  typeName: string
  custName: string
  summary: string
  custCount: number
  status: 'pending' | 'completed' | 'skipped'
  assignedSlot: 'morning' | 'afternoon'
  priorityWeight: number
  customerIds: number[]
  customerNames: string[]
}

export interface ScheduleCardData {
  cardType: 'customer' | 'opportunity' | 'work'
  cardName: string
  morning: TaskItem[]
  afternoon: TaskItem[]
  totalCount: number
  maxCapacity: number
}

export interface PendingTask extends TaskItem {
  // 与 TaskItem 相同结构
}

// 静态回落数据（三卡片结构）
const staticCards: ScheduleCardData[] = [
  {
    cardType: 'customer', cardName: '客户待办',
    morning: [
      { taskId:'c1', typeCode:'due', typeName:'产品到期', custName:'王建国', summary:'2笔产品到期, 合计30万', custCount:2, status:'pending', assignedSlot:'morning', priorityWeight:100, customerIds:[1], customerNames:['王建国'] },
      { taskId:'c2', typeCode:'big_move', typeName:'大额异动', custName:'张丽华', summary:'昨日转出30万', custCount:1, status:'pending', assignedSlot:'morning', priorityWeight:80, customerIds:[2], customerNames:['张丽华'] },
    ],
    afternoon: [
      { taskId:'c3', typeCode:'contact_lapse', typeName:'联络超期', custName:'刘大明', summary:'超期16天未联络', custCount:1, status:'pending', assignedSlot:'afternoon', priorityWeight:50, customerIds:[3], customerNames:['刘大明'] },
    ],
    totalCount: 3, maxCapacity: 10,
  },
  {
    cardType: 'opportunity', cardName: '商机待办',
    morning: [
      { taskId:'o1', typeCode:'opp', typeName:'商机待办', custName:'赵明辉', summary:'定存到期承接', custCount:1, status:'pending', assignedSlot:'morning', priorityWeight:75, customerIds:[4], customerNames:['赵明辉'] },
    ],
    afternoon: [],
    totalCount: 1, maxCapacity: 4,
  },
  {
    cardType: 'work', cardName: '工作待办',
    morning: [
      { taskId:'w1', typeCode:'morning_meeting', typeName:'早会', custName:'', summary:'每日晨会', custCount:1, status:'pending', assignedSlot:'morning', priorityWeight:100, customerIds:[], customerNames:[] },
    ],
    afternoon: [
      { taskId:'w2', typeCode:'evening_meeting', typeName:'晚会', custName:'', summary:'每日夕会', custCount:1, status:'pending', assignedSlot:'afternoon', priorityWeight:100, customerIds:[], customerNames:[] },
    ],
    totalCount: 2, maxCapacity: 4,
  },
]

/* 获取本地日期字符串（yyyy-MM-dd），避免 toISOString 在 UTC+8 时区偏差 */
function todayStr(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export const useScheduleStore = defineStore('schedule', () => {
  const cards = ref<ScheduleCardData[]>(staticCards)
  const pendingTasks = ref<PendingTask[]>([])
  const loading = ref(false)
  const weekPlan = ref<any[]>([])

  const visibleCards = computed(() => cards.value)

  const pendingCount = computed(() => pendingTasks.value.length)

  async function loadTasks(mgrId: string) {
    loading.value = true
    try {
      const today = todayStr()
      console.log(`[schedule] 请求日程: manager=${mgrId} date=${today}`)
      const res = await api.getScheduleDay(mgrId, today)
      console.log(`[schedule] 响应: code=${res.code} cards=${res.data?.cards?.length ?? '?'}`)
      const data = res.data
      if (data?.cards && Array.isArray(data.cards) && data.cards.length > 0) {
        cards.value = data.cards.map(mapRawCard)
        console.log(`[schedule] 已加载 ${cards.value.length} 张卡片`)
      } else {
        console.warn('[schedule] API 返回空卡片，保留静态数据')
      }
      // 同时加载未安排待办
      await loadPending(mgrId)
    } catch (e) {
      console.warn('[schedule] 加载日程失败，使用静态数据', e)
    } finally {
      loading.value = false
    }
  }

  async function loadPending(mgrId: string) {
    try {
      const today = todayStr()
      const res = await api.getSchedulePending(mgrId, today)
      const data = res.data
      if (data?.pending && Array.isArray(data.pending)) {
        pendingTasks.value = data.pending.map(mapRawTask)
      }
    } catch (e) {
      console.warn('加载未安排待办失败', e)
    }
  }

  async function loadWeekSchedule(mgrId: string, startDate?: string) {
    try {
      const res = await api.getScheduleWeek(mgrId, startDate)
      const d = res.data
      if (d?.days || Array.isArray(d)) {
        weekPlan.value = d.days || d
      }
    } catch (e) {
      console.warn('加载周计划失败', e)
    }
  }

  async function completeTask(mgrId: string, taskId: string) {
    const today = todayStr()
    try {
      const res = await api.completeScheduleTask(today, { manager_id: mgrId, task_id: taskId })
      if (res.data?.schedule) {
        cards.value = res.data.schedule.cards.map(mapRawCard)
      }
      return true
    } catch (e) {
      console.warn('标记完成失败', e)
      return false
    }
  }

  async function processCustomerTask(
    mgrId: string,
    taskId: string,
    custId: number,
    custName: string,
    action: string,
  ) {
    const today = todayStr()
    try {
      await api.processScheduleTask(today, {
        manager_id: mgrId,
        task_id: taskId,
        cust_id: custId,
        cust_name: custName,
        action,
      })
      return true
    } catch (e) {
      console.warn('记录处理方式失败', e)
      return false
    }
  }

  async function returnTaskToPool(mgrId: string, taskId: string) {
    const today = todayStr()
    try {
      const res = await api.returnTaskToPool(today, { manager_id: mgrId, task_id: taskId })
      if (res.data?.schedule) {
        cards.value = res.data.schedule.cards.map(mapRawCard)
      }
      // 重新加载 pending
      await loadPending(mgrId)
      return true
    } catch (e) {
      console.warn('放回待办池失败', e)
      return false
    }
  }

  async function addTaskFromPending(mgrId: string, taskId: string, cardType: string) {
    const today = todayStr()
    try {
      const res = await api.addTaskToSchedule(today, {
        manager_id: mgrId,
        task_id: taskId,
        card_type: cardType,
      })
      if (res.data?.schedule) {
        cards.value = res.data.schedule.cards.map(mapRawCard)
        // 重新加载 pending，确保待办池同步更新
        await loadPending(mgrId)
        return { success: true, message: res.data?.message || '' }
      }
      // 当 res.data 为 null 时（如容量满），错误信息在顶层 res.message
      return { success: false, message: res.data?.message || (res as any).message || '添加失败：未获取到日程' }
    } catch (e: any) {
      return { success: false, message: e?.message || '添加失败' }
    }
  }

  return {
    cards, pendingTasks, loading, weekPlan,
    visibleCards, pendingCount,
    loadTasks, loadPending, loadWeekSchedule,
    completeTask, addTaskFromPending, processCustomerTask, returnTaskToPool,
  }
})

/* 原始卡片数据 -> ScheduleCardData */
function mapRawCard(raw: any): ScheduleCardData {
  return {
    cardType: raw.card_type || 'customer',
    cardName: raw.card_name || '',
    morning: (raw.morning || []).map(mapRawTask),
    afternoon: (raw.afternoon || []).map(mapRawTask),
    totalCount: raw.total_count ?? 0,
    maxCapacity: raw.max_capacity ?? 10,
  }
}

/* 原始任务数据 -> TaskItem */
function mapRawTask(raw: any): TaskItem {
  return {
    taskId: raw.task_id || '',
    typeCode: raw.type_code || '',
    typeName: raw.type_name || '',
    custName: raw.cust_name || '',
    summary: raw.summary || '',
    custCount: raw.cust_count ?? 1,
    status: raw.status || 'pending',
    assignedSlot: raw.assigned_slot || 'morning',
    priorityWeight: raw.priority_weight ?? 30,
    customerIds: raw.customer_ids || [],
    customerNames: raw.customer_names || [],
  }
}
