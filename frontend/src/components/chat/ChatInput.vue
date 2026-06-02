<template>
  <div class="chat-input-area">
    <div class="input-wrapper" :class="{ focused: isFocused }">
      <textarea
        ref="inputRef"
        v-model="text"
        placeholder="输入您的问题..."
        rows="1"
        :disabled="loading"
        @focus="isFocused = true"
        @blur="isFocused = false"
        @keydown="handleKeydown"
        @input="autoResize"
      ></textarea>
      <div class="input-actions">
        <div class="send-btn" :class="{ disabled: !text.trim() || loading }" title="发送" @click="handleSend">
          <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" /></svg>
        </div>
      </div>
    </div>
    <div class="input-hint">基于 RAG 架构，回答来源于企业知识库，仅供参考 | Enter 发送, Shift+Enter 换行</div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({ loading: Boolean })
const emit = defineEmits(['send'])

const text = ref('')
const inputRef = ref()
const isFocused = ref(false)

function autoResize() {
  nextTick(() => {
    const el = inputRef.value
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 120) + 'px'
    }
  })
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function handleSend() {
  const q = text.value.trim()
  if (!q || props.loading) return
  emit('send', q)
  text.value = ''
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.style.height = 'auto'
    }
  })
}
</script>

<style scoped>
.chat-input-area {
  border-top: 1px solid var(--color-border);
  padding: 16px 24px;
  background: rgba(8, 12, 22, 0.7);
  backdrop-filter: blur(12px);
}
.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  max-width: 860px;
  margin: 0 auto;
  background: var(--color-surface);
  border-radius: 10px;
  padding: 12px 16px;
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-xs);
  transition: all 0.25s ease;
  backdrop-filter: blur(8px);
}
.input-wrapper.focused {
  border-color: var(--color-primary);
  background: var(--color-surface-solid);
  box-shadow: 0 0 0 3px var(--color-primary-soft), 0 0 20px rgba(14, 165, 233, 0.1);
}
.input-wrapper textarea {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text);
  resize: none;
  min-height: 24px;
  max-height: 120px;
  line-height: 1.5;
}
.input-wrapper textarea::placeholder {
  color: var(--color-text-subtle);
}
.input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.send-btn {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-purple));
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 0 12px rgba(14, 165, 233, 0.3);
}
.send-btn:hover {
  box-shadow: 0 0 20px rgba(14, 165, 233, 0.45);
  transform: translateY(-1px);
}
.send-btn.disabled {
  opacity: 0.4;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}
.send-btn svg {
  width: 18px;
  height: 18px;
  fill: #fff;
}
.input-hint {
  text-align: center;
  font-size: 11px;
  color: var(--color-text-subtle);
  margin-top: 8px;
}
</style>
