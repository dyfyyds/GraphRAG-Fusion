import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../store/user'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../components/layout/UserLayout.vue'),
    children: [
      { path: '', name: 'Chat', component: () => import('../views/user/Chat.vue') },
      { path: 'history', name: 'UserHistory', component: () => import('../views/user/UserHistory.vue') },
    ],
  },
  {
    path: '/admin',
    component: () => import('../components/layout/AdminLayout.vue'),
    meta: { role: 'admin' },
    children: [
      { path: '', name: 'Dashboard', component: () => import('../views/admin/Dashboard.vue') },
      { path: 'knowledge', name: 'KnowledgeBase', component: () => import('../views/admin/KnowledgeBase.vue') },
      { path: 'users', name: 'UserManage', component: () => import('../views/admin/UserManage.vue') },
      { path: 'history', name: 'AdminHistory', component: () => import('../views/admin/AdminHistory.vue') },
      { path: 'config', name: 'SystemConfig', component: () => import('../views/admin/SystemConfig.vue') },
      { path: 'graph', name: 'KnowledgeGraph', component: () => import('../views/admin/KnowledgeGraph.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  if (to.meta.public) return next()

  if (!userStore.token) {
    const redirect = to.fullPath !== '/' ? `?redirect=${encodeURIComponent(to.fullPath)}` : ''
    return next(`/login${redirect}`)
  }

  // 刷新后 userInfo 丢失：从 token 恢复用户信息
  if (!userStore.userInfo) {
    try {
      await userStore.fetchUser()
    } catch (err) {
      if (err?.response?.status === 401) {
        userStore.logout()
        return next('/login')
      }
      // 网络错误等瞬态异常不登出，允许继续（用户稍后刷新即可）
    }
  }

  if (to.meta.role === 'admin' && userStore.userInfo?.role !== 'admin') return next('/')
  next()
})

export default router
