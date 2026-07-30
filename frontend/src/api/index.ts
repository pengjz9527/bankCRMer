/**
 * API 封装层 —— 对接 FastAPI 后端 (http://localhost:8008)
 */

const API_BASE = 'http://localhost:8008'

interface ApiResponse<T = any> {
  code: number
  data: T
  message?: string
}

async function request<T = any>(path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  const url = API_BASE + path
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

/** SSE 流式请求，返回 Response 以便逐行读取 */
function sseRequest(path: string, body: any): Promise<Response> {
  const url = API_BASE + path
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export const api = {
  /* ── 基础 ── */
  get<T = any>(path: string) { return request<T>(path) },
  post<T = any>(path: string, body: any) {
    return request<T>(path, { method: 'POST', body: JSON.stringify(body) })
  },
  put<T = any>(path: string, body: any) {
    return request<T>(path, { method: 'PUT', body: JSON.stringify(body) })
  },
  delete_<T = any>(path: string) {
    return request<T>(path, { method: 'DELETE' })
  },

  /* ── 日程 ── */
  getTasks(managerId: string, date: string) {
    return this.get(`/api/tasks?manager_id=${managerId}&date=${date}`)
  },
  saveProcessingRecord(body: Record<string, any>) {
    return this.post('/api/tasks/processing-records', body)
  },

  /* ── 商机 ── */
  getOpportunities(managerId: string) {
    return this.get(`/api/opportunities?manager_id=${managerId}`)
  },

  /* ── 客户 ── */
  getCustomers(managerId: string, size = 50) {
    return this.get(`/api/customers?manager_id=${managerId}&size=${size}`)
  },
  getCustomerBasic(cid: string) {
    return this.get(`/api/customers/${cid}/basic`)
  },
  getCustomerProfile(cid: string) {
    return this.get(`/api/customers/${cid}/profile`)
  },
  getCustomerFamily(cid: string) {
    return this.get(`/api/customers/${cid}/family`)
  },
  getCustomerEmployment(cid: string) {
    return this.get(`/api/customers/${cid}/employment`)
  },
  getCustomerWealth(cid: string) {
    return this.get(`/api/customers/${cid}/wealth/summary`)
  },
  getCustomerHoldings(cid: string) {
    return this.get(`/api/customers/${cid}/wealth/holdings`)
  },
  getCustomerFundFlow(cid: string) {
    return this.get(`/api/customers/${cid}/wealth/fund-flow`)
  },
  getCustomerSalary(cid: string) {
    return this.get(`/api/customers/${cid}/wealth/salary`)
  },
  getCustomerLoans(cid: string) {
    return this.get(`/api/customers/${cid}/credit/loans`)
  },
  getCustomerBehavior(cid: string) {
    return this.get(`/api/customers/${cid}/behavior/preferences`)
  },
  getCustomerBehaviorLogs(cid: string) {
    return this.get(`/api/customers/${cid}/behavior/logs`)
  },
  getCustomerRelations(cid: string) {
    return this.get(`/api/customers/${cid}/relations`)
  },
  getCustomerBenefits(cid: string) {
    return this.get(`/api/customers/${cid}/benefits`)
  },
  getCustomerActivities(cid: string) {
    return this.get(`/api/customers/${cid}/activities`)
  },

  /* ── 产品 ── */
  getProducts() {
    return this.get('/api/products')
  },

  /* ── 活动 ── */
  getActivities() {
    return this.get('/api/activities')
  },

  /* ── 客户洞察 ── */
  getCustomerInsights(managerId: string) {
    return this.get(`/api/customer-insights?manager_id=${managerId}`)
  },
  getCustomerInsightDetail(custId: string) {
    return this.get(`/api/customer-insights/${custId}`)
  },

  /* ── KPI 业绩看板 ── */
  getKpiDefinitions() {
    return this.get('/api/kpi/definitions')
  },
  getKpiSnapshot(managerId: string, period = 'month') {
    return this.get(`/api/kpi/snapshot?manager_id=${managerId}&period=${period}`)
  },
  getKpiTargets(managerId: string) {
    return this.get(`/api/kpi/targets?manager_id=${managerId}`)
  },
  getKpiRanking(managerId: string, period = 'quarter') {
    return this.get(`/api/kpi/ranking?manager_id=${managerId}&period=${period}`)
  },
  getKpiTrend(managerId: string) {
    return this.get(`/api/kpi/trend?manager_id=${managerId}`)
  },

  /* ── 作战包 ── */
  getBattlePackages(params?: { cust_id?: number; opp_id?: string }) {
    const parts: string[] = []
    if (params?.cust_id) parts.push(`cust_id=${params.cust_id}`)
    if (params?.opp_id) parts.push(`opp_id=${params.opp_id}`)
    const q = parts.length > 0 ? `?${parts.join('&')}` : ''
    return this.get(`/api/battle-packages${q}`)
  },
  getBattlePackageDetail(bpid: string) {
    return this.get(`/api/battle-packages/${bpid}`)
  },
  getBattlePackageClues(bpid: string) {
    return this.get(`/api/battle-packages/${bpid}/clues`)
  },
  useBattlePackage(bpid: string, body: Record<string, any>) {
    return this.post(`/api/battle-packages/${bpid}/use`, body)
  },
  generateBattlePackage(body: {
    cust_id: string | number
    mode: string
    opp_id?: string
    opportunity_info?: Record<string, any>
  }) {
    return this.post('/api/ai/battle-package/generate', body)
  },

  /* ── 日程排程 ── */
  getScheduleWeek(managerId: string, startDate?: string) {
    const q = startDate ? `?manager_id=${managerId}&start_date=${startDate}` : `?manager_id=${managerId}`
    return this.get(`/api/schedule/week${q}`)
  },
  getScheduleDay(managerId: string, date: string) {
    return this.get(`/api/schedule/${date}?manager_id=${managerId}`)
  },
  getSchedulePending(managerId: string, date: string) {
    return this.get(`/api/schedule/${date}/pending?manager_id=${managerId}`)
  },
  addTaskToSchedule(date: string, body: { manager_id: string; task_id: string; card_type: string }) {
    return this.post(`/api/schedule/${date}/add-task`, body)
  },
  completeScheduleTask(date: string, body: { manager_id: string; task_id: string }) {
    return this.post(`/api/schedule/${date}/complete`, body)
  },
  processScheduleTask(date: string, body: {
    manager_id: string
    task_id: string
    cust_id: number
    cust_name: string
    action: string
  }) {
    return this.post(`/api/schedule/${date}/process-task`, body)
  },
  returnTaskToPool(date: string, body: { manager_id: string; task_id: string }) {
    return this.post(`/api/schedule/${date}/return-to-pool`, body)
  },
  getMonthEvents(managerId: string, year: number, month: number) {
    return this.get(`/api/schedule/${year}/${month}/events?manager_id=${managerId}`)
  },
  adjustDaySchedule(date: string, body: Record<string, any>) {
    return this.post(`/api/schedule/${date}/adjust`, body)
  },

  /* ── AI 能力 ── */
  aiMine(managerId: string) {
    return this.post('/api/ai/opportunity/mining', { manager_id: managerId })
  },
  aiMineStream(managerId: string) {
    return sseRequest('/api/ai/opportunity/mining/stream', { manager_id: managerId })
  },
  aiGetOpportunityList(managerId: string) {
    return this.get(`/api/ai/opportunity/list?manager_id=${managerId}`)
  },
  aiGenerateBattlePackage(customerId: string, mode: string) {
    return this.post('/api/ai/battle-package/generate', { customer_id: customerId, mode })
  },
  aiBattlePackageStream(customerId: string, mode: string) {
    return sseRequest('/api/ai/battle-package/generate/stream', { customer_id: customerId, mode })
  },
  aiGenerateCustomerInsight(customerId: string) {
    return this.post('/api/ai/customer-insight/generate', { customer_id: customerId })
  },
}

/* ── Admin API：运营智能体管理后台 ── */
export const adminApi = {
  /* 定时任务管理 */
  getScheduledTasks() { return api.get('/api/admin/scheduled-tasks') },
  getTaskHistory(jobId: string, page = 1, size = 20) {
    return api.get(`/api/admin/scheduled-tasks/${jobId}/history?page=${page}&size=${size}`)
  },
  pauseTask(jobId: string) { return api.post(`/api/admin/scheduled-tasks/${jobId}/pause`, {}) },
  resumeTask(jobId: string) { return api.post(`/api/admin/scheduled-tasks/${jobId}/resume`, {}) },
  triggerTask(jobId: string) { return api.post(`/api/admin/scheduled-tasks/${jobId}/trigger`, {}) },

  /* 智能体配置管理 */
  getAgents() { return api.get('/api/admin/agents') },
  getAgentDetail(role: string) { return api.get(`/api/admin/agents/${role}`) },
  pauseAgent(role: string) { return api.post(`/api/admin/agents/${role}/pause`, {}) },
  resumeAgent(role: string) { return api.post(`/api/admin/agents/${role}/resume`, {}) },
  getAgentParams(role: string) { return api.get(`/api/admin/agents/${role}/params`) },
  updateAgentParams(role: string, params: any[]) {
    return api.put(`/api/admin/agents/${role}/params`, { params })
  },
  getAgentResults(role: string, params: Record<string, any> = {}) {
    const q = new URLSearchParams(params as any).toString()
    return api.get(`/api/admin/agents/${role}/results?${q}`)
  },
  async exportAgentResults(role: string, dateFrom?: string, dateTo?: string) {
    const qs = new URLSearchParams()
    if (dateFrom) qs.set('date_from', dateFrom)
    if (dateTo) qs.set('date_to', dateTo)
    const url = `http://localhost:8008/api/admin/agents/${role}/results/export?${qs.toString()}`
    const res = await fetch(url, { method: 'POST' })
    if (!res.ok) throw new Error('Export failed')
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${role}_results.csv`
    a.click()
    URL.revokeObjectURL(a.href)
  },
  async exportAgentRuns(agentRole?: string, status?: string, dateFrom?: string, dateTo?: string) {
    const qs = new URLSearchParams()
    if (agentRole) qs.set('agent_role', agentRole)
    if (status) qs.set('status', status)
    if (dateFrom) qs.set('date_from', dateFrom)
    if (dateTo) qs.set('date_to', dateTo)
    const url = `http://localhost:8008/api/admin/agents/runs/export?${qs.toString()}`
    const res = await fetch(url, { method: 'POST' })
    if (!res.ok) throw new Error('Export failed')
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'agent_runs.csv'
    a.click()
    URL.revokeObjectURL(a.href)
  },

  /* 运行监测 */
  getAgentRuns(params: Record<string, any> = {}) {
    const q = new URLSearchParams(params as any).toString()
    return api.get(`/api/admin/agents/runs?${q}`)
  },
  getAgentRunDetail(runId: number) { return api.get(`/api/admin/agents/runs/${runId}`) },
  getAuditLogs(params: Record<string, any> = {}) {
    const q = new URLSearchParams(params as any).toString()
    return api.get(`/api/admin/audit-logs?${q}`)
  },

  /* 费用分析 */
  getTokenStats(period = 'today') { return api.get(`/api/admin/agents/token-stats?period=${period}`) },
  getTokenRanking(period = 'today', limit = 5) {
    return api.get(`/api/admin/agents/token-ranking?period=${period}&limit=${limit}`)
  },
  getTokenTrend(days = 30) { return api.get(`/api/admin/agents/token-trend?days=${days}`) },
  getTokenDetails(params: Record<string, any> = {}) {
    const q = new URLSearchParams(params as any).toString()
    return api.get(`/api/admin/agents/token-details?${q}`)
  },

  /* 大模型配置管理 */
  getModels() { return api.get('/api/admin/models') },
  createModel(body: Record<string, any>) { return api.post('/api/admin/models', body) },
  updateModel(configKey: string, body: Record<string, any>) {
    return api.put(`/api/admin/models/${configKey}`, body)
  },
  deleteModel(configKey: string) { return api.delete_('/api/admin/models/' + configKey) },
  activateModel(configKey: string) { return api.post(`/api/admin/models/${configKey}/activate`, {}) },
}
