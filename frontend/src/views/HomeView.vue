<template>
  <div class="home-root">
  <div class="scroll-content">
    <!-- Block 1: AI 智能摘要 -->
    <AiSummaryBanner :task-count="totalTaskCount" :total-hours="totalHours" />

    <!-- Block 2: 今日日程 -->
    <div>
      <div class="section-header">
        <span class="title">
          <svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-clipboard" /></svg> 今日日程安排
        </span>
        <div class="header-actions-group">
          <span class="header-action header-action--badge" @click="pendingFilterCardType = ''; pendingVisible = true" v-if="scheduleStore.pendingCount > 0">
            未安排待办({{ scheduleStore.pendingCount }})
          </span>
          <span class="header-action" @click="$router.push('/schedule/all')">全部待办 &gt;</span>
        </div>
      </div>

      <div class="schedule-block">
        <van-swipe ref="swiperRef" :loop="false" @change="onSwipeChange">
          <van-swipe-item v-for="card in scheduleCards" :key="card.cardType">
            <ScheduleCard
              :card="card"
              @complete="onCompleteTask"
              @add-task="onAddTaskClick"
              @process-task="onProcessTask"
              @opp-detail="onOppDetail"
            />
          </van-swipe-item>
        </van-swipe>
        <div class="sched-pager">
          <span
            v-for="(card, vi) in scheduleCards"
            :key="card.cardType"
            class="pager-dot"
            :class="{ active: vi === currentCardIndex }"
            @click="swipeTo(vi)"
          />
        </div>
      </div>
    </div>

    <!-- Block 3: 商机看板 -->
    <div>
      <div class="section-header">
        <span class="title">
          <svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-lightbulb" /></svg> 商机看板
        </span>
        <span style="font-size:12px;color:var(--color-primary);cursor:pointer" @click="$router.push('/opportunity')">详情 ›</span>
      </div>
      <OppBoardCard @ai-mine="onAiMine" />
    </div>

    <!-- Block 4: 新客拓展 -->
    <NewCustomerCard state="normal" />

    <div class="bottom-spacer"></div>
  </div>

  <!-- FAB -->
  <FabButton />

  <!-- 未安排待办浮层 -->
  <van-popup v-model:show="pendingVisible" position="bottom" round teleport=".phone-frame" :style="{ height: '60vh' }">
    <div class="pending-popup">
      <div class="pending-popup-hd">
        <span class="pending-popup-title">{{ pendingPopupTitle }}</span>
        <span class="pending-popup-close" @click="pendingVisible = false">关闭</span>
      </div>
      <div class="pending-popup-body">
        <template v-for="group in groupedPending" :key="group.cardType">
          <div class="pending-section">
            <div class="pending-section-hd">
              {{ group.cardName }}
              <template v-if="group.cardType === 'customer'">
                · 上午 {{ group.morningMax - group.morningUsed }}/{{ group.morningMax }}
                下午 {{ group.afternoonMax - group.afternoonUsed }}/{{ group.afternoonMax }}
              </template>
              <template v-else>
                · 剩余容量 {{ group.remaining }}/{{ group.maxCapacity }}
              </template>
            </div>
            <div
              v-for="task in group.tasks"
              :key="task.taskId"
              class="pending-task"
            >
              <div class="pending-task-row">
                <span class="task-type-tag" :class="getTypeTagClass(task.typeCode)">{{ task.typeName }}</span>
                <span class="pending-task-text">
                  <template v-if="task.custName">{{ task.custName }} · </template>
                  {{ task.summary }}
                </span>
              </div>
              <div class="pending-task-action">
                <button
                  v-if="group.canAdd"
                  class="btn-add-pending"
                  @click="onAddPendingTask(task.taskId, group.cardType)"
                >
                  添加到{{ group.cardName }}
                </button>
                <span v-else class="capacity-warn">
                  ⚠ {{ group.cardName }}已满({{ group.maxCapacity }}/{{ group.maxCapacity }})，无法添加
                </span>
              </div>
            </div>
          </div>
        </template>
        <div class="pending-empty" v-if="scheduleStore.pendingCount === 0">
          暂无未安排待办
        </div>
      </div>
    </div>
  </van-popup>

  <!-- 客户待办处理面板 -->
  <van-popup v-model:show="processPanelVisible" position="bottom" round teleport=".phone-frame" :style="{ height: '65vh' }">
    <div class="process-panel">
      <div class="process-panel-hd">
        <span class="process-panel-title">处理面板</span>
        <span class="process-panel-close" @click="closeProcessPanel">关闭</span>
      </div>
      <div class="process-panel-body" v-if="currentProcessTask">
        <!-- 任务摘要 -->
        <div class="process-task-summary">
          <span class="task-type-tag" :class="getTypeTagClass(currentProcessTask.typeCode)">{{ currentProcessTask.typeName }}</span>
          <span class="process-task-desc">{{ currentProcessTask.summary }}</span>
        </div>

        <div class="process-section-label">── 客户待办列表 ──</div>

        <!-- 客户列表 -->
        <div
          v-for="pc in processCustomers"
          :key="pc.custId"
          class="process-customer-card"
          :class="{ 'cust-processed': pc.processed }"
        >
          <div class="cust-info-row">
            <span class="cust-dot" :class="pc.processed ? 'dot-done' : 'dot-pending'">{{ pc.processed ? '✓' : '○' }}</span>
            <span class="cust-name">{{ pc.custName }}</span>
            <template v-if="pc.info">
              <span class="cust-meta">· {{ pc.info.gender }}</span>
              <span class="cust-meta">· {{ pc.info.age }}岁</span>
              <span class="cust-meta" v-if="pc.info.industry">· {{ pc.info.industry }}</span>
            </template>
            <span v-if="pc.infoLoading" class="cust-meta" style="color:#999">加载中...</span>
          </div>
          <div class="cust-detail-row" v-if="currentProcessTask">
            {{ currentProcessTask.summary }}
          </div>
          <div class="cust-actions" v-if="!pc.processed">
            <button
              class="act-btn act-btn--phone"
              :disabled="pc.actionLoading"
              @click="onProcessCustomer(pc, '电话联系')"
            >
              {{ pc.actionLoading ? '处理中...' : '📞 电话' }}
            </button>
            <button
              class="act-btn act-btn--wechat"
              :disabled="pc.actionLoading"
              @click="onProcessCustomer(pc, '微信联系')"
            >
              {{ pc.actionLoading ? '处理中...' : '✉️ 微信' }}
            </button>
            <button
              class="act-btn act-btn--pool"
              :disabled="pc.actionLoading"
              @click="onReturnToPool"
            >
              ✓ 放入待办池
            </button>
            <button
              class="act-btn act-btn--profile"
              :disabled="pc.actionLoading"
              @click="onViewProfile(pc.custId)"
            >
              🟣 画像
            </button>
          </div>
          <div class="cust-done-hint" v-else>✓ 已处理</div>
        </div>

        <div class="process-all-done" v-if="allCustomersProcessed">
          ✅ 全部客户已处理完成
        </div>
      </div>
    </div>
  </van-popup>

  <!-- 商机待办详情面板 -->
  <van-popup v-model:show="oppDetailVisible" position="bottom" round teleport=".phone-frame" :style="{ height: '65vh' }">
    <div class="process-panel">
      <div class="process-panel-hd">
        <span class="process-panel-title">商机详情</span>
        <span class="process-panel-close" @click="oppDetailVisible = false">关闭</span>
      </div>
      <div class="process-panel-body" v-if="currentOppTask">
        <!-- 商机分组标题 -->
        <div class="opp-group-header">
          <span class="opp-group-icon">📥</span>
          <span>{{ currentOppTask.typeName }} · 来源：系统推送</span>
        </div>

        <!-- 客户卡片 -->
        <div
          v-for="oc in oppCustomers"
          :key="oc.custId"
          class="opp-customer-card"
        >
          <div class="cust-info-row">
            <span class="cust-name">{{ oc.custName }}</span>
            <template v-if="oc.info">
              <span class="cust-meta">· {{ oc.info.gender }}</span>
              <span class="cust-meta">· {{ oc.info.age }}岁</span>
              <span class="cust-meta" v-if="oc.info.industry">· {{ oc.info.industry }}</span>
            </template>
            <span v-if="oc.infoLoading" class="cust-meta" style="color:#999">加载中...</span>
          </div>
          <div class="cust-detail-row" v-if="currentOppTask">
            {{ currentOppTask.summary }}
          </div>
          <div class="cust-actions">
            <button class="act-btn act-btn--profile" @click="onViewProfile(oc.custId)">
              查看画像
            </button>
            <button class="act-btn act-btn--battle" :disabled="bpGenerating" @click="onViewBattlePackage(oc.custId)">
              {{ bpGenerating ? '生成中...' : '查看作战包' }}
            </button>
            <button class="act-btn act-btn--pool" @click="onOppReturnToPool">
              放入待办池
            </button>
          </div>
        </div>
      </div>
    </div>
  </van-popup>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'
