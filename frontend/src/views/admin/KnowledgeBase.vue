<template>
  <div class="knowledge-page">
    <!-- Stats Bar -->
    <div class="stats-bar">
      <div class="stat-item">
        <div><span class="num">{{ documents.length }}</span></div>
        <div><span class="label">文档总数</span></div>
      </div>
      <div class="stat-item">
        <div><span class="num">{{ statusCounts.completed }}</span></div>
        <div><span class="label">已解析</span></div>
      </div>
      <div class="stat-item">
        <div><span class="num">{{ statusCounts.parsing }}</span></div>
        <div><span class="label">解析中</span></div>
      </div>
      <div class="stat-item">
        <div><span class="num">{{ statusCounts.building_graph }}</span></div>
        <div><span class="label">图谱构建中</span></div>
      </div>
      <div class="stat-item">
        <div><span class="num">{{ statusCounts.failed }}</span></div>
        <div><span class="label">解析失败</span></div>
      </div>
      <div class="stat-item">
        <div><span class="num">{{ statusCounts.graph_failed }}</span></div>
        <div><span class="label">图谱失败</span></div>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <div class="search-box">
          <svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
          <input v-model="searchKeyword" type="text" placeholder="搜索文档名称..." />
        </div>
        <el-select v-model="filterType" class="filter-select" placeholder="全部类型">
          <el-option label="全部类型" value="" />
          <el-option label="PDF" value="pdf" />
          <el-option label="Word" value="docx" />
          <el-option label="TXT" value="txt" />
          <el-option label="Markdown" value="md" />
        </el-select>
        <el-select v-model="filterStatus" class="filter-select" placeholder="全部状态">
          <el-option label="全部状态" value="" />
          <el-option label="已完成" value="completed" />
          <el-option label="解析中" value="parsing" />
          <el-option label="图谱构建中" value="building_graph" />
          <el-option label="图谱失败" value="graph_failed" />
          <el-option label="待解析" value="pending" />
          <el-option label="解析失败" value="failed" />
        </el-select>
      </div>
      <div class="toolbar-right">
        <template v-if="selectedIds.length > 1">
          <span class="selected-count">已选 {{ selectedIds.length }} 项</span>
          <el-button class="btn-default" @click="batchReparse">批量解析</el-button>
          <el-button class="btn-default btn-batch-delete" @click="batchDelete">批量删除</el-button>
        </template>
        <el-button class="btn-default" @click="showUploadModal = true">
          <el-icon><Upload /></el-icon>
          上传文档
        </el-button>
      </div>
    </div>

    <!-- Table -->
    <div class="table-card">
      <table>
        <thead>
          <tr>
            <th style="width: 40px">
              <input type="checkbox" v-model="selectAll" @change="toggleSelectAll" />
            </th>
            <th>文档名称</th>
            <th>类型</th>
            <th>大小</th>
            <th>分块数</th>
            <th>状态</th>
            <th>上传时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredDocuments" :key="row.id">
            <td>
              <input type="checkbox" v-model="selectedIds" :value="row.id" />
            </td>
            <td>
              <div class="file-icon">
                <div class="icon" :class="fileIconClass(row.file_type)">
                  <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"/></svg>
                </div>
                <span>{{ row.name }}</span>
              </div>
            </td>
            <td>{{ fileTypeName(row.file_type) }}</td>
            <td>{{ formatFileSize(row.file_size) }}</td>
            <td>{{ ['completed', 'building_graph', 'graph_failed'].includes(row.status) ? row.chunk_count : '—' }}</td>
            <td>
              <span class="status-tag" :class="'status-' + row.status" :title="row.error_message || ''">{{ statusLabel(row.status) }}</span>
              <div v-if="row.error_message" class="error-tip">{{ row.error_message }}</div>
            </td>
            <td>{{ formatTime(row.created_at) }}</td>
            <td>
              <div class="actions">
                <button
                  class="action-btn view"
                  :disabled="!['completed', 'graph_failed'].includes(row.status)"
                  @click="['completed', 'graph_failed'].includes(row.status) && viewChunks(row)"
                >预览</button>
                <button
                  class="action-btn reparse"
                  :disabled="row.status === 'parsing' || row.status === 'building_graph'"
                  @click="(row.status !== 'parsing' && row.status !== 'building_graph') && reparseDoc(row)"
                >{{ row.status === 'pending' ? '解析' : '重解析' }}</button>
                <button class="action-btn delete" @click="deleteDoc(row)">删除</button>
              </div>
            </td>
          </tr>
          <tr v-if="filteredDocuments.length === 0">
            <td colspan="8" class="empty-cell">暂无数据</td>
          </tr>
        </tbody>
      </table>
      <div class="list-summary">共 {{ filteredDocuments.length }} 条，滚动查看全部文档</div>
    </div>

    <!-- Upload Modal -->
    <div v-if="showUploadModal" class="modal-overlay" @click.self="showUploadModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>上传文档</h3>
          <svg class="modal-close" viewBox="0 0 24 24" @click="showUploadModal = false"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        </div>
        <div class="modal-body">
          <div
            class="upload-zone"
            :class="{ 'upload-zone-active': isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="triggerFileInput"
          >
            <svg viewBox="0 0 24 24"><path d="M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z"/></svg>
            <h4>将文件拖拽到此处，或 <span class="highlight">点击上传</span></h4>
            <p>支持 PDF、Word、TXT、Markdown 格式，单文件不超过 50MB</p>
          </div>
          <input
            ref="fileInputRef"
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.md"
            style="display: none"
            @change="handleFileSelect"
          />
          <div class="upload-list" v-if="uploadFiles.length > 0">
            <div class="upload-item" v-for="(file, index) in uploadFiles" :key="index">
              <div class="file-info">
                <div class="upload-file-icon" :class="fileIconClass(getExtension(file.name))">
                  <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6z"/></svg>
                </div>
                <span>{{ file.name }}</span>
                <span class="file-size">{{ formatFileSize(file.size) }}</span>
              </div>
              <svg class="remove" viewBox="0 0 24 24" @click="removeUploadFile(index)"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <el-button @click="showUploadModal = false">取消</el-button>
          <el-button type="primary" :disabled="uploadFiles.length === 0" :loading="uploading" @click="startUpload">开始上传</el-button>
        </div>
      </div>
    </div>

    <!-- Chunk Preview Drawer -->
    <el-drawer v-model="drawerVisible" title="文档分块" size="50%">
      <div class="chunk-list">
        <div v-for="chunk in chunks" :key="chunk.id" class="chunk-item">
          <div class="chunk-meta">分块 #{{ chunk.chunk_index }}<span v-if="chunk.page_number"> &middot; 第{{ chunk.page_number }}页</span></div>
          <div class="chunk-text">{{ chunk.content }}</div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElButton, ElDrawer, ElIcon, ElMessage, ElMessageBox, ElOption, ElSelect } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import request from '../../api/request'
