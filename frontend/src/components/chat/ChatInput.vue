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
  border-top: 1px solid #ebeef5;
  padding: 16px 24px;
}
.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  max-width: 800px;
  margin: 0 auto;
  background: #f5f7fa;
  border-radius: 12px;
  padding: 12px 16px;
  border: 1px solid #ebeef5;
  transition: border-color 0.2s, background 0.2s;
}
.input-wrapper.focused {
  border-color: #667eea;
  background: #fff;
}
.input-wrapper textarea {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  min-height: 24px;
  max-height: 120px;
  line-height: 1.5;
}
.input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.send-btn {
  width: 36px;
  height: 36px;
  background: #667eea;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s;
}
.send-btn:hover {
  background: #5a6fd6;
}
.send-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.send-btn svg {
  width: 18px;
  height: 18px;
  fill: #fff;
}
.input-hint {
  text-align: center;
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 8px;
}
</style>
