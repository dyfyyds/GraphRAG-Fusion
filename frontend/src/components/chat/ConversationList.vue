<template>
  <div class="conversation-sidebar">
    <div class="sidebar-header">
      <div class="logo-row">
        <div class="logo">
          <div class="icon">
            <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" /></svg>
          </div>
          <span>智能问答</span>
        </div>
      </div>
      <div class="conversation-actions">
        <div class="new-chat-btn" @click="$emit('select', null)" title="新对话">
          <svg viewBox="0 0 24 24"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" /></svg>
        </div>
        <el-input
          v-model="searchQuery"
          class="search-input"
          placeholder="搜索对话..."
          :prefix-icon="Search"
          clearable
          size="small"
        />
      </div>
    </div>

    <div class="conversation-list">
      <template v-for="(group, groupName) in groupedConversations" :key="groupName">
        <div class="conv-date-group">{{ groupName }}</div>
        <div
          v-for="conv in group"
          :key="conv.id"
          class="conv-item"
          :class="{ active: conv.id === currentId }"
          @click="$emit('select', conv.id)"
        >
          <span class="title">{{ conv.title }}</span>
          <span v-if="conv.thinking" class="thinking-dot" title="后台思考中"></span>
          <div class="delete-btn" @click.stop="$emit('delete', conv.id)" title="删除">
            <svg viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" /></svg>
          </div>
        </div>
      </template>
      <el-empty v-if="!Object.keys(groupedConversations).length" description="暂无对话" :image-size="60" />
    </div>

    <div class="sidebar-footer">
      <div class="user-avatar">{{ userInitial }}</div>
      <div class="user-info">
        <div class="name">{{ userStore.userInfo?.username || '用户' }}</div>
        <div class="role">{{ userStore.userInfo?.role === 'admin' ? '管理员' : '普通用户' }}</div>
      </div>
      <router-link to="/history" class="settings-btn" title="问答历史">
        <svg viewBox="0 0 24 24"><path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z" /></svg>
      </router-link>
      <div class="settings-btn" @click="$emit('logout')" title="退出登录">
        <svg viewBox="0 0 24 24"><path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z" /></svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useUserStore } from '../../store/user'

const props = defineProps({
  conversations: { type: Array, default: () => [] },
  currentId: [Number, String],
})
defineEmits(['select', 'delete', 'logout'])

const userStore = useUserStore()
const searchQuery = ref('')

const userInitial = computed(() => {
  const name = userStore.userInfo?.username || '用'
  return name.charAt(0)
})

const filteredConversations = computed(() => {
  if (!searchQuery.value) return props.conversations
  const q = searchQuery.value.toLowerCase()
  return props.conversations.filter(c => c.title?.toLowerCase().includes(q))
})

const groupedConversations = computed(() => {
  const groups = {}
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 86400000)
  const weekStart = new Date(today.getTime() - 7 * 86400000)

  filteredConversations.value.forEach(conv => {
    const d = conv.updated_at ? new Date(conv.updated_at) : new Date(conv.created_at || Date.now())
    const convDate = new Date(d.getFullYear(), d.getMonth(), d.getDate())
    let label
    if (convDate.getTime() === today.getTime()) {
      label = '今天'
    } else if (convDate.getTime() === yesterday.getTime()) {
      label = '昨天'
    } else if (convDate >= weekStart) {
      label = '本周'
    } else {
      label = '更早'
    }
    if (!groups[label]) groups[label] = []
    groups[label].push(conv)
  })
  return groups
})
</script>

<style scoped>
.conversation-sidebar {
  width: 280px;
  background: var(--color-sidebar);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  height: 100%;
}
.sidebar-header {
  padding: 18px;
  border-bottom: 1px solid var(--color-border);
}
.logo-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  margin-bottom: 16px;
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}
.logo .icon {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-purple));
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 10px rgba(14, 165, 233, 0.3);
}
.logo .icon svg {
  width: 18px;
  height: 18px;
  fill: #fff;
}
.logo span {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text);
}
.conversation-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.new-chat-btn {
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--color-surface);
}
.new-chat-btn:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  box-shadow: 0 0 12px rgba(14, 165, 233, 0.15);
}
.new-chat-btn svg {
  width: 18px;
  height: 18px;
  fill: var(--color-text-muted);
}
.search-input {
  flex: 1;
  min-width: 0;
}
.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.conv-date-group {
  padding: 8px 12px 4px;
  font-size: 12px;
  color: var(--color-text-subtle);
  font-weight: 600;
  letter-spacing: 0.3px;
}
.conv-item {
  padding: 12px 14px;
  border-radius: 7px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 2px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.conv-item:hover {
  background: var(--color-surface-hover);
}
.conv-item.active {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.15), rgba(139, 92, 246, 0.08));
  border: 1px solid rgba(14, 165, 233, 0.2);
}
.conv-item .title {
  font-size: 13px;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.thinking-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--color-primary);
  box-shadow: 0 0 10px rgba(14, 165, 233, 0.75);
  margin: 0 8px;
  flex-shrink: 0;
  animation: pulse-thinking 1.2s ease-in-out infinite;
}
@keyframes pulse-thinking {
  0%, 100% {
    opacity: 0.45;
    transform: scale(0.9);
  }
  50% {
    opacity: 1;
    transform: scale(1.25);
  }
}
.conv-item .delete-btn {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  display: none;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}
.conv-item:hover .delete-btn {
  display: flex;
}
.conv-item .delete-btn svg {
  width: 14px;
  height: 14px;
  fill: var(--color-text-subtle);
}
.conv-item .delete-btn:hover svg {
  fill: var(--color-danger);
}
.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  gap: 10px;
}
.sidebar-footer .user-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-purple));
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
  box-shadow: 0 0 8px rgba(14, 165, 233, 0.25);
}
.sidebar-footer .user-info {
  flex: 1;
}
.sidebar-footer .user-info .name {
  font-size: 13px;
  font-weight: 650;
  color: var(--color-text);
}
.sidebar-footer .user-info .role {
  font-size: 11px;
  color: var(--color-text-subtle);
}
.sidebar-footer .settings-btn {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s;
}
.sidebar-footer .settings-btn:hover {
  background: var(--color-surface-hover);
}
.sidebar-footer .settings-btn svg {
  width: 18px;
  height: 18px;
  fill: var(--color-text-subtle);
}

@media (max-width: 900px) {
  .conversation-sidebar {
    width: 0;
    border-right: none;
    overflow: hidden;
  }
}
</style>