import { emit } from '../../utils/eventBus'
import { subscribeDocumentEvents } from '../../utils/documentEvents'

// ---- Data ----
const documents = ref([])
const chunks = ref([])
const drawerVisible = ref(false)
let unsubscribeDocumentEvents = null

// Filter / search state
const searchKeyword = ref('')
const filterType = ref('')
const filterStatus = ref('')

// Selection
const selectAll = ref(false)
const selectedIds = ref([])

// Upload modal
const showUploadModal = ref(false)
const isDragging = ref(false)
const uploadFiles = ref([])
const uploading = ref(false)
const fileInputRef = ref(null)

// ---- Computed ----
const statusCounts = computed(() => {
  const counts = { completed: 0, parsing: 0, building_graph: 0, graph_failed: 0, pending: 0, failed: 0 }
  documents.value.forEach(d => {
    if (counts[d.status] !== undefined) counts[d.status]++
  })
  return counts
})

const filteredDocuments = computed(() => {
  return documents.value.filter(d => {
    const matchKeyword = !searchKeyword.value || d.name.toLowerCase().includes(searchKeyword.value.toLowerCase())
    const matchType = !filterType.value || d.file_type === filterType.value
    const matchStatus = !filterStatus.value || d.status === filterStatus.value
    return matchKeyword && matchType && matchStatus
  })
})

// ---- Helpers ----
function fileIconClass(type) {
  const t = (type || '').toLowerCase()
  if (t === 'pdf') return 'icon-pdf'
  if (t === 'docx' || t === 'doc') return 'icon-docx'
  if (t === 'txt') return 'icon-txt'
  if (t === 'md') return 'icon-md'
  return 'icon-txt'
}

function fileTypeName(type) {
  const t = (type || '').toLowerCase()
  if (t === 'pdf') return 'PDF'
  if (t === 'docx' || t === 'doc') return 'Word'
  if (t === 'txt') return 'TXT'
  if (t === 'md') return 'Markdown'
  return t.toUpperCase()
}

