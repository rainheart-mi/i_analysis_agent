<template>
  <div class="sidebar">
    <!-- Logo区域 -->
    <div class="logo-section">
      <div class="logo-icon">
        <svg width="32" height="32" viewBox="0 0 48 48" fill="none">
          <rect width="48" height="48" rx="12" fill="url(#logoGrad)"/>
          <path d="M14 24h20M24 14v20" stroke="white" stroke-width="3" stroke-linecap="round"/>
          <defs>
            <linearGradient id="logoGrad" x1="0" y1="0" x2="48" y2="48">
              <stop stop-color="#667eea"/>
              <stop offset="1" stop-color="#764ba2"/>
            </linearGradient>
          </defs>
        </svg>
      </div>
      <span class="logo-text">IERP</span>
    </div>

    <!-- 导航菜单 -->
    <nav class="nav-menu">
      <div class="nav-label">导航</div>
      <el-menu
        :default-active="$route.path"
        router
        class="sidebar-menu"
      >
        <el-menu-item
          v-for="(item, index) in menuItems"
          :key="item.path"
          :index="item.path"
          class="menu-item"
          :style="{ '--delay': `${index * 0.05}s` }"
        >
          <el-icon class="menu-icon">
            <component :is="item.icon" />
          </el-icon>
          <span class="menu-text">{{ item.label }}</span>
          <span v-if="item.badge" class="menu-badge">{{ item.badge }}</span>
        </el-menu-item>
      </el-menu>
    </nav>

    <!-- 底部信息 -->
    <div class="sidebar-footer">
      <div class="version">v1.0.0</div>
    </div>
  </div>
</template>

<script setup>
import { Odometer, ChatDotRound, Setting } from '@element-plus/icons-vue'

const menuItems = [
  { path: '/', label: '中控仪表盘', icon: Odometer },
  { path: '/ai-assistant', label: 'AI 助手', icon: ChatDotRound, badge: '新' },
  { path: '/workflow-config', label: '工作流配置', icon: Setting }
]
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

.sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%);
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  position: relative;
}

/* 背景纹理 */
.sidebar::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 20% 20%, rgba(102, 126, 234, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 80% 80%, rgba(118, 75, 162, 0.08) 0%, transparent 50%);
  pointer-events: none;
}

/* Logo区域 */
.logo-section {
  padding: 24px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: relative;
  z-index: 1;
}

.logo-icon {
  animation: pulse 3s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.logo-text {
  font-size: 1.4rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* 导航菜单 */
.nav-menu {
  flex: 1;
  padding: 16px 12px;
  position: relative;
  z-index: 1;
}

.nav-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.25);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 0 12px;
  margin-bottom: 8px;
}

.sidebar-menu {
  background: transparent !important;
  border: none !important;
}

:deep(.menu-item) {
  height: 48px;
  line-height: 48px;
  margin-bottom: 4px;
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.6) !important;
  background: transparent !important;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
  animation: slideIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: var(--delay);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

:deep(.menu-item:hover) {
  color: #fff !important;
  background: rgba(255, 255, 255, 0.05) !important;
}

:deep(.menu-item.is-active) {
  color: #fff !important;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%) !important;
}

:deep(.menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 24px;
  background: linear-gradient(180deg, #667eea, #764ba2);
  border-radius: 0 2px 2px 0;
}

.menu-icon {
  margin-right: 12px;
  font-size: 18px;
  transition: transform 0.3s;
}

:deep(.menu-item:hover .menu-icon) {
  transform: scale(1.1);
}

.menu-text {
  font-size: 0.9rem;
  font-weight: 500;
}

.menu-badge {
  margin-left: auto;
  padding: 2px 8px;
  font-size: 0.65rem;
  font-weight: 600;
  color: #667eea;
  background: rgba(102, 126, 234, 0.15);
  border-radius: 10px;
  animation: badgePulse 2s ease-in-out infinite;
}

@keyframes badgePulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* 底部 */
.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  position: relative;
  z-index: 1;
}

.version {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.2);
  text-align: center;
}
</style>