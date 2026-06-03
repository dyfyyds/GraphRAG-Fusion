<template>
  <div class="message" :class="message.role">
    <div class="avatar">{{ avatarText }}</div>
    <div class="bubble-wrapper">
      <div class="bubble" v-html="renderedContent"></div>
      <div v-if="sourceItems.length" class="sources">
        <button type="button" class="sources-toggle" @click="sourcesExpanded = !sourcesExpanded">
          <span>引用来源</span>
          <strong>{{ sourceItems.length }}</strong>
          <svg viewBox="0 0 24 24" :class="{ expanded: sourcesExpanded }" aria-hidden="true">
            <path d="M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6z" />
          </svg>
        </button>
        <div v-if="sourcesExpanded" class="sources-list">
          <SourceCard v-for="(s, i) in sourceItems" :key="i" :source="s" />
        </div>
      </div>
      <div v-if="message.role === 'assistant'" class="feedback-row">
        <button
          type="button"
          class="feedback-btn"
          :class="{ active: feedback === 'good' }"
          title="有帮助"
          @click="setFeedback('good')"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 21h4V9H2v12zm20-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L13.17 1 6.59 7.59C6.22 7.95 6 8.45 6 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg>
        </button>
        <button
          type="button"
          class="feedback-btn"
          :class="{ active: feedback === 'bad' }"
          title="没帮助"
          @click="setFeedback('bad')"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 3h-4v12h4V3zM2 14c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L10.83 23l6.58-6.59c.37-.36.59-.86.59-1.41V5c0-1.1-.9-2-2-2H7c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2z"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import markdownit from 'markdown-it'
import hljs from 'highlight.js/lib/core'
import bash from 'highlight.js/lib/languages/bash'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'
import python from 'highlight.js/lib/languages/python'
import xml from 'highlight.js/lib/languages/xml'
import SourceCard from './SourceCard.vue'
import { useUserStore } from '../../store/user'

hljs.registerLanguage('bash', bash)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('json', json)
hljs.registerLanguage('python', python)
hljs.registerLanguage('py', python)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('xml', xml)

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
const sourcesExpanded = ref(false)

const renderedContent = computed(() => md.render(props.message.content || ''))
const sourceItems = computed(() => props.message.sources?.items || [])

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
  margin-top: 8px;
}
.sources-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 30px;
  padding: 0 10px;
  border: 1px solid rgba(14, 165, 233, 0.2);
  border-radius: 7px;
  background: rgba(14, 165, 233, 0.08);
  color: var(--color-text-muted);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.sources-toggle:hover {
  border-color: rgba(14, 165, 233, 0.36);
  color: var(--color-primary);
  background: rgba(14, 165, 233, 0.12);
}
.sources-toggle strong {
  color: var(--color-primary);
  font-weight: 650;
}
.sources-toggle svg {
  width: 14px;
  height: 14px;
  fill: currentColor;
  transition: transform 0.2s;
}
.sources-toggle svg.expanded {
  transform: rotate(180deg);
}
.sources-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
  padding: 10px;
  border-radius: 8px;
  background: rgba(8, 12, 22, 0.42);
  border: 1px solid rgba(148, 163, 184, 0.12);
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
  color: var(--color-text-subtle);
  font-size: 14px;
  transition: all 0.2s;
  user-select: none;
}
.feedback-btn svg {
  width: 15px;
  height: 15px;
  fill: currentColor;
}
.feedback-btn:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  box-shadow: 0 0 8px rgba(14, 165, 233, 0.15);
}
.feedback-btn.active {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
  box-shadow: 0 0 8px rgba(14, 165, 233, 0.15);
}

@media (max-width: 900px) {
  .bubble-wrapper {
    max-width: calc(100vw - 128px);
  }
}
</style>
