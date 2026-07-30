<template>
  <div class="task-card" :class="{ 'task-card--opportunity': isOpportunity }" @click="$emit('click', cardId)">
    <div class="card-top">
      <span class="time-seg" :class="'time-seg--' + period">
        <svg viewBox="0 0 24 24" class="ico ico--sm"><use :href="period === 'am' ? '#ico-sun' : '#ico-cloud-sun'" /></svg>
        {{ period === 'am' ? '上午' : '下午' }}
      </span>
      <span class="task-num">#{{ index }}</span>
      <span class="task-type-tag" :class="tagClass">{{ type }}</span>
    </div>
    <div class="card-body">
      <div class="task-summary">{{ summary }}</div>
    </div>
    <div class="task-time">
      <svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-clock" /></svg>
      <span class="time-range">{{ time }}</span>
      <span class="time-dur">{{ duration }}</span>
    </div>
    <div class="card-foot">
      <span class="count-badge">{{ customerCount }}人</span>
      <button class="btn-action" @click.stop="$emit('process', cardId)">立即处理</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  cardId: string
  index: number
  type: string
  period: string
  time: string
  duration: string
  tagClass: string
  summary: string
  customerCount: number
}>()

defineEmits<{
  click: [cardId: string]
  process: [cardId: string]
}>()

const isOpportunity = computed(() => props.tagClass === 'tag-opportunity')
</script>

<style scoped>
.task-card {
  width: 100%;
  background: var(--color-card); border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition: box-shadow var(--duration-fast);
  -webkit-tap-highlight-color: transparent;
  display: flex; flex-direction: column;
  padding: var(--sp-sm) var(--sp-md);
}
.task-card--opportunity {
  border: 1.5px solid var(--color-ai);
  box-shadow: 0 1px 4px rgba(108,92,231,0.12);
}
.card-top {
  display: flex; align-items: center; gap: var(--sp-xs);
  padding: var(--sp-sm) var(--sp-md) 0;
}
.time-seg {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: var(--radius-sm);
  font-size: var(--fs-caption); font-weight: var(--fw-bold);
  margin-bottom: var(--sp-xs);
}
.time-seg--am { background: #FFF0F0; color: #C0392B; }
.time-seg--pm { background: #F0F4FF; color: #3B5998; }
.task-num {
  font-family: var(--font-number); font-size: var(--fs-small);
  color: var(--color-text-tertiary); font-weight: var(--fw-bold);
  background: var(--color-bg); padding: 2px 7px; border-radius: 4px;
  letter-spacing: 0.5px;
}
.task-type-tag {
  font-size: var(--fs-small); font-weight: var(--fw-bold);
  padding: 2px 8px; border-radius: 4px; letter-spacing: 0.3px;
}
.card-body {
  padding: var(--sp-xs) var(--sp-md);
  flex: 1;
}
.task-summary {
  font-size: var(--fs-body); font-weight: var(--fw-medium);
  color: var(--color-text-primary); line-height: 1.45;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}
.task-time {
  display: flex; align-items: center; gap: 4px;
  padding: var(--sp-xs) var(--sp-md);
  background: var(--color-bg); margin: 0 var(--sp-md);
  border-radius: var(--radius-sm);
  font-size: var(--fs-caption); color: var(--color-text-secondary);
}
.time-range {
  font-family: var(--font-number); font-weight: var(--fw-bold);
  color: var(--color-primary); font-size: var(--fs-caption);
}
.time-dur {
  color: var(--color-text-tertiary); font-size: var(--fs-small); margin-left: auto;
}
.card-foot {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--sp-sm) var(--sp-md);
}
.count-badge {
  font-family: var(--font-number); font-size: var(--fs-caption);
  font-weight: var(--fw-bold); color: var(--color-text-secondary);
  background: var(--color-bg); padding: 3px 10px; border-radius: var(--radius-full);
  white-space: nowrap;
}
.btn-action {
  height: 30px; padding: 0 var(--sp-md); font-size: var(--fs-caption);
  font-weight: var(--fw-bold); border: none; border-radius: var(--radius-sm);
  background: var(--color-primary); color: #fff; cursor: pointer;
  white-space: nowrap;
  transition: all var(--duration-fast);
  -webkit-tap-highlight-color: transparent;
}
.btn-action:active { background: var(--color-primary-dark); transform: scale(0.96); }
</style>
