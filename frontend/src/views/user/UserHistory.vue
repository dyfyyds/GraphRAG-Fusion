<template>
  <div class="user-history-page">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <div class="search-box">
          <el-icon><Search /></el-icon>
          <el-input v-model="keyword" placeholder="搜索问题内容..." clearable />
        </div>
      </div>
      <span class="record-count">共 {{ filteredMessages.length }} 条问答记录</span>
    </div>

    <!-- History List -->
    <div class="history-list">
      <template v-for="(group, date) in groupedMessages" :key="date">
        <div class="history-date">{{ group.label }}</div>
        <div
          v-for="item in group.items"
          :key="item.id"
          class="history-item"
          @click="showDetail(item)"
        >
          <div class="history-item-header">
            <div class="question">{{ item.content }}</div>
            <div class="time">{{ formatTime(item.created_at) }}</div>
          </div>
          <div class="history-item-body">
            <div class="answer">{{ item.answer || '暂无回答内容' }}</div>
          </div>
          <div class="history-item-footer">
            <div class="sources">
              <span v-for="(src, idx) in (item.source_names || []).slice(0, 3)" :key="idx" class="source-tag">{{ src }}</span>
              <span v-if="item.feedback === 'positive'" class="feedback-tag feedback-good">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 21h4V9H2v12zm20-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L13.17 1 6.59 7.59C6.22 7.95 6 8.45 6 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg>
                好评
              </span>
              <span v-else-if="item.feedback === 'negative'" class="feedback-tag feedback-bad">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 3h-4v12h4V3zM2 14c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L10.83 23l6.58-6.59c.37-.36.59-.86.59-1.41V5c0-1.1-.9-2-2-2H7c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2z"/></svg>
                差评
              </span>
            </div>
            <div class="actions" @click.stop>
              <span @click="showDetail(item)">查看详情</span>
              <span class="delete" @click="deleteItem(item)">删除</span>
            </div>
          </div>
        </div>
      </template>

      <el-empty v-if="!filteredMessages.length" description="暂无问答记录" />
    </div>

    <!-- Pagination -->
    <div class="pagination" v-if="totalPages > 1">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="filteredMessages.length"
        layout="prev, pager, next"
        small
      />
    </div>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" title="问答详情" width="680px" :close-on-click-modal="false">
      <div class="detail-body" v-if="detailItem">
        <div class="qa-bubble question">
          <div class="role q">我的提问</div>
          {{ detailItem.content }}
        </div>
        <div class="qa-bubble answer">
          <div class="role a">AI 回答</div>
          <span v-html="detailItem.answer || '暂无回答内容'"></span>
        </div>
        <div class="sources-section" v-if="detailItem.source_list && detailItem.source_list.length">
          <h4>引用来源</h4>
          <ul class="source-list">
            <li v-for="(src, idx) in detailItem.source_list" :key="idx">
              <div class="source-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div>
                <div style="font-weight: 500">{{ src.name }}</div>
                <div class="source-meta">{{ src.path }} | 相似度: {{ src.score }}</div>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElDialog, ElEmpty, ElIcon, ElInput, ElMessage, ElMessageBox, ElPagination } from 'element-plus'
import { Search, Document } from '@element-plus/icons-vue'
import request from '../../api/request'

const keyword = ref('')
const messages = ref([])
const currentPage = ref(1)
const pageSize = 10
const detailVisible = ref(false)
const detailItem = ref(null)

const filteredMessages = computed(() => {
  if (!keyword.value) return messages.value
  const kw = keyword.value.toLowerCase()
  return messages.value.filter(m => m.content?.toLowerCase().includes(kw))
})

const totalPages = computed(() => Math.ceil(filteredMessages.value.length / pageSize))

const groupedMessages = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const pageItems = filteredMessages.value.slice(start, start + pageSize)
  const groups = {}

  for (const item of pageItems) {
    const dateStr = item.created_at ? item.created_at.substring(0, 10) : '未知日期'
    if (!groups[dateStr]) {
      groups[dateStr] = {
        label: getDateLabel(dateStr),
        items: [],
      }
    }
    groups[dateStr].items.push(item)
  }

  return groups
})

function getDateLabel(dateStr) {
  const today = new Date().toISOString().substring(0, 10)
  const yesterday = new Date(Date.now() - 86400000).toISOString().substring(0, 10)

  if (dateStr === today) return `今天 (${dateStr})`
  if (dateStr === yesterday) return `昨天 (${dateStr})`
  return dateStr
}

function formatTime(datetime) {
  if (!datetime) return ''
  // If today, show HH:mm; otherwise show MM-DD HH:mm
  const today = new Date().toISOString().substring(0, 10)
  const dateStr = datetime.substring(0, 10)
  if (dateStr === today) {
    return datetime.substring(11, 16)
  }
  return datetime.substring(5, 16)
}

