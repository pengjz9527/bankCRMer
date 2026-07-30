<template>
  <div class="ai-summary-banner" @click="$router.push('/ai/schedule')">
    <div class="ai-main-row">
      <div class="ai-main">
        今日<strong>{{ taskCount }}项</strong>待办，预计总耗时 <strong>{{ totalHours }}小时</strong>
      </div>
      <span class="ai-review-btn" @click.stop="$router.push('/review')">
        <svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-refresh" /></svg> 昨日回顾 &gt;
      </span>
    </div>
    <div class="ai-sub-row">
      <span class="ai-sub-tag ai-sub-tag--am">
        <svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-sun" /></svg> 上午优先处理 高价值到期客户
      </span>
      <span class="ai-sub-tag ai-sub-tag--pm">
        <svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-cloud-sun" /></svg> 下午集中 联络超期客户
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  taskCount: number
  totalHours: number
}>()
</script>

<style scoped>
.ai-summary-banner {
  background: var(--color-card);
  border-radius: var(--radius-md);
  padding: 12px var(--sp-md);
  display: flex; flex-direction: column; gap: 6px;
  border: 1px solid var(--color-divider);
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  cursor: pointer;
}
.ai-main-row {
  display: flex; align-items: center; justify-content: space-between;
}
.ai-main {
  font-size: var(--fs-body); font-weight: var(--fw-medium);
  color: var(--color-text-primary); line-height: 1.5;
}
.ai-main strong {
  font-weight: var(--fw-bold); color: var(--color-primary);
}
.ai-sub-row {
  display: flex; flex-wrap: wrap; gap: 6px;
}
.ai-sub-tag {
  font-size: var(--fs-caption); padding: 2px 8px;
  border-radius: var(--radius-sm); display: inline-flex;
  align-items: center; gap: 4px;
}
.ai-sub-tag--am { background: #FFF0F0; color: #C0392B; }
.ai-sub-tag--pm { background: #F0F4FF; color: #3B5998; }
.ai-review-btn {
  font-size: var(--fs-caption); color: var(--color-primary);
  cursor: pointer; white-space: nowrap; flex-shrink: 0;
  display: inline-flex; align-items: center; gap: 4px;
  font-weight: var(--fw-bold);
}
</style>
