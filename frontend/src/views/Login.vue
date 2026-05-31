<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <div class="logo">
          <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" fill="#fff"/></svg>
        </div>
        <h1 class="login-title">RAG 智能问答系统</h1>
        <p class="login-subtitle">基于检索增强生成的企业知识库问答平台</p>
      </div>

      <div class="auth-tabs">
        <button type="button" :class="{ active: mode === 'login' }" @click="switchMode('login')">登录</button>
        <button type="button" :class="{ active: mode === 'register' }" @click="switchMode('register')">注册</button>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="handleSubmit">
        <el-form-item prop="username" class="form-group">
          <label class="form-label">用户名</label>
          <el-input v-model="form.username" placeholder="请输入用户名" size="large">
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item v-if="mode === 'register'" prop="email" class="form-group">
          <label class="form-label">邮箱</label>
          <el-input v-model="form.email" placeholder="请输入邮箱（选填）" size="large">
            <template #prefix>
              <el-icon><Message /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="password" class="form-group">
          <label class="form-label">密码</label>
          <el-input v-model="form.password" placeholder="请输入密码" type="password" show-password size="large" @keyup.enter="handleSubmit">
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item v-if="mode === 'register'" prop="confirmPassword" class="form-group">
          <label class="form-label">确认密码</label>
          <el-input v-model="form.confirmPassword" placeholder="请再次输入密码" type="password" show-password size="large" @keyup.enter="handleSubmit">
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <div v-if="mode === 'login'" class="login-options">
          <el-checkbox v-model="rememberMe">记住我</el-checkbox>
          <a href="#" class="forgot-link">忘记密码？</a>
        </div>

        <el-button type="primary" size="large" :loading="loading" class="login-btn" @click="handleSubmit">
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../store/user'
import { ElMessage } from 'element-plus'
import { User, Lock, Message } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const formRef = ref()
const loading = ref(false)
const rememberMe = ref(true)
const mode = ref('login')

const form = reactive({ username: '', password: '', email: '', confirmPassword: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (mode.value === 'register' && value && value.length < 6) {
          callback(new Error('密码至少 6 位'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  email: [{ type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }],
  confirmPassword: [
    {
      validator: (_rule, value, callback) => {
        if (mode.value === 'register' && !value) {
          callback(new Error('请确认密码'))
        } else if (mode.value === 'register' && value !== form.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

function switchMode(nextMode) {
  mode.value = nextMode
  form.password = ''
  form.confirmPassword = ''
  formRef.value?.clearValidate()
}

async function handleSubmit() {
  await formRef.value.validate()
  loading.value = true
  try {
    if (mode.value === 'register') {
      await userStore.register(form.username, form.password, form.email)
      ElMessage.success('注册成功')
    } else {
      await userStore.login(form.username, form.password)
      ElMessage.success('登录成功')
    }
    const redirect = route.query.redirect
    if (redirect) {
      router.push(redirect)
    } else if (userStore.userInfo?.role === 'admin') {
      router.push('/admin')
    } else {
      router.push('/')
    }
  } catch (err) {
    ElMessage.error(getErrorMessage(err))
  } finally {
    loading.value = false
  }
}

function getErrorMessage(err) {
  const data = err.response?.data
  const detail = data?.detail?.[0]
  if (detail?.loc?.includes('password') && detail?.type === 'string_too_short') return '密码至少 6 位'
  if (detail?.loc?.includes('username')) return '请输入 1-50 位用户名'
  if (detail?.loc?.includes('email')) return '请输入正确的邮箱地址'
  return data?.message || (mode.value === 'register' ? '注册失败' : '登录失败')
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}

.login-card {
  width: 400px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  padding: 36px 40px;
}

.login-header {
  text-align: center;
  margin-bottom: 24px;
}

.logo {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
}

.logo svg {
  width: 32px;
  height: 32px;
}

.login-title {
  font-size: 22px;
  color: #303133;
  font-weight: 600;
  margin: 0;
}

.login-subtitle {
  font-size: 13px;
  color: #909399;
  margin-top: 8px;
  margin-bottom: 0;
}

.form-group {
  margin-bottom: 20px;
}

.login-card :deep(.el-form-item__content) {
  display: block;
}

.auth-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 4px;
  margin-bottom: 22px;
  background: #f4f6fb;
  border-radius: 8px;
}

.auth-tabs button {
  height: 36px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #606266;
  font-size: 14px;
  cursor: pointer;
}

.auth-tabs button.active {
  background: #fff;
  color: #667eea;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.16);
}

.form-label {
  display: block;
  font-size: 14px;
  color: #606266;
  margin-bottom: 6px;
  font-weight: 500;
}

.login-card :deep(.el-input__wrapper) {
  border-radius: 8px;
  height: 44px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

.login-card :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c0c4cc inset;
}

.login-card :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #667eea inset;
}

.login-card :deep(.el-input__prefix .el-icon) {
  color: #c0c4cc;
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 16px 0;
}

.forgot-link {
  font-size: 13px;
  color: #667eea;
  text-decoration: none;
}

.forgot-link:hover {
  text-decoration: underline;
}

.login-btn {
  width: 100%;
  height: 44px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
}

.login-btn:hover {
  background: linear-gradient(135deg, #5a6fd6 0%, #6a4293 100%);
}
</style>
