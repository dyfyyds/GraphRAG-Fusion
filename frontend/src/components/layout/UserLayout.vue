<template>
  <el-container class="layout">
    <el-aside width="220px" class="sidebar">
      <div class="sidebar-logo">
        <div class="icon">
          <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" /></svg>
        </div>
        <span>RAG 智能问答</span>
      </div>
      <el-scrollbar class="sidebar-menu">
        <el-menu :default-active="$route.path" router>
          <el-menu-item index="/">
            <el-icon><ChatDotRound /></el-icon>
            <span>智能问答</span>
          </el-menu-item>
          <el-menu-item index="/history">
            <el-icon><Clock /></el-icon>
            <span>问答历史</span>
          </el-menu-item>
          <div style="flex:1"></div>
          <el-menu-item v-if="userStore.userInfo?.role === 'admin'" index="/admin" @click="$router.push('/admin')">
            <el-icon><Setting /></el-icon>
            <span>管理后台</span>
          </el-menu-item>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <el-container class="main-area">
      <el-header v-if="$route.name !== 'Chat'" class="header">
        <div class="header-left">
          <div class="breadcrumb">
            <a href="#" @click.prevent="$router.push('/')">首页</a> / {{ currentPageName }}
          </div>
          <h2>{{ currentPageName }}</h2>
        </div>
        <div class="header-right">
          <div class="user-info">
            <div class="user-avatar">{{ userInitial }}</div>
            <span>{{ userStore.userInfo?.username || '用户' }}</span>
          </div>
          <div class="logout-btn" @click="handleLogout" title="退出登录">
            <svg viewBox="0 0 24 24"><path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z" /></svg>
          </div>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../../store/user'
import { ChatDotRound, Clock, Setting } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const pageNameMap = {
  Chat: '智能问答',
  UserHistory: '我的问答历史',
}

const currentPageName = computed(() => pageNameMap[route.name] || '智能问答')

const userInitial = computed(() => {
  const name = userStore.userInfo?.username || '用'
  return name.charAt(0)
})

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout {
  height: 100vh;
  background: var(--color-bg);
}
.sidebar {
  background: var(--color-sidebar);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--color-border);
  position: relative;
}
.sidebar::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 1px;
  height: 100%;
  background: linear-gradient(180deg, rgba(14, 165, 233, 0.2), transparent 30%, transparent 70%, rgba(139, 92, 246, 0.2));
  pointer-events: none;
}
.sidebar-logo {
  height: 68px;
  display: flex;
  align-items: center;
  padding: 0 18px;
  border-bottom: 1px solid var(--color-border);
}
.sidebar-logo .icon {
  width: 34px;
  height: 34px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-purple));
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
  box-shadow: 0 0 12px rgba(14, 165, 233, 0.3);
}
.sidebar-logo .icon svg {
  width: 18px;
  height: 18px;
  fill: #fff;
}
.sidebar-logo span {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(90deg, #fff, var(--color-cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.sidebar-menu {
  flex: 1;
}
.sidebar-menu :deep(.el-menu) {
  border-right: none;
  background: transparent;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 8px;
}
.sidebar-menu :deep(.el-menu-item) {
  color: rgba(139, 153, 176, 0.85);
  height: 42px;
  line-height: 42px;
  margin-bottom: 4px;
  border-radius: 7px;
  transition: all 0.2s ease;
}
.sidebar-menu :deep(.el-menu-item:hover) {
  color: var(--color-text);
  background: var(--color-surface-hover);
}
.sidebar-menu :deep(.el-menu-item.is-active) {
  color: #fff;
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.25), rgba(139, 92, 246, 0.15));
  border: 1px solid rgba(14, 165, 233, 0.3);
  box-shadow: 0 0 16px rgba(14, 165, 233, 0.15);
}
.main-area {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.header {
  height: 68px;
  background: rgba(8, 12, 22, 0.85);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  backdrop-filter: blur(16px);
}
.header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.header-left h2 {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}
.breadcrumb {
  font-size: 12px;
  color: var(--color-text-subtle);
}
.breadcrumb a {
  color: var(--color-text-subtle);
  text-decoration: none;
  transition: color 0.2s;
}
.breadcrumb a:hover {
  color: var(--color-primary);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-purple));
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  box-shadow: 0 0 10px rgba(14, 165, 233, 0.3);
}
.user-info span {
  font-size: 14px;
  color: var(--color-text);
}
.logout-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}
.logout-btn:hover {
  background: var(--color-danger-soft);
}
.logout-btn svg {
  width: 18px;
  height: 18px;
  fill: var(--color-text-subtle);
}
.logout-btn:hover svg {
  fill: var(--color-danger);
}
.main-content {
  flex: 1;
  overflow: hidden;
  padding: 0;
  background: var(--color-bg);
}

@media (max-width: 900px) {
  .sidebar {
    width: 72px !important;
  }

  .sidebar-logo span,
  .sidebar-menu :deep(.el-menu-item span) {
    display: none;
  }

  .sidebar-logo {
    justify-content: center;
    padding: 0;
  }

  .sidebar-logo .icon {
    margin-right: 0;
  }
}
</style>
