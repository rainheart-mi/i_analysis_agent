<template>
  <div class="workflow-sidebar">
    <!-- Header -->
    <div class="sidebar-header">
      <h3 class="sidebar-title">工作流实例</h3>
    </div>

    <!-- Task List -->
    <div class="task-list">
      <!-- "新对话" 虚拟实例 -->
      <div
        class="task-item"
        :class="{ active: !taskStore.currentTask }"
        @click="selectNewConversation"
      >
        <div class="task-icon new-conversation">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M5 12h14"/>
          </svg>
        </div>
        <div class="task-content">
          <div class="task-name">新对话</div>
          <div class="task-meta">
            <span class="task-status draft">草稿</span>
            <span class="task-time">未开始执行</span>
          </div>
        </div>
      </div>

      <!-- 已存在的任务实例 -->
      <div
        v-for="task in taskStore.tasks"
        :key="task.id"
        class="task-item"
        :class="{ active: taskStore.currentTask?.id === task.id }"
        @click="selectTask(task)"
      >
        <div class="task-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M9 12l2 2 4-4"/>
          </svg>
        </div>
        <div class="task-content">
          <div class="task-name">{{ task.name || '未命名任务' }}</div>

          <!-- Node Progress Indicator -->
          <div class="node-progress" v-if="task.node_executions?.length">
            <template v-for="(node, index) in task.node_executions" :key="node.node_id">
              <div
                class="node-dot"
                :class="{
                  completed: node.status === 'completed',
                  active: node.status === 'executing' || node.node_id === taskStore.currentNodeId,
                  pending: node.status === 'pending'
                }"
              ></div>
              <div
                v-if="index < task.node_executions.length - 1"
                class="node-line"
                :class="{ completed: node.status === 'completed' }"
              ></div>
            </template>
          </div>

          <div class="task-meta">
            <span class="task-status" :class="task.status">
              {{ statusText(task.status) }}
            </span>
            <span class="task-time">{{ formatTime(task.updated_at) }}</span>
          </div>
        </div>
      </div>

      <div v-if="taskStore.tasks.length === 0" class="empty-state">
        暂无任务实例
      </div>
    </div>
  </div>
</template>

<script setup>
import { useTaskStore } from '@/store/task'

const taskStore = useTaskStore()

const selectNewConversation = () => {
  taskStore.clearCurrentTask()
}

const selectTask = async (task) => {
  await taskStore.fetchTask(task.id)
}

const statusText = (status) => {
  const map = {
    pending: '待执行',
    executing: '执行中',
    completed: '已完成',
    failed: '失败'
  }
  return map[status] || status
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  // Parse as UTC by appending 'Z' if not already present
  const dateStr = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z'
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`

  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.workflow-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #f1f1f1;
}

.sidebar-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.task-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.task-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
}

.task-item:hover {
  background: #f9fafb;
}

.task-item.active {
  background: #f3f4ff;
}

.task-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  flex-shrink: 0;
}

.task-icon.new-conversation {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
  color: #667eea;
}

.task-item.active .task-icon {
  background: #e0e7ff;
  color: #6366f1;
}

.task-content {
  flex: 1;
  min-width: 0;
}

.task-name {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-progress {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
}

.node-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d1d5db;
  flex-shrink: 0;
}

.node-dot.completed {
  background: #10b981;
}

.node-dot.active {
  background: #8b5cf6;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.4);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(139, 92, 246, 0);
  }
}

.node-line {
  width: 16px;
  height: 2px;
  background: #d1d5db;
  margin: 0 2px;
}

.node-line.completed {
  background: #10b981;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}

.task-status {
  color: #9ca3af;
}

.task-status.executing,
.task-status.draft {
  color: #8b5cf6;
}

.task-status.completed {
  color: #10b981;
}

.task-status.failed {
  color: #ef4444;
}

.task-time {
  color: #9ca3af;
}

.empty-state {
  text-align: center;
  padding: 32px 16px;
  color: #9ca3af;
  font-size: 13px;
}

.create-form {
  padding: 8px 0;
}

.form-item {
  margin-bottom: 16px;
}

.form-item label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  color: #374151;
}
</style>