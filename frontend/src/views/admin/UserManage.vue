<template>
  <div class="user-manage-page">
    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <div class="search-box">
          <el-icon><Search /></el-icon>
          <el-input v-model="search" placeholder="搜索用户名或邮箱..." clearable @clear="loadUsers" @keyup.enter="loadUsers" />
        </div>
        <el-select v-model="roleFilter" placeholder="全部角色" clearable @change="loadUsers" style="width: 130px">
          <el-option label="全部角色" value="" />
          <el-option label="管理员" value="admin" />
          <el-option label="普通用户" value="user" />
        </el-select>
        <el-select v-model="statusFilter" placeholder="全部状态" clearable @change="loadUsers" style="width: 130px">
          <el-option label="全部状态" value="" />
          <el-option label="启用" :value="true" />
          <el-option label="禁用" :value="false" />
        </el-select>
      </div>
      <el-button type="primary" @click="showDialog()">
        <el-icon><Plus /></el-icon> 新增用户
      </el-button>
    </div>

    <!-- Table Card -->
    <div class="table-card">
      <el-table :data="pagedUsers" style="width: 100%" row-key="id">
        <el-table-column label="用户信息" min-width="220">
          <template #default="{ row }">
            <div class="user-cell">
              <div class="avatar" :style="{ background: avatarGradient(row.username) }">
                {{ avatarLetter(row.username) }}
              </div>
              <div>
                <div class="user-name">{{ row.username }}</div>
                <div class="user-id">ID: {{ row.id }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <span class="role-tag" :class="row.role === 'admin' ? 'role-admin' : 'role-user'">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="问答次数" width="100" prop="qa_count">
          <template #default="{ row }">
            <span>{{ row.qa_count ?? '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <div class="status-switch" :class="row.status ? 'on' : 'off'" @click="toggleStatus(row)"></div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="120" />
        <el-table-column prop="last_login" label="最后登录" width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <div class="actions">
              <button class="action-btn edit" @click="showDialog(row)">编辑</button>
              <button class="action-btn reset" @click="resetPassword(row)">重置密码</button>
              <button class="action-btn delete" @click="deleteUser(row)">删除</button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination">
        <div class="info">共 {{ filteredUsers.length }} 条，每页 {{ pageSize }} 条</div>
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="filteredUsers.length"
          layout="prev, pager, next"
          small
        />
      </div>
    </div>

    <!-- Add/Edit User Dialog -->
    <el-dialog v-model="dialogVisible" :title="editingUser ? '编辑用户' : '新增用户'" width="480px" :close-on-click-modal="false">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" :disabled="!!editingUser" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" required v-if="!editingUser">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="邮箱" required>
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="角色" required>
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveUser">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import request from '../../api/request'

const users = ref([])
const search = ref('')
const roleFilter = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = 10
const dialogVisible = ref(false)
const editingUser = ref(null)
const form = reactive({ username: '', password: '', email: '', role: 'user' })

const avatarColors = [
  'linear-gradient(135deg, #f56c6c, #e74c3c)',
  'linear-gradient(135deg, #409eff, #337ecc)',
  'linear-gradient(135deg, #67c23a, #4caf50)',
  'linear-gradient(135deg, #e6a23c, #f39c12)',
  'linear-gradient(135deg, #909399, #606266)',
  'linear-gradient(135deg, #667eea, #764ba2)',
]

function avatarLetter(name) {
  return name ? name.charAt(0).toUpperCase() : '?'
}

function avatarGradient(name) {
  if (!name) return avatarColors[0]
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return avatarColors[Math.abs(hash) % avatarColors.length]
}

const filteredUsers = computed(() => {
  let list = users.value
  if (search.value) {
    const kw = search.value.toLowerCase()
    list = list.filter(u => u.username?.toLowerCase().includes(kw) || u.email?.toLowerCase().includes(kw))
  }
  if (roleFilter.value) {
    list = list.filter(u => u.role === roleFilter.value)
  }
  if (statusFilter.value !== '') {
    list = list.filter(u => u.status === statusFilter.value)
  }
  return list
})

const pagedUsers = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredUsers.value.slice(start, start + pageSize)
})

async function loadUsers() {
  try {
    const res = await request.get('/users')
    users.value = res.items || res || []
  } catch {}
}

function showDialog(user = null) {
  editingUser.value = user
  Object.assign(form, user
    ? { username: user.username, email: user.email, role: user.role, password: '' }
    : { username: '', password: '', email: '', role: 'user' }
  )
  dialogVisible.value = true
}

async function saveUser() {
  try {
    if (editingUser.value) {
      await request.put(`/users/${editingUser.value.id}`, { email: form.email, role: form.role })
    } else {
      await request.post('/users', form)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadUsers()
  } catch {
    ElMessage.error('操作失败')
  }
}

async function toggleStatus(row) {
  try {
    row.status = !row.status
    await request.put(`/users/${row.id}`, { status: row.status })
  } catch {
    row.status = !row.status
  }
}

async function resetPassword(row) {
  try {
    await ElMessageBox.confirm(`确定重置用户 ${row.username} 的密码？`, '重置密码')
    await request.put(`/users/${row.id}/reset-password`, { new_password: '123456' })
    ElMessage.success('密码已重置为 123456')
  } catch {}
}

async function deleteUser(row) {
  try {
    await ElMessageBox.confirm(`确定删除用户 ${row.username}？`, '确认删除')
    await request.delete(`/users/${row.id}`)
    ElMessage.success('已删除')
    loadUsers()
  } catch {}
}

onMounted(loadUsers)
</script>

<style scoped>
.user-manage-page {
  padding: 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-box {
  display: flex;
  align-items: center;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  padding: 0 12px;
  height: 36px;
  background: #fff;
  width: 260px;
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

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-cell .avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.user-cell .user-name {
  font-weight: 500;
  font-size: 14px;
  color: #303133;
}

.user-cell .user-id {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
}

.role-tag {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 12px;
}

.role-admin {
  background: #fef0f0;
  color: #f56c6c;
}

.role-user {
  background: #ecf5ff;
  color: #409eff;
}

.status-switch {
  width: 40px;
  height: 20px;
  border-radius: 10px;
  position: relative;
  cursor: pointer;
  transition: background 0.3s;
}

.status-switch.on {
  background: #67c23a;
}

.status-switch.off {
  background: #dcdfe6;
}

.status-switch::after {
  content: '';
  position: absolute;
  top: 2px;
  width: 16px;
  height: 16px;
  background: #fff;
  border-radius: 50%;
  transition: left 0.3s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.status-switch.on::after {
  left: 22px;
}

.status-switch.off::after {
  left: 2px;
}

.actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  border: none;
  background: transparent;
}

.action-btn.edit {
  color: #409eff;
}

.action-btn.edit:hover {
  background: #ecf5ff;
}

.action-btn.reset {
  color: #e6a23c;
}

.action-btn.reset:hover {
  background: #fdf6ec;
}

.action-btn.delete {
  color: #f56c6c;
}

.action-btn.delete:hover {
  background: #fef0f0;
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
</style>
