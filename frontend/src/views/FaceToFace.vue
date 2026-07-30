<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const bpId = (route.params.id as string) || ''
const loading = ref(true)
const bpData = ref<any>(null)
const clues = ref<any[]>([])

// 面谈状态
const timer = ref(0)
const timerRunning = ref(true)
let timerInterval: any = null
const currentClueIdx = ref(0)
const clueStatuses = ref<('pending' | 'done' | 'skipped' | 'active')[]>([])

// 界面状态
const showMode = ref<'private' | 'public'>('private')         // P2 私密/展示
const scriptStyle = ref<'natural' | 'professional'>('natural') // 话术风格
const showDeviation = ref(false)    // P3 偏离详情
const deviationClue = ref<any>(null)
const deviationItem = ref<any>(null)
const showClueSwitcher = ref(false) // P5 线索切换
const showQuickNote = ref(false)    // P6 快速记录
const quickNoteText = ref('')
const quickNoteTags = ref<string[]>([])
const showFallback = ref(false)     // P8 兜底搜索
const fallbackQuery = ref('')
const fallbackResult = ref<string[]>([])

const fmtTime = computed(() => {
  const m = Math.floor(timer.value / 60).toString().padStart(2, '0')
  const s = (timer.value % 60).toString().padStart(2, '0')
  return `${m}:${s}`
})

const currentClue = computed(() => clues.value[currentClueIdx.value] || null)
const totalClues = computed(() => clues.value.length)
const allDone = computed(() => clueStatuses.value.every(s => s === 'done' || s === 'skipped'))

onMounted(async () => {
  if (!bpId) { loading.value = false; return }
  try {
    const res = await api.getBattlePackageDetail(bpId)
    bpData.value = res.data
    clues.value = res.data?.clues || []
    clueStatuses.value = clues.value.map(() => 'pending')
    clueStatuses.value[0] = 'active'
    startTimer()
  } catch (e) {
    console.warn('加载作战包失败', e)
    appStore.showToast('加载作战包失败')
  } finally { loading.value = false }
})

onUnmounted(() => stopTimer())

function startTimer() { timerInterval = setInterval(() => { timer.value++ }, 1000) }
function stopTimer() { if (timerInterval) { clearInterval(timerInterval); timerInterval = null } }

// 线索导航
function prevClue() {
  if (currentClueIdx.value > 0) {
    clueStatuses.value[currentClueIdx.value] = 'pending'
    currentClueIdx.value--
    clueStatuses.value[currentClueIdx.value] = 'active'
  }
}
function nextClue() {
  if (currentClueIdx.value < totalClues.value - 1) {
    clueStatuses.value[currentClueIdx.value] = 'done'
    currentClueIdx.value++
    clueStatuses.value[currentClueIdx.value] = 'active'
  }
}
function goClue(idx: number) {
  if (idx >= 0 && idx < totalClues.value) {
    clueStatuses.value[currentClueIdx.value] = 'pending'
    currentClueIdx.value = idx
    clueStatuses.value[idx] = 'active'
    showClueSwitcher.value = false
  }
}
function markClueDone() {
  clueStatuses.value[currentClueIdx.value] = 'done'
  appStore.showToast('线索已标记完成')
}
function skipClue() {
  clueStatuses.value[currentClueIdx.value] = 'skipped'
  showClueSwitcher.value = false
  appStore.showToast('已跳过')
}

// P3 偏离详情
function openDeviation(clue: any, devItem: any) {
  deviationClue.value = clue
  deviationItem.value = devItem
  showDeviation.value = true
}
function closeDeviation() { showDeviation.value = false }

function goBackToMain() { closeDeviation() }
function switchToDeviation() {
  const newClue = {
    title: deviationClue.value?.title + '（偏离应对）',
    priority: '高',
    opening_script: deviationItem.value?.response || '',
    products: deviationItem.value?.suggested_products?.map((p: string) => ({ name: p })) || [],
    deviation_branches: [],
  }
  clues.value.push(newClue)
  clueStatuses.value.push('active')
  currentClueIdx.value = clues.value.length - 1
  closeDeviation()
  appStore.showToast('已切换到新线索')
}

// P4 展示模式
function toggleDisplayMode() {
  showMode.value = showMode.value === 'private' ? 'public' : 'private'
}

