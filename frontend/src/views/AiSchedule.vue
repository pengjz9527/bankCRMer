<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const enableAutoSchedule = ref(true)
const preferMorning = ref(true)
const bufferTime = ref(15)
const maxMeetingsPerDay = ref(6)

function goBack() { router.back() }
</script>

<template>
  <div class="as-page">
    <div class="as-header">
      <span class="as-back" @click="goBack">←</span>
      <span class="as-title">AI 日程设置</span>
    </div>
    <div class="as-body">
      <div class="as-section">
        <div class="as-section-title"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-robot" /></svg> 智能排程</div>
        <div class="as-row">
          <span class="as-label">自动排程</span>
          <div class="as-toggle" :class="{ on: enableAutoSchedule }" @click="enableAutoSchedule = !enableAutoSchedule">
            <div class="as-toggle-knob"></div>
          </div>
        </div>
      </div>

      <div class="as-section">
        <div class="as-section-title"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-clock" /></svg> 时间偏好</div>
        <div class="as-row">
          <span class="as-label">偏好上午</span>
          <div class="as-toggle" :class="{ on: preferMorning }" @click="preferMorning = !preferMorning">
            <div class="as-toggle-knob"></div>
          </div>
        </div>
        <div class="as-row">
          <span class="as-label">缓冲时间</span>
          <select v-model="bufferTime" class="as-select">
            <option :value="0">无缓冲</option>
            <option :value="15">15 分钟</option>
            <option :value="30">30 分钟</option>
          </select>
        </div>
        <div class="as-row">
          <span class="as-label">每日最多面谈</span>
          <select v-model="maxMeetingsPerDay" class="as-select">
            <option :value="4">4 场</option>
            <option :value="5">5 场</option>
            <option :value="6">6 场</option>
            <option :value="8">8 场</option>
          </select>
        </div>
      </div>

      <div class="as-section">
        <div class="as-section-title"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-chart" /></svg> 当前排程概况</div>
        <div class="as-stats">
          <div class="as-stat">
            <div class="as-stat-val">6</div>
            <div class="as-stat-label">今日待办</div>
          </div>
          <div class="as-stat">
            <div class="as-stat-val">2</div>
            <div class="as-stat-label">待排程会议</div>
          </div>
          <div class="as-stat">
            <div class="as-stat-val">85%</div>
            <div class="as-stat-label">排程效率评分</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.as-page { min-height: 100%; background: #f8f8f8; padding-bottom: 40px; }
.as-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.as-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.as-title { font-size: 16px; font-weight: 600; }
.as-body { padding: 12px 16px; }

.as-section { background: #fff; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.as-section-title { font-size: 14px; font-weight: 600; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }

.as-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f5f5f5; }
.as-row:last-child { border-bottom: none; }
.as-label { font-size: 13px; color: var(--color-text); }
.as-select { padding: 6px 10px; border: 1px solid #e0e0e0; border-radius: 6px; font-size: 12px; background: #fff; outline: none; }

.as-toggle {
  width: 44px;
  height: 24px;
  border-radius: 12px;
  background: #ddd;
  cursor: pointer;
  position: relative;
  transition: background 0.2s;
}
.as-toggle.on { background: var(--color-primary); }
.as-toggle-knob {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fff;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
.as-toggle.on .as-toggle-knob { transform: translateX(20px); }

.as-stats { display: flex; gap: 16px; }
.as-stat { flex: 1; text-align: center; }
.as-stat-val { font-size: 22px; font-weight: 700; color: var(--color-primary); }
.as-stat-label { font-size: 11px; color: var(--color-text-secondary); margin-top: 2px; }
</style>
