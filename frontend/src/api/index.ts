/**
 * API 封装层 —— 对接 FastAPI 后端（Vite 代理 / Nginx 反向代理）
 */

const API_BASE = ''

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
  getOpportunityDetail(oppId: string) {
    return this.get(`/api/opportunity/${oppId}`)
  },
  updateOpportunityStatus(oppId: string, status: string) {
    return this.put(`/api/opportunity/${oppId}/status`, { status })
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

  /* ── 昨日回顾 ── */
  getDailyReview(managerId: string) {
    return this.get(`/api/daily-review?manager_id=${managerId}`)
  },

  /* ── 资讯摘要 ── */
  getDailyDigest() {
    return this.get('/api/daily-digest')
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
  getBattlePackages(params?: { cust_id?: number; opp_id?: string; task_id?: string; status?: string }) {
    const parts: string[] = []
    if (params?.cust_id) parts.push(`cust_id=${params.cust_id}`)
    if (params?.opp_id) parts.push(`opp_id=${params.opp_id}`)
    if (params?.task_id) parts.push(`task_id=${params.task_id}`)
    if (params?.status) parts.push(`status=${params.status}`)
    const q = parts.length > 0 ? `?${parts.join('&')}` : ''
    return this.get(`/api/battle-packages${q}`)
  },
  getBattlePackageDetail(bpid: string) {
    return this.get(`/api/battle-packages/${bpid}`)
  },
  getBattlePackageClues(bpid: string) {
    return this.get(`/api/battle-packages/${bpid}/clues`)
  },
  getLinkedBattlePackages(oppIds: string[]) {
    return this.get(`/api/battle-packages/linked?opp_ids=${oppIds.join(',')}`)
  },
  useBattlePackage(bpid: string, body: Record<string, any>) {
    return this.post(`/api/battle-packages/${bpid}/use`, body)
  },
  generateBattlePackage(body: {
    cust_id: string | number
    mode: string
    visit_context?: {
      task_id?: string
      opp_ids?: string[]
      care_items?: { type_code: string; type_name: string; summary: string }[]
    }
    force?: boolean
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
  confirmCompleteScheduleTask(date: string, body: {
    manager_id: string
    task_id: string
    cust_id: number
    cust_name: string
  }) {
    return this.post(`/api/schedule/${date}/confirm-complete`, body)
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
  aiGetOpportunityList(managerId?: string, custId?: number) {
    const params = new URLSearchParams()
    if (managerId) params.set('manager_id', managerId)
    if (custId) params.set('cust_id', String(custId))
    return this.get(`/api/ai/opportunity/list?${params.toString()}`)
  },
  aiGenerateBattlePackage(customerId: string | number, visitContext?: {
    task_id?: string
    opp_ids?: string[]
    care_items?: { type_code: string; type_name: string; summary: string }[]
  }) {
    return this.post('/api/ai/battle-package/generate', {
      cust_id: customerId,
      mode: '标准版',
      visit_context: visitContext,
    })
  },
  aiBattlePackageStream(customerId: string | number, visitContext?: Record<string, any>) {
    return sseRequest('/api/ai/battle-package/generate/stream', {
      cust_id: customerId,
      mode: '标准版',
      visit_context: visitContext,
    })
  },
  aiGenerateCustomerInsight(customerId: string) {
    return this.post('/api/ai/customer-insight/generate', { customer_id: customerId })
  },
  aiQaAsk(question: string, managerId: string) {
    return this.post('/api/ai/qa/ask', { question, manager_id: managerId })
  },

  /* ── 面谈口述转写 ── */
  async aiTranscribeDictation(audioBlob: Blob, managerId: string, opts?: {
    custName?: string
    custId?: string | number
    bpId?: string
    oppId?: string
    meetingId?: number
  }) {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'dictation.webm')
    formData.append('manager_id', managerId)
    if (opts?.custName) formData.append('cust_name', opts.custName)
    if (opts?.custId) formData.append('cust_id', String(opts.custId))
    if (opts?.bpId) formData.append('bp_id', opts.bpId)
    if (opts?.oppId) formData.append('opp_id', opts.oppId)
    if (opts?.meetingId) formData.append('meeting_id', String(opts.meetingId))
    const url = API_BASE + '/api/ai/dictation/transcribe'
    const res = await fetch(url, { method: 'POST', body: formData })
    if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`)
    return res.json()
  },

  /* ── 面谈记录查询 ── */
  getMeetingRecords(params?: {
    manager_id?: string
    cust_name?: string
    cust_id?: number
    status?: string
    page?: number
    page_size?: number
  }) {
    const q = new URLSearchParams()
    if (params?.manager_id) q.set('manager_id', params.manager_id)
    if (params?.cust_name) q.set('cust_name', params.cust_name)
    if (params?.cust_id) q.set('cust_id', String(params.cust_id))
    if (params?.status) q.set('status', params.status)
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    const qs = q.toString()
    return this.get(`/api/meeting/records${qs ? '?' + qs : ''}`)
  },
  getMeetingRecordDetail(id: number) {
    return this.get(`/api/meeting/records/${id}`)
  },
  createMeetingRecord(opts: {
    manager_id?: string
    cust_name?: string
    cust_id?: string | number
    bp_id?: string
    opp_id?: string
  }) {
    const formData = new FormData()
    if (opts.manager_id) formData.append('manager_id', opts.manager_id)
    if (opts.cust_name) formData.append('cust_name', opts.cust_name)
    if (opts.cust_id) formData.append('cust_id', String(opts.cust_id))
    if (opts.bp_id) formData.append('bp_id', opts.bp_id)
    if (opts.opp_id) formData.append('opp_id', opts.opp_id)
    const url = API_BASE + '/api/meeting/records'
    return fetch(url, { method: 'POST', body: formData }).then(r => r.json())
  },

  /* ── AI 对话路由 (RouterAgent) — 统一对话入口 ── */
  aiChat(question: string, managerId: string, channel = 'home', history: any[] = []) {
    return this.post('/api/ai/chat', { question, manager_id: managerId, channel, history })
  },
}

/* ── Admin API：运营智能体管理后台 ── */
export const adminApi = {
  /* 定时任务管理 */
  getScheduledTasks() { return api.get('/api/admin/scheduled-tasks') },
  getTaskHistory(jobId: string, page = 1, size = 20) {
    return api.get(`/api/admin/scheduled-tasks/${jobId}/history?page=${page}&size=${size}`)
  },
  getTaskHistoryDetail(historyId: number) {
    return api.get(`/api/admin/scheduled-tasks/history/${historyId}/detail`)
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
    const url = `${API_BASE}/api/admin/agents/${role}/results/export?${qs.toString()}`
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
    const url = `${API_BASE}/api/admin/agents/runs/export?${qs.toString()}`
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
