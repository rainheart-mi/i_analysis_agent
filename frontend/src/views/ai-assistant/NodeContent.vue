<template>
  <div class="node-content">
    <!-- Intent Section (Top) -->
    <div class="intent-section">
      <div class="section-header">
        <div class="header-left">
          <h3 class="section-title">意图澄清</h3>
          <span class="status-badge" :class="statusClass">
            {{ statusText }}
          </span>
        </div>
      </div>
      <div class="section-body">
        <dynamic-form
          ref="intentFormRef"
          :schema="intentSchema"
          v-model="intentFormData"
          :readonly="isNodeExecuted"
        />
      </div>
      <div v-if="!isNodeExecuted && !isLoading" class="action-bar">
        <el-button @click="handleReset" class="btn-reset">重置</el-button>
        <el-button type="primary" @click="handleExecute" class="btn-primary">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M13 5l7 7-7 7M5 12h15"/>
          </svg>
          执行工作流
        </el-button>
      </div>
      <div v-if="isLoading" class="action-bar">
        <el-button type="warning" @click="handleMockComplete" class="btn-mock">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
          Mock 完成
        </el-button>
      </div>
    </div>

    <!-- Divider with badge -->
    <div v-if="hasArtifact" class="divider">
      <div class="divider-line"></div>
      <span class="divider-badge">数据输出</span>
      <div class="divider-line"></div>
    </div>

    <!-- Artifact Section (Bottom) -->
    <div v-if="hasArtifact" class="artifact-section">
      <div class="section-header">
        <div class="header-left">
          <h3 class="section-title">生成物展示</h3>
        </div>
      </div>
      <div class="section-body">
        <dynamic-form
          :schema="artifactSchema"
          :model-value="artifactFormData"
          readonly
        />
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-state">
      <div class="loading-ring"></div>
      <p>执行中...</p>
    </div>

    <!-- Empty State -->
    <div v-if="!hasArtifact && !isLoading && isNodeExecuted" class="empty-state">
      <p>暂无生成物数据</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useTaskStore } from '@/store/task'
import DynamicForm from './DynamicForm.vue'

const taskStore = useTaskStore()

const intentFormRef = ref(null)
const intentFormData = ref({})
const artifactFormData = ref({})

// Computed: check if node is executed
const isNodeExecuted = computed(() => {
  const node = taskStore.currentNode
  if (!node) return false
  return node.status === 'completed' || node.status === 'running'
})

// Computed: check if node has artifact data
const hasArtifact = computed(() => {
  const node = taskStore.currentNode
  if (!node || !node.artifact_data) return false
  return Object.keys(node.artifact_data).length > 0
})

// Computed: status text
const statusText = computed(() => {
  const node = taskStore.currentNode
  if (!node) return '未知'
  const statusMap = {
    pending: '待执行',
    running: '执行中',
    completed: '已完成',
    failed: '失败'
  }
  return statusMap[node.status] || node.status
})

// Computed: status class
const statusClass = computed(() => {
  const node = taskStore.currentNode
  if (!node) return ''
  return `status-${node.status}`
})

// Computed: loading state
const isLoading = computed(() => {
  const node = taskStore.currentNode
  return node && node.status === 'running'
})

// Computed: load intent schema from node
const intentSchema = computed(() => {
  const node = taskStore.currentNode
  if (!node || !node.intent_schema) return null
  return node.intent_schema
})

// Computed: load artifact schema from node
const artifactSchema = computed(() => {
  const node = taskStore.currentNode
  if (!node || !node.artifact_schema) return null
  return node.artifact_schema
})

// Watch artifact data changes
watch(
  () => taskStore.currentNode?.artifact_data,
  (data) => {
    if (data) {
      artifactFormData.value = { ...data }
    }
  },
  { immediate: true, deep: true }
)

// Watch intent data changes (to load saved form data)
watch(
  () => taskStore.currentTask?.node_executions,
  (executions) => {
    if (executions && taskStore.currentNodeId) {
      const node = executions.find(n => n.node_id === taskStore.currentNodeId)
      if (node && node.intent_data) {
        intentFormData.value = { ...node.intent_data }
      }
    }
  },
  { immediate: true, deep: true }
)

// Also watch currentNodeId changes
watch(
  () => taskStore.currentNodeId,
  () => {
    const node = taskStore.currentNode
    if (node && node.intent_data) {
      intentFormData.value = { ...node.intent_data }
    }
  }
)

// Handle reset
const handleReset = () => {
  intentFormData.value = {}
}

// Handle execute
const handleExecute = async () => {
  const node = taskStore.currentNode
  if (!node) return

  await taskStore.executeNode(node.node_id, intentFormData.value)
}

// Handle mock complete for testing
const handleMockComplete = async () => {
  const node = taskStore.currentNode
  if (!node) return

  await taskStore.mockCompleteNode(node.node_id)
}
</script>

<style scoped>
.node-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.04) 0%, rgba(118, 75, 162, 0.04) 100%);
  border-radius: 12px 12px 0 0;
  border: 1px solid rgba(0, 0, 0, 0.04);
  border-bottom: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-badge.status-pending {
  background: rgba(100, 116, 139, 0.1);
  color: #64748b;
}

.status-badge.status-running {
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
}

.status-badge.status-completed {
  background: rgba(16, 185, 129, 0.1);
  color: #10B981;
}

.status-badge.status-failed {
  background: rgba(239, 68, 68, 0.1);
  color: #EF4444;
}

.section-body {
  padding: 20px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.04);
  border-radius: 0 0 12px 12px;
  border-top: none;
}

/* Intent section card styling */
.intent-section {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

/* Action bar */
.action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  background: #fafafa;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
}

.btn-reset {
  padding: 10px 20px;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #fff;
  color: #64748b;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-reset:hover {
  border-color: #667eea;
  color: #667eea;
}

.btn-primary {
  padding: 10px 24px;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: #fff;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.35);
}

/* Divider */
.divider {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 20px;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, rgba(102, 126, 234, 0.3) 50%, transparent 100%);
}

.divider-badge {
  padding: 6px 14px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #667eea;
}

/* Artifact section card styling */
.artifact-section {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.04);
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* Loading state */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.loading-ring {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: #667eea;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

.loading-ring::before {
  content: '';
  position: absolute;
  inset: 4px;
  border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: #764ba2;
  animation: spin 0.8s linear infinite reverse;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state p {
  margin: 0;
  font-size: 0.85rem;
  color: #64748b;
}

/* Empty state */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.empty-state p {
  margin: 0;
  font-size: 0.85rem;
  color: #94a3b8;
}

/* Form readonly state - gray background */
:deep(.section-body:has(.dynamic-form[readonly])) {
  background: #f8f9fb;
}
</style>