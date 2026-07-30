<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface Msg { type: string; title: string; detail: string; time: string; unread: boolean }
const messages = ref<Msg[]>([
  { type:'系统', title:'商机提醒', detail:'赵明辉代发到账预计明天到账，请及时配置', time:'10分钟前', unread:true },
  { type:'系统', title:'到期提醒', detail:'王建国定存将于7月18日到期（3天后）', time:'30分钟前', unread:true },
  { type:'AI', title:'客户洞察更新', detail:'陈晓燕近7日浏览理财产品8次，可推荐对接', time:'1小时前', unread:true },
  { type:'系统', title:'业绩通报', detail:'本月理财销售进度 70%，距月度目标差 180万', time:'2小时前', unread:false },
  { type:'系统', title:'活动通知', detail:'稳健投资·达标有礼 活动进行中（剩余20天）', time:'昨天', unread:false },
  { type:'AI', title:'流失预警', detail:'吴大伟疑似转投他行，流失概率72%，建议尽快挽留', time:'昨天', unread:false },
  { type:'系统', title:'产品更新', detail:'新增 悦享稳健理财 A 款 等3款产品上线', time:'3天前', unread:false },
])

function goBack() { router.back() }
const typeIcons: Record<string, string> = { '系统':'ico-megaphone', 'AI':'ico-robot' }
const typeColors: Record<string, string> = { '系统':'#2980b9', 'AI':'#6C5CE7' }
</script>

<template>
  <div class="msg-page">
    <div class="msg-header">
      <span class="msg-back" @click="goBack">←</span>
      <span class="msg-title">消息中心</span>
    </div>
    <div class="msg-body">
      <div v-for="m in messages" :key="m.title + m.time" class="msg-card" :class="{ unread: m.unread }">
        <div class="msg-card-left">
          <span class="msg-card-dot" v-if="m.unread"></span>
          <span class="msg-card-icon"><svg viewBox="0 0 24 24" class="ico ico--md"><use :href="'#' + (typeIcons[m.type] || 'ico-megaphone')" /></svg></span>
        </div>
        <div class="msg-card-info">
          <div class="msg-card-header">
            <span class="msg-card-type" :style="{ color: typeColors[m.type] || '#999' }">{{ m.type }}</span>
            <span class="msg-card-time">{{ m.time }}</span>
          </div>
          <div class="msg-card-title">{{ m.title }}</div>
          <div class="msg-card-detail">{{ m.detail }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.msg-page { min-height: 100%; background: #f8f8f8; padding-bottom: 40px; }
.msg-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.msg-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.msg-title { font-size: 16px; font-weight: 600; }
.msg-body { padding: 12px 16px; }

.msg-card {
  display: flex;
  gap: 12px;
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.msg-card.unread { background: #FFFBEB; }
.msg-card-left { position: relative; flex-shrink: 0; }
.msg-card-dot {
  position: absolute;
  top: 0;
  left: -4px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
}
.msg-card-icon { width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border-radius: 8px; background: var(--color-bg); color: var(--color-text-secondary); }
.msg-card-info { flex: 1; min-width: 0; }
.msg-card-header { display: flex; justify-content: space-between; margin-bottom: 2px; }
.msg-card-type { font-size: 10px; font-weight: 600; }
.msg-card-time { font-size: 10px; color: #bbb; }
.msg-card-title { font-size: 14px; font-weight: 600; margin-bottom: 2px; }
.msg-card-detail { font-size: 12px; color: var(--color-text-secondary); line-height: 1.4; }
</style>
