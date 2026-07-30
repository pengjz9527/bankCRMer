<template>
  <div class="schedule-card" :class="cardClass">
    <!-- 卡片头 -->
    <div class="card-header">
      <div class="card-title-row">
        <svg viewBox="0 0 24 24" class="ico ico--md">
          <use :href="cardIcon" />
        </svg>
        <span class="card-name">{{ card.cardName }}</span>
        <span class="count-badge" :class="{ 'count-full': card.totalCount >= card.maxCapacity }">
          {{ card.totalCount }}/{{ card.maxCapacity }}
        </span>
      </div>
    </div>

    <!-- 可滚动内容区 -->
    <div class="card-body">
      <!-- 上午区 -->
      <div class="slot-section" v-if="card.morning.length > 0">
        <div class="slot-label slot-label--am">
          <svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-sun" /></svg>
          上午
        </div>
        <div class="task-list">
          <div
            v-for="task in card.morning"
            :key="task.taskId"
            class="task-row"
            :class="{ 'task-completed': task.status === 'completed' }"
          >
            <span class="task-type-tag" :class="getTypeTagClass(task.typeCode)">{{ task.typeName }}</span>
            <span class="task-text">
              <template v-if="task.custName">{{ task.custName }} · </template>
              {{ task.summary }}
            </span>
            <!-- 客户待办：开始处理按钮 -->
            <button
              v-if="card.cardType === 'customer' && task.status !== 'completed'"
              class="btn-process"
              @click.stop="$emit('process-task', task.taskId)"
            >开始处理</button>
            <!-- 商机待办：详情按钮 + 勾选 -->
            <template v-else-if="card.cardType === 'opportunity'">
              <button
                v-if="task.status !== 'completed'"
                class="btn-detail"
                @click.stop="$emit('opp-detail', task.taskId)"
              >详情</button>
              <span class="task-check" @click.stop="$emit('complete', task.taskId)" v-if="task.status !== 'completed'">
                <svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-check-circle" /></svg>
              </span>
            </template>
            <!-- 工作待办：勾选 -->
            <template v-else>
              <span class="task-check" @click.stop="$emit('complete', task.taskId)" v-if="task.status !== 'completed'">
                <svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-check-circle" /></svg>
              </span>
            </template>
            <span class="task-done" v-if="task.status === 'completed'">✓</span>
          </div>
        </div>
      </div>

      <!-- 下午区 -->
      <div class="slot-section" v-if="card.afternoon.length > 0">
        <div class="slot-label slot-label--pm">
          <svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-cloud-sun" /></svg>
          下午
        </div>
        <div class="task-list">
          <div
            v-for="task in card.afternoon"
            :key="task.taskId"
            class="task-row"
            :class="{ 'task-completed': task.status === 'completed' }"
          >
            <span class="task-type-tag" :class="getTypeTagClass(task.typeCode)">{{ task.typeName }}</span>
            <span class="task-text">
              <template v-if="task.custName">{{ task.custName }} · </template>
              {{ task.summary }}
            </span>
            <!-- 客户待办：开始处理按钮 -->
            <button
              v-if="card.cardType === 'customer' && task.status !== 'completed'"
              class="btn-process"
              @click.stop="$emit('process-task', task.taskId)"
            >开始处理</button>
            <!-- 商机待办：详情按钮 + 勾选 -->
            <template v-else-if="card.cardType === 'opportunity'">
              <button
                v-if="task.status !== 'completed'"
                class="btn-detail"
                @click.stop="$emit('opp-detail', task.taskId)"
              >详情</button>
              <span class="task-check" @click.stop="$emit('complete', task.taskId)" v-if="task.status !== 'completed'">
                <svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-check-circle" /></svg>
              </span>
            </template>
            <!-- 工作待办：勾选 -->
            <template v-else>
              <span class="task-check" @click.stop="$emit('complete', task.taskId)" v-if="task.status !== 'completed'">
                <svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-check-circle" /></svg>
              </span>
            </template>
            <span class="task-done" v-if="task.status === 'completed'">✓</span>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div class="slot-empty" v-if="card.morning.length === 0 && card.afternoon.length === 0">
        暂无待办
      </div>
    </div>

    <!-- 底部操作 -->
    <div class="card-footer" v-if="card.totalCount < card.maxCapacity">
      <span class="add-link" @click="$emit('add-task', card.cardType)">
        + 从待办池添加
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ScheduleCardData } from '../../stores/schedule'

