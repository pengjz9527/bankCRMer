<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const bpId = (route.params.id as string) || ''
const meetingState = ref<any>(null)
const newScenario = ref('')
const newResponse = ref('')
const showDevFeedback = ref(false)
const showConfirmation = ref(false)  // P9 客户确认要点
const confirmNotes = ref<string[]>([])
const tasks = ref([
  { text: '3天后联系确认意向', done: false },
])

onMounted(() => {
  const raw = sessionStorage.getItem('meeting_state_' + bpId)
  if (raw) {
    try { meetingState.value = JSON.parse(raw) } catch { }
  }
})

const durationMin = computed(() => {
  if (!meetingState.value) return 0
  return Math.floor((meetingState.value.duration || 0) / 60)
})

const cluesSummary = computed(() => {
  if (!meetingState.value?.clues) return ''
  const done = meetingState.value.clues.filter((c: any) => c.status === 'done')
  return done.map((c: any) => c.title).join('、') || '无'
})

function addTask() {
  tasks.value.push({ text: '', done: false })
}
function removeTask(idx: number) {
  tasks.value.splice(idx, 1)
}

function saveDeviation() {
  if (!newScenario.value.trim()) return
  appStore.showToast('偏离场景已保存，将用于后续作战包预制')
  showDevFeedback.value = false
  newScenario.value = ''
  newResponse.value = ''
}

function goToCustomer() {
  const name = meetingState.value?.custName
  if (name) router.push({ name: 'customer-detail', params: { id: name } })
}
function goHome() {
  sessionStorage.removeItem('meeting_state_' + bpId)
  router.push({ name: 'home' })
}

// P9 客户确认要点
function generateConfirmation() {
  confirmNotes.value = [
    '定存到期资金安排 — 您有一笔定存即将到期，向您介绍了多款稳健理财产品',
    '理财产品了解 — 根据您的风险偏好，推荐了2款适合的理财产品',
  ]
  showConfirmation.value = true
}
function closeConfirmation() { showConfirmation.value = false }
function shareConfirmation() {
  const text = confirmNotes.value.map((n, i) => `${i + 1}. ${n}`).join('\n')
  navigator.clipboard?.writeText(text).then(() => appStore.showToast('已复制，可分享给客户'))
}
</script>

<template>
  <div class="me-page">
    <div class="me-header">
      <span class="me-title">面谈结束</span>
      <span class="me-close" @click="goHome">✕</span>
    </div>

    <div class="me-body">
      <!-- 面谈小结 -->
      <div class="me-card">
        <div class="me-section-title">📊 面谈小结</div>
        <div class="me-summary-text">
          本次与{{ meetingState?.custName || '客户' }}面谈 {{ durationMin }} 分钟，
          覆盖 {{ meetingState?.cluesTotal || 0 }} 条线索中的 {{ meetingState?.cluesDone || 0 }} 条，
          涵盖：{{ cluesSummary }}
        </div>
      </div>

      <!-- 偏离补充 -->
      <div class="me-card">
        <div class="me-section-title">─ 偏离补充 ─</div>
        <div class="me-hint">面谈中出现了预制列表外的偏离，建议补充为新偏离场景：</div>
        <button class="me-add-btn" @click="showDevFeedback = !showDevFeedback">
          {{ showDevFeedback ? '收起' : '+ 补充新偏离场景' }}
        </button>
        <div v-if="showDevFeedback" class="me-feedback-form">
          <input v-model="newScenario" class="me-input" placeholder="客户原话..." />
          <textarea v-model="newResponse" class="me-textarea" placeholder="您是如何应对的..." rows="3"></textarea>
          <div class="me-feedback-actions">
            <button class="bp-btn bp-btn--primary" style="flex:none;padding:8px 24px" @click="saveDeviation">保存为新偏离分支</button>
            <span class="me-feedback-skip" @click="showDevFeedback = false">跳过</span>
          </div>
        </div>
      </div>

      <!-- 跟进任务 -->
      <div class="me-card">
        <div class="me-section-title">─ 跟进任务 ─</div>
        <div v-for="(t, i) in tasks" :key="i" class="me-task-row">
          <input type="checkbox" v-model="t.done" class="me-checkbox" />
          <input v-model="t.text" class="me-task-input" placeholder="任务描述..." />
          <span class="me-task-del" @click="removeTask(i)">✕</span>
        </div>
        <button class="me-add-btn" @click="addTask">+ 添加自定义任务</button>
      </div>

      <!-- 客户标签 -->
      <div class="me-card">
        <div class="me-section-title">📌 更新客户标签</div>
        <div class="me-tag-list">
          <span class="me-tag me-tag--active">意向:理财</span>
          <span class="me-tag me-tag--active">意向:基金</span>
          <span class="me-tag">近期大额支出</span>
          <span class="me-tag">风险偏好变化</span>
        </div>
      </div>
    </div>

    <!-- 底部 -->
    <div class="me-bottom">
      <button class="bp-btn bp-btn--ghost" style="flex:0.8" @click="generateConfirmation">生成确认要点</button>
      <button class="bp-btn bp-btn--outline" @click="goToCustomer">查看画像</button>
      <button class="bp-btn bp-btn--primary" @click="goHome">返回工作台</button>
    </div>

    <!-- ===== P9 客户确认要点（全屏浮层） ===== -->
    <Transition name="sheet-fade">
      <div v-if="showConfirmation" class="me-overlay">
        <div class="me-confirm-page">
          <div class="me-confirm-notice">🤝 当前为确认模式</div>
          <div class="me-confirm-body">
            <div class="me-confirm-section">
              <div class="me-confirm-label">──── 今日交流要点 ────</div>
            </div>
            <div class="me-confirm-section">
              <div class="me-section-title">📋 本次交流主要内容</div>
              <div
                v-for="(note, ni) in confirmNotes"
                :key="ni"
                class="me-confirm-note"
              >
                <span class="me-confirm-num">{{ ni + 1 }}.</span>
                <span>{{ note }}</span>
              </div>
            </div>
            <div class="me-confirm-section">
              <div class="me-section-title">✅ 后续事项确认</div>
              <div v-for="(t, ti) in tasks" :key="ti" class="me-confirm-task">
                <span class="me-confirm-check">☐</span>
                <span>{{ t.text }}</span>
              </div>
            </div>
          </div>
          <div class="me-confirm-bottom">
            <button class="bp-btn bp-btn--ghost" style="flex:0.8" @click="closeConfirmation">仅我确认</button>
            <button class="bp-btn bp-btn--outline" @click="shareConfirmation">分享给客户</button>
            <button class="bp-btn bp-btn--ghost" style="flex:0.6" @click="closeConfirmation">关闭</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.me-page { min-height: 100%; background: var(--color-bg); padding-bottom: 80px; }
