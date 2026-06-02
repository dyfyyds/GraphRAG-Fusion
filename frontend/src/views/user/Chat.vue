<template>
  <div class="chat-layout">
    <ConversationList
      :conversations="conversationItems"
      :current-id="currentKey"
      @select="selectConversation"
      @delete="deleteConversation"
      @logout="handleLogout"
    />

    <div class="chat-main">
      <div class="chat-header">
        <span class="title">{{ currentTitle }}</span>
        <div class="actions">
          <div class="action-btn" title="清除对话" @click="clearCurrentChat">
            <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" /></svg>
          </div>
        </div>
      </div>

      <div class="chat-messages" ref="messagesRef">
        <!-- Welcome state -->
        <div v-if="!messages.length && !isStreaming" class="welcome-state">
          <div class="welcome-icon">
            <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" /></svg>
          </div>
          <h2>RAG 智能问答</h2>
          <p>基于企业知识库的精准问答服务，请输入您的问题开始对话</p>
        </div>

        <MessageBubble
          v-for="msg in messages"
          :key="msg.id"
          :message="msg"
          @feedback="handleFeedback"
        />

        <!-- Typing indicator -->
        <div v-if="isStreaming && !streamingText" class="message assistant">
          <div class="avatar">AI</div>
          <div class="bubble">
            <div class="typing-indicator">
              <div class="dot"></div>
              <div class="dot"></div>
              <div class="dot"></div>
            </div>
          </div>
        </div>

        <!-- Streaming message -->
        <div v-if="streamingText" class="message assistant">
          <div class="avatar">AI</div>
          <div class="stream-wrapper">
            <div class="bubble" v-html="renderMarkdown(streamingText)"></div>
            <div v-if="currentSources.length" class="stream-sources-note">
              已检索到 {{ currentSources.length }} 条引用，回答完成后可展开查看
            </div>
          </div>
        </div>
      </div>

      <ChatInput :loading="isStreaming" @send="sendMessage" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ConversationList from '../../components/chat/ConversationList.vue'
import MessageBubble from '../../components/chat/MessageBubble.vue'
import ChatInput from '../../components/chat/ChatInput.vue'
import { useUserStore } from '../../store/user'
import { streamChat } from '../../utils/sse'
import request from '../../api/request'
import markdownit from 'markdown-it'

const md = markdownit({ html: false, linkify: true })
const router = useRouter()
const userStore = useUserStore()

const conversations = ref([])
const currentKey = ref(null)
const chatSessions = reactive({})
const messagesRef = ref(null)

function toKey(id) {
  if (id === null || id === undefined) return null
  return String(id)
}

function isPendingKey(key) {
  return typeof key === 'string' && key.startsWith('pending:')
}

function isPersistedKey(key) {
  return key !== null && key !== undefined && !isPendingKey(key)
}

