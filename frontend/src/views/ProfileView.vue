<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useManagerStore } from '@/stores/manager'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const managerStore = useManagerStore()
const appStore = useAppStore()

// 每位经理的扩展信息
const managerProfiles: Record<string, any> = {
  'M001': {
    branch: '合肥分行营业部', phone: '139****5678', email: 'lijianguo@example.com',
    title: '客户经理', teamSize: 3, totalCustomers: 247, totalAum: 1250.8, joinDate: '2018-03',
  },
  'M002': {
    branch: '合肥分行营业部', phone: '138****1234', email: 'wangfang@example.com',
    title: '资深客户经理', teamSize: 4, totalCustomers: 312, totalAum: 1680.5, joinDate: '2015-07',
  },
  'M003': {
    branch: '芜湖分行营业部', phone: '137****8765', email: 'zhangwei@example.com',
    title: '客户经理', teamSize: 2, totalCustomers: 189, totalAum: 890.3, joinDate: '2020-01',
  },
}

const profile = computed(() => ({
  name: managerStore.currentName,
  id: managerStore.currentId,
  ...(managerProfiles[managerStore.currentId] || managerProfiles['M001']),
}))

function goTo(path: string) {
  if (path === 'profile') {
    appStore.showToast('个人信息功能开发中')
    return
  }
  router.push({ name: path })
}
</script>

<template>
  <div class="profile">
    <!-- Avatar Card -->
    <div class="pf-top-card">
      <div class="pf-avatar">
        <span>{{ profile.name?.charAt(0) }}</span>
      </div>
      <div class="pf-name">{{ profile.name }}</div>
      <div class="pf-title">{{ profile.title }} · {{ profile.branch }}</div>
      <div class="pf-stats">
        <div class="pf-stat">
          <div class="pf-stat-val">{{ profile.totalCustomers }}</div>
          <div class="pf-stat-label">管户数</div>
        </div>
        <div class="pf-stat">
          <div class="pf-stat-val">{{ profile.totalAum.toFixed(1) }}万</div>
          <div class="pf-stat-label">总AUM</div>
        </div>
        <div class="pf-stat">
          <div class="pf-stat-val">{{ profile.teamSize }}</div>
          <div class="pf-stat-label">团队成员</div>
        </div>
      </div>
    </div>

    <!-- Menu List -->
    <div class="pf-menu">
      <div class="pf-menu-item" @click="goTo('profile')">
        <span class="pf-menu-icon"><svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-user" /></svg></span>
        <span class="pf-menu-label">个人信息</span>
        <span class="pf-menu-arrow">›</span>
      </div>
      <div class="pf-menu-item" @click="goTo('messages')">
        <span class="pf-menu-icon"><svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-bell" /></svg></span>
        <span class="pf-menu-label">消息中心</span>
        <span class="pf-menu-arrow">›</span>
      </div>
      <div class="pf-menu-item" @click="goTo('performance')">
        <span class="pf-menu-icon"><svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-chart" /></svg></span>
        <span class="pf-menu-label">业绩看板</span>
        <span class="pf-menu-arrow">›</span>
      </div>
      <div class="pf-menu-item" @click="goTo('meetings')">
        <span class="pf-menu-icon"><svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-edit" /></svg></span>
        <span class="pf-menu-label">会议记录</span>
        <span class="pf-menu-arrow">›</span>
      </div>
      <div class="pf-menu-item" @click="goTo('ai-schedule')">
        <span class="pf-menu-icon"><svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-calendar" /></svg></span>
        <span class="pf-menu-label">AI 日程设置</span>
        <span class="pf-menu-arrow">›</span>
      </div>
      <div class="pf-menu-item" @click="goTo('search')">
        <span class="pf-menu-icon"><svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-search" /></svg></span>
        <span class="pf-menu-label">全局搜索</span>
        <span class="pf-menu-arrow">›</span>
      </div>
    </div>

    <!-- Contact Info -->
    <div class="pf-contact">
      <div class="pf-contact-item">
        <span class="pf-contact-icon"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-mobile" /></svg></span>
        <span>{{ profile.phone }}</span>
      </div>
      <div class="pf-contact-item">
        <span class="pf-contact-icon"><svg viewBox="0 0 24 24" class="ico ico--sm"><use href="#ico-email" /></svg></span>
        <span>{{ profile.email }}</span>
      </div>
    </div>

    <!-- Logout -->
    <div class="pf-logout" @click="router.push('/')">
      退出登录
    </div>
  </div>
</template>

<style scoped>
.profile {
  min-height: 100%;
  background: var(--color-bg);
  padding-bottom: 80px;
}

.pf-top-card {
  background: linear-gradient(135deg, var(--color-primary) 0%, #c0392b 100%);
  padding: 30px 20px 20px;
  text-align: center;
  color: #fff;
}

.pf-avatar {
  width: 68px;
  height: 68px;
  border-radius: 50%;
  background: rgba(255,255,255,0.25);
  margin: 0 auto 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
}

.pf-name { font-size: 20px; font-weight: 700; margin-bottom: 2px; }
.pf-title { font-size: 13px; opacity: 0.85; margin-bottom: 16px; }

.pf-stats {
  display: flex;
  justify-content: center;
  gap: 32px;
}
.pf-stat { text-align: center; }
.pf-stat-val { font-size: 20px; font-weight: 700; }
.pf-stat-label { font-size: 11px; opacity: 0.75; margin-top: 2px; }

.pf-menu {
  background: #fff;
  margin: 12px 16px;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.pf-menu-item {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
}
.pf-menu-item:last-child { border-bottom: none; }
.pf-menu-item:active { background: #fafafa; }

.pf-menu-icon { width: 24px; margin-right: 12px; flex-shrink: 0; display: flex; align-items: center; color: var(--color-text-secondary); }
.pf-menu-label { flex: 1; font-size: 14px; color: var(--color-text); }
.pf-menu-arrow { font-size: 20px; color: #ccc; }

.pf-contact {
  background: #fff;
  margin: 0 16px 12px;
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.pf-contact-item {
  display: flex;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.pf-contact-icon { width: 20px; margin-right: 10px; display: inline-flex; align-items: center; color: var(--color-text-secondary); }

.pf-logout {
  margin: 12px 16px;
  padding: 14px;
  background: #fff;
  border-radius: 10px;
  text-align: center;
  font-size: 14px;
  color: var(--color-text-secondary);
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.pf-logout:active { background: #fafafa; }
</style>
