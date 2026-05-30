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
          <div class="menu-group-title">工作空间</div>
          <el-menu-item index="/admin">
            <el-icon><DataBoard /></el-icon>
            <span>工作台</span>
          </el-menu-item>

          <div class="menu-group-title">知识管理</div>
          <el-menu-item index="/admin/knowledge">
            <el-icon><Document /></el-icon>
            <span>知识库管理</span>
          </el-menu-item>
          <el-menu-item index="/admin/graph">
            <el-icon><Share /></el-icon>
            <span>知识图谱</span>
          </el-menu-item>

          <div class="menu-group-title">系统管理</div>
          <el-menu-item index="/admin/users">
            <el-icon><User /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item index="/admin/history">
            <el-icon><Clock /></el-icon>
            <span>问答历史</span>
          </el-menu-item>
          <el-menu-item index="/admin/config">
            <el-icon><Setting /></el-icon>
            <span>系统配置</span>
          </el-menu-item>

          <div style="flex:1"></div>
          <el-menu-item index="/">
            <el-icon><ChatDotRound /></el-icon>
            <span>用户端问答</span>
          </el-menu-item>
        </el-menu>
      </el-scrollbar>
    </el-aside>

    <el-container class="main-area">
      <el-header class="header">
        <div class="header-left">
          <div class="breadcrumb">
            <a href="#" @click.prevent="$router.push('/admin')">首页</a> / {{ currentPageName }}
          </div>
          <h2>{{ currentPageName }}</h2>
        </div>
        <div class="header-right">
          <div class="notification" title="通知">
            <svg viewBox="0 0 24 24"><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" /></svg>
            <div class="badge"></div>
          </div>
          <div class="user-info" @click="$router.push('/')" title="切换到用户端">
            <div class="user-avatar">{{ userInitial }}</div>
            <span>{{ userStore.userInfo?.username || 'Admin' }}</span>
          </div>
          <div class="logout-btn" @click="handleLogout" title="退出登录">
            <svg viewBox="0 0 24 24"><path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z" /></svg>
          </div>
        </div>
      </el-header>
      <el-main class="content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../../store/user'
import { DataBoard, Document, Share, User, Clock, Setting, ChatDotRound } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const pageNameMap = {
  Dashboard: '工作台',
  KnowledgeBase: '知识库管理',
  KnowledgeGraph: '知识图谱',
  UserManage: '用户管理',
  AdminHistory: '问答历史',
  SystemConfig: '系统配置',
}

const currentPageName = computed(() => pageNameMap[route.name] || '工作台')

const userInitial = computed(() => {
  const name = userStore.userInfo?.username || 'A'
  return name.charAt(0).toUpperCase()
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
.menu-group-title {
  padding: 16px 20px 8px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
  text-transform: uppercase;
  letter-spacing: 1px;
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
.notification {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s;
  position: relative;
}
.notification:hover {
  background: #f5f7fa;
}
.notification svg {
  width: 20px;
  height: 20px;
  fill: #606266;
}
.notification .badge {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 8px;
  height: 8px;
  background: #f56c6c;
  border-radius: 50%;
  border: 2px solid #fff;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.2s;
}
.user-info:hover {
  background: #f5f7fa;
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
.content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #f0f2f5;
}
</style>
