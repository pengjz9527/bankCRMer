<script setup lang="ts">
import { ref, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'
import { useManagerStore } from '@/stores/manager'
import { marked } from 'marked'

// 配置 marked 安全渲染
marked.setOptions({
  breaks: true,    // 支持单换行
  gfm: true,       // GitHub 风格 Markdown
})

const route = useRoute()
const router = useRouter()
const managerStore = useManagerStore()

interface Message {
  role: 'user' | 'bot'
  text: string
  summary?: string
  fullAnswer?: string
  expanded?: boolean
}

const channel = ref((route.query.from as string) || 'home')
const messages = ref<Message[]>([])
const inputText = ref('')
const isThinking = ref(false)
const chatBody = ref<HTMLElement | null>(null)

// Channel configs
const channelConfig: Record<string, any> = {
  home: {
    title: 'AI 助手',
    welcome: '你好，我是 AI 展业助手',
    subtitle: '试试下面的快捷提问，或直接输入你的需求',
    placeholder: '输入你的问题...',
    chips: [
      { label:'财富客户有哪些', text:'帮我列出我的财富客户' },
      { label:'本周到期产品', text:'本周有哪些定存到期的客户' },
      { label:'未联系客户', text:'超过30天未联系的客户有哪些' },
      { label:'推荐理财产品', text:'推荐适合稳健型客户的理财产品' },
    ],
  },
  w8: {
    title: '客户管理助手',
    welcome: '你好，我是客户管理助手',
    subtitle: '你可以用自然语言筛选客户',
    placeholder: '例如：财富客户中超过7天未联系的',
    chips: [
      { label:'财富客户', text:'帮我列出财富客户' },
      { label:'AUM>50万', text:'AUM超过50万的客户' },
      { label:'30天未联系', text:'超过30天未联系的客户' },
      { label:'持有基金', text:'持有基金的客户有哪些' },
    ],
  },
  product: {
    title: '产品推荐助手',
    welcome: '你好，我是产品推荐助手',
    subtitle: '我可以根据你的客户画像推荐合适的产品',
    placeholder: '例如：推荐适合稳健客户的理财产品',
    chips: [
      { label:'推荐理财', text:'推荐适合财富客户的理财产品' },
      { label:'R2产品', text:'列出所有R2中低风险产品' },
      { label:'短期理财', text:'有哪些短期理财产品' },
      { label:'高收益', text:'有哪些收益较高的产品' },
    ],
  },
}

const cfg = computed(() => channelConfig[channel.value] || channelConfig.home)

function sendQuick(text: string) {
  inputText.value = text
  send()
}

function send() {
  const text = inputText.value.trim()
  if (!text || isThinking.value) return
  inputText.value = ''

  // Add user message
  messages.value.push({ role: 'user', text })
  isThinking.value = true
  scrollToBottom()

  // 调用 QAAgent 接口
  callQaAgent(text)
}

/** 调用 QAAgent 智能问答接口 */
async function callQaAgent(userText: string) {
  try {
    const res = await api.aiQaAsk(userText, managerStore.currentId)
    isThinking.value = false

    if (res.code === 0 && res.data) {
      const summary = res.data.summary || extractFirstLine(res.data.answer || '')
      const answer = res.data.answer || '暂无回答，请换个问题试试。'

      messages.value.push({
        role: 'bot',
        text: summary,
        summary: summary,
        fullAnswer: answer,
        expanded: false,
      })
    } else {
      messages.value.push({
        role: 'bot',
        text: res.message || 'AI 问答服务暂不可用，请稍后重试',
      })
    }
  } catch {
    isThinking.value = false
    messages.value.push({
      role: 'bot',
      text: 'AI 问答服务连接失败，请确保后端服务已启动后重试',
    })
  }
  scrollToBottom()
}

/** 提取第一段文字作为降级摘要 */
function extractFirstLine(text: string): string {
  const first = text.split('\n').filter(l => l.trim()).slice(0, 2).join(' ')
  return first.length > 100 ? first.slice(0, 100) + '...' : first
}

/** 渲染 Markdown 为 HTML */
function renderMarkdown(md: string): string {
  if (!md) return ''
  try {
    return marked.parse(md) as string
  } catch {
    return md.replace(/\n/g, '<br>')
  }
}

/** 展开/折叠完整回答 */
function toggleExpand(msg: Message) {
  msg.expanded = !msg.expanded
  scrollToBottom()
}

/** 内容是否可展开 */
function hasMoreContent(msg: Message): boolean {
  return !!(msg.fullAnswer && msg.fullAnswer.length > msg.text.length + 20)
}

function scrollToBottom() {
  nextTick(() => {
    if (chatBody.value) {
      chatBody.value.scrollTop = chatBody.value.scrollHeight
    }
  })
}

function goBack() {
  router.back()
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}
</script>

<template>
  <div class="ai-chat">
    <!-- Header -->
    <div class="ac-header">
      <span class="ac-back" @click="goBack">←</span>
      <span class="ac-title">{{ cfg.title }}</span>
      <span class="ac-clear" @click="messages = []">清空</span>
    </div>

    <!-- Chat Body -->
    <div class="ac-body" ref="chatBody">
      <!-- Welcome -->
      <div v-if="messages.length === 0 && !isThinking" class="ac-welcome">
        <div class="ac-welcome-icon"><svg viewBox="0 0 24 24" class="ico" style="font-size:42px;color:#6C5CE7"><use href="#ico-robot" /></svg></div>
        <div class="ac-welcome-title">{{ cfg.welcome }}</div>
        <div class="ac-welcome-sub">{{ cfg.subtitle }}</div>
        <div class="ac-chips">
          <span
            v-for="chip in cfg.chips"
            :key="chip.label"
            class="ac-chip"
            @click="sendQuick(chip.text)"
          >{{ chip.label }}</span>
        </div>
      </div>

      <!-- Messages -->
      <div v-for="(msg, idx) in messages" :key="idx" class="ac-msg" :class="'ac-msg--' + msg.role">
        <!-- 用户消息 -->
        <template v-if="msg.role === 'user'">
          <div class="ac-bubble user">{{ msg.text }}</div>
        </template>

        <!-- Bot 消息（带摘要/展开） -->
        <template v-else-if="msg.role === 'bot'">
          <div class="ac-bubble bot">
            <!-- 摘要区：始终显示 -->
            <div class="md-body">{{ msg.text }}</div>

            <!-- 展开按钮：仅有完整内容时显示 -->
            <div
              v-if="hasMoreContent(msg)"
              class="ac-expand-btn"
              @click="toggleExpand(msg)"
            >
              <span>{{ msg.expanded ? '收起全部 ▲' : '展开全部 ▼' }}</span>
            </div>

            <!-- 完整回答：展开后显示，带 Markdown 渲染 -->
            <div
              v-if="msg.expanded && msg.fullAnswer"
              class="ac-full-answer"
              v-html="renderMarkdown(msg.fullAnswer)"
            ></div>
          </div>
        </template>
      </div>

      <!-- Thinking -->
      <div v-if="isThinking" class="ac-msg ac-msg--bot">
        <div class="ac-thinking">
          <span class="ac-thinking-dot"></span>
          <span class="ac-thinking-dot"></span>
          <span class="ac-thinking-dot"></span>
          思考中...
        </div>
      </div>
    </div>

    <!-- Input Bar -->
    <div class="ac-input-bar">
      <input
        v-model="inputText"
        class="ac-input"
        :placeholder="cfg.placeholder"
        @keydown="handleKeydown"
      />
      <button class="ac-send-btn" :disabled="!inputText.trim() || isThinking" @click="send">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.ai-chat {
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh;
  background: #f8f8f8;
}

.ac-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #fff;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}
.ac-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.ac-title { flex: 1; font-size: 17px; font-weight: 600; }
.ac-clear { font-size: 13px; color: var(--color-text-secondary); cursor: pointer; }

.ac-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  -webkit-overflow-scrolling: touch;
}

.ac-welcome { text-align: center; padding: 40px 20px; }
.ac-welcome-icon { margin-bottom: 12px; display: flex; justify-content: center; }
.ac-welcome-title { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
.ac-welcome-sub { font-size: 13px; color: var(--color-text-secondary); margin-bottom: 20px; }

.ac-chips { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.ac-chip {
  padding: 8px 14px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}
.ac-chip:active { background: #EDE9FE; border-color: #6C5CE7; color: #6C5CE7; }

.ac-msg { margin-bottom: 14px; display: flex; }
.ac-msg--user { justify-content: flex-end; }
.ac-msg--bot { justify-content: flex-start; }

.ac-bubble {
  max-width: 88%;
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
}
.ac-bubble.user {
  background: var(--color-primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.ac-bubble.bot {
  background: #fff;
  color: var(--color-text);
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

/* ── 摘要文本 ── */
.md-body {
  font-size: 14px;
  line-height: 1.7;
}

/* ── 展开按钮 ── */
.ac-expand-btn {
  margin-top: 10px;
  padding: 8px 0 2px;
  border-top: 1px dashed #e8e8e8;
  text-align: center;
  cursor: pointer;
}
.ac-expand-btn span {
  font-size: 13px;
  color: var(--color-primary);
  font-weight: 500;
}
.ac-expand-btn:active span { opacity: 0.7; }

/* ── 完整回答（Markdown 渲染区） ── */
.ac-full-answer {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #f0f0f0;
  font-size: 14px;
  line-height: 1.75;
  color: var(--color-text);
}

/* Markdown 渲染样式 */
.ac-full-answer :deep(h2) {
  font-size: 17px;
  font-weight: 700;
  margin: 18px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #eee;
  color: #333;
}
.ac-full-answer :deep(h2:first-child) { margin-top: 0; }

.ac-full-answer :deep(h3) {
  font-size: 15px;
  font-weight: 600;
  margin: 14px 0 6px;
  color: #444;
}

.ac-full-answer :deep(p) {
  margin: 6px 0;
}

.ac-full-answer :deep(ul),
.ac-full-answer :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}
.ac-full-answer :deep(li) {
  margin: 3px 0;
}

.ac-full-answer :deep(strong) {
  font-weight: 600;
  color: #333;
}

.ac-full-answer :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
  font-size: 12px;
}
.ac-full-answer :deep(th) {
  background: #f5f3ff;
  color: #5b4ae0;
  font-weight: 600;
  padding: 7px 8px;
  text-align: left;
  border: 1px solid #e8e4f8;
}
.ac-full-answer :deep(td) {
  padding: 6px 8px;
  border: 1px solid #eee;
  vertical-align: top;
}
.ac-full-answer :deep(tr:nth-child(even) td) {
  background: #fafafa;
}

.ac-full-answer :deep(code) {
  background: #f5f5f5;
  padding: 2px 5px;
  border-radius: 3px;
  font-size: 12px;
}

.ac-full-answer :deep(blockquote) {
  margin: 8px 0;
  padding: 6px 12px;
  border-left: 3px solid #6C5CE7;
  background: #f8f6ff;
  color: #666;
}

.ac-full-answer :deep(hr) {
  border: none;
  border-top: 1px solid #eee;
  margin: 14px 0;
}

.ac-full-answer :deep(em) {
  color: #888;
}

.ac-thinking {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 10px 14px;
  background: #fff;
  border-radius: 16px;
  font-size: 13px;
  color: #999;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.ac-thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #bbb;
  animation: ac-pulse 1.2s infinite;
}
.ac-thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.ac-thinking-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes ac-pulse {
  0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
  30% { opacity: 1; transform: scale(1); }
}

.ac-input-bar {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  background: #fff;
  border-top: 1px solid #eee;
  gap: 10px;
  flex-shrink: 0;
  padding-bottom: calc(10px + env(safe-area-inset-bottom));
}
.ac-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  font-size: 14px;
  outline: none;
  background: #f5f5f5;
}
.ac-input:focus { border-color: #6C5CE7; }
.ac-send-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background: var(--color-primary);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: opacity 0.2s;
}
.ac-send-btn:disabled { opacity: 0.4; }
</style>
