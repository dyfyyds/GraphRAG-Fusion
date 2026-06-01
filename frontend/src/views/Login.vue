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
  padding: 32px 16px;
  background:
    radial-gradient(ellipse at 30% 30%, rgba(14, 165, 233, 0.06) 0%, transparent 50%),
    radial-gradient(ellipse at 70% 70%, rgba(139, 92, 246, 0.04) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 50%, rgba(232, 121, 249, 0.02) 0%, transparent 50%),
    var(--color-bg);
}

.login-card {
  width: min(420px, 100%);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md), 0 0 60px rgba(14, 165, 233, 0.06);
  padding: 34px 38px;
  backdrop-filter: blur(20px);
  position: relative;
}

.login-card::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.15), transparent 40%, transparent 60%, rgba(139, 92, 246, 0.15));
  z-index: -1;
  pointer-events: none;
}

.login-header {
  text-align: center;
  margin-bottom: 24px;
}

.logo {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-purple));
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
  box-shadow: 0 0 24px rgba(14, 165, 233, 0.3);
  position: relative;
}

.logo::after {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 17px;
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.2), rgba(139, 92, 246, 0.2));
  z-index: -1;
  filter: blur(8px);
}

.logo svg {
  width: 32px;
  height: 32px;
}

.login-title {
  font-size: 22px;
  color: var(--color-text);
  font-weight: 750;
  margin: 0;
  background: linear-gradient(90deg, #fff, var(--color-cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.login-subtitle {
  font-size: 13px;
  color: var(--color-text-muted);
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
  background: var(--color-surface-muted);
  border-radius: 8px;
  border: 1px solid var(--color-border-soft);
}

.auth-tabs button {
  height: 36px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-muted);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.auth-tabs button.active {
  background: var(--color-surface-hover);
  color: var(--color-primary);
  font-weight: 650;
  box-shadow: 0 0 12px rgba(14, 165, 233, 0.1);
  border: 1px solid rgba(14, 165, 233, 0.2);
}

.form-label {
  display: block;
  font-size: 14px;
  color: var(--color-text-muted);
  margin-bottom: 6px;
  font-weight: 500;
}

.login-card :deep(.el-input__wrapper) {
  border-radius: 8px;
  height: 44px;
  background: var(--color-surface-solid) !important;
}

.login-card :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--color-border-glow) inset !important;
}

.login-card :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--color-primary) inset, 0 0 0 3px var(--color-primary-soft) !important;
}

.login-card :deep(.el-input__prefix .el-icon) {
  color: var(--color-text-subtle);
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 16px 0;
}

.forgot-link {
  font-size: 13px;
  color: var(--color-primary);
  text-decoration: none;
  transition: color 0.2s;
}

.forgot-link:hover {
  color: var(--color-primary-strong);
  text-decoration: underline;
}

.login-btn {
  width: 100%;
  height: 44px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 650;
  background: linear-gradient(135deg, var(--color-primary), var(--color-purple));
  border: none;
  box-shadow: 0 0 20px rgba(14, 165, 233, 0.3);
  transition: all 0.3s;
}

.login-btn:hover {
  background: linear-gradient(135deg, var(--color-primary-strong), var(--color-purple));
  box-shadow: 0 0 30px rgba(14, 165, 233, 0.45);
  transform: translateY(-1px);
}

@media (max-width: 480px) {
  .login-container {
    align-items: flex-start;
    padding-top: 48px;
  }

  .login-card {
    padding: 28px 22px;
  }
}
</style>