import { useScheduleStore } from '../stores/schedule'
import type { PendingTask, TaskItem, ScheduleCardData } from '../stores/schedule'
import { useManagerStore } from '../stores/manager'
import { useOpportunityStore } from '../stores/opportunity'
import { useKpiStore } from '../stores/kpi'
import { api } from '../api'
import AiSummaryBanner from '../components/business/AiSummaryBanner.vue'
import ScheduleCard from '../components/business/ScheduleCard.vue'
import OppBoardCard from '../components/business/OppBoardCard.vue'
import NewCustomerCard from '../components/business/NewCustomerCard.vue'
import FabButton from '../components/business/FabButton.vue'

const router = useRouter()
const appStore = useAppStore()
const scheduleStore = useScheduleStore()
const managerStore = useManagerStore()
const opportunityStore = useOpportunityStore()
const kpiStore = useKpiStore()

const currentCardIndex = ref(0)
const swiperRef = ref<any>(null)
const pendingVisible = ref(false)
const pendingFilterCardType = ref('')

// 待办池浮层标题（支持按卡片过滤）
const pendingPopupTitle = computed(() => {
  if (pendingFilterCardType.value) {
    const count = scheduleStore.pendingTasks.filter(
      t => getTargetCardType(t.typeCode) === pendingFilterCardType.value
    ).length
    const nameMap: Record<string, string> = { customer: '客户', opportunity: '商机', work: '工作' }
    return `${nameMap[pendingFilterCardType.value] || ''}待办 (${count})`
  }
  return `未安排待办 (${scheduleStore.pendingCount})`
})