.me-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; background: #fff; border-bottom: 1px solid #eee;
  position: sticky; top: 0; z-index: 5;
}
.me-title { font-size: 16px; font-weight: 600; }
.me-close { font-size: 18px; cursor: pointer; color: #999; }

.me-body { padding: 12px 16px; }
.me-card {
  background: #fff; border-radius: 10px; padding: 14px 16px;
  margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.me-section-title { font-size: 13px; font-weight: 600; margin-bottom: 10px; color: var(--color-text-secondary); }
.me-summary-text { font-size: 14px; line-height: 1.7; color: var(--color-text); }
.me-hint { font-size: 12px; color: #999; margin-bottom: 8px; }
.me-add-btn {
  border: none; background: none; color: var(--color-primary);
  font-size: 12px; cursor: pointer; padding: 4px 0;
}

.me-feedback-form { margin-top: 10px; }
.me-input, .me-textarea {
  width: 100%; border: 1px solid #eee; border-radius: 8px;
  padding: 10px; font-size: 13px; box-sizing: border-box; margin-bottom: 8px;
  font-family: inherit;
}
.me-input:focus, .me-textarea:focus { outline: none; border-color: var(--color-primary); }
.me-textarea { resize: none; }
.me-feedback-actions { display: flex; align-items: center; gap: 12px; }
.me-feedback-skip { font-size: 12px; color: #999; cursor: pointer; }

.me-task-row {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 0; border-bottom: 1px solid #f5f5f5;
}
.me-checkbox { width: 18px; height: 18px; accent-color: var(--color-primary); cursor: pointer; }
.me-task-input {
  flex: 1; border: none; font-size: 13px; padding: 4px 0;
  background: transparent; outline: none;
}
.me-task-del { font-size: 14px; color: #ccc; cursor: pointer; padding: 4px; }

.me-tag-list { display: flex; gap: 8px; flex-wrap: wrap; }
.me-tag {
  padding: 5px 12px; border-radius: 16px; font-size: 11px;
  background: #f0f0f0; cursor: pointer;
}
.me-tag--active { background: var(--color-primary); color: #fff; }

.me-bottom {
  display: flex; gap: 10px; padding: 10px 16px;
  background: #fff; border-top: 1px solid #eee;
  position: sticky; bottom: 0; z-index: 10;
  box-shadow: 0 -2px 8px rgba(0,0,0,0.04);
}

/* P9 Confirmation Overlay */
.me-overlay {
  position: fixed; inset: 0; z-index: 200;
  display: flex; flex-direction: column;
}
.me-confirm-page {
  flex: 1; background: #f7faf7; display: flex; flex-direction: column;
}
.me-confirm-notice {
  text-align: center; font-size: 14px; color: #155724;
  background: #D4EDDA; padding: 10px; font-weight: 600;
}
.me-confirm-body {
  flex: 1; padding: 16px 20px; overflow-y: auto;
}
.me-confirm-section {
  background: #fff; border-radius: 10px; padding: 14px 16px;
  margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.me-confirm-label {
  text-align: center; font-size: 14px; font-weight: 600;
  color: var(--color-text-secondary);
}
.me-confirm-note {
  display: flex; gap: 8px; padding: 8px 0; font-size: 14px;
  line-height: 1.6; color: var(--color-text);
  border-bottom: 1px solid #f5f5f5;
}
.me-confirm-note:last-child { border-bottom: none; }
.me-confirm-num { color: var(--color-primary); font-weight: 600; flex-shrink: 0; }
.me-confirm-task {
  display: flex; gap: 10px; padding: 6px 0; font-size: 14px;
  color: var(--color-text);
}
.me-confirm-check { color: var(--color-primary); font-size: 16px; }
.me-confirm-bottom {
  display: flex; gap: 10px; padding: 10px 16px;
  background: #fff; border-top: 1px solid #eee;
}

/* Transitions */
.sheet-fade-enter-active, .sheet-fade-leave-active { transition: opacity 0.25s; }
.sheet-fade-enter-from, .sheet-fade-leave-to { opacity: 0; }
</style>
