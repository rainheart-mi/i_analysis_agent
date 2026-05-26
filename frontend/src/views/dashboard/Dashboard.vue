<template>
  <div class="dashboard">
    <div class="header">
      <div class="header-content">
        <h1>中控仪表盘</h1>
        <p>实时监控系统运行状态</p>
      </div>
      <div class="header-actions">
        <el-button class="refresh-btn" @click="refreshData">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6M1 20v-6h6"/>
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
          </svg>
          刷新数据
        </el-button>
      </div>
    </div>

    <div class="stats-grid">
      <div
        v-for="(stat, index) in stats"
        :key="index"
        class="stat-card"
        :style="{ '--delay': `${index * 0.1}s` }"
      >
        <div class="stat-icon" :style="{ background: stat.iconBg }">
          <component :is="stat.icon" />
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
        <div class="stat-trend" :class="stat.trend">
          <svg v-if="stat.trend === 'up'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 15l-6-6-6 6"/>
          </svg>
          <svg v-else-if="stat.trend === 'down'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 9l6 6 6-6"/>
          </svg>
          <span>{{ stat.change }}</span>
        </div>
      </div>
    </div>

    <div class="content-grid">
      <el-card class="chart-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">执行趋势</span>
            <div class="card-tabs">
              <span class="tab active">本周</span>
              <span class="tab">本月</span>
            </div>
          </div>
        </template>
        <div class="chart-placeholder">
          <div class="chart-bars">
            <div v-for="i in 7" :key="i" class="bar" :style="{ height: `${Math.random() * 60 + 40}%` }"></div>
          </div>
        </div>
      </el-card>

      <el-card class="activity-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">最近活动</span>
          </div>
        </template>
        <div class="activity-list">
          <div v-for="i in 5" :key="i" class="activity-item">
            <div class="activity-dot"></div>
            <div class="activity-content">
              <div class="activity-title">品类运营分析</div>
              <div class="activity-desc">已完成 · 2分钟前</div>
            </div>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const stats = ref([
  { label: '工作流总数', value: '12', trend: 'up', change: '+2', iconBg: 'rgba(102, 126, 234, 0.1)' },
  { label: '今日执行', value: '156', trend: 'up', change: '+12%', iconBg: 'rgba(16, 185, 129, 0.1)' },
  { label: '成功率', value: '98.7%', trend: 'down', change: '-0.3%', iconBg: 'rgba(245, 158, 11, 0.1)' },
  { label: 'N8N环境', value: '3', trend: 'up', change: '+1', iconBg: 'rgba(118, 75, 162, 0.1)' }
])

const refreshData = () => {
  console.log('Refresh data')
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

.dashboard {
  padding: 24px;
  background: #f8f9fb;
  min-height: 100%;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.header-content h1 {
  margin: 0 0 4px 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a1a2e;
}

.header-content p {
  margin: 0;
  font-size: 0.85rem;
  color: #94a3b8;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #fff;
  color: #64748b;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.refresh-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid rgba(0, 0, 0, 0.04);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
  animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: var(--delay);
  transition: all 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #667eea;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
}

.stat-label {
  font-size: 0.8rem;
  color: #94a3b8;
  margin-top: 2px;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
}

.stat-trend.up {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
}

.stat-trend.down {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.content-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}

.chart-card, .activity-card {
  border-radius: 16px;
  border: 1px solid rgba(0, 0, 0, 0.04);
}

:deep(.el-card__header) {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1a1a2e;
}

.card-tabs {
  display: flex;
  gap: 8px;
}

.tab {
  padding: 4px 12px;
  font-size: 0.8rem;
  color: #94a3b8;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab:hover {
  color: #667eea;
}

.tab.active {
  color: #667eea;
  background: rgba(102, 126, 234, 0.1);
}

.chart-placeholder {
  height: 200px;
  display: flex;
  align-items: flex-end;
  padding: 20px 0;
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  width: 100%;
  height: 100%;
  gap: 12px;
}

.bar {
  flex: 1;
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px 8px 0 0;
  animation: growUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes growUp {
  from {
    transform: scaleY(0);
    transform-origin: bottom;
  }
  to {
    transform: scaleY(1);
    transform-origin: bottom;
  }
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.activity-dot {
  width: 8px;
  height: 8px;
  background: #667eea;
  border-radius: 50%;
  margin-top: 6px;
}

.activity-content {
  flex: 1;
}

.activity-title {
  font-size: 0.9rem;
  font-weight: 500;
  color: #1a1a2e;
}

.activity-desc {
  font-size: 0.8rem;
  color: #94a3b8;
  margin-top: 2px;
}
</style>