const scheduleCards = computed(() => scheduleStore.cards)

// 总任务数（三卡片合计，用于 AI 摘要）
const totalTaskCount = computed(() =>
  scheduleStore.cards.reduce((sum, c) => sum + c.totalCount, 0)
)

// 预计总耗时（按每个任务 0.5h 估算）
const totalHours = computed(() => {
  const t = totalTaskCount.value
  const h = Math.round(t * 0.5 * 10) / 10
  return h || 0.5
})

// 未安排待办按目标卡片分组（含上下午分时容量）
const groupedPending = computed(() => {
  const groups: Record<string, {
    cardType: string
    cardName: string
    maxCapacity: number
    remaining: number
    canAdd: boolean
    morningUsed: number
    afternoonUsed: number
    morningMax: number
    afternoonMax: number
    tasks: PendingTask[]
  }> = {}

  const cardMap: Record<string, { cardName: string; totalCount: number; maxCapacity: number; morning: TaskItem[]; afternoon: TaskItem[] }> = {}
  for (const c of scheduleStore.cards) {
    cardMap[c.cardType] = { cardName: c.cardName, totalCount: c.totalCount, maxCapacity: c.maxCapacity, morning: c.morning, afternoon: c.afternoon }
  }

  // 按卡片过滤：仅展示触发卡对应的待办类型
  const filter = pendingFilterCardType.value
  for (const task of scheduleStore.pendingTasks) {
    const targetCard = getTargetCardType(task.typeCode)
    if (filter && targetCard !== filter) continue
    if (!groups[targetCard]) {
      const card = cardMap[targetCard]
      const maxCap = card?.maxCapacity ?? (targetCard === 'opportunity' ? 4 : targetCard === 'work' ? 4 : 10)
      const total = card?.totalCount ?? 0

      // 上下午分时统计（仅客户待办有限制）
      const morningUsed = card ? card.morning.filter((t: TaskItem) => t.status !== 'completed').length : 0
      const afternoonUsed = card ? card.afternoon.filter((t: TaskItem) => t.status !== 'completed').length : 0
      const morningMax = targetCard === 'customer' ? 5 : 99
      const afternoonMax = targetCard === 'customer' ? 5 : 99

      // canAdd: 客户待办需同时满足总容量和分时容量
      let canAdd = false
      if (targetCard === 'customer') {
        canAdd = (morningUsed < morningMax || afternoonUsed < afternoonMax) && total < maxCap
      } else {
        canAdd = total < maxCap
      }

      groups[targetCard] = {
        cardType: targetCard,
        cardName: card?.cardName || (targetCard === 'customer' ? '客户待办' : targetCard === 'opportunity' ? '商机待办' : '工作待办'),
        maxCapacity: maxCap,
        remaining: maxCap - total,
        canAdd,
        morningUsed,
        afternoonUsed,
        morningMax,
        afternoonMax,
        tasks: [],
      }
    }
    groups[targetCard].tasks.push(task)
  }

  return Object.values(groups)
})