async function loadMessages() {
  try {
    const convs = await request.get('/conversations')
    const convList = Array.isArray(convs) ? convs : (convs.items || [])
    const all = []
    for (const c of convList) {
      const msgs = await request.get(`/conversations/${c.id}/messages`)
      const msgList = Array.isArray(msgs) ? msgs : (msgs.items || [])
      // Build a map of assistant answers by conversation
      const answers = msgList.filter(m => m.role === 'assistant')
      const userMsgs = msgList.filter(m => m.role === 'user')
      userMsgs.forEach((m, idx) => {
        m.conversation_id = c.id
        m.answer = answers[idx]?.content || ''
        m.source_names = answers[idx]?.source_names || c.source_names || []
        m.source_list = answers[idx]?.source_list || c.source_list || []
        m.feedback = m.feedback || answers[idx]?.feedback || null
      })
      all.push(...userMsgs)
    }
    // Sort by created_at descending
    all.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
    messages.value = all
  } catch {}
}

function showDetail(item) {
  detailItem.value = item
  detailVisible.value = true
}

async function deleteItem(item) {
  try {
    await ElMessageBox.confirm('确定删除这条问答记录？', '确认删除')
    await request.delete(`/conversations/${item.conversation_id}/messages/${item.id}`)
    ElMessage.success('已删除')
    loadMessages()
  } catch {}
}

onMounted(loadMessages)
</script>

<style scoped>
.user-history-page {
  padding: 24px;
  max-width: 980px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-box {
  display: flex;
  align-items: center;
  border: 1px solid var(--color-border);
  border-radius: 7px;
  padding: 0 12px;
  height: 36px;
  background: var(--color-surface);
  width: 300px;
  backdrop-filter: blur(8px);
}

.search-box .el-icon {
  color: var(--color-text-subtle);
  margin-right: 8px;
  font-size: 16px;
}

.search-box :deep(.el-input__wrapper) {
  box-shadow: none !important;
  padding: 0;
  background: transparent !important;
}

.search-box :deep(.el-input__inner) {
  font-size: 13px;
  color: var(--color-text) !important;
}

.record-count {
  font-size: 13px;
  color: var(--color-text-subtle);
}

.history-list {
  max-width: 900px;
}

.history-date {
  font-size: 13px;
  color: var(--color-primary);
  font-weight: 650;
  padding: 12px 0 8px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 12px;
  letter-spacing: 0.3px;
}

.history-item {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xs);
  margin-bottom: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s ease;
  backdrop-filter: blur(8px);
}

.history-item:hover {
  border-color: var(--color-border-glow);
  box-shadow: var(--shadow-glow);
  transform: translateY(-1px);
}

.history-item-header {
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.history-item-header .question {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  flex: 1;
  margin-right: 16px;
}

.history-item-header .time {
  font-size: 12px;
  color: var(--color-text-subtle);
  white-space: nowrap;
}

.history-item-body {
  padding: 0 20px 16px;
}

.history-item-body .answer {
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.history-item-footer {
  padding: 10px 20px;
  background: rgba(20, 28, 50, 0.4);
  border-top: 1px solid var(--color-border-soft);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-item-footer .sources {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.source-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--color-primary-soft);
  border: 1px solid rgba(14, 165, 233, 0.15);
  border-radius: 999px;
  font-size: 11px;
  color: var(--color-primary);
}

.feedback-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
}

.feedback-tag svg {
  width: 12px;
  height: 12px;
  fill: currentColor;
}

.feedback-good {
  background: var(--color-success-soft);
  color: var(--color-success);
}

.feedback-bad {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.history-item-footer .actions {
  display: flex;
  gap: 12px;
}

.history-item-footer .actions span {
  font-size: 12px;
  color: var(--color-text-subtle);
  cursor: pointer;
  transition: color 0.2s;
}

.history-item-footer .actions span:hover {
  color: var(--color-primary);
}

.history-item-footer .actions span.delete:hover {
  color: var(--color-danger);
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px 0;
}

/* Detail Dialog */
.qa-bubble {
  padding: 14px 16px;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  line-height: 1.7;
}

.qa-bubble.question {
  background: var(--color-primary-soft);
  border: 1px solid rgba(14, 165, 233, 0.2);
}

.qa-bubble.answer {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.qa-bubble .role {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
}

.qa-bubble .role.q {
  color: var(--color-primary);
}

.qa-bubble .role.a {
  color: var(--color-success);
}

.sources-section {
  margin-top: 16px;
}

.sources-section h4 {
  font-size: 14px;
  color: var(--color-text-muted);
  margin-bottom: 10px;
}

.source-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.source-list li {
  padding: 8px 12px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-soft);
  border-radius: 7px;
  margin-bottom: 6px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.source-list li .source-icon {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-purple));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.source-list li .source-icon .el-icon {
  font-size: 12px;
  color: #fff;
}

.source-meta {
  font-size: 11px;
  color: var(--color-text-subtle);
  margin-top: 2px;
}

@media (max-width: 760px) {
  .user-history-page {
    padding: 16px;
  }

  .toolbar,
  .toolbar-left {
    align-items: stretch;
    flex-direction: column;
  }

  .search-box {
    width: 100%;
  }

  .history-item-header,
  .history-item-footer {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }
}
</style>
