<template>
  <div class="home-root">
  <div class="scroll-content">
    <!-- Block 1: AI 智能摘要 -->
    <AiSummaryBanner :task-count="totalTaskCount" :total-hours="totalHours" :review-tips="reviewTips" />

    <!-- Block 1.5: 资讯早报 -->
    <div v-if="digestBriefing" class="digest-teaser" @click="$router.push('/digest')">
      <div class="digest-teaser-header">
        <span class="digest-teaser-icon">📰</span>
        <span class="digest-teaser-title">资讯早报</span>
        <span class="digest-teaser-more">查看全部 &gt;</span>
      </div>
      <div class="digest-teaser-briefing">{{ digestBriefing }}</div>
      <div v-if="digestHeadlines.length > 0" class="digest-teaser-headlines">
        <div v-for="(h, i) in digestHeadlines.slice(0, 2)" :key="i" class="digest-teaser-hl">
          <span class="digest-teaser-dot"></span>{{ h.title }}
        </div>
      </div>
    </div>

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
      <OppBoardCard />
    </div>

    <!-- Block 4: 商机挖掘 -->
    <div>
      <div class="section-header">
        <span class="title">
          <svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-lightning" /></svg> 商机挖掘
        </span>
      </div>
      <OppMiningCard @ai-mine="onAiMine" />
    </div>

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
                <span class="task-cust-name">{{ task.custName || '-' }}</span>
                <span
                  v-for="(si, siIdx) in (task.subItems || []).slice(0, 2)"
                  :key="siIdx"
                  class="task-sub-tag"
                  :class="getTypeTagClass(si.typeCode)"
                >{{ si.typeName }}</span>
                <span v-if="(task.subItems || []).length > 2" class="task-sub-more">+{{ task.subItems!.length - 2 }}</span>
                <span class="pending-task-text">{{ task.summary }}</span>
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
import OppMiningCard from '../components/business/OppMiningCard.vue'
import FabButton from '../components/business/FabButton.vue'
import SensitiveText from '../components/SensitiveText.vue'

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
    const nameMap: Record<string, string> = { customer: '客户', work: '工作' }
    return `${nameMap[pendingFilterCardType.value] || ''}待办 (${count})`
  }
  return `未安排待办 (${scheduleStore.pendingCount})`
})

const scheduleCards = computed(() => scheduleStore.cards)

// 总任务数（二卡片合计，用于 AI 摘要）
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
      const maxCap = card?.maxCapacity ?? (targetCard === 'work' ? 4 : 7)
      const total = card?.totalCount ?? 0

      // 上下午分时统计（仅客户待办有限制）
      const morningUsed = card ? card.morning.filter((t: TaskItem) => t.status !== 'completed').length : 0
      const afternoonUsed = card ? card.afternoon.filter((t: TaskItem) => t.status !== 'completed').length : 0
      const morningMax = targetCard === 'customer' ? 4 : 99
      const afternoonMax = targetCard === 'customer' ? 3 : 99

      // canAdd: 客户待办需同时满足总容量和分时容量
      let canAdd = false
      if (targetCard === 'customer') {
        canAdd = (morningUsed < morningMax || afternoonUsed < afternoonMax) && total < maxCap
      } else {
        canAdd = total < maxCap
      }

      groups[targetCard] = {
        cardType: targetCard,
        cardName: card?.cardName || (targetCard === 'customer' ? '客户待办' : '工作待办'),
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
    opp: 'customer', customer_synthesis: 'customer',
    report: 'work', report_review: 'work',
    morning_meeting: 'work', evening_meeting: 'work',
  }
  return m[typeCode] || 'customer'
}

function priLabel(weight: number): string {
  if (weight >= 80) return 'P0'
  if (weight >= 60) return 'P1'
  if (weight >= 40) return 'P2'
  return 'P3'
}

function priClass(weight: number): string {
  if (weight >= 80) return 'pri-p0'
  if (weight >= 60) return 'pri-p1'
  if (weight >= 40) return 'pri-p2'
  return 'pri-p3'
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

// ======================== 客户处理（路由跳转） ========================

function onProcessTask(taskId: string) {
  router.push({ name: 'customer-process', query: { taskId } })
}

function onAiMine() {
  opportunityStore.loadOpportunities(managerStore.currentId)
}

const reviewTips = ref<string[]>([])

// 从昨日回顾中提取提示文本
async function loadReviewTips() {
  try {
    const res = await api.getDailyReview(managerStore.currentId)
    const data = res.data
    if (data.has_review && data.sections) {
      const tips: string[] = []
      for (const sec of data.sections) {
        const content = sec.content || ''
        if (content && content.length > 5) {
          // 截取每条 section 的前 18 个字符作为提示
          const tip = content.length > 18 ? content.slice(0, 18) + '…' : content
          tips.push(tip)
          if (tips.length >= 2) break
        }
      }
      reviewTips.value = tips
    }
  } catch {
    reviewTips.value = []
  }
}

// 资讯早报数据
const digestBriefing = ref('')
const digestHeadlines = ref<{ title: string }[]>([])

async function loadDigestCard() {
  try {
    const res = await api.getDailyDigest()
    const data = res.data
    if (data.has_digest) {
      digestBriefing.value = data.briefing || ''
      digestHeadlines.value = data.headlines || []
    } else {
      digestBriefing.value = ''
      digestHeadlines.value = []
    }
  } catch {
    digestBriefing.value = ''
    digestHeadlines.value = []
  }
}

onMounted(() => {
  // 从后端加载日程和商机数据
  scheduleStore.loadTasks(managerStore.currentId)
  opportunityStore.loadOpportunities(managerStore.currentId)
  kpiStore.loadKpi(managerStore.currentId)
  loadReviewTips()
  loadDigestCard()
})

// 监听经理切换，重新加载数据
watch(() => managerStore.currentId, (newId) => {
  scheduleStore.loadTasks(newId)
  opportunityStore.loadOpportunities(newId)
  kpiStore.loadKpi(newId)
  loadReviewTips()
  loadDigestCard()
})
</script>

<style scoped>
.home-root {
  position: relative;
  display: flex;
  flex-direction: column;
}

/* ── 资讯早报卡片 ── */
.digest-teaser {
  background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 12px;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}
.digest-teaser-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.digest-teaser-icon { font-size: 16px; }
.digest-teaser-title { font-size: 13px; font-weight: 700; color: #fff; flex: 1; }
.digest-teaser-more { font-size: 11px; color: rgba(255,255,255,0.6); }
.digest-teaser-briefing { font-size: 12px; color: rgba(255,255,255,0.85); line-height: 1.6; margin-bottom: 8px; }
.digest-teaser-headlines { border-top: 1px solid rgba(255,255,255,0.15); padding-top: 8px; }
.digest-teaser-hl { font-size: 11px; color: rgba(255,255,255,0.7); padding: 3px 0; display: flex; align-items: flex-start; gap: 6px; line-height: 1.4; }
.digest-teaser-dot { width: 5px; height: 5px; border-radius: 50%; background: #f59e0b; margin-top: 5px; flex-shrink: 0; }

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

/* 客户名（pending 列表 / 卡片复用） */
.task-cust-name {
  font-weight: var(--fw-bold);
  color: var(--color-text-primary);
  font-size: var(--fs-small);
  white-space: nowrap;
  flex-shrink: 0;
  max-width: 64px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 子事件标签（小号，pending 列表 / 卡片复用） */
.task-sub-tag {
  font-size: 10px;
  font-weight: var(--fw-bold);
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
  flex-shrink: 0;
  line-height: 1.4;
}
.task-sub-more {
  font-size: 10px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
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