function getTargetCardType(typeCode: string): string {
  const m: Record<string, string> = {
    due: 'customer', big_move: 'customer', overdue: 'customer',
    birthday: 'customer', contact_lapse: 'customer', credit_card: 'customer',
    post_meeting: 'customer', insight_alert: 'customer',
    opp: 'opportunity',
    report: 'work', report_review: 'work',
    morning_meeting: 'work', evening_meeting: 'work',
  }
  return m[typeCode] || 'customer'
}

function getTypeTagClass(typeCode: string): string {
  const m: Record<string, string> = {
    due: 'tag-danger',
    big_move: 'tag-warning',
    overdue: 'tag-warning',
    opp: 'tag-opportunity',
    birthday: 'tag-success',
    contact_lapse: 'tag-muted',
    credit_card: 'tag-muted',
    post_meeting: 'tag-muted',
    insight_alert: 'tag-danger',
    report: 'tag-info',
    report_review: 'tag-info',
    morning_meeting: 'tag-primary',
    evening_meeting: 'tag-primary',
  }
  return m[typeCode] || 'tag-muted'
}

function onSwipeChange(index: number) {
  currentCardIndex.value = index
}

function swipeTo(index: number) {
  currentCardIndex.value = index
  swiperRef.value?.swipeTo?.(index)
}

async function onCompleteTask(taskId: string) {
  const ok = await scheduleStore.completeTask(managerStore.currentId, taskId)
  if (ok) {
    appStore.showToast('已完成')
  } else {
    appStore.showToast('操作失败，请重试')
  }
}

function onAddTaskClick(cardType: string) {
  pendingFilterCardType.value = cardType
  pendingVisible.value = true
}

async function onAddPendingTask(taskId: string, cardType: string) {
  const result = await scheduleStore.addTaskFromPending(managerStore.currentId, taskId, cardType)
  if (result.success) {
    appStore.showToast('已添加到日程')
  } else {
    appStore.showToast(result.message || '添加失败')
  }
}

// ======================== 客户处理面板 ========================
interface ProcessCustomer {
  custId: number
  custName: string
  info: Record<string, any> | null
  infoLoading: boolean
  processed: boolean
  actionLoading: boolean
}

const processPanelVisible = ref(false)
const currentProcessTaskId = ref('')
const processCustomers = ref<ProcessCustomer[]>([])

const currentProcessTask = computed<TaskItem | null>(() => {
  if (!currentProcessTaskId.value) return null
  return findTask(currentProcessTaskId.value)
})

const allCustomersProcessed = computed(() =>
  processCustomers.value.length > 0 && processCustomers.value.every(c => c.processed)
)

function findTask(taskId: string): TaskItem | null {
  for (const card of scheduleStore.cards) {
    for (const t of [...card.morning, ...card.afternoon]) {
      if (t.taskId === taskId) return t
    }
  }
  return null
}

async function onProcessTask(taskId: string) {
  const task = findTask(taskId)
  if (!task) return

  currentProcessTaskId.value = taskId

  // 初始化客户列表
  const ids = task.customerIds || []
  const names = task.customerNames || []
  processCustomers.value = ids.map((cid, i) => ({
    custId: cid,
    custName: names[i] || `客户${cid}`,
    info: null,
    infoLoading: true,
    processed: false,
    actionLoading: false,
  }))

  processPanelVisible.value = true

  // 异步加载客户基本信息
  for (const pc of processCustomers.value) {
    try {
      const res = await api.getCustomerBasic(String(pc.custId))
      pc.info = res.data || {}
    } catch {
      pc.info = null
    } finally {
      pc.infoLoading = false
    }
  }
}

