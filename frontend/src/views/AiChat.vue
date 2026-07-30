<script setup lang="ts">
import { ref, nextTick, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'
import { useManagerStore } from '@/stores/manager'

const route = useRoute()
const router = useRouter()
const managerStore = useManagerStore()

interface Message {
  role: 'user' | 'bot' | 'result'
  text: string
  result?: { queries: string[]; count: number; total: number }
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

  // 尝试通过 SSE 流式调用 AI 接口
  trySseMining(text).catch(() => {
    // SSE 失败时回退到本地模拟
    setTimeout(() => {
      isThinking.value = false
      const reply = generateReply(text)
      messages.value.push({ role: 'bot', text: reply.text })
      if (reply.result) {
        messages.value.push({ role: 'result', text: '', result: reply.result })
      }
      scrollToBottom()
    }, 800 + Math.random() * 600)
  })
}

/** 尝试 SSE 流式调用商机挖掘接口 */
async function trySseMining(userText: string) {
  const res = await api.aiMineStream(managerStore.currentId)
  if (!res.ok) throw new Error(`SSE error: ${res.status}`)

  isThinking.value = false
  const botMsg: Message = { role: 'bot', text: '' }
  messages.value.push(botMsg)

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const payload = line.slice(6).trim()
        if (payload === '[DONE]') continue
        try {
          const chunk = JSON.parse(payload)
          if (chunk.text) botMsg.text += chunk.text
          if (chunk.content) botMsg.text += chunk.content
        } catch {
          botMsg.text += payload
        }
        scrollToBottom()
      }
    }
  }

  if (!botMsg.text) botMsg.text = 'AI 分析完成，暂无更多结果。'
  scrollToBottom()
}

function generateReply(text: string): { text: string; result?: { queries: string[]; count: number; total: number } } {
  const t = text.toLowerCase()

  // Customer queries
  if (t.includes('财富') || t.includes('列出')) {
    return {
      text: '好的，已为你筛选出符合条件的客户：',
      result: { queries: ['财富客户'], count: 3, total: 7 },
    }
  }
  if (t.includes('未联系') || t.includes('30天')) {
    return {
      text: '以下客户超过30天未联系，建议尽快跟进：',
      result: { queries: ['超30天未联系'], count: 2, total: 7 },
    }
  }
  if (t.includes('基金')) {
    return {
      text: '以下是持有基金的客户清单：',
      result: { queries: ['持有基金'], count: 2, total: 7 },
    }
  }
  if (t.includes('定存到期') || t.includes('到期')) {
    return {
      text: '以下客户近期有定存到期，请及时对接：',
      result: { queries: ['定存到期'], count: 1, total: 7 },
    }
  }
  if (t.includes('aum') || t.includes('50万')) {
    return {
      text: '已筛选 AUM 超过 50 万的客户：',
      result: { queries: ['AUM≥50万'], count: 3, total: 7 },
    }
  }

  // Product queries
  if (t.includes('理财') || t.includes('推荐')) {
    return {
      text: '根据你的管户画像，推荐以下理财产品：',
      result: { queries: ['理财产品推荐'], count: 4, total: 12 },
    }
  }
  if (t.includes('r2') || t.includes('中低风险')) {
    return {
      text: '以下是 R2 中低风险产品：',
      result: { queries: ['R2中低风险'], count: 4, total: 12 },
    }
  }
  if (t.includes('短期')) {
    return {
      text: '以下是短期/灵活申赎产品：',
      result: { queries: ['短期产品'], count: 3, total: 12 },
    }
  }
  if (t.includes('高收益') || t.includes('收益较高')) {
    return {
      text: '以下是收益表现较好的产品（R3及以上）：',
      result: { queries: ['高收益产品'], count: 4, total: 12 },
    }
  }

  return {
    text: '我理解你的需求。你可以尝试更具体的提问，例如："列出财富客户中超过30天未联系的"、或"推荐适合稳健型客户的理财产品"。',
  }
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
        <template v-if="msg.role === 'user'">
          <div class="ac-bubble user">{{ msg.text }}</div>
        </template>
        <template v-else-if="msg.role === 'bot'">
          <div class="ac-bubble bot">{{ msg.text }}</div>
        </template>
        <template v-else-if="msg.role === 'result' && msg.result">
          <div class="ac-result-card">
            <div class="ac-result-header">
              <svg viewBox="0 0 24 24" class="ico ico--sm" style="color:#6C5CE7"><use href="#ico-robot" /></svg> AI 筛选结果
              <span class="ac-result-count">找到 {{ msg.result.count }} / {{ msg.result.total }}</span>
            </div>
            <div class="ac-result-tags">
              <span v-for="q in msg.result.queries" :key="q" class="ac-result-tag">{{ q }}</span>
            </div>
            <div class="ac-result-action" @click="router.push({ name: 'customer-list' })">
              查看结果 →
            </div>
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
.ac-msg--result { justify-content: flex-start; }

.ac-bubble {
  max-width: 80%;
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

.ac-result-card {
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  max-width: 90%;
  border-left: 3px solid #6C5CE7;
}
.ac-result-header {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.ac-result-count {
  margin-left: auto;
  font-size: 11px;
  font-weight: 400;
  color: var(--color-text-secondary);
}
.ac-result-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 10px;
}
.ac-result-tag {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  background: #EDE9FE;
  color: #6C5CE7;
}
.ac-result-action {
  font-size: 13px;
  color: var(--color-primary);
  cursor: pointer;
  font-weight: 500;
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