// 话术风格切换
function toggleStyle() {
  scriptStyle.value = scriptStyle.value === 'natural' ? 'professional' : 'natural'
  appStore.showToast(scriptStyle.value === 'natural' ? '已切换为口语化' : '已切换为专业化')
}

function styleScript(text: string): string {
  if (!text) return ''
  if (scriptStyle.value === 'natural') {
    // 口语化：简短的、带语气的
    return text
  }
  // 专业化：正式的、完整的
  return text
}

// P8 兜底搜索
function openFallback() {
  showFallback.value = true
  fallbackQuery.value = ''
  fallbackResult.value = []
}
function closeFallback() { showFallback.value = false }
function searchFallback() {
  const q = fallbackQuery.value.trim()
  if (!q) return
  // 模拟搜索匹配
  const keywords = ['购房', '转走', '风险', '亏损', '期限', '对比', '保险', '基金', '收益', '门槛']
  fallbackResult.value = keywords.filter(k => q.includes(k) || k.includes(q)).map(k => {
    const map: Record<string, string> = {
      '购房': '新购房需求 → 推荐按揭贷款 + 家装分期',
      '转走': '资金转出挽留 → 对比收益 + 专属权益',
      '风险': '风险顾虑 → 介绍R1/R2低风险产品',
      '亏损': '亏损疑虑 → 历史数据 + 分散配置',
      '期限': '期限偏好 → 匹配合适持有期产品',
      '对比': '他行对比 → 差异化优势展示',
      '保险': '保险异议 → 保障理念沟通',
      '基金': '基金偏好 → 推荐优质基金产品',
      '收益': '收益比较 → 同业对比 + 本行优势',
      '门槛': '门槛顾虑 → 灵活起投产品',
    }
    return map[k] || `匹配方向：${k}`
  })
  if (fallbackResult.value.length === 0) {
    fallbackResult.value = ['未匹配到明确方向，建议追问客户具体需求']
  }
}
function adoptFallbackResult(text: string) {
  const scenario = fallbackQuery.value || '新偏离场景'
  deviationClue.value = currentClue.value
  deviationItem.value = {
    scenario: scenario,
    response: '根据您的情况，我来帮您看看有什么更好的方案。',
    suggested_products: [],
  }
  showFallback.value = false
  showDeviation.value = true
}

// P5 线索切换
function openClueSwitcher() { showClueSwitcher.value = true }
function closeClueSwitcher() { showClueSwitcher.value = false }

// P6 快速记录
function openQuickNote() { showQuickNote.value = true; quickNoteText.value = ''; quickNoteTags.value = [] }
function closeQuickNote() { showQuickNote.value = false }
function toggleTag(tag: string) {
  const idx = quickNoteTags.value.indexOf(tag)
  if (idx >= 0) quickNoteTags.value.splice(idx, 1)
  else quickNoteTags.value.push(tag)
}
function saveQuickNote() {
  appStore.showToast('记录已保存')
  closeQuickNote()
}
function saveAndDone() {
  clueStatuses.value[currentClueIdx.value] = 'done'
  appStore.showToast('记录已保存，当前线索已完成')
  closeQuickNote()
}

// 结束面谈
function endMeeting() {
  if (!confirm('确定结束面谈？')) return
  stopTimer()
  timerRunning.value = false
  storeMeetingState()
  router.push({ name: 'meeting-end', params: { id: bpId } })
}

function storeMeetingState() {
  // 将面谈状态临时存储，供 P7 使用
  const state = {
    bpId,
    custName: bpData.value?.cust_name || '客户',
    duration: timer.value,
    cluesDone: clueStatuses.value.filter(s => s === 'done').length,
    cluesTotal: totalClues.value,
    clues: clues.value.map((c, i) => ({ title: c.title, status: clueStatuses.value[i] })),
  }
  sessionStorage.setItem('meeting_state_' + bpId, JSON.stringify(state))
}

// 复制话术
function copyScript(text: string) {
  navigator.clipboard?.writeText(text).then(() => appStore.showToast('已复制'))
}
</script>