function closeProcessPanel() {
  processPanelVisible.value = false
  currentProcessTaskId.value = ''
  processCustomers.value = []
}

async function onProcessCustomer(pc: ProcessCustomer, action: string) {
  pc.actionLoading = true
  const mgrId = managerStore.currentId
  const taskId = currentProcessTaskId.value
  const ok = await scheduleStore.processCustomerTask(mgrId, taskId, pc.custId, pc.custName, action)
  if (ok) {
    pc.processed = true
    appStore.showToast(`已记录: ${action}`)

    // 全部处理完 → 自动标记任务完成
    if (allCustomersProcessed.value) {
      await scheduleStore.completeTask(mgrId, taskId)
      nextTick(() => {
        setTimeout(() => closeProcessPanel(), 800)
      })
    }
  } else {
    appStore.showToast('操作失败，请重试')
  }
  pc.actionLoading = false
}

async function onReturnToPool() {
  const taskId = currentProcessTaskId.value
  if (!taskId) return
  const ok = await scheduleStore.returnTaskToPool(managerStore.currentId, taskId)
  if (ok) {
    appStore.showToast('已放回待办池')
    closeProcessPanel()
  } else {
    appStore.showToast('操作失败，请重试')
  }
}

function onViewProfile(custId: number) {
  router.push(`/customer/${custId}`)
}

// ======================== 商机详情面板 ========================
interface OppCustomer {
  custId: number
  custName: string
  info: Record<string, any> | null
  infoLoading: boolean
}

const oppDetailVisible = ref(false)
const currentOppTaskId = ref('')
const oppCustomers = ref<OppCustomer[]>([])
const bpGenerating = ref(false)

const currentOppTask = computed<TaskItem | null>(() => {
  if (!currentOppTaskId.value) return null
  return findTask(currentOppTaskId.value)
})

async function onOppDetail(taskId: string) {
  const task = findTask(taskId)
  if (!task) return

  currentOppTaskId.value = taskId
  oppDetailVisible.value = true

  // 初始化客户列表
  const ids = task.customerIds || []
  const names = task.customerNames || []
  oppCustomers.value = ids.map((cid, i) => ({
    custId: cid,
    custName: names[i] || `客户${cid}`,
    info: null,
    infoLoading: true,
  }))

  // 异步加载客户信息
  for (const oc of oppCustomers.value) {
    try {
      const res = await api.getCustomerBasic(String(oc.custId))
      oc.info = res.data || {}
    } catch {
      oc.info = null
    } finally {
      oc.infoLoading = false
    }
  }
}

function deriveOppIdFromTask(task: TaskItem | null): string | undefined {
  // 优先使用任务自带的 opp_id（由 query_tasks_for_schedule 步骤8 注入）
  if (task?.oppId) return task.oppId

  const taskId = task?.taskId || ''
  // TK_OPP_{opp_id} 格式 — 从 opportunities 表来的 AI 挖掘商机任务
  if (taskId.startsWith('TK_OPP_') && !taskId.startsWith('TK_OPP_SAL_') && !taskId.startsWith('TK_OPP_DUE_') && !taskId.startsWith('TK_OPP_DEC_') && !taskId.startsWith('TK_OPP_FUND_') && !taskId.startsWith('TK_OPP_BIG_')) {
    return taskId.slice(7)
  }
  return undefined
}

async function generateAndViewBattlePackage(custId: number, oppId?: string) {
  bpGenerating.value = true
  try {
    const res = await api.generateBattlePackage({
      cust_id: custId,
      mode: '标准版',
      opp_id: oppId || '',
    })
    const bpId = res?.data?.bp_id
    if (bpId) {
      appStore.showToast('作战包生成成功！')
      router.push({ name: 'battle-package', params: { id: bpId } })
    } else {
      appStore.showToast('作战包生成失败')
    }
  } catch (e: any) {
    appStore.showToast('生成失败: ' + (e?.message || '未知错误'))
  } finally {
    bpGenerating.value = false
  }
}

