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
        <el-menu :default-active="$route.path" router background-color="#001529" text-color="rgba(255,255,255,0.65)" active-text-color="#fff">
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
}
.sidebar {
  background: #001529;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sidebar-logo {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.sidebar-logo .icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
}
.sidebar-logo .icon svg {
  width: 18px;
  height: 18px;
  fill: #fff;
}
.sidebar-logo span {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}
.sidebar-menu {
  flex: 1;
}
.sidebar-menu :deep(.el-menu) {
  border-right: none;
  background: #001529;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.sidebar-menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.65);
  height: 44px;
  line-height: 44px;
}
.sidebar-menu :deep(.el-menu-item:hover) {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}
.sidebar-menu :deep(.el-menu-item.is-active) {
  color: #fff;
  background: #667eea;
}
.main-area {
  display: flex;
  flex-direction: column;
}
.header {
  height: 64px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}
.header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.header-left h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}
.breadcrumb {
  font-size: 13px;
  color: #909399;
}
.breadcrumb a {
  color: #909399;
  text-decoration: none;
}
.breadcrumb a:hover {
  color: #667eea;
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
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
}
.user-info span {
  font-size: 14px;
  color: #303133;
}
.logout-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s;
}
.logout-btn:hover {
  background: #f5f7fa;
}
.logout-btn svg {
  width: 18px;
  height: 18px;
  fill: #909399;
}
.main-content {
  flex: 1;
  overflow: hidden;
  padding: 0;
  background: #f5f5f5;
}
</style>
