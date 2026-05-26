<template>
  <div class="intent-form-preview">
    <div class="preview-header">
      <div class="header-left">
        <h3 class="preview-title">意图澄清</h3>
        <span class="preview-badge">草稿</span>
      </div>
      <div class="workflow-name">{{ currentWorkflow?.title }}</div>
    </div>
    <div class="preview-body">
      <template v-if="intentSchema">
        <dynamic-form
          ref="formRef"
          :schema="intentSchema"
          :model-value="formData"
          @update:model-value="formData = $event"
        />
      </template>
      <div v-else class="loading-state">
        <div class="loading-ring"></div>
        <p>加载表单中...</p>
      </div>
    </div>
    <div class="action-bar">
      <el-button @click="handleReset" class="btn-reset">重置</el-button>
      <el-button type="primary" @click="handleExecute" class="btn-primary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M13 5l7 7-7 7M5 12h15"/>
        </svg>
        执行工作流
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useWorkflowStore } from '@/store/workflow'
import { useTaskStore } from '@/store/task'
import { useChatStore } from '@/store/chat'
import DynamicForm from './DynamicForm.vue'

const workflowStore = useWorkflowStore()
const taskStore = useTaskStore()
const chatStore = useChatStore()

const formRef = ref(null)
const formData = ref({})

const intentSchema = computed(() => workflowStore.currentIntentSchema)
const currentWorkflow = computed(() => chatStore.selectedWorkflow)

const handleReset = () => {
  formData.value = {}
}

const handleExecute = async () => {
  if (!chatStore.selectedWorkflow) {
    return
  }

  try {
    const taskName = chatStore.selectedWorkflow.title

    const task = await taskStore.createTask(chatStore.selectedWorkflow.id, taskName)

    if (!task?.id) {
      throw new Error('任务创建失败')
    }

    // Add user message to chat
    chatStore.addMessage({
      type: 'user',
      content: `执行工作流: ${taskName}`
    })

    // Execute first node with intent data
    if (task.node_executions?.length > 0) {
      const firstNode = task.node_executions[0]
      await taskStore.executeNode(firstNode.node_id, formData.value, task.id)
    }

    // Add AI response
    chatStore.addMessage({
      type: 'ai',
      content: `工作流 "${taskName}" 执行完成`
    })
  } catch (e) {
    console.error('Execute error:', e)
    chatStore.addMessage({
      type: 'ai',
      content: `执行失败: ${e.message}`
    })
  }
}
</script>

<style scoped>
.intent-form-preview {
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.04);
  overflow: hidden;
  margin: 20px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.04) 0%, rgba(118, 75, 162, 0.04) 100%);
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.preview-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.preview-badge {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
}

.workflow-name {
  font-size: 0.8rem;
  color: #94a3b8;
}

.preview-body {
  padding: 20px;
  flex: 1;
}

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

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}

.loading-ring {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: #667eea;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-state p {
  margin: 0;
  font-size: 0.85rem;
  color: #94a3b8;
}
</style>