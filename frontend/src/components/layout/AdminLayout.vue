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
import 'element-plus/dist/index.css'
import { ElAside, ElContainer, ElHeader, ElIcon, ElMain, ElMenu, ElMenuItem, ElScrollbar } from 'element-plus'
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
  background: #000;
}
.sidebar {
  background: #030712;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid rgba(125, 211, 252, 0.18);
  position: relative;
}
.sidebar::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 1px;
  height: 100%;
  background: linear-gradient(180deg, rgba(125, 211, 252, 0.25), transparent 30%, transparent 70%, rgba(167, 139, 250, 0.25));
  pointer-events: none;
}
.sidebar-logo {
  height: 68px;
  display: flex;
  align-items: center;
  padding: 0 18px;
  border-bottom: 1px solid rgba(125, 211, 252, 0.15);
}
.sidebar-logo .icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, #7dd3fc, #a78bfa);
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
  box-shadow: 0 0 14px rgba(125, 211, 252, 0.35);
}
.sidebar-logo .icon svg {
  width: 18px;
  height: 18px;
  fill: #fff;
}
.sidebar-logo span {
  font-size: 15px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(90deg, #ffffff, #7dd3fc);
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
  padding: 8px;
}
.sidebar-menu :deep(.el-menu-item) {
  height: 44px;
  line-height: 44px;
  margin-bottom: 4px;
  border-radius: 8px;
  color: rgba(148, 163, 184, 0.9);
  transition: all 0.25s ease;
  border: 1px solid transparent;
}
.sidebar-menu :deep(.el-menu-item:hover) {
  color: #eaf2ff;
  background: rgba(25, 38, 68, 0.7);
  border-color: rgba(125, 211, 252, 0.15);
}
.sidebar-menu :deep(.el-menu-item.is-active) {
  color: #fff;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.28), rgba(167, 139, 250, 0.18));
  border: 1px solid rgba(125, 211, 252, 0.35);
  box-shadow: 0 0 18px rgba(125, 211, 252, 0.18);
}
.menu-group-title {
  padding: 18px 12px 8px;
  font-size: 11px;
  color: #93c5fd;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  font-weight: 700;
}
.main-area {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.header {
  height: 68px;
  background: rgba(3, 7, 18, 0.92);
  border-bottom: 1px solid rgba(125, 211, 252, 0.18);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  backdrop-filter: blur(18px);
}
.header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.header-left h2 {
  font-size: 18px;
  font-weight: 800;
  color: #eaf2ff;
  margin: 0;
}
.breadcrumb {
  font-size: 12px;
  color: #94a3b8;
}
.breadcrumb a {
  color: #94a3b8;
  text-decoration: none;
  transition: color 0.2s;
}
.breadcrumb a:hover {
  color: #7dd3fc;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.notification {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.25s;
  position: relative;
  border: 1px solid transparent;
}
.notification:hover {
  background: rgba(25, 38, 68, 0.7);
  border-color: rgba(125, 211, 252, 0.2);
}
.notification svg {
  width: 20px;
  height: 20px;
  fill: #93c5fd;
}
.notification .badge {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 9px;
  height: 9px;
  background: #f87171;
  border-radius: 50%;
  border: 2px solid #030712;
  box-shadow: 0 0 8px rgba(248, 113, 113, 0.6);
}
.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 9px;
  transition: all 0.25s;
  border: 1px solid transparent;
}
.user-info:hover {
  background: rgba(25, 38, 68, 0.7);
  border-color: rgba(125, 211, 252, 0.2);
}
.user-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7dd3fc, #a78bfa);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  box-shadow: 0 0 12px rgba(125, 211, 252, 0.35);
}
.user-info span {
  font-size: 14px;
  color: #eaf2ff;
  font-weight: 600;
}
.logout-btn {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.25s;
  border: 1px solid transparent;
}
.logout-btn:hover {
  background: rgba(248, 113, 113, 0.15);
  border-color: rgba(248, 113, 113, 0.3);
}
.logout-btn svg {
  width: 18px;
  height: 18px;
  fill: #94a3b8;
}
.logout-btn:hover svg {
  fill: #f87171;
}
.content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #000;
  position: relative;
}
.content::before {
  content: '';
  position: fixed;
  top: 68px;
  right: 0;
  width: calc(100% - 220px);
  height: 200px;
  background: radial-gradient(ellipse at 70% 0%, rgba(125, 211, 252, 0.04), transparent 70%);
  pointer-events: none;
  z-index: 0;
}

@media (max-width: 900px) {
  .sidebar {
    width: 72px !important;
  }

  .sidebar-logo span,
  .menu-group-title,
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

  .content {
    padding: 16px;
  }

  .content::before {
    width: calc(100% - 72px);
  }
}
</style>