<template>
  <div class="mt-page" :class="{ 'mt-page--public': showMode === 'public' }">
    <!-- === 状态栏 === -->
    <div class="mt-status-bar">
      <span class="mt-status-dot">🟢</span>
      <span class="mt-status-text">面谈中 · {{ fmtTime }} · {{ bpData?.cust_name || '客户' }}</span>
      <span class="mt-status-end" @click="endMeeting">⏹ 结束</span>
    </div>

    <!-- === 线索导航栏 === -->
    <div class="mt-clue-nav">
      <button class="mt-clue-arrow" :disabled="currentClueIdx === 0" @click="prevClue">←</button>
      <span class="mt-clue-title" @click="openClueSwitcher">
        📍 线索 {{ currentClueIdx + 1 }}/{{ totalClues }} · {{ currentClue?.title || '' }}
        <span v-if="allDone" class="mt-clue-done-badge">✅ 全部完成</span>
      </span>
      <button class="mt-clue-arrow" :disabled="currentClueIdx >= totalClues - 1" @click="nextClue">→</button>
    </div>

    <!-- === 内容区（私密模式） === -->
    <div v-if="showMode === 'private'" class="mt-body">
      <!-- 主剧本区 -->
      <div v-if="currentClue" class="mt-main-script">
        <div class="mt-section-label">💬 切入话术 · <span :class="scriptStyle === 'natural' ? 'mt-style-tag--active' : ''" @click="scriptStyle='natural'">口语化</span> / <span :class="scriptStyle === 'professional' ? 'mt-style-tag--active' : ''" @click="scriptStyle='professional'">专业化</span></div>
        <div class="mt-script-text">{{ styleScript(currentClue.opening_script) }}</div>
        <div class="mt-script-actions">
          <span class="mt-style-btn" @click="toggleStyle">{{ scriptStyle === 'natural' ? '切换为专业化' : '切换为口语化' }}</span>
          <span class="mt-copy-btn" @click="copyScript(currentClue.opening_script)">复制</span>
        </div>
      </div>

      <!-- 推荐产品区 -->
      <div v-if="currentClue?.products?.length" class="mt-products">
        <div class="mt-section-label">📦 推荐产品（{{ currentClue.products.length }}只）</div>
        <div class="mt-product-list">
          <div v-for="(p, pi) in currentClue.products" :key="pi" class="mt-product-card">
            <div class="mt-product-name">{{ p.name }}</div>
            <div class="mt-product-meta">
              <span v-if="p.type">{{ p.type }}</span>
              <span v-if="p.risk">风险 {{ p.risk }}</span>
              <span v-if="p.yield || p.expected_return">{{ p.expected_return || (p.yield ? p.yield + '%' : '') }}</span>
            </div>
            <div v-if="p.script" class="mt-product-script">「{{ p.script }}」</div>
          </div>
        </div>
      </div>

      <!-- 偏离预制区 -->
      <div v-if="currentClue?.deviation_branches?.length" class="mt-deviations">
        <div class="mt-deviations-header">
          <span class="mt-section-label">─ 客户可能偏离 ─</span>
        </div>
        <div class="mt-dev-list">
          <div
            v-for="(db, di) in currentClue.deviation_branches"
            :key="di"
            class="mt-dev-item"
            @click="openDeviation(currentClue, db)"
          >
            <span class="mt-dev-radio">○</span>
            <span>{{ db.scenario || (typeof db === 'string' ? db : '选项 ' + (di + 1)) }}</span>
          </div>
          <div class="mt-dev-item mt-dev-item--fallback" @click="openFallback">
            <span class="mt-dev-radio">○</span>
            <span>以上都不匹配 → 兜底话术</span>
          </div>
        </div>
      </div>
    </div>

    <!-- === 内容区（展示模式） === -->
    <div v-else class="mt-body mt-body--public">
      <div class="mt-public-notice">🟢 当前为展示模式</div>
      <div v-if="currentClue?.products?.length" class="mt-public-products">
        <div v-for="(p, pi) in currentClue.products" :key="pi" class="mt-public-card">
          <div class="mt-public-name">{{ p.name }}</div>
          <div class="mt-public-risk">{{ p.type || '产品' }} · 风险{{ p.risk || 'R2' }}</div>
          <div class="mt-public-return">
            <span class="mt-public-return-val">{{ p.expected_return || (p.yield ? p.yield + '%' : '收益稳健') }}</span>
          </div>
          <div class="mt-public-points">
            <div v-if="p.reason" class="mt-public-point">✔ {{ p.reason }}</div>
            <div class="mt-public-point">✔ 成立多年 · 历史业绩稳定</div>
          </div>
        </div>
      </div>
      <div v-else class="mt-public-empty">
        <div style="font-size:48px;margin-bottom:12px">📊</div>
        <div>暂无产品数据</div>
      </div>
    </div>

    <!-- === 底部工具栏 === -->
    <div class="mt-toolbar">
      <button
        class="mt-tool-btn"
        :class="{ 'mt-tool-btn--disabled': showMode === 'private' }"
        :disabled="showMode === 'private'"
      >🔒 私密</button>
      <button class="mt-tool-btn" @click="toggleDisplayMode">
        {{ showMode === 'private' ? '👁 展示' : '🔒 切回私密' }}
      </button>
      <button class="mt-tool-btn" @click="openQuickNote">📝 记录</button>
      <button class="mt-tool-btn" @click="openClueSwitcher">📋 线索</button>
      <button class="mt-tool-btn mt-tool-btn--end" @click="endMeeting">⏹ 结束</button>
    </div>

    <!-- ===== P3 偏离详情卡片（半屏浮层） ===== -->
    <Transition name="sheet-fade">
      <div v-if="showDeviation" class="mt-overlay" @click.self="closeDeviation">
        <div class="mt-deviation-panel">
          <div class="mt-dev-header">
            <span>📍 偏离：{{ deviationItem?.scenario || '详情' }}</span>
            <span class="mt-dev-close" @click="closeDeviation">✕</span>
          </div>
          <div class="mt-dev-content">
            <!-- 应对话术 -->
            <div v-if="deviationItem?.response" class="mt-dev-section">
              <div class="mt-section-label">💬 应对话术</div>
              <div class="mt-script-text">{{ deviationItem.response }}</div>
              <div class="mt-script-actions">
                <span class="mt-copy-btn" @click="copyScript(deviationItem.response)">复制</span>
              </div>
            </div>
            <!-- 备选产品 -->
            <div v-if="deviationItem?.suggested_products?.length" class="mt-dev-section">
              <div class="mt-section-label">📦 备选产品</div>
              <div class="mt-dev-products">
                <span v-for="(sp, si) in deviationItem.suggested_products" :key="si" class="mt-dev-prod-tag">{{ sp }}</span>
              </div>
            </div>
          </div>
          <div class="mt-dev-actions">
            <button class="bp-btn bp-btn--outline" @click="goBackToMain">返回当前剧本</button>
            <button class="bp-btn bp-btn--primary" @click="switchToDeviation">切换为新线索</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ===== P5 线索切换面板（浮层） ===== -->
    <Transition name="sheet-fade">
      <div v-if="showClueSwitcher" class="mt-overlay" @click.self="closeClueSwitcher">
        <div class="mt-clue-panel">
          <div class="mt-dev-header">
            <span>线索列表</span>
            <span class="mt-dev-close" @click="closeClueSwitcher">✕</span>
          </div>
          <div class="mt-clue-list">
            <div
              v-for="(c, i) in clues"
              :key="i"
              class="mt-clue-item"
              :class="{
                'mt-clue-item--active': i === currentClueIdx,
                'mt-clue-item--done': clueStatuses[i] === 'done',
                'mt-clue-item--skipped': clueStatuses[i] === 'skipped',
              }"
              @click="goClue(i)"
            >
              <span v-if="clueStatuses[i] === 'done'" class="mt-clue-status">✅</span>
              <span v-else-if="clueStatuses[i] === 'skipped'" class="mt-clue-status">⏸</span>
              <span v-else-if="i === currentClueIdx" class="mt-clue-status">▶</span>
              <span v-else class="mt-clue-status">○</span>
              <span class="mt-clue-item-title">线索 {{ i + 1 }} · {{ c.title }}</span>
              <span v-if="clueStatuses[i] === 'done'" class="mt-clue-item-tag">已完成</span>
              <span v-else-if="clueStatuses[i] === 'skipped'" class="mt-clue-item-tag">已跳过</span>
              <span v-else-if="i === currentClueIdx" class="mt-clue-item-tag mt-clue-item-tag--active">进行中</span>
            </div>
          </div>
          <div class="mt-clue-actions">
            <span class="mt-clue-action" @click="markClueDone">标记当前为已完成</span>
            <span class="mt-clue-action" @click="skipClue">跳过当前</span>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ===== P6 快速记录浮层 ===== -->
    <Transition name="sheet-fade">
      <div v-if="showQuickNote" class="mt-overlay" @click.self="closeQuickNote">
        <div class="mt-note-panel">
          <div class="mt-dev-header">
            <span>📝 快速记录</span>
            <span class="mt-dev-close" @click="closeQuickNote">✕</span>
          </div>
          <div class="mt-note-body">
            <textarea v-model="quickNoteText" class="mt-note-input" placeholder="输入关键信息..."></textarea>
            <div class="mt-note-tags">
              <span class="mt-note-label">🏷 快捷标签</span>
              <div class="mt-note-tag-list">
                <span
                  v-for="tag in ['有意向', '需跟进', '已拒绝', '新需求', '改天再聊', '转介绍']"
                  :key="tag"
                  class="mt-note-tag"
                  :class="{ 'mt-note-tag--active': quickNoteTags.includes(tag) }"
                  @click="toggleTag(tag)"
                >{{ tag }}</span>
              </div>
            </div>
          </div>
          <div class="mt-note-actions">
            <button class="bp-btn bp-btn--outline" @click="saveQuickNote">保存</button>
            <button class="bp-btn bp-btn--primary" @click="saveAndDone">保存并标记完成</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ===== P8 兜底搜索界面 ===== -->
    <Transition name="sheet-fade">
      <div v-if="showFallback" class="mt-overlay" @click.self="closeFallback">
        <div class="mt-fallback-panel">
          <div class="mt-dev-header">
            <span>客户说了什么？</span>
            <span class="mt-dev-close" @click="closeFallback">✕</span>
          </div>
          <div class="mt-fallback-body">
            <div class="mt-fallback-search">
              <input v-model="fallbackQuery" class="mt-fallback-input" placeholder="输入客户原话..." @keyup.enter="searchFallback" />
              <button class="mt-fallback-btn" @click="searchFallback">搜索</button>
            </div>
            <div v-if="fallbackResult.length" class="mt-fallback-results">
              <div class="mt-section-label">💡 匹配到 {{ fallbackResult.length }} 个可能方向</div>
              <div
                v-for="(r, ri) in fallbackResult"
                :key="ri"
                class="mt-fallback-item"
                @click="adoptFallbackResult(r)"
              >
                · {{ r }}
              </div>
            </div>
            <div v-if="fallbackResult.length === 0" class="mt-fallback-empty">
              <div class="mt-fallback-dialog">
                <div class="mt-section-label">💬 兜底话术</div>
                <div class="mt-script-text">"您说的这个情况我了解了，方便详细跟我说说吗？我看看怎么帮您规划更好。"</div>
                <div class="mt-script-actions">
                  <span class="mt-copy-btn" @click="copyScript('您说的这个情况我了解了，方便详细跟我说说吗？我看看怎么帮您规划更好。')">复制</span>
                </div>
              </div>
              <div class="mt-fallback-hint">
                <div class="mt-section-label">📌 追问方向</div>
                <div class="mt-fallback-point">· 发生了什么变化？</div>
                <div class="mt-fallback-point">· 您现在最关心的是什么？</div>
                <div class="mt-fallback-point">· 有什么我可以帮您解决的？</div>
              </div>
            </div>
          </div>
          <div class="mt-dev-actions">
            <button class="bp-btn bp-btn--outline" @click="closeFallback">返回面谈</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.mt-page { min-height: 100%; background: var(--color-bg); }
