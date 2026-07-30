<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useManagerStore } from '@/stores/manager'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const managerStore = useManagerStore()
const appStore = useAppStore()
const regenerating = ref(false)

interface Task {
  time: string; title: string; customer?: string; type: 'meeting' | 'call' | 'reminder' | 'todo'
  done: boolean
}
const tasks = ref<Task[]>([
  { time:'09:00', title:'晨会 · 部门周例会', type:'meeting', done:false },
  { time:'10:30', title:'面谈 · 王建国 · 定存到期承接', customer:'王建国', type:'meeting', done:false },
  { time:'14:00', title:'电话回访 · 张丽华', customer:'张丽华', type:'call', done:false },
  { time:'15:00', title:'赵明辉代发到账配置', customer:'赵明辉', type:'reminder', done:true },
  { time:'16:30', title:'整理客户资料 · 月度总结', type:'todo', done:false },
  { time:'17:00', title:'明日日程准备', type:'todo', done:false },
])

function goBack() { router.back() }
function toggleDone(idx: number) {
  tasks.value[idx].done = !tasks.value[idx].done
  // 完成任务时保存处理记录
  const t = tasks.value[idx]
  if (t.done && t.customer) {
    api.saveProcessingRecord({
      task_type: t.type,
      cust_name: t.customer,
      action: 'completed',
      notes: t.title,
      card_id: 'schedule_' + idx,
    }).catch(() => {})
  }
}

const typeIcons: Record<string, string> = { meeting:'ico-handshake', call:'ico-phone', reminder:'ico-bell', todo:'ico-clipboard' }