async function onViewBattlePackage(custId: number) {
  // 从当前商机任务推导 opp_id（优先按任务携带的 oppId 精确匹配）
  const task = currentOppTask.value
  const oppId = deriveOppIdFromTask(task)

  try {
    // 优先按 opp_id 查询对应商机的作战包
    const res = oppId
      ? await api.getBattlePackages({ opp_id: oppId })
      : await api.getBattlePackages({ cust_id: custId })
    const pkgs = res.data?.packages || []
    if (pkgs.length > 0) {
      router.push({ name: 'battle-package', params: { id: pkgs[0].bp_id } })
    } else {
      // 无作战包 → 触发 AI 生成（与商机管理页行为一致）
      await generateAndViewBattlePackage(custId, oppId)
    }
  } catch {
    // 查询失败也尝试生成
    await generateAndViewBattlePackage(custId, oppId)
  }
}

async function onOppReturnToPool() {
  const taskId = currentOppTaskId.value
  if (!taskId) return
  const ok = await scheduleStore.returnTaskToPool(managerStore.currentId, taskId)
  if (ok) {
    appStore.showToast('已放回待办池')
    oppDetailVisible.value = false
    currentOppTaskId.value = ''
    oppCustomers.value = []
  } else {
    appStore.showToast('操作失败，请重试')
  }
}

function onAiMine() {
  router.push('/ai/chat')
}

onMounted(() => {
  // 从后端加载日程和商机数据
  scheduleStore.loadTasks(managerStore.currentId)
  opportunityStore.loadOpportunities(managerStore.currentId)
  kpiStore.loadKpi(managerStore.currentId)
})

// 监听经理切换，重新加载数据
watch(() => managerStore.currentId, (newId) => {
  scheduleStore.loadTasks(newId)
  opportunityStore.loadOpportunities(newId)
  kpiStore.loadKpi(newId)
})
</script>

<style scoped>
.home-root {
  position: relative;
  display: flex;
  flex-direction: column;
}
.schedule-block {
  background: var(--color-card); border-radius: var(--radius-md);
  box-shadow: var(--shadow-card); overflow: hidden;
}
.sched-pager {
  display: flex; justify-content: center; gap: 10px;
  padding: 12px 0 4px;
}
.pager-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--color-border);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: all var(--duration-fast);
}
.pager-dot.active {
  background: var(--color-primary);
  width: 24px;
  border-radius: 4px;
}
.header-action--badge {
  color: var(--color-warning, #E67E22);
  font-weight: var(--fw-bold);
}

/* 未安排待办浮层 */
.pending-popup {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.pending-popup-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-md);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}
.pending-popup-title {
  font-size: var(--fs-body);
  font-weight: var(--fw-bold);
  color: var(--color-text-primary);
}
.pending-popup-close {
  font-size: var(--fs-small);
  color: var(--color-text-tertiary);
  cursor: pointer;
}
.pending-popup-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--sp-sm) var(--sp-md);
}
.pending-section {
  margin-bottom: var(--sp-md);
}
.pending-section-hd {
  font-size: var(--fs-caption);
  font-weight: var(--fw-bold);
  color: var(--color-text-secondary);
  padding: var(--sp-xs) 0;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--sp-xs);
}
.pending-task {
  padding: var(--sp-sm) var(--sp-xs);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  margin-bottom: 6px;
}
.pending-task-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.pending-task-text {
  flex: 1;
  font-size: var(--fs-small);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pending-task-action {
  display: flex;
  justify-content: flex-end;
}
.btn-add-pending {
  height: 28px;
  padding: 0 var(--sp-md);
  font-size: var(--fs-caption);
  font-weight: var(--fw-bold);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: #fff;
  cursor: pointer;
  transition: all var(--duration-fast);
}
.btn-add-pending:active {
  opacity: 0.8;
  transform: scale(0.96);
}
.capacity-warn {
  font-size: var(--fs-caption);
  color: #C0392B;
}
.pending-empty {
  padding: var(--sp-lg);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--fs-small);
}

/* ======== 处理面板通用样式 ======== */
.process-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.process-panel-hd {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-md);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}
.process-panel-title {
  font-size: var(--fs-body);
  font-weight: var(--fw-bold);
  color: var(--color-text-primary);
}
.process-panel-close {
  font-size: var(--fs-small);
  color: var(--color-text-tertiary);
  cursor: pointer;
}
.process-panel-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--sp-md);
}