function statusLabel(status) {
  const map = { completed: '已完成', parsing: '解析中', building_graph: '图谱构建中', graph_failed: '图谱失败', pending: '待解析', failed: '解析失败' }
  return map[status] || status
}

function formatFileSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatTime(isoString) {
  if (!isoString) return '—'
  const d = new Date(isoString)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function getExtension(filename) {
  return filename.includes('.') ? filename.split('.').pop().toLowerCase() : ''
}

function toggleSelectAll() {
  if (selectAll.value) {
    selectedIds.value = filteredDocuments.value.map(d => d.id)
  } else {
    selectedIds.value = []
  }
}

// ---- Upload logic ----
function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleDrop(e) {
  isDragging.value = false
  const files = Array.from(e.dataTransfer.files)
  addFiles(files)
}

function handleFileSelect(e) {
  const files = Array.from(e.target.files)
  addFiles(files)
  e.target.value = ''
}

function addFiles(files) {
  const allowedExts = ['pdf', 'docx', 'txt', 'md']
  for (const file of files) {
    const ext = getExtension(file.name)
    if (!allowedExts.includes(ext)) {
      ElMessage.warning(`不支持的文件格式: ${file.name}`)
      continue
    }
    if (file.size > 50 * 1024 * 1024) {
      ElMessage.warning(`文件过大(>50MB): ${file.name}`)
      continue
    }
    uploadFiles.value.push(file)
  }
}

function removeUploadFile(index) {
  uploadFiles.value.splice(index, 1)
}

// 并发上传数：多个文件同时上传（避免一次性几十个请求压垮服务，限制为 5）
const UPLOAD_CONCURRENCY = 5

async function uploadOne(file, maxRetries = 5) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const formData = new FormData()
      formData.append('file', file)
      await request.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return // 成功，直接返回
    } catch (error) {
      // 如果是 429 限流且还有重试机会，等待后重试
      if (error?.response?.status === 429 && attempt < maxRetries) {
        // 从 Retry-After 头或指数退避计算等待时间
        const retryAfter = parseInt(error.response.headers?.['retry-after'])
        const delay = retryAfter
          ? retryAfter * 1000
          : Math.min(1000 * Math.pow(2, attempt), 10000) // 指数退避，最大 10 秒
        await new Promise(r => setTimeout(r, delay))
        continue
      }
      throw error // 非 429 错误或重试用尽，抛出
    }
  }
}

async function startUpload() {
  if (uploadFiles.value.length === 0) return

  const files = [...uploadFiles.value]
  // 上传请求一旦发出，后端即异步解析；这里立即关闭弹窗并清空列表，
  // 不再等待全部解析完成（解析/图谱构建会在后台进行，列表通过 SSE 自动刷新）
  uploadFiles.value = []
  showUploadModal.value = false
  uploading.value = false
  ElMessage.success(`已开始上传 ${files.length} 个文件，解析与图谱构建将在后台进行`)

  // 并发上传：用固定数量的 worker 从队列里取文件，互不阻塞
  let cursor = 0
  let success = 0
  const failedFiles = []

  async function worker() {
    while (cursor < files.length) {
      const file = files[cursor++]
      try {
        await uploadOne(file)
        success++
      } catch (error) {
        failedFiles.push(file)
        console.error('上传失败:', file.name, error)
      }
    }
  }

  const workers = Array.from(
    { length: Math.min(UPLOAD_CONCURRENCY, files.length) },
    () => worker(),
  )
  await Promise.all(workers)

  await loadDocuments()
  if (failedFiles.length === 0) {
    ElMessage.success(`全部 ${success} 个文件上传完成`)
  } else {
    // 失败的文件保留下来，重新放回上传列表并打开弹窗，方便用户一键重试
    // （合并时按文件名去重，避免与上传期间用户新添加的文件重复）
    const existingNames = new Set(uploadFiles.value.map(f => f.name))
    const retained = failedFiles.filter(f => !existingNames.has(f.name))
    uploadFiles.value = [...retained, ...uploadFiles.value]
    showUploadModal.value = true
    const names = failedFiles.map(f => f.name)
    ElMessage.warning(`上传完成：成功 ${success} 个，失败 ${failedFiles.length} 个（${names.slice(0, 3).join('、')}${names.length > 3 ? ' 等' : ''}）。失败文件已保留，可点击“开始上传”重试`)
  }
}