function ensureSession(key) {
  if (!key) return null
  if (!chatSessions[key]) {
    chatSessions[key] = {
      messages: [],
      streamingText: '',
      sources: [],
      isStreaming: false,
      title: '新对话',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
  }
  return chatSessions[key]
}

function titleFromQuestion(question) {
  return question.length > 28 ? `${question.slice(0, 28)}...` : question
}

const activeSession = computed(() => currentKey.value ? chatSessions[currentKey.value] : null)
const messages = computed(() => activeSession.value?.messages || [])
const streamingText = computed(() => activeSession.value?.streamingText || '')
const isStreaming = computed(() => Boolean(activeSession.value?.isStreaming))
const currentSources = computed(() => activeSession.value?.sources || [])

const conversationItems = computed(() => {
  const persisted = conversations.value.map(conv => {
    const key = toKey(conv.id)
    return {
      ...conv,
      id: key,
      thinking: Boolean(chatSessions[key]?.isStreaming),
    }
  })
  const pending = Object.entries(chatSessions)
    .filter(([key]) => isPendingKey(key))
    .map(([key, session]) => ({
      id: key,
      title: session.title || '新对话',
      created_at: session.created_at,
      updated_at: session.updated_at,
      thinking: session.isStreaming,
    }))
  return [...pending, ...persisted]
})

const currentTitle = computed(() => {
  if (!currentKey.value) return '新对话'
  if (activeSession.value?.title) return activeSession.value.title
  const conv = conversationItems.value.find(c => c.id === currentKey.value)
  return conv?.title || '对话'
})

function renderMarkdown(text) {
  return md.render(text || '')
}

function handleLogout() {
  userStore.logout()
  router.push('/login')
}

async function loadConversations() {
  try {
    const res = await request.get('/conversations')
    conversations.value = Array.isArray(res) ? res : (res.items || [])
  } catch {}
}

async function selectConversation(id) {
  const key = toKey(id)
  if (id === null) {
    currentKey.value = null
    return
  }
  currentKey.value = key
  const existing = ensureSession(key)
  existing.title = conversationItems.value.find(c => c.id === key)?.title || existing.title
  if (existing?.isStreaming || isPendingKey(key)) {
    scrollToBottom()
    return
  }
  try {
    existing.messages = await request.get(`/conversations/${Number(key)}/messages`)
    scrollToBottom()
  } catch {}
}

async function deleteConversation(id) {
  const key = toKey(id)
  try {
    if (isPendingKey(key)) {
      delete chatSessions[key]
    } else {
      await request.delete(`/conversations/${Number(key)}`)
      conversations.value = conversations.value.filter(c => toKey(c.id) !== key)
      delete chatSessions[key]
    }
    if (currentKey.value === key) {
      currentKey.value = null
    }
  } catch {}
}

function clearCurrentChat() {
  currentKey.value = null
}

async function sendMessage(question) {
  let key = currentKey.value
  if (!key) {
    key = `pending:${Date.now()}`
    currentKey.value = key
  }

  const session = ensureSession(key)
  if (!session || session.isStreaming) return

  session.isStreaming = true
  session.streamingText = ''
  session.sources = []
  session.title = session.messages.length ? session.title : titleFromQuestion(question)
  session.updated_at = new Date().toISOString()

  session.messages.push({
    id: Date.now(),
    role: 'user',
    content: question,
    created_at: new Date().toISOString(),
  })
  scrollToBottom()

  await streamChat(
    { question, conversation_id: isPersistedKey(key) ? Number(key) : null },
    {
      onChunk(chunk) {
        session.streamingText += chunk
        if (currentKey.value === key) scrollToBottom()
      },
      onSources(sources) {
        session.sources = sources
      },
      onDone(data) {
        session.messages.push({
          id: Date.now() + 1,
          role: 'assistant',
          content: session.streamingText,
          sources: { items: session.sources },
          created_at: new Date().toISOString(),
        })
        session.streamingText = ''
        session.isStreaming = false
        session.updated_at = new Date().toISOString()
        const persistedKey = toKey(data.conversation_id)
        if (persistedKey && persistedKey !== key) {
          chatSessions[persistedKey] = session
          delete chatSessions[key]
          if (currentKey.value === key) currentKey.value = persistedKey
        }
        loadConversations()
        if (currentKey.value === key || currentKey.value === persistedKey) scrollToBottom()
      },
      onError(err) {
        session.streamingText = ''
        session.isStreaming = false
        if (currentKey.value === key) ElMessage.error(err || '问答失败，请稍后重试')
      },
    }
  )
}

function handleFeedback({ messageId, value }) {
  // Send feedback to API (fire-and-forget)
  request.post(`/messages/${messageId}/feedback`, { value }).catch(() => {})
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

onMounted(loadConversations)
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100%;
  background: var(--color-bg);
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-nebula);
  min-width: 0;
  position: relative;
}
.chat-header {
  height: 60px;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: rgba(8, 12, 22, 0.6);
  backdrop-filter: blur(12px);
}
.chat-header .title {
  font-size: 15px;
  font-weight: 650;
  color: var(--color-text);
}
.chat-header .actions {
  display: flex;
  gap: 8px;
}
.chat-header .action-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.chat-header .action-btn:hover {
  background: var(--color-danger-soft);
}
.chat-header .action-btn svg {
  width: 18px;
  height: 18px;
  fill: var(--color-text-muted);
}
.chat-header .action-btn:hover svg {
  fill: var(--color-danger);
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 28px;
  background: transparent;
}
.welcome-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-subtle);
  text-align: center;
}
.welcome-state .welcome-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-purple));
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  box-shadow: 0 0 24px rgba(14, 165, 233, 0.3);
  position: relative;
}
.welcome-state .welcome-icon::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.2), rgba(139, 92, 246, 0.2));
  z-index: -1;
  filter: blur(10px);
}
.welcome-state .welcome-icon svg {
  width: 32px;
  height: 32px;
  fill: #fff;
}
.welcome-state h2 {
  font-size: 20px;
  color: var(--color-text);
  margin-bottom: 8px;
  background: linear-gradient(90deg, #fff, var(--color-cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.welcome-state p {
  font-size: 14px;
  color: var(--color-text-muted);
}
/* Message styling (mirrors MessageBubble but for streaming/welcome) */
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  max-width: 800px;
}
.message.assistant {
  /* default left-aligned */
}
.message .avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 600;
  background: linear-gradient(135deg, var(--color-success), var(--color-teal));
  color: #fff;
  box-shadow: 0 0 10px rgba(52, 211, 153, 0.3);
}
.message .bubble {
  padding: 14px 18px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.7;
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-top-left-radius: 4px;
  backdrop-filter: blur(8px);
}
.stream-wrapper {
  max-width: min(680px, calc(100vw - 420px));
  min-width: 0;
}
.stream-sources-note {
  width: fit-content;
  margin-top: 8px;
  padding: 6px 10px;
  border-radius: 7px;
  border: 1px solid rgba(14, 165, 233, 0.18);
  background: rgba(14, 165, 233, 0.08);
  color: var(--color-text-muted);
  font-size: 12px;
}
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}
.typing-indicator .dot {
  width: 8px;
  height: 8px;
  background: var(--color-primary);
  border-radius: 50%;
  animation: typing 1.4s infinite;
  box-shadow: 0 0 6px rgba(14, 165, 233, 0.4);
}
.typing-indicator .dot:nth-child(2) {
  animation-delay: 0.2s;
}
.typing-indicator .dot:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes typing {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-8px);
    opacity: 1;
  }
}

@media (max-width: 900px) {
  .chat-messages {
    padding: 18px;
  }
}
</style>
