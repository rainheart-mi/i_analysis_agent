<template>
  <div class="header-bar">
    <div class="left">
      <div class="breadcrumb">
        <span class="breadcrumb-item">{{ currentPageTitle }}</span>
      </div>
    </div>

    <div class="right">
      <div class="env-tag">
        <span class="env-dot"></span>
        <span class="env-name">生产环境</span>
      </div>

      <el-select v-model="selectedStore" placeholder="选择门店" class="store-select" size="default">
        <el-option label="上海门店" value="shanghai" />
        <el-option label="北京门店" value="beijing" />
        <el-option label="广州门店" value="guangzhou" />
      </el-select>

      <el-badge :value="3" class="notification-badge">
        <el-button circle class="icon-btn">
          <el-icon><Bell /></el-icon>
        </el-button>
      </el-badge>

      <el-dropdown @command="handleCommand" trigger="click">
        <div class="user-menu">
          <el-avatar :size="36" class="user-avatar">
            {{ userStore.user?.username?.[0]?.toUpperCase() || 'A' }}
          </el-avatar>
          <div class="user-info">
            <span class="user-name">{{ userStore.user?.username || 'Admin' }}</span>
            <span class="user-role">管理员</span>
          </div>
          <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu class="user-dropdown">
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>
              个人中心
            </el-dropdown-item>
            <el-dropdown-item command="settings">
              <el-icon><Setting /></el-icon>
              设置
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { Bell, ArrowDown, User, Setting, SwitchButton } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const selectedStore = ref('shanghai')

const currentPageTitle = computed(() => {
  const routeMap = {
    '/': '中控仪表盘',
    '/ai-assistant': 'AI 助手',
    '/workflow-config': '工作流配置'
  }
  return routeMap[route.path] || '仪表盘'
})

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.header-bar {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
}

.breadcrumb-item {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a1a2e;
}

.right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.env-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(16, 185, 129, 0.08);
  border-radius: 20px;
}

.env-dot {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.env-name {
  font-size: 0.8rem;
  font-weight: 500;
  color: #10b981;
}

.store-select {
  width: 140px;
}

:deep(.store-select .el-input__wrapper) {
  border-radius: 8px !important;
  box-shadow: none !important;
  border: 1px solid rgba(0, 0, 0, 0.08) !important;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border: none !important;
  background: rgba(0, 0, 0, 0.04) !important;
  color: #64748b !important;
  transition: all 0.2s !important;
}

.icon-btn:hover {
  background: rgba(102, 126, 234, 0.1) !important;
  color: #667eea !important;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px 6px 6px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.user-menu:hover {
  background: rgba(0, 0, 0, 0.04);
}

.user-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-size: 14px;
  font-weight: 600;
}

.user-info {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: #1a1a2e;
  line-height: 1.2;
}

.user-role {
  font-size: 0.7rem;
  color: #94a3b8;
  line-height: 1.2;
}

.dropdown-icon {
  color: #94a3b8;
  transition: transform 0.2s;
}

.user-menu:hover .dropdown-icon {
  transform: rotate(180deg);
}

.user-dropdown :deep(.el-dropdown-menu__item) {
  padding: 10px 16px;
  font-size: 0.85rem;
}

.user-dropdown :deep(.el-dropdown-menu__item .el-icon) {
  margin-right: 8px;
}
</style>