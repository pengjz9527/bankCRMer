<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const oppId = (route.query.oppId as string) || 'd1'

function selectMode(mode: string) {
  router.push({ name: 'battle-package', query: { id: oppId, mode } })
}
function goBack() { router.back() }
</script>

<template>
  <div class="bpm-page">
    <div class="bpm-header">
      <span class="bpm-back" @click="goBack">←</span>
      <span class="bpm-title">选择作战包模式</span>
    </div>
    <div class="bpm-body">
      <div class="bpm-hint">请选择 AI 生成作战包的模式：</div>

      <div class="bpm-card" @click="selectMode('full')">
        <div class="bpm-card-icon"><svg viewBox="0 0 24 24" class="ico ico--lg"><use href="#ico-clipboard" /></svg></div>
        <div class="bpm-card-info">
          <div class="bpm-card-title">完整作战包</div>
          <div class="bpm-card-desc">包含客户画像分析、面谈目标、产品推荐、话术建议、注意事项等全部内容</div>
        </div>
        <span class="bpm-card-arrow">›</span>
      </div>

      <div class="bpm-card" @click="selectMode('quick')">
        <div class="bpm-card-icon"><svg viewBox="0 0 24 24" class="ico ico--lg"><use href="#ico-lightning" /></svg></div>
        <div class="bpm-card-info">
          <div class="bpm-card-title">快速话术</div>
          <div class="bpm-card-desc">仅生成核心话术和产品推荐，适合面谈前快速准备</div>
        </div>
        <span class="bpm-card-arrow">›</span>
      </div>

      <div class="bpm-card" @click="selectMode('product')">
        <div class="bpm-card-icon"><svg viewBox="0 0 24 24" class="ico ico--lg"><use href="#ico-lightbulb" /></svg></div>
        <div class="bpm-card-info">
          <div class="bpm-card-title">仅产品推荐</div>
          <div class="bpm-card-desc">仅生成针对该客户的个性化产品组合建议</div>
        </div>
        <span class="bpm-card-arrow">›</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bpm-page { min-height: 100%; background: #f8f8f8; padding-bottom: 40px; }
.bpm-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.bpm-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.bpm-title { font-size: 16px; font-weight: 600; }
.bpm-body { padding: 16px; }
.bpm-hint { font-size: 13px; color: var(--color-text-secondary); margin-bottom: 16px; }

.bpm-card {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  cursor: pointer;
  gap: 12px;
}
.bpm-card:active { background: #fafafa; }
.bpm-card-icon { width: 40px; height: 40px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; border-radius: 10px; background: var(--color-bg); color: var(--color-text-primary); }
.bpm-card-info { flex: 1; }
.bpm-card-title { font-size: 15px; font-weight: 600; margin-bottom: 4px; }
.bpm-card-desc { font-size: 12px; color: var(--color-text-secondary); line-height: 1.5; }
.bpm-card-arrow { font-size: 20px; color: #ccc; }
</style>
