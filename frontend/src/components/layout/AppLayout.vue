<template>
  <div class="app-layout">
    <el-aside width="260px">
      <sidebar />
    </el-aside>
    <el-container>
      <el-header>
        <header-bar />
      </el-header>
      <el-main>
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import Sidebar from './Sidebar.vue'
import HeaderBar from './Header.vue'
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* 全局滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* 页面切换动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>

<style scoped>
.app-layout {
  height: 100vh;
  display: flex;
}

.el-aside {
  background: #0f0f1a;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.el-header {
  background: rgba(255, 255, 255, 0.98);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  display: flex;
  align-items: center;
  padding: 0 24px;
  height: 64px;
}

.el-main {
  background: #f8f9fb;
  padding: 0;
  overflow: hidden;
}
</style>