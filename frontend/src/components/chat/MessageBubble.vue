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
  margin-bottom: 24px;
  max-width: 800px;
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
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
}
.message.assistant .avatar {
  background: linear-gradient(135deg, #67c23a, #4caf50);
  color: #fff;
}
.bubble-wrapper {
  max-width: 640px;
}
.message .bubble {
  padding: 14px 18px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
}
.message.user .bubble {
  background: #667eea;
  color: #fff;
  border-top-right-radius: 4px;
}
.message.assistant .bubble {
  background: #f5f7fa;
  color: #303133;
  border-top-left-radius: 4px;
}
.message .bubble :deep(p) {
  margin-bottom: 8px;
}
.message .bubble :deep(p:last-child) {
  margin-bottom: 0;
}
.message .bubble :deep(strong) {
  color: #667eea;
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
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Consolas', monospace;
  font-size: 13px;
}
.message.user .bubble :deep(code) {
  background: rgba(255, 255, 255, 0.2);
}
.sources {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e8e8e8;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.sources .title {
  width: 100%;
  font-size: 12px;
  color: #909399;
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
  border-radius: 6px;
  border: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: #fff;
  font-size: 14px;
  transition: all 0.2s;
  user-select: none;
}
.feedback-btn:hover {
  border-color: #667eea;
  background: #ecf5ff;
}
.feedback-btn.active {
  border-color: #667eea;
  background: #ecf5ff;
}
</style>