const props = defineProps<{
  card: ScheduleCardData
}>()

defineEmits<{
  complete: [taskId: string]
  'add-task': [cardType: string]
  'process-task': [taskId: string]
  'opp-detail': [taskId: string]
}>()

const cardIcons: Record<string, string> = {
  customer: '#ico-users',
  opportunity: '#ico-lightbulb',
  work: '#ico-clipboard',
}

const cardIcon = computed(() => cardIcons[props.card.cardType] || '#ico-clipboard')

const cardClass = computed(() => ({
  'card--customer': props.card.cardType === 'customer',
  'card--opportunity': props.card.cardType === 'opportunity',
  'card--work': props.card.cardType === 'work',
}))

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
</script>

<style scoped>
.schedule-card {
  width: 100%;
  max-height: 300px;
  min-height: 200px;
  background: var(--color-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-body {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
  scrollbar-color: var(--color-border) transparent;
}

.card--opportunity {
  border: 1.5px solid var(--color-ai);
}

.card-header {
  padding: var(--sp-sm) var(--sp-md);
  border-bottom: 1px solid var(--color-border);
}

.card-title-row {
  display: flex;
  align-items: center;
  gap: var(--sp-xs);
}

.card-name {
  font-size: var(--fs-body);
  font-weight: var(--fw-bold);
  color: var(--color-text-primary);
  flex: 1;
}

.count-badge {
  font-family: var(--font-number);
  font-size: var(--fs-caption);
  font-weight: var(--fw-bold);
  color: var(--color-text-secondary);
  background: var(--color-bg);
  padding: 2px 8px;
  border-radius: var(--radius-full);
}
.count-badge.count-full {
  color: #C0392B;
  background: #FFF0F0;
}

.slot-section {
  padding: var(--sp-xs) var(--sp-md);
}

.slot-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--fs-caption);
  font-weight: var(--fw-bold);
  margin-bottom: var(--sp-xs);
}
.slot-label--am {
  background: #FFF0F0;
  color: #C0392B;
}
.slot-label--pm {
  background: #F0F4FF;
  color: #3B5998;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  font-size: var(--fs-small);
}

.task-row.task-completed {
  opacity: 0.5;
}

.task-type-tag {
  font-size: var(--fs-small);
  font-weight: var(--fw-bold);
  padding: 1px 6px;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
}

.task-text {
  flex: 1;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
}

.task-check {
  cursor: pointer;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
  opacity: 0.6;
  transition: opacity var(--duration-fast);
}
.task-check:hover {
  opacity: 1;
  color: var(--color-success);
}

.task-done {
  color: var(--color-success);
  font-weight: var(--fw-bold);
  flex-shrink: 0;
}

.btn-process {
  height: 26px;
  padding: 0 10px;
  font-size: 11px;
  font-weight: var(--fw-bold);
  border: none;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: #fff;
  cursor: pointer;
  flex-shrink: 0;
  white-space: nowrap;
}
.btn-process:active {
  opacity: 0.8;
}

.btn-detail {
  height: 26px;
  padding: 0 10px;
  font-size: 11px;
  font-weight: var(--fw-bold);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-primary);
  cursor: pointer;
  flex-shrink: 0;
  white-space: nowrap;
}
.btn-detail:active {
  opacity: 0.7;
}

.slot-empty {
  padding: var(--sp-lg);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--fs-small);
}

.card-footer {
  padding: var(--sp-sm) var(--sp-md);
  border-top: 1px solid var(--color-border);
  text-align: center;
}

.add-link {
  font-size: var(--fs-caption);
  color: var(--color-primary);
  cursor: pointer;
  font-weight: var(--fw-medium);
}
.add-link:active {
  opacity: 0.7;
}

/* 复用 TaskCard 的 tag 样式 */
.tag-danger { background: #FFF0F0; color: #C0392B; }
.tag-warning { background: #FFF8E1; color: #E67E22; }
.tag-muted { background: #F0F0F0; color: #666; }
.tag-success { background: #E8F8E8; color: #27AE60; }
.tag-opportunity { background: #F0E8FF; color: #6C5CE7; }
.tag-info { background: #E8F4FD; color: #2980B9; }
.tag-primary { background: #E8F0FE; color: #3366FF; }
</style>
