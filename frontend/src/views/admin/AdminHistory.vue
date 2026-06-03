<template>
  <div class="admin-history-page">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <div class="search-box">
          <el-icon><Search /></el-icon>
          <el-input v-model="keyword" placeholder="搜索问题内容..." clearable @clear="loadData" @keyup.enter="loadData" />
        </div>
        <el-select v-model="userFilter" placeholder="全部用户" clearable @change="loadData" style="width: 130px">
          <el-option label="全部用户" value="" />
          <el-option v-for="u in userList" :key="u" :label="u" :value="u" />
        </el-select>
        <el-select v-model="feedbackFilter" placeholder="全部反馈" clearable @change="loadData" style="width: 130px">
          <el-option label="全部反馈" value="" />
          <el-option label="好评" value="positive" />
          <el-option label="差评" value="negative" />
          <el-option label="未评价" value="none" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 280px" @change="loadData" />
      </div>
      <div style="display: flex; gap: 12px">
        <el-button @click="exportCSV">
          <el-icon><Download /></el-icon> 导出 Excel
        </el-button>
      </div>
    </div>

    <!-- Table Card -->
    <div class="table-card">
      <el-table :data="pagedMessages" style="width: 100%" row-key="id">
        <el-table-column width="40">
          <template #header>
            <el-checkbox v-model="selectAll" @change="toggleSelectAll" />
          </template>
          <template #default="{ row }">
            <el-checkbox v-model="row._selected" />
          </template>
        </el-table-column>
        <el-table-column label="问题内容" min-width="320">
          <template #default="{ row }">
            <div class="question-text">{{ row.content }}</div>
          </template>
        </el-table-column>
        <el-table-column label="提问用户" width="140">
          <template #default="{ row }">
            <span class="user-tag">
              <span class="dot"></span>
              {{ row.username || '未知用户' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="引用来源" min-width="180">
          <template #default="{ row }">
            <span class="source-text">{{ row.sources || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="反馈" width="80">
          <template #default="{ row }">
            <div class="feedback-icons">
              <span v-if="row.feedback === 'positive'" class="icon like" title="好评">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 21h4V9H2v12zm20-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L13.17 1 6.59 7.59C6.22 7.95 6 8.45 6 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg>
              </span>
              <span v-else-if="row.feedback === 'negative'" class="icon dislike" title="差评">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 3h-4v12h4V3zM2 14c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L10.83 23l6.58-6.59c.37-.36.59-.86.59-1.41V5c0-1.1-.9-2-2-2H7c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2z"/></svg>
              </span>
              <span v-else class="icon none">—</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="提问时间" width="160" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <button class="action-btn" @click="showDetail(row)">详情</button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination">
        <div class="info">共 {{ filteredMessages.length }} 条，每页 {{ pageSize }} 条</div>
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="filteredMessages.length"
          layout="prev, pager, next"
          small
        />
      </div>
    </div>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailVisible" title="问答详情" width="680px" :close-on-click-modal="false">
      <div class="detail-body" v-if="detailItem">
        <!-- Basic Info -->
        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="info-grid">
            <div>
              <div class="label">提问用户</div>
              <div class="value">{{ detailItem.username || '未知用户' }}</div>
            </div>
            <div>
              <div class="label">提问时间</div>
              <div class="value">{{ detailItem.created_at }}</div>
            </div>
            <div>
              <div class="label">对话ID</div>
              <div class="value">#CONV-{{ detailItem.conversation_id || detailItem.id }}</div>
            </div>
            <div>
              <div class="label">反馈</div>
              <div class="value">
                <span v-if="detailItem.feedback === 'positive'" class="feedback-value feedback-good">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 21h4V9H2v12zm20-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L13.17 1 6.59 7.59C6.22 7.95 6 8.45 6 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/></svg>
                  好评
                </span>
                <span v-else-if="detailItem.feedback === 'negative'" class="feedback-value feedback-bad">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 3h-4v12h4V3zM2 14c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L10.83 23l6.58-6.59c.37-.36.59-.86.59-1.41V5c0-1.1-.9-2-2-2H7c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2z"/></svg>
                  差评
                </span>
                <span v-else>未评价</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Q&A Content -->
        <div class="detail-section">
          <h4>对话内容</h4>
          <div class="qa-bubble question">
            <div class="role q">用户提问</div>
            {{ detailItem.content }}
          </div>
          <div class="qa-bubble answer">
            <div class="role a">AI 回答</div>
            <span v-html="detailItem.answer || '暂无回答内容'"></span>
          </div>
        </div>

        <!-- Sources -->
        <div class="detail-section" v-if="detailItem.source_list && detailItem.source_list.length">
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
import {
  ElButton,
  ElCheckbox,
  ElDatePicker,
  ElDialog,
  ElIcon,
  ElInput,
  ElMessage,
  ElOption,
  ElPagination,
  ElSelect,
  ElTable,
  ElTableColumn,
} from 'element-plus'
import { Search, Download, Document } from '@element-plus/icons-vue'
import request from '../../api/request'

const keyword = ref('')
const feedbackFilter = ref('')
const userFilter = ref('')
const dateRange = ref(null)
const selectAll = ref(false)
const messages = ref([])
const userList = ref([])
const currentPage = ref(1)
const pageSize = 10
const detailVisible = ref(false)
const detailItem = ref(null)

const filteredMessages = computed(() => {
  let list = messages.value
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter(m => m.content?.toLowerCase().includes(kw))
  }
  if (userFilter.value) {
    list = list.filter(m => m.username === userFilter.value)
  }
  if (feedbackFilter.value) {
    if (feedbackFilter.value === 'none') {
      list = list.filter(m => !m.feedback)
    } else {
      list = list.filter(m => m.feedback === feedbackFilter.value)
    }
  }
  if (dateRange.value && dateRange.value.length === 2) {
    const [start, end] = dateRange.value
    list = list.filter(m => {
      if (!m.created_at) return false
      const d = m.created_at.substring(0, 10)
      return d >= start && d <= end
    })
  }
  return list
})

const pagedMessages = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredMessages.value.slice(start, start + pageSize)
})

function toggleSelectAll(val) {
  pagedMessages.value.forEach(row => { row._selected = val })
}

async function loadData() {
  try {
    const result = await request.get('/conversations/admin', { params: { page: 1, size: 100 } })
    const convList = result.items || []
    const all = []
    const users = new Set()
    for (const c of convList) {
      // AdminConversationOut already contains question, answer, sources, feedback
      all.push({
        id: c.id,
        content: c.question || c.title,
        answer: c.answer || '',
        username: c.username || '',
        sources: c.sources ? (c.sources.items || []).map(s => s.document_name || '未知来源').join(', ') : '',
        source_list: c.sources ? (c.sources.items || []) : [],
        feedback: c.feedback === 1 ? 'positive' : c.feedback === -1 ? 'negative' : null,
        created_at: c.created_at,
        conversation_id: c.id,
      })
      if (c.username) users.add(c.username)
    }
    messages.value = all
    userList.value = Array.from(users)
  } catch (e) {
    console.error('Failed to load admin history:', e)
  }
}

function showDetail(row) {
  detailItem.value = row
  detailVisible.value = true
}

function exportCSV() {
  const header = '问题,用户,满意度,时间\n'
  const rows = filteredMessages.value.map(m =>
    `"${(m.content || '').replace(/"/g, '""')}",${m.username || ''},${m.feedback || ''},${m.created_at || ''}`
  ).join('\n')
  const blob = new Blob(['﻿' + header + rows], { type: 'text/csv;charset=utf-8;' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'history.csv'
  a.click()
}

onMounted(loadData)
</script>

<style scoped>
.admin-history-page {
  padding: 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 22px;
  flex-wrap: wrap;
  gap: 14px;
}

.toolbar-left {
  display: flex;
  gap: 14px;
  align-items: center;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  align-items: center;
  border: 1px solid rgba(125, 211, 252, 0.22);
  border-radius: 8px;
  padding: 0 14px;
  height: 38px;
  background: rgba(8, 15, 30, 0.82);
  width: 250px;
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

.table-card {
  background: rgba(8, 15, 30, 0.86);
  border: 1px solid rgba(125, 211, 252, 0.2);
  border-radius: 9px;
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.45);
  overflow: hidden;
  backdrop-filter: blur(12px);
}

.question-text {
  max-width: 330px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: #eaf2ff;
}

.user-tag {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  color: #eaf2ff;
}

.user-tag .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #7dd3fc;
  box-shadow: 0 0 8px rgba(125, 211, 252, 0.5);
}

.source-text {
  font-size: 12px;
  color: #93c5fd;
  font-weight: 600;
}

.feedback-icons {
  display: flex;
  gap: 5px;
}

.feedback-icons .icon {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.feedback-icons .icon svg,
.feedback-value svg {
  width: 13px;
  height: 13px;
  fill: currentColor;
}

.feedback-icons .like {
  background: rgba(52, 211, 153, 0.15);
  color: #34d399;
}

.feedback-icons .dislike {
  background: rgba(248, 113, 113, 0.15);
  color: #f87171;
}

.feedback-icons .none {
  background: rgba(8, 15, 30, 0.82);
  color: #94a3b8;
  border: 1px solid rgba(125, 211, 252, 0.15);
}

.feedback-value {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

.feedback-good {
  color: #34d399;
}

.feedback-bad {
  color: #f87171;
}

.action-btn {
  padding: 5px 10px;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  background: transparent;
  color: #7dd3fc;
  transition: all 0.25s;
}

.action-btn:hover {
  background: rgba(125, 211, 252, 0.15);
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px;
}

.pagination .info {
  font-size: 13px;
  color: #94a3b8;
  font-weight: 600;
}

/* Detail Dialog Styles */
.detail-section {
  margin-bottom: 26px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h4 {
  font-size: 14px;
  color: #93c5fd;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(125, 211, 252, 0.18);
  font-weight: 700;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.info-grid .label {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 5px;
  font-weight: 600;
}

.info-grid .value {
  font-size: 14px;
  color: #eaf2ff;
}

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
  color: #eaf2ff;
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

@media (max-width: 900px) {
  .toolbar-left {
    align-items: stretch;
    flex-direction: column;
    width: 100%;
  }

  .search-box {
    width: 100%;
  }
}
</style>
