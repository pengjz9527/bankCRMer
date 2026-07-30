import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
    },
    {
      path: '/schedule/all',
      name: 'schedule-all',
      component: () => import('../views/ScheduleAll.vue'),
    },
    {
      path: '/opportunity',
      name: 'opportunity',
      component: () => import('../views/OpportunityList.vue'),
    },
    {
      path: '/opportunity/:id',
      name: 'opportunity-detail',
      component: () => import('../views/OpportunityDetail.vue'),
    },
    {
      path: '/battle-packages',
      name: 'battle-package-list',
      component: () => import('../views/BattlePackageList.vue'),
    },
    {
      path: '/battle-package/mode',
      name: 'battle-package-mode',
      component: () => import('../views/BattlePackageMode.vue'),
    },
    {
      path: '/battle-package/:id',
      name: 'battle-package',
      component: () => import('../views/BattlePackage.vue'),
    },
    {
      path: '/customer',
      name: 'customer-list',
      component: () => import('../views/CustomerList.vue'),
    },
    {
      path: '/customer/:id',
      name: 'customer-detail',
      component: () => import('../views/CustomerDetail.vue'),
    },
    {
      path: '/product',
      name: 'product-search',
      component: () => import('../views/ProductSearch.vue'),
    },
    {
      path: '/product/compare',
      name: 'product-compare',
      component: () => import('../views/ProductCompare.vue'),
    },
    {
      path: '/product/:id',
      name: 'product-detail',
      component: () => import('../views/ProductDetail.vue'),
    },
    {
      path: '/performance',
      name: 'performance',
      component: () => import('../views/PerformanceView.vue'),
    },
    {
      path: '/review',
      name: 'review',
      component: () => import('../views/YesterdayReview.vue'),
    },
    {
      path: '/meetings',
      name: 'meetings',
      component: () => import('../views/MeetingRecords.vue'),
    },
    {
      path: '/meetings/detail',
      name: 'meeting-detail',
      component: () => import('../views/MeetingDetail.vue'),
    },
    {
      path: '/ai/chat',
      name: 'ai-chat',
      component: () => import('../views/AiChat.vue'),
    },
    {
      path: '/ai/schedule',
      name: 'ai-schedule',
      component: () => import('../views/AiSchedule.vue'),
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/ProfileView.vue'),
    },
    {
      path: '/messages',
      name: 'messages',
      component: () => import('../views/MessageCenter.vue'),
    },
    {
      path: '/customer-insights',
      name: 'customer-insights',
      component: () => import('../views/CustomerInsights.vue'),
    },
    {
      path: '/search',
      name: 'search',
      component: () => import('../views/GlobalSearch.vue'),
    },
    {
      path: '/meeting/:id',
      name: 'meeting',
      component: () => import('../views/FaceToFace.vue'),
    },
    {
      path: '/meeting/:id/end',
      name: 'meeting-end',
      component: () => import('../views/MeetingEnd.vue'),
    },
    {
      path: '/admin',
      component: () => import('../views/admin/AdminLayout.vue'),
      children: [
        { path: '', name: 'admin-dashboard', component: () => import('../views/admin/AdminDashboard.vue') },
        { path: 'tasks', name: 'admin-tasks', component: () => import('../views/admin/ScheduledTaskManager.vue') },
        { path: 'agents', name: 'admin-agents', component: () => import('../views/admin/AgentConfigManager.vue') },
        { path: 'monitor', name: 'admin-monitor', component: () => import('../views/admin/AgentMonitor.vue') },
        { path: 'cost', name: 'admin-cost', component: () => import('../views/admin/CostAnalysis.vue') },
        { path: 'models', name: 'admin-models', component: () => import('../views/admin/ModelConfigManager.vue') },
      ],
    },
  ],
})

export default router
