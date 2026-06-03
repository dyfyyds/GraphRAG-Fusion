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
import 'element-plus/dist/index.css'
import { ElButton, ElCheckbox, ElForm, ElFormItem, ElIcon, ElInput, ElMessage } from 'element-plus'
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
  background: #000;
  position: relative;
  overflow: hidden;
}

.login-container::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 30%, rgba(125, 211, 252, 0.08), transparent 30%),
    radial-gradient(circle at 75% 65%, rgba(167, 139, 250, 0.06), transparent 30%),
    radial-gradient(circle at 50% 85%, rgba(232, 121, 249, 0.05), transparent 30%);
  pointer-events: none;
}

.login-container::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(1px 1px at 10% 15%, rgba(255, 255, 255, 0.5), transparent),
    radial-gradient(1px 1px at 25% 35%, rgba(255, 255, 255, 0.4), transparent),
    radial-gradient(1px 1px at 40% 55%, rgba(125, 211, 252, 0.6), transparent),
    radial-gradient(1px 1px at 55% 25%, rgba(255, 255, 255, 0.45), transparent),
    radial-gradient(1px 1px at 70% 65%, rgba(255, 255, 255, 0.35), transparent),
    radial-gradient(1px 1px at 85% 45%, rgba(167, 139, 250, 0.5), transparent),
    radial-gradient(1px 1px at 15% 75%, rgba(255, 255, 255, 0.4), transparent),
    radial-gradient(1px 1px at 30% 90%, rgba(125, 211, 252, 0.45), transparent);
  pointer-events: none;
  animation: starTwinkle 6s ease-in-out infinite;
}

@keyframes starTwinkle {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

.login-card {
  width: min(420px, 100%);
  background: rgba(8, 15, 30, 0.86);
  border: 1px solid rgba(125, 211, 252, 0.24);
  border-radius: 12px;
  box-shadow:
    0 24px 64px rgba(0, 0, 0, 0.6),
    0 0 40px rgba(125, 211, 252, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
  padding: 34px 38px;
  backdrop-filter: blur(16px);
  position: relative;
  z-index: 1;
}

.login-card::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(125, 211, 252, 0.2), transparent 40%, transparent 60%, rgba(167, 139, 250, 0.2));
  z-index: -1;
  pointer-events: none;
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.logo {
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #7dd3fc, #a78bfa);
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  box-shadow: 0 0 28px rgba(125, 211, 252, 0.4);
  position: relative;
}

.logo::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 20px;
  background: linear-gradient(135deg, rgba(125, 211, 252, 0.3), rgba(167, 139, 250, 0.3));
  z-index: -1;
  filter: blur(10px);
}

.logo svg {
  width: 34px;
  height: 34px;
}

.login-title {
  font-size: 24px;
  color: #eaf2ff;
  font-weight: 800;
  margin: 0;
  background: linear-gradient(90deg, #ffffff, #7dd3fc);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.login-subtitle {
  font-size: 13px;
  color: #94a3b8;
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
  margin-bottom: 24px;
  background: rgba(8, 15, 30, 0.82);
  border-radius: 8px;
  border: 1px solid rgba(125, 211, 252, 0.15);
}

.auth-tabs button {
  height: 38px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #94a3b8;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s;
}

.auth-tabs button:hover {
  color: #eaf2ff;
}

.auth-tabs button.active {
  background: rgba(37, 99, 235, 0.22);
  color: #7dd3fc;
  font-weight: 700;
  box-shadow: 0 0 16px rgba(125, 211, 252, 0.15);
  border: 1px solid rgba(125, 211, 252, 0.3);
}

.form-label {
  display: block;
  font-size: 13px;
  color: #93c5fd;
  margin-bottom: 6px;
  font-weight: 600;
}

.login-card :deep(.el-input__wrapper) {
  border-radius: 7px;
  height: 46px;
  background: rgba(8, 15, 30, 0.82) !important;
  border: 1px solid rgba(125, 211, 252, 0.22) !important;
}

.login-card :deep(.el-input__wrapper:hover) {
  border-color: rgba(125, 211, 252, 0.56) !important;
  box-shadow: 0 0 0 1px rgba(125, 211, 252, 0.56) inset !important;
}

.login-card :deep(.el-input__wrapper.is-focus) {
  border-color: rgba(125, 211, 252, 0.56) !important;
  box-shadow: 0 0 0 1px rgba(125, 211, 252, 0.56) inset, 0 0 0 3px rgba(125, 211, 252, 0.12) !important;
}

.login-card :deep(.el-input__prefix .el-icon) {
  color: #94a3b8;
}

.login-card :deep(.el-input__inner) {
  color: #eaf2ff;
}

.login-card :deep(.el-input__inner::placeholder) {
  color: #64748b;
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 18px 0;
}

.forgot-link {
  font-size: 13px;
  color: #7dd3fc;
  text-decoration: none;
  transition: color 0.2s;
}

.forgot-link:hover {
  color: #bae6fd;
  text-decoration: underline;
}

.login-btn {
  width: 100%;
  height: 46px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 700;
  background: #7dd3fc;
  color: #07111f;
  border: none;
  box-shadow: 0 0 18px rgba(125, 211, 252, 0.4);
  transition: all 0.3s;
}

.login-btn:hover {
  background: #bae6fd;
  box-shadow: 0 0 28px rgba(125, 211, 252, 0.55);
  transform: translateY(-2px);
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