.mt-page--public { background: #f0f7f0; }

/* Status Bar */
.mt-status-bar {
  display: flex; align-items: center; padding: 8px 16px;
  background: #D4EDDA; color: #155724; font-size: 12px;
  position: sticky; top: 0; z-index: 10;
}
.mt-status-dot { margin-right: 6px; }
.mt-status-text { flex: 1; font-weight: 500; }
.mt-status-end { cursor: pointer; color: #721C24; font-weight: 600; }

/* Clue Nav */
.mt-clue-nav {
  display: flex; align-items: center; padding: 10px 16px;
  background: #fff; border-bottom: 1px solid #eee;
}
.mt-clue-arrow {
  border: none; background: #f0f0f0; border-radius: 6px;
  padding: 4px 10px; font-size: 14px; cursor: pointer; color: #666;
}
.mt-clue-arrow:disabled { opacity: 0.3; cursor: default; }
.mt-clue-title {
  flex: 1; text-align: center; font-size: 13px; font-weight: 600;
  cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px;
}
.mt-clue-done-badge { font-size: 11px; color: #28a745; }

/* Body */
.mt-body { padding: 12px 16px 80px; }
.mt-body--public { padding-top: 20px; }
.mt-section-label { font-size: 11px; color: #999; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 1px; }

/* Main Script */
.mt-main-script {
  background: #fff; border-radius: 10px; padding: 14px; margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.mt-script-text {
  font-size: 14px; line-height: 1.8; color: var(--color-text);
  background: #f8f8f8; padding: 10px 12px; border-radius: 6px;
  border-left: 3px solid var(--color-primary); font-style: italic;
}
.mt-script-actions { margin-top: 8px; display: flex; justify-content: flex-end; }
.mt-copy-btn {
  font-size: 11px; color: var(--color-primary); cursor: pointer;
  padding: 3px 10px; border-radius: 4px; background: rgba(171,32,41,0.06);
}
.mt-copy-btn:active { background: rgba(171,32,41,0.12); }

/* Products */
.mt-products { margin-bottom: 12px; }
.mt-product-list { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px; }
.mt-product-card {
  flex: 0 0 auto; min-width: 140px; background: #fff; border-radius: 8px;
  padding: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.mt-product-name { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
.mt-product-meta { display: flex; gap: 6px; font-size: 10px; color: var(--color-text-secondary); flex-wrap: wrap; }
.mt-product-script { font-size: 11px; color: var(--color-primary); margin-top: 4px; font-style: italic; }

/* Deviations */
.mt-deviations { margin-bottom: 12px; }
.mt-deviations-header { margin-bottom: 8px; text-align: center; }
.mt-dev-list {
  background: #fff; border-radius: 10px; overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.mt-dev-item {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 14px; border-bottom: 1px solid #f5f5f5;
  font-size: 13px; cursor: pointer; color: var(--color-text);
}
.mt-dev-item:active { background: #fafafa; }
.mt-dev-item:last-child { border-bottom: none; }
.mt-dev-item--fallback { color: #999; font-style: italic; }
.mt-dev-radio { color: #ccc; font-size: 14px; }

/* Toolbar */
.mt-toolbar {
  display: flex; gap: 6px; padding: 8px 12px;
  background: #fff; border-top: 1px solid #eee;
  position: sticky; bottom: 0; z-index: 10;
  box-shadow: 0 -2px 8px rgba(0,0,0,0.04);
}
.mt-tool-btn {
  flex: 1; padding: 8px 4px; border-radius: 6px; border: 1px solid #eee;
  background: #fff; font-size: 11px; cursor: pointer; display: flex;
  align-items: center; justify-content: center; gap: 2px;
}
.mt-tool-btn:active { background: #f5f5f5; }
.mt-tool-btn--disabled { opacity: 0.5; cursor: default; background: #f5f5f5; }
.mt-tool-btn--end { color: #e74c3c; border-color: #f8d7da; }

/* Style toggle */
.mt-style-tag--active { color: var(--color-primary); font-weight: 600; text-decoration: underline; }
.mt-style-btn {
  font-size: 11px; color: var(--color-text-secondary); cursor: pointer;
  padding: 3px 10px; border-radius: 4px; background: #f0f0f0; margin-right: 8px;
}
.mt-style-btn:active { background: #e0e0e0; }

/* P8 Fallback */
.mt-fallback-panel {
  background: #fff; width: 100%; border-radius: 16px 16px 0 0;
  max-height: 75%; overflow-y: auto; padding: 0 0 16px;
}
.mt-fallback-body { padding: 12px 16px; }
.mt-fallback-search { display: flex; gap: 8px; margin-bottom: 12px; }
.mt-fallback-input {
  flex: 1; border: 1px solid #eee; border-radius: 8px;
  padding: 10px 12px; font-size: 13px; font-family: inherit;
}
.mt-fallback-input:focus { outline: none; border-color: var(--color-primary); }
.mt-fallback-btn {
  border: none; background: var(--color-primary); color: #fff;
  border-radius: 8px; padding: 10px 16px; font-size: 13px; cursor: pointer; font-weight: 500;
}
.mt-fallback-results { margin-bottom: 12px; }
.mt-fallback-item {
  padding: 10px 12px; margin: 6px 0; background: #fff8f0;
  border-radius: 6px; border-left: 3px solid #f0a020;
  font-size: 12px; cursor: pointer; color: var(--color-text);
}
.mt-fallback-item:active { background: #fff0e0; }
.mt-fallback-dialog { margin-bottom: 12px; }
.mt-fallback-hint { margin-bottom: 12px; }
.mt-fallback-point { font-size: 12px; color: var(--color-text-secondary); padding: 2px 0; }

/* Public mode */
.mt-public-notice {
  text-align: center; font-size: 13px; color: #155724;
  background: #D4EDDA; padding: 8px; border-radius: 6px; margin-bottom: 16px;
}
.mt-public-products { display: flex; flex-direction: column; gap: 16px; }
.mt-public-card {
  background: #fff; border-radius: 12px; padding: 20px 18px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center;
}
.mt-public-name { font-size: 18px; font-weight: 700; margin-bottom: 6px; }
.mt-public-risk { font-size: 12px; color: #999; margin-bottom: 12px; }
.mt-public-return-val { font-size: 36px; font-weight: 700; color: var(--color-primary); }
.mt-public-points { text-align: left; margin-top: 16px; }
.mt-public-point { font-size: 13px; padding: 4px 0; color: var(--color-text-secondary); }
.mt-public-empty { text-align: center; padding: 60px 20px; color: #999; }

/* Overlay */
.mt-overlay {
  position: absolute; inset: 0; z-index: 100;
  background: rgba(0,0,0,0.4); display: flex; align-items: flex-end;
}

/* Deviation Panel (P3) */
.mt-deviation-panel {
  background: #fff; width: 100%; border-radius: 16px 16px 0 0;
  max-height: 75%; overflow-y: auto; padding: 0 0 16px;
}
.mt-dev-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px 10px; border-bottom: 1px solid #eee;
  font-size: 14px; font-weight: 600; position: sticky; top: 0; background: #fff;
}
.mt-dev-close { font-size: 16px; cursor: pointer; color: #999; padding: 4px; }
.mt-dev-content { padding: 12px 16px; }
.mt-dev-section { margin-bottom: 14px; }
.mt-dev-products { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.mt-dev-prod-tag {
  background: var(--color-bg); padding: 4px 10px; border-radius: 4px;
  font-size: 12px; color: var(--color-text-secondary);
}
.mt-dev-actions {
  display: flex; gap: 8px; padding: 0 16px;
}

/* Clue Panel (P5) */
.mt-clue-panel {
  background: #fff; width: 100%; border-radius: 16px 16px 0 0;
  max-height: 65%; overflow-y: auto; padding: 0 0 16px;
}
.mt-clue-list { padding: 0 16px; }
.mt-clue-item {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 0; border-bottom: 1px solid #f5f5f5;
  cursor: pointer; font-size: 13px;
}
.mt-clue-item--active { background: rgba(171,32,41,0.04); margin: 0 -16px; padding: 12px 16px; }
.mt-clue-item--done { color: #999; }
.mt-clue-item--skipped { color: #ccc; }
.mt-clue-status { font-size: 14px; flex-shrink: 0; }
.mt-clue-item-title { flex: 1; }
.mt-clue-item-tag { font-size: 10px; padding: 2px 6px; border-radius: 4px; background: #f0f0f0; color: #999; }
.mt-clue-item-tag--active { background: #D4EDDA; color: #155724; }
.mt-clue-actions { padding: 12px 16px; display: flex; gap: 16px; }
.mt-clue-action { font-size: 12px; color: var(--color-primary); cursor: pointer; }

/* Note Panel (P6) */
.mt-note-panel {
  background: #fff; width: 100%; border-radius: 16px 16px 0 0;
  max-height: 65%; padding: 0 0 16px;
}
.mt-note-body { padding: 12px 16px; }
.mt-note-input {
  width: 100%; min-height: 80px; border: 1px solid #eee;
  border-radius: 8px; padding: 10px; font-size: 13px; resize: none;
  font-family: inherit; box-sizing: border-box;
}
.mt-note-input:focus { outline: none; border-color: var(--color-primary); }
.mt-note-tags { margin-top: 12px; }
.mt-note-label { font-size: 11px; color: #999; }
.mt-note-tag-list { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
.mt-note-tag {
  padding: 5px 12px; border-radius: 16px; font-size: 11px;
  background: #f0f0f0; cursor: pointer;
}
.mt-note-tag--active { background: var(--color-primary); color: #fff; }
.mt-note-actions { display: flex; gap: 8px; padding: 0 16px; margin-top: 8px; }

/* Transitions */
.sheet-fade-enter-active, .sheet-fade-leave-active { transition: opacity 0.25s; }
.sheet-fade-enter-from, .sheet-fade-leave-to { opacity: 0; }
</style>