/* 任务摘要 */
.process-task-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: var(--sp-sm);
  background: var(--color-bg);
  border-radius: var(--radius-sm);
  margin-bottom: var(--sp-md);
}
.process-task-desc {
  font-size: var(--fs-small);
  color: var(--color-text-secondary);
}
.process-section-label {
  text-align: center;
  font-size: var(--fs-caption);
  color: var(--color-text-tertiary);
  margin-bottom: var(--sp-sm);
}

/* 客户卡片 */
.process-customer-card,
.opp-customer-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--sp-sm) var(--sp-md);
  margin-bottom: var(--sp-sm);
  transition: opacity 0.3s;
}
.process-customer-card.cust-processed {
  opacity: 0.5;
  background: #F5FFF5;
}
.cust-info-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}
.cust-dot {
  font-size: 14px;
  flex-shrink: 0;
}
.dot-pending { color: var(--color-text-tertiary); }
.dot-done { color: var(--color-success); font-weight: var(--fw-bold); }
.cust-name {
  font-size: var(--fs-body);
  font-weight: var(--fw-bold);
  color: var(--color-text-primary);
}
.cust-meta {
  font-size: var(--fs-caption);
  color: var(--color-text-tertiary);
}
.cust-detail-row {
  font-size: var(--fs-caption);
  color: var(--color-text-secondary);
  padding: 4px 0;
  margin-bottom: 6px;
  border-bottom: 1px dashed var(--color-border);
}
.cust-done-hint {
  text-align: right;
  font-size: var(--fs-small);
  color: var(--color-success);
  font-weight: var(--fw-bold);
  padding: 4px 0;
}

/* 操作按钮行 */
.cust-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.act-btn {
  height: 30px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: var(--fw-bold);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text-primary);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--duration-fast);
}
.act-btn:active {
  opacity: 0.7;
  transform: scale(0.96);
}
.act-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.act-btn--phone {
  border-color: #27AE60;
  color: #27AE60;
}
.act-btn--wechat {
  border-color: #27AE60;
  color: #27AE60;
}
.act-btn--pool {
  border-color: #E67E22;
  color: #E67E22;
}
.act-btn--profile {
  border-color: #8E44AD;
  color: #8E44AD;
}
.act-btn--battle {
  border-color: var(--color-ai, #6C5CE7);
  color: var(--color-ai, #6C5CE7);
}

/* 全部完成提示 */
.process-all-done {
  text-align: center;
  padding: var(--sp-md);
  font-size: var(--fs-body);
  font-weight: var(--fw-bold);
  color: var(--color-success);
}

/* 商机分组标题 */
.opp-group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--sp-sm) 0;
  margin-bottom: var(--sp-sm);
  font-size: var(--fs-small);
  font-weight: var(--fw-bold);
  color: var(--color-text-primary);
  border-bottom: 2px solid var(--color-ai, #6C5CE7);
}
.opp-group-icon {
  font-size: 16px;
}

/* 任务标签样式（与 ScheduleCard 保持一致） */
.tag-danger { background: #FFF0F0; color: #C0392B; font-weight: var(--fw-bold); padding: 1px 6px; border-radius: 4px; font-size: var(--fs-small); white-space: nowrap; }
.tag-warning { background: #FFF8E1; color: #E67E22; font-weight: var(--fw-bold); padding: 1px 6px; border-radius: 4px; font-size: var(--fs-small); white-space: nowrap; }
.tag-muted { background: #F0F0F0; color: #666; font-weight: var(--fw-bold); padding: 1px 6px; border-radius: 4px; font-size: var(--fs-small); white-space: nowrap; }
.tag-success { background: #E8F8E8; color: #27AE60; font-weight: var(--fw-bold); padding: 1px 6px; border-radius: 4px; font-size: var(--fs-small); white-space: nowrap; }
.tag-opportunity { background: #F0E8FF; color: #6C5CE7; font-weight: var(--fw-bold); padding: 1px 6px; border-radius: 4px; font-size: var(--fs-small); white-space: nowrap; }
.tag-info { background: #E8F4FD; color: #2980B9; font-weight: var(--fw-bold); padding: 1px 6px; border-radius: 4px; font-size: var(--fs-small); white-space: nowrap; }
.tag-primary { background: #E8F0FE; color: #3366FF; font-weight: var(--fw-bold); padding: 1px 6px; border-radius: 4px; font-size: var(--fs-small); white-space: nowrap; }
</style>
