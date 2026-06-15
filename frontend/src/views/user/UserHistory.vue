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
          <span v-html="DOMPurify.sanitize(detailItem.answer || '暂无回答内容')"></span>
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
import DOMPurify from 'dompurify'
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
  padding: 26px;
  max-width: 980px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 22px;
  gap: 14px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  gap: 14px;
  align-items: center;
}

.search-box {
  display: flex;
  align-items: center;
  border: 1px solid rgba(125, 211, 252, 0.22);
  border-radius: 8px;
  padding: 0 14px;
  height: 38px;
  background: rgba(8, 15, 30, 0.82);
  width: 310px;
  backdrop-filter: blur(12px);
}

.search-box .el-icon {
  color: #94a3b8;
  margin-right: 10px;
  font-size: 16px;
}

.search-box :deep(.el-input__wrapper) {
  box-shadow: none !important;
  padding: 0;
  background: transparent !important;
}

.search-box :deep(.el-input__inner) {
  font-size: 13px;
  color: #eaf2ff !important;
}

.record-count {
  font-size: 13px;
  color: #94a3b8;
  font-weight: 600;
}

.history-list {
  max-width: 900px;
}

.history-date {
  font-size: 13px;
  color: #7dd3fc;
  font-weight: 700;
  padding: 14px 0 10px;
  border-bottom: 1px solid rgba(125, 211, 252, 0.18);
  margin-bottom: 14px;
  letter-spacing: 0.3px;
}

.history-item {
  background: rgba(8, 15, 30, 0.86);
  border: 1px solid rgba(125, 211, 252, 0.2);
  border-radius: 10px;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.4);
  margin-bottom: 14px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(12px);
}

.history-item:hover {
  border-color: rgba(125, 211, 252, 0.42);
  box-shadow: 0 0 24px rgba(125, 211, 252, 0.18);
  transform: translateY(-2px);
}

.history-item-header {
  padding: 18px 22px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.history-item-header .question {
  font-size: 14px;
  font-weight: 600;
  color: #eaf2ff;
  flex: 1;
  margin-right: 18px;
}

.history-item-header .time {
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
}

.history-item-body {
  padding: 0 22px 18px;
}

.history-item-body .answer {
  font-size: 13px;
  color: #93c5fd;
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.history-item-footer {
  padding: 12px 22px;
  background: rgba(8, 15, 30, 0.95);
  border-top: 1px solid rgba(125, 211, 252, 0.12);
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
  padding: 3px 10px;
  background: rgba(125, 211, 252, 0.12);
  border: 1px solid rgba(125, 211, 252, 0.2);
  border-radius: 999px;
  font-size: 11px;
  color: #7dd3fc;
  font-weight: 600;
}

.feedback-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 999px;
  font-weight: 600;
}

.feedback-tag svg {
  width: 12px;
  height: 12px;
  fill: currentColor;
}

.feedback-good {
  background: rgba(52, 211, 153, 0.15);
  color: #34d399;
  border: 1px solid rgba(52, 211, 153, 0.3);
}

.feedback-bad {
  background: rgba(248, 113, 113, 0.15);
  color: #f87171;
  border: 1px solid rgba(248, 113, 113, 0.3);
}

.history-item-footer .actions {
  display: flex;
  gap: 14px;
}

.history-item-footer .actions span {
  font-size: 12px;
  color: #94a3b8;
  cursor: pointer;
  transition: color 0.25s;
  font-weight: 600;
}

.history-item-footer .actions span:hover {
  color: #7dd3fc;
}

.history-item-footer .actions span.delete:hover {
  color: #f87171;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 28px 0;
}

/* Detail Dialog */
.qa-bubble {
  padding: 16px 18px;
  border-radius: 10px;
  margin-bottom: 14px;
  font-size: 14px;
  line-height: 1.75;
}

.qa-bubble.question {
  background: rgba(125, 211, 252, 0.1);
  border: 1px solid rgba(125, 211, 252, 0.25);
}

.qa-bubble.answer {
  background: rgba(8, 15, 30, 0.86);
  border: 1px solid rgba(125, 211, 252, 0.2);
}

.qa-bubble .role {
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 8px;
}

.qa-bubble .role.q {
  color: #7dd3fc;
}

.qa-bubble .role.a {
  color: #34d399;
}

.sources-section {
  margin-top: 18px;
}

.sources-section h4 {
  font-size: 14px;
  color: #93c5fd;
  margin-bottom: 12px;
  font-weight: 700;
}

.source-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.source-list li {
  padding: 10px 14px;
  background: rgba(8, 15, 30, 0.86);
  border: 1px solid rgba(125, 211, 252, 0.15);
  border-radius: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #eaf2ff;
}

.source-list li .source-icon {
  width: 22px;
  height: 22px;
  border-radius: 5px;
  background: linear-gradient(135deg, #7dd3fc, #a78bfa);
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
  color: #94a3b8;
  margin-top: 3px;
}

@media (max-width: 760px) {
  .user-history-page {
    padding: 18px;
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
    gap: 12px;
  }
}
</style>