// ---- API calls ----
async function loadDocuments() {
  try {
    const res = await request.get('/documents?all=true')
    applyDocuments(Array.isArray(res) ? res : (res.items || []))

    const graphFailed = documents.value.find(d => d.status === 'graph_failed' && d.error_message)
    if (graphFailed) {
      ElMessage.warning(graphFailed.error_message)
    }
  } catch {}
}

function applyDocuments(nextDocuments) {
  const oldStatuses = documents.value.map(d => `${d.id}:${d.status}:${d.chunk_count}:${d.error_message || ''}`)
  documents.value = nextDocuments
  const newStatuses = documents.value.map(d => `${d.id}:${d.status}:${d.chunk_count}:${d.error_message || ''}`)

  if (oldStatuses.length > 0 && JSON.stringify(oldStatuses) !== JSON.stringify(newStatuses)) {
    emit('documents:updated', { documents: documents.value })
  }
}

watch(filteredDocuments, (rows) => {
  const visibleIds = new Set(rows.map(row => row.id))
  selectedIds.value = selectedIds.value.filter(id => visibleIds.has(id))
  selectAll.value = rows.length > 0 && selectedIds.value.length === rows.length
})

async function viewChunks(row) {
  try {
    chunks.value = await request.get(`/documents/${row.id}/chunks`)
    drawerVisible.value = true
  } catch {}
}

async function reparseDoc(row) {
  try {
    await request.post(`/documents/${row.id}/reparse`)
    ElMessage.success('已提交重新解析')
    await loadDocuments()
  } catch {
    ElMessage.error('重解析失败')
  }
}

async function deleteDoc(row) {
  await ElMessageBox.confirm('确定删除此文档？', '确认')
  try {
    const res = await request.delete(`/documents/${row.id}`)
    if (res?.success) {
      ElMessage.success('已删除')
    } else {
      ElMessage.warning(res?.message || '部分数据删除失败')
    }
    await loadDocuments()
  } catch {}
}

function clearSelection() {
  selectedIds.value = []
  selectAll.value = false
}

