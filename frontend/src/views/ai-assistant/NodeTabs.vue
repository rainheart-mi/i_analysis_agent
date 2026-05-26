<template>
  <div class="node-tabs">
    <div
      v-for="node in taskStore.nodes"
      :key="node.node_id"
      class="tab-item"
      :class="{ active: node.node_id === taskStore.currentNodeId }"
      @click="handleTabClick(node.node_id)"
    >
      <span class="status-dot" :class="getStatusClass(node.status)"></span>
      <span class="node-name">{{ node.node_name }}</span>
    </div>
  </div>
</template>

<script setup>
import { useTaskStore } from '@/store/task'

const taskStore = useTaskStore()

const getStatusClass = (status) => {
  switch (status) {
    case 'completed':
      return 'completed'
    case 'running':
      return 'running'
    case 'pending':
    default:
      return 'pending'
  }
}

const handleTabClick = (nodeId) => {
  taskStore.setCurrentNode(nodeId)
}
</script>

<style scoped>
.node-tabs {
  display: flex;
  gap: 8px;
  padding: 0 16px;
  background: #fafafa;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
  color: #64748b;
  font-size: 0.9rem;
  font-weight: 500;
}

.tab-item:hover {
  color: #4a5568;
  background: rgba(102, 126, 234, 0.04);
}

.tab-item.active {
  color: #667eea;
  border-bottom-color: #667eea;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.completed {
  background: #10B981;
}

.status-dot.pending {
  background: #94a3b8;
}

.status-dot.running {
  background: #667eea;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

.node-name {
  white-space: nowrap;
}
</style>