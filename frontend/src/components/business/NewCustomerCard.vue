<template>
  <div class="new-customer-card" :class="stateClass">
    <div class="nc-title">
      <svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-lightbulb" /></svg>
      新客拓展推荐
    </div>
    <div v-if="state === 'warn'" class="nc-warn-tag">
      <svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-warning" /></svg> 商机缺口较大，建议尽快拓展新客源
    </div>
    <div class="nc-desc">
      当前管户238位客户中，可挖掘商机已近上限。如需持续完成季度目标，建议<strong>拓展新客源</strong>。AI推荐新增50户目标客群。
    </div>
    <button class="btn-nc" @click="$router.push('/customer')">
      <svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-clipboard" /></svg> 获取AI推荐新客名单
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  state?: 'normal' | 'warn' | 'hidden'
}>(), {
  state: 'normal',
})

const stateClass = computed(() => ({
  'new-customer-card--warn': props.state === 'warn',
  'hidden': props.state === 'hidden',
}))
</script>

<style scoped>
.new-customer-card {
  background: var(--color-card); border-radius: var(--radius-md);
  box-shadow: var(--shadow-card); padding: var(--sp-md);
  border: 1px solid var(--color-divider);
}
.nc-title {
  font-size: var(--fs-body); font-weight: var(--fw-bold);
  color: var(--color-text-primary); margin-bottom: var(--sp-xs);
  display: flex; align-items: center; gap: var(--sp-xs);
}
.nc-desc {
  font-size: var(--fs-caption); color: var(--color-text-secondary); line-height: 1.5;
  margin-bottom: var(--sp-sm);
}
.btn-nc {
  width: 100%; height: 36px;
  background: transparent; color: var(--color-primary);
  border: 1px solid var(--color-primary); border-radius: var(--radius-sm);
  font-size: var(--fs-body); font-weight: var(--fw-bold);
  cursor: pointer; transition: all var(--duration-fast);
  -webkit-tap-highlight-color: transparent;
}
.btn-nc:active { background: var(--color-primary-light); }
.new-customer-card--warn {
  border-color: var(--color-warning);
  background: #FFFDF5;
}
.nc-warn-tag {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: var(--fs-caption); font-weight: var(--fw-bold);
  color: #B45309; background: var(--color-warning-light);
  padding: 3px 10px; border-radius: var(--radius-full);
  margin-bottom: var(--sp-sm);
}
.hidden { display: none; }
</style>
