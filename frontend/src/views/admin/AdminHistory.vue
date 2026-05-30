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
              <span v-if="row.feedback === 'positive'" class="icon like">👍</span>
              <span v-else-if="row.feedback === 'negative'" class="icon dislike">👎</span>
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
                <span v-if="detailItem.feedback === 'positive'">👍 好评</span>
                <span v-else-if="detailItem.feedback === 'negative'">👎 差评</span>
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
import { ElMessage } from 'element-plus'
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
    const convs = await request.get('/conversations')
    const convList = Array.isArray(convs) ? convs : (convs.items || [])
    const all = []
    const users = new Set()
    for (const c of convList.slice(0, 50)) {
      const msgs = await request.get(`/conversations/${c.id}/messages`)
      const msgList = Array.isArray(msgs) ? msgs : (msgs.items || [])
      for (const m of msgList) {
        if (m.role === 'user') {
          m.conversation_id = c.id
          m.username = c.username || m.username || ''
          m.sources = m.sources || (c.sources ? c.sources.join(', ') : '')
          m.source_list = m.source_list || c.source_list || []
          m.answer = m.answer || ''
          all.push(m)
          if (m.username) users.add(m.username)
        }
      }
    }
    messages.value = all
    userList.value = Array.from(users)
  } catch {}
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
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.search-box {
  display: flex;
  align-items: center;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 0 12px;
  height: 36px;
  background: #fff;
  width: 240px;
}

.search-box .el-icon {
  color: #c0c4cc;
  margin-right: 8px;
  font-size: 16px;
}

.search-box :deep(.el-input__wrapper) {
  box-shadow: none !important;
  padding: 0;
}

.search-box :deep(.el-input__inner) {
  font-size: 13px;
}

.table-card {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.question-text {
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.user-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.user-tag .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #409eff;
}

.source-text {
  font-size: 12px;
  color: #606266;
}

.feedback-icons {
  display: flex;
  gap: 4px;
}

.feedback-icons .icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.feedback-icons .like {
  background: #f0f9eb;
  color: #67c23a;
}

.feedback-icons .dislike {
  background: #fef0f0;
  color: #f56c6c;
}

.feedback-icons .none {
  background: #f5f7fa;
  color: #c0c4cc;
}

.action-btn {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  border: none;
  background: transparent;
  color: #409eff;
}

.action-btn:hover {
  background: #ecf5ff;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
}

.pagination .info {
  font-size: 13px;
  color: #909399;
}

/* Detail Dialog Styles */
.detail-section {
  margin-bottom: 24px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h4 {
  font-size: 14px;
  color: #606266;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.info-grid .label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.info-grid .value {
  font-size: 14px;
  color: #303133;
}

.qa-bubble {
  padding: 14px 16px;
  border-radius: 10px;
  margin-bottom: 12px;
  font-size: 14px;
  line-height: 1.7;
}

.qa-bubble.question {
  background: #ecf5ff;
  border: 1px solid #d9ecff;
}

.qa-bubble.answer {
  background: #f5f7fa;
  border: 1px solid #ebeef5;
}

.qa-bubble .role {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
}

.qa-bubble .role.q {
  color: #409eff;
}

.qa-bubble .role.a {
  color: #67c23a;
}

.source-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.source-list li {
  padding: 8px 12px;
  background: #f9fafc;
  border-radius: 6px;
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
  background: #667eea;
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
  color: #909399;
  margin-top: 2px;
}
</style>
