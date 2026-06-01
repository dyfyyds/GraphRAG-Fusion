<template>
  <div class="message" :class="message.role">
    <div class="avatar">{{ avatarText }}</div>
    <div class="bubble-wrapper">
      <div class="bubble" v-html="renderedContent"></div>
      <div v-if="message.sources?.items?.length" class="sources">
        <div class="title">引用来源</div>
        <SourceCard v-for="(s, i) in message.sources.items" :key="i" :source="s" />
      </div>
      <div v-if="message.role === 'assistant'" class="feedback-row">
        <div
          class="feedback-btn"
          :class="{ active: feedback === 'good' }"
          title="有帮助"
          @click="setFeedback('good')"
        >&#128077;</div>
        <div
          class="feedback-btn"
          :class="{ active: feedback === 'bad' }"
          title="没帮助"
          @click="setFeedback('bad')"
        >&#128078;</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import markdownit from 'markdown-it'
import hljs from 'highlight.js'
import SourceCard from './SourceCard.vue'
import { useUserStore } from '../../store/user'

const md = markdownit({
  html: false,
  linkify: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(str, { language: lang }).value
    }
    return md.utils.escapeHtml(str)
  },
})

const props = defineProps({ message: Object })
const emit = defineEmits(['feedback'])
const userStore = useUserStore()
const feedback = ref(props.message.feedback || null)

const renderedContent = computed(() => md.render(props.message.content || ''))

const avatarText = computed(() => {
  if (props.message.role === 'user') {
    return (userStore.userInfo?.username || '用').charAt(0)
  }
  return 'AI'
})

function setFeedback(val) {
  feedback.value = feedback.value === val ? null : val
  emit('feedback', { messageId: props.message.id, value: feedback.value })
}
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 22px;
  max-width: min(860px, 100%);
}
.message.user {
  flex-direction: row-reverse;
  margin-left: auto;
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
}
.message.user .avatar {
  background: linear-gradient(135deg, var(--color-primary), var(--color-purple));
  color: #fff;
  box-shadow: 0 0 10px rgba(14, 165, 233, 0.3);
}
.message.assistant .avatar {
  background: linear-gradient(135deg, var(--color-success), var(--color-teal));
  color: #fff;
  box-shadow: 0 0 10px rgba(52, 211, 153, 0.3);
}
.bubble-wrapper {
  max-width: min(680px, calc(100vw - 420px));
  min-width: 0;
}
.message .bubble {
  padding: 14px 18px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}
.message.user .bubble {
  background: linear-gradient(135deg, var(--color-primary), #0369a1);
  color: #fff;
  border-top-right-radius: 4px;
  box-shadow: 0 0 16px rgba(14, 165, 233, 0.2);
}
.message.assistant .bubble {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-top-left-radius: 4px;
  backdrop-filter: blur(8px);
}
.message .bubble :deep(p) {
  margin-bottom: 8px;
}
.message .bubble :deep(p:last-child) {
  margin-bottom: 0;
}
.message .bubble :deep(strong) {
  color: var(--color-primary);
}
.message.user .bubble :deep(strong) {
  color: #fff;
}
.message .bubble :deep(ul) {
  margin: 8px 0;
  padding-left: 20px;
}
.message .bubble :deep(li) {
  margin-bottom: 4px;
}
.message .bubble :deep(code) {
  background: rgba(14, 165, 233, 0.1);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Consolas', monospace;
  font-size: 13px;
  color: var(--color-cyan);
  border: 1px solid rgba(14, 165, 233, 0.15);
}
.message.user .bubble :deep(code) {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  border-color: rgba(255, 255, 255, 0.2);
}
.message .bubble :deep(pre) {
  background: var(--color-surface-solid) !important;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 12px;
  overflow-x: auto;
}
.message .bubble :deep(a) {
  color: var(--color-primary);
  text-decoration: none;
}
.message .bubble :deep(a:hover) {
  text-decoration: underline;
}
.message .bubble :deep(blockquote) {
  border-left: 3px solid var(--color-primary);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--color-text-muted);
}
.sources {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.sources .title {
  width: 100%;
  font-size: 12px;
  color: var(--color-text-subtle);
  margin-bottom: 4px;
}
.feedback-row {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
.feedback-btn {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: var(--color-surface);
  font-size: 14px;
  transition: all 0.2s;
  user-select: none;
}
.feedback-btn:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  box-shadow: 0 0 8px rgba(14, 165, 233, 0.15);
}
.feedback-btn.active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  box-shadow: 0 0 8px rgba(14, 165, 233, 0.15);
}

@media (max-width: 900px) {
  .bubble-wrapper {
    max-width: calc(100vw - 128px);
  }
}
</style>