// 并发执行器：固定数量 worker 处理任务队列，返回成功/失败计数
async function runPool(items, limit, fn) {
  let cursor = 0
  let ok = 0
  let fail = 0
  async function worker() {
    while (cursor < items.length) {
      const item = items[cursor++]
      try {
        await fn(item)
        ok++
      } catch (e) {
        fail++
        console.error(e)
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, () => worker()))
  return { ok, fail }
}

async function batchReparse() {
  const ids = [...selectedIds.value]
  if (ids.length === 0) return
  try {
    await ElMessageBox.confirm(`确定对选中的 ${ids.length} 个文档重新解析？`, '批量解析')
  } catch {
    return
  }
  const { ok, fail } = await runPool(ids, 5, (id) => request.post(`/documents/${id}/reparse`))
  clearSelection()
  await loadDocuments()
  if (fail === 0) ElMessage.success(`已提交 ${ok} 个文档重新解析，后台进行中`)
  else ElMessage.warning(`提交完成：成功 ${ok} 个，失败 ${fail} 个`)
}

async function batchDelete() {
  const ids = [...selectedIds.value]
  if (ids.length === 0) return
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${ids.length} 个文档？该操作不可恢复。`, '批量删除', { type: 'warning' })
  } catch {
    return
  }
  const { ok, fail } = await runPool(ids, 5, (id) => request.delete(`/documents/${id}`))
  clearSelection()
  await loadDocuments()
  if (fail === 0) ElMessage.success(`已删除 ${ok} 个文档`)
  else ElMessage.warning(`删除完成：成功 ${ok} 个，失败 ${fail} 个`)
}

onMounted(() => {
  loadDocuments()
  unsubscribeDocumentEvents = subscribeDocumentEvents(({ event, data }) => {
    if (event !== 'documents') return
    applyDocuments(data.items || [])
  })
})
onUnmounted(() => {
  unsubscribeDocumentEvents?.()
})
</script>

<style scoped>
.knowledge-page {
  padding: 0;
}

/* Stats Bar */
.stats-bar {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 22px;
}
.stat-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  padding: 16px 18px;
  background: rgba(8, 15, 30, 0.86);
  border: 1px solid rgba(125, 211, 252, 0.2);
  border-radius: 9px;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.4);
  font-size: 13px;
  color: #93c5fd;
  backdrop-filter: blur(12px);
}
.stat-item .num {
  font-size: 22px;
  font-weight: 800;
  color: #eaf2ff;
}
.stat-item .label {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 600;
}

/* Toolbar */
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
.toolbar-right {
  display: flex;
  gap: 14px;
  align-items: center;
}
.selected-count {
  font-size: 13px;
  color: #7dd3fc;
  font-weight: 700;
}
.btn-batch-delete {
  color: #f87171;
  border-color: rgba(248, 113, 113, 0.3);
}
.btn-batch-delete:hover {
  color: #fff;
  background: #f87171;
  border-color: #f87171;
}
.search-box {
  display: flex;
  align-items: center;
  border: 1px solid rgba(125, 211, 252, 0.22);
  border-radius: 8px;
  padding: 0 14px;
  height: 38px;
  background: rgba(8, 15, 30, 0.82);
  width: 290px;
  backdrop-filter: blur(12px);
}
.search-box svg {
  width: 16px;
  height: 16px;
  fill: #94a3b8;
  margin-right: 10px;
  flex-shrink: 0;
}
.search-box input {
  border: none;
  outline: none;
  flex: 1;
  font-size: 13px;
  background: transparent;
  color: #eaf2ff;
}
.search-box input::placeholder {
  color: #64748b;
}
.filter-select {
  width: 140px;
}

/* Table Card */
.table-card {
  background: rgba(8, 15, 30, 0.86);
  border: 1px solid rgba(125, 211, 252, 0.2);
  border-radius: 9px;
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.45);
  max-height: min(640px, calc(100vh - 270px));
  overflow: auto;
  backdrop-filter: blur(12px);
}
table {
  width: 100%;
  border-collapse: collapse;
}
thead {
  background: rgba(8, 15, 30, 0.95);
  position: sticky;
  top: 0;
  z-index: 2;
}
th {
  padding: 16px 18px;
  text-align: left;
  font-size: 12px;
  font-weight: 700;
  color: #93c5fd;
  border-bottom: 1px solid rgba(125, 211, 252, 0.18);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
td {
  padding: 16px 18px;
  font-size: 13px;
  color: #eaf2ff;
  border-bottom: 1px solid rgba(125, 211, 252, 0.08);
}
tr:hover {
  background: rgba(25, 38, 68, 0.7);
}

/* File Icon */
.file-icon {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.file-icon .icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.file-icon .icon svg {
  width: 16px;
  height: 16px;
  fill: #fff;
}
.icon-pdf {
  background: linear-gradient(135deg, #f87171, #dc2626);
  box-shadow: 0 0 10px rgba(248, 113, 113, 0.3);
}
.icon-docx {
  background: linear-gradient(135deg, #38bdf8, #0284c7);
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
}
.icon-txt {
  background: linear-gradient(135deg, #94a3b8, #64748b);
  box-shadow: 0 0 10px rgba(148, 163, 184, 0.3);
}
.icon-md {
  background: linear-gradient(135deg, #34d399, #059669);
  box-shadow: 0 0 10px rgba(52, 211, 153, 0.3);
}

/* Status Tags */
.status-tag {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  display: inline-block;
}
.status-pending {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
}
.status-parsing {
  background: rgba(125, 211, 252, 0.15);
  color: #7dd3fc;
  animation: pulse 1.5s infinite;
  border: 1px solid rgba(125, 211, 252, 0.3);
}
.status-completed {
  background: rgba(52, 211, 153, 0.15);
  color: #34d399;
  border: 1px solid rgba(52, 211, 153, 0.3);
}
.status-building_graph {
  background: rgba(125, 211, 252, 0.15);
  color: #7dd3fc;
  animation: pulse 1.5s infinite;
  border: 1px solid rgba(125, 211, 252, 0.3);
}
.status-failed {
  background: rgba(248, 113, 113, 0.15);
  color: #f87171;
  border: 1px solid rgba(248, 113, 113, 0.3);
}
.status-graph_failed {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(251, 191, 36, 0.3);
}
.error-tip {
  max-width: 230px;
  margin-top: 6px;
  color: #fca5a5;
  font-size: 12px;
  line-height: 1.4;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* Actions */
.actions {
  display: flex;
  gap: 8px;
}
.action-btn {
  padding: 5px 10px;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  background: transparent;
  transition: all 0.25s;
}

.action-btn:disabled {
  color: #64748b;
  cursor: not-allowed;
  opacity: 0.5;
}
.action-btn.view {
  color: #7dd3fc;
}
.action-btn.view:hover:not(:disabled) {
  background: rgba(125, 211, 252, 0.15);
}
.action-btn.reparse {
  color: #fbbf24;
}
.action-btn.reparse:hover:not(:disabled) {
  background: rgba(251, 191, 36, 0.15);
}
.action-btn.delete {
  color: #f87171;
}
.action-btn.delete:hover {
  background: rgba(248, 113, 113, 0.15);
}

.empty-cell {
  text-align: center;
  color: #94a3b8;
  padding: 44px;
}

.list-summary {
  position: sticky;
  bottom: 0;
  padding: 14px 18px;
  border-top: 1px solid rgba(125, 211, 252, 0.15);
  background: rgba(8, 15, 30, 0.95);
  font-size: 13px;
  color: #94a3b8;
  backdrop-filter: blur(14px);
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(3, 7, 18, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(8px);
}
.modal {
  background: linear-gradient(135deg, rgba(8, 15, 30, 0.96), rgba(15, 23, 42, 0.94));
  border: 1px solid rgba(125, 211, 252, 0.28);
  border-radius: 12px;
  width: 580px;
  max-height: 82vh;
  overflow-y: auto;
  box-shadow: 0 28px 64px rgba(0, 0, 0, 0.7), 0 0 40px rgba(125, 211, 252, 0.1);
}
.modal-header {
  padding: 22px 26px;
  border-bottom: 1px solid rgba(125, 211, 252, 0.18);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-header h3 {
  font-size: 17px;
  margin: 0;
  color: #eaf2ff;
  font-weight: 700;
}
.modal-close {
  width: 26px;
  height: 26px;
  cursor: pointer;
  fill: #94a3b8;
  transition: fill 0.25s;
}
.modal-close:hover {
  fill: #eaf2ff;
}
.modal-body {
  padding: 26px;
}
.modal-footer {
  padding: 18px 26px;
  border-top: 1px solid rgba(125, 211, 252, 0.18);
  display: flex;
  justify-content: flex-end;
  gap: 14px;
}

/* Upload Zone */
.upload-zone {
  border: 2px dashed rgba(125, 211, 252, 0.25);
  border-radius: 10px;
  padding: 52px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
}
.upload-zone:hover,
.upload-zone-active {
  border-color: #7dd3fc;
  background: rgba(125, 211, 252, 0.08);
  box-shadow: 0 0 24px rgba(125, 211, 252, 0.12);
}
.upload-zone svg {
  width: 52px;
  height: 52px;
  fill: #94a3b8;
  margin-bottom: 18px;
}
.upload-zone h4 {
  font-size: 16px;
  color: #eaf2ff;
  margin-bottom: 10px;
  font-weight: 700;
}
.upload-zone p {
  font-size: 13px;
  color: #94a3b8;
}
.upload-zone .highlight {
  color: #7dd3fc;
  cursor: pointer;
  font-weight: 600;
}

/* Upload List */
.upload-list {
  margin-top: 18px;
  max-height: 250px;
  overflow-y: auto;
  padding-right: 4px;
}
.upload-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: rgba(8, 15, 30, 0.86);
  border: 1px solid rgba(125, 211, 252, 0.15);
  border-radius: 8px;
  margin-bottom: 10px;
}
.upload-item .file-info {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #eaf2ff;
}
.upload-item .file-size {
  font-size: 12px;
  color: #94a3b8;
}
.upload-item .remove {
  width: 20px;
  height: 20px;
  cursor: pointer;
  fill: #94a3b8;
  transition: fill 0.25s;
}
.upload-item .remove:hover {
  fill: #f87171;
}
.upload-file-icon {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.upload-file-icon svg {
  width: 14px;
  height: 14px;
  fill: #fff;
}

/* Chunk list */
.chunk-list {
  max-height: 420px;
  overflow-y: auto;
}
.chunk-item {
  padding: 14px;
  background: rgba(8, 15, 30, 0.86);
  border-radius: 9px;
  margin-bottom: 10px;
  border-left: 3px solid #7dd3fc;
  border: 1px solid rgba(125, 211, 252, 0.18);
  border-left: 3px solid #7dd3fc;
}
.chunk-item .chunk-meta {
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 8px;
  font-weight: 600;
}
.chunk-item .chunk-text {
  font-size: 13px;
  color: #eaf2ff;
  line-height: 1.7;
  white-space: pre-wrap;
}

@media (max-width: 1100px) {
  .stats-bar {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 760px) {
  .stats-bar {
    grid-template-columns: repeat(2, 1fr);
  }

  .toolbar,
  .toolbar-left,
  .toolbar-right {
    align-items: stretch;
    flex-direction: column;
  }

  .search-box,
  .filter-select {
    width: 100%;
  }
}
</style>