/* 获取本地日期字符串（yyyy-MM-dd），避免 toISOString 在 UTC+8 时区偏差 */
function todayStr(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/* 从 API 加载今日日程 */
async function loadDaySchedule(mgrId: string) {
  try {
    const today = todayStr()
    const res = await api.getScheduleDay(mgrId, today)
    const d = res.data
    const slots = d?.slots || d?.tasks || d?.schedule_items || []
    if (Array.isArray(slots) && slots.length > 0) {
      tasks.value = slots.map((s: any) => ({
        time: s.time || s.start_time || '',
        title: s.title || s.summary || s.task_type || '',
        customer: s.customer_name || s.cust_name || '',
        type: mapTaskType(s.type || s.task_type || ''),
        done: s.done || s.completed || false,
      }))
    }
  } catch (e) {
    console.warn('加载日程失败，使用静态数据', e)
  }
}

onMounted(() => {
  loadDaySchedule(managerStore.currentId)
})

// 监听经理切换，重新加载日程
watch(() => managerStore.currentId, (newId) => {
  loadDaySchedule(newId)
})

function mapTaskType(t: string): Task['type'] {
  if (t.includes('面谈') || t.includes('会议')) return 'meeting'
  if (t.includes('电话') || t.includes('回访')) return 'call'
  if (t.includes('提醒') || t.includes('到期')) return 'reminder'
  return 'todo'
}

/* AI 重排日程 */
async function aiRegenerate() {
  if (regenerating.value) return
  regenerating.value = true
  appStore.showToast('AI 正在重排日程...')
  try {
    const today = todayStr()
    const res = await api.regenerateSchedule(today, managerStore.currentId)
    if (res.code === 0 || res.data) {
      appStore.showToast('AI 重排完成，正在刷新')
      // 重新加载日程
      const dayRes = await api.getScheduleDay(managerStore.currentId, today)
      const d = dayRes.data
      const slots = d?.slots || d?.tasks || d?.schedule_items || []
      if (Array.isArray(slots) && slots.length > 0) {
        tasks.value = slots.map((s: any) => ({
          time: s.time || s.start_time || '',
          title: s.title || s.summary || s.task_type || '',
          customer: s.customer_name || s.cust_name || '',
          type: mapTaskType(s.type || s.task_type || ''),
          done: s.done || s.completed || false,
        }))
      }
    } else {
      appStore.showToast('AI 重排失败')
    }
  } catch (e) {
    console.warn('AI重排失败', e)
    appStore.showToast('AI 重排失败，请稍后重试')
  } finally {
    regenerating.value = false
  }
}

/* 批量调整日程 */
async function adjustAll() {
  try {
    const today = todayStr()
    const undoneTasks = tasks.value.filter(t => !t.done).map((t, i) => ({
      task_type: t.type,
      cust_name: t.customer || '',
      original_time: t.time,
      action: 'reschedule',
      new_date: today,
    }))
    if (undoneTasks.length === 0) {
      appStore.showToast('没有未完成的日程需要调整')
      return
    }
    await api.adjustSchedule({ manager_id: managerStore.currentId, adjustments: undoneTasks })
    appStore.showToast(`已提交 ${undoneTasks.length} 项日程调整`)
  } catch (e) {
    console.warn('日程调整失败', e)
    appStore.showToast('日程调整失败')
  }
}
</script>

<template>
  <div class="sa-page">
    <div class="sa-header">
      <span class="sa-back" @click="goBack">←</span>
      <span class="sa-title">全部日程</span>
      <span class="sa-date">7月16日 周三</span>
    </div>
    <div class="sa-actions">
      <button class="sa-action-btn" @click="adjustAll" :disabled="regenerating">调整日程</button>
      <button class="sa-action-btn primary" @click="aiRegenerate" :disabled="regenerating">
        {{ regenerating ? 'AI 重排中...' : 'AI 重排' }}
      </button>
    </div>
    <div class="sa-body">
      <div class="sa-timeline">
        <div v-for="(t, idx) in tasks" :key="idx" class="sa-task" :class="{ done: t.done }">
          <div class="sa-task-time">{{ t.time }}</div>
          <div class="sa-task-line">
            <div class="sa-task-dot" :class="{ checked: t.done }" @click="toggleDone(idx)">
              <span v-if="t.done">✓</span>
            </div>
            <div v-if="idx < tasks.length - 1" class="sa-task-connector"></div>
          </div>
          <div class="sa-task-content" @click="toggleDone(idx)">
            <div class="sa-task-icon"><svg viewBox="0 0 24 24" class="ico ico--md"><use :href="'#' + typeIcons[t.type]" /></svg></div>
            <div>
              <div class="sa-task-title">{{ t.title }}</div>
              <div v-if="t.customer" class="sa-task-customer">{{ t.customer }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sa-page { min-height: 100%; background: #f8f8f8; padding-bottom: 40px; }
.sa-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.sa-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.sa-title { flex: 1; font-size: 16px; font-weight: 600; }
.sa-date { font-size: 13px; color: var(--color-text-secondary); }
.sa-actions { display: flex; gap: 8px; padding: 12px 16px 0; }
.sa-action-btn {
  flex: 1; padding: 8px; border-radius: 6px; border: 1px solid #e0e0e0;
  background: #fff; font-size: 13px; cursor: pointer; text-align: center;
}
.sa-action-btn.primary {
  background: var(--color-primary); color: #fff; border-color: var(--color-primary);
}
.sa-action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.sa-body { padding: 16px; }

.sa-timeline { position: relative; }
.sa-task { display: flex; gap: 12px; margin-bottom: 20px; }
.sa-task.done { opacity: 0.5; }
.sa-task-time { font-size: 12px; color: var(--color-text-secondary); width: 36px; text-align: right; flex-shrink: 0; }
.sa-task-line { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; width: 20px; }
.sa-task-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  flex-shrink: 0;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
}
.sa-task-dot.checked { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.sa-task-connector { flex: 1; width: 1px; background: var(--color-primary); min-height: 32px; }
.sa-task-content { flex: 1; display: flex; gap: 8px; cursor: pointer; padding-top: 2px; }
.sa-task-icon { width: 28px; height: 28px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; border-radius: 6px; background: var(--color-bg); color: var(--color-text-secondary); }
.sa-task-title { font-size: 14px; font-weight: 500; }
.sa-task-customer { font-size: 11px; color: var(--color-text-secondary); }
</style>
