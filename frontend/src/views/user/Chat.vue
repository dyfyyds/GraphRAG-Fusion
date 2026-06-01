<template>
  <div class="chat-layout">
    <ConversationList
      :conversations="conversations"
      :current-id="currentConvId"
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
          <div class="bubble" v-html="renderMarkdown(streamingText)"></div>
        </div>
      </div>

      <!-- Sources bar (shown during streaming) -->
      <div v-if="currentSources.length" class="sources-bar">
        <span class="sources-label">引用来源:</span>
        <SourceCard v-for="(s, i) in currentSources" :key="i" :source="s" />
      </div>

      <ChatInput :loading="isStreaming" @send="sendMessage" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ConversationList from '../../components/chat/ConversationList.vue'
import MessageBubble from '../../components/chat/MessageBubble.vue'
import SourceCard from '../../components/chat/SourceCard.vue'
import ChatInput from '../../components/chat/ChatInput.vue'
import { useUserStore } from '../../store/user'
import { streamChat } from '../../utils/sse'
import request from '../../api/request'
import markdownit from 'markdown-it'

const md = markdownit({ html: false, linkify: true })
const router = useRouter()
const userStore = useUserStore()

const conversations = ref([])
const messages = ref([])
const currentConvId = ref(null)
const streamingText = ref('')
const isStreaming = ref(false)
const currentSources = ref([])
const messagesRef = ref(null)

const currentTitle = computed(() => {
  if (!currentConvId.value) return '新对话'
  const conv = conversations.value.find(c => c.id === currentConvId.value)
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
  if (id === null) {
    currentConvId.value = null
    messages.value = []
    return
  }
  currentConvId.value = id
  try {
    messages.value = await request.get(`/conversations/${id}/messages`)
    scrollToBottom()
  } catch {}
}

async function deleteConversation(id) {
  try {
    await request.delete(`/conversations/${id}`)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (currentConvId.value === id) {
      currentConvId.value = null
      messages.value = []
    }
  } catch {}
}

function clearCurrentChat() {
  currentConvId.value = null
  messages.value = []
}

async function sendMessage(question) {
  isStreaming.value = true
  streamingText.value = ''
  currentSources.value = []

  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: question,
    created_at: new Date().toISOString(),
  })
  scrollToBottom()

  await streamChat(
    { question, conversation_id: currentConvId.value },
    {
      onChunk(chunk) {
        streamingText.value += chunk
        scrollToBottom()
      },
      onSources(sources) {
        currentSources.value = sources
      },
      onDone(data) {
        messages.value.push({
          id: Date.now() + 1,
          role: 'assistant',
          content: streamingText.value,
          sources: { items: currentSources.value },
          created_at: new Date().toISOString(),
        })
        streamingText.value = ''
        isStreaming.value = false
        currentConvId.value = data.conversation_id
        loadConversations()
      },
      onError(err) {
        ElMessage.error(err || '问答失败，请稍后重试')
        streamingText.value = ''
        isStreaming.value = false
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
.sources-bar {
  display: flex;
  gap: 8px;
  padding: 8px 24px;
  overflow-x: auto;
  border-top: 1px solid var(--color-border);
  background: rgba(8, 12, 22, 0.6);
  backdrop-filter: blur(8px);
  align-items: center;
}
.sources-label {
  font-size: 12px;
  color: var(--color-text-subtle);
  flex-shrink: 0;
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
