<template>
  <div class="ai-assistant">
    <!-- 左侧工作流边栏 -->
    <div class="workflow-sidebar">
      <workflow-sidebar />
    </div>

    <!-- 中央画布区域 -->
    <div class="canvas-area">
      <!-- 有任务时显示 NodeTabs + NodeContent -->
      <template v-if="taskStore.currentTask">
        <node-tabs />
        <node-content />
      </template>
      <!-- 无任务但已选择工作流时显示意图表单 -->
      <template v-else-if="chatStore.selectedWorkflow">
        <intent-form-preview />
      </template>
      <!-- 无任务时显示空状态 -->
      <div v-else class="empty-state">
        <div class="empty-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
          </svg>
        </div>
        <h3 class="empty-title">暂无选中任务</h3>
        <p class="empty-desc">请从右侧选择一个工作流开始对话</p>
      </div>
    </div>

    <!-- 右侧对话面板 -->
    <div class="chat-panel">
      <chat-panel
        :workflows="workflowStore.workflows"
        :messages="chatStore.messages"
        @select-workflow="handleSelectWorkflow"
        @send-message="handleSendMessage"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useChatStore } from '@/store/chat'
import { useWorkflowStore } from '@/store/workflow'
import { useTaskStore } from '@/store/task'
import { useUserStore } from '@/store/user'
import WorkflowSidebar from './WorkflowSidebar.vue'
import NodeTabs from './NodeTabs.vue'
import NodeContent from './NodeContent.vue'
import ChatPanel from './ChatPanel.vue'
import IntentFormPreview from './IntentFormPreview.vue'

const chatStore = useChatStore()
const workflowStore = useWorkflowStore()
const taskStore = useTaskStore()
const userStore = useUserStore()

const executionResult = ref(null)

onMounted(async () => {
  await workflowStore.fetchWorkflows()
  await taskStore.fetchTasks()
})

const handleSelectWorkflow = async (workflow) => {
  chatStore.setSelectedWorkflow(workflow)
  await workflowStore.fetchIntentSchema(workflow.id)
}

const handleFormSubmit = async (formData) => {
  if (!chatStore.selectedWorkflow) return

  chatStore.addMessage({
    type: 'user',
    content: '提交表单'
  })

  try {
    const res = await workflowStore.executeWorkflow(chatStore.selectedWorkflow.id, {
      user_id: userStore.user?.id || 'anonymous',
      inputs: formData
    })

    executionResult.value = res.data

    await workflowStore.fetchArtifactSchema(chatStore.selectedWorkflow.id)

    chatStore.addMessage({
      type: 'ai',
      content: '工作流执行完成'
    })
  } catch (e) {
    chatStore.addMessage({
      type: 'ai',
      content: `执行失败: ${e.message}`
    })
  }
}

const handleSendMessage = (message) => {
  chatStore.addMessage({
    type: 'user',
    content: message
  })
}
</script>

<style scoped>
.ai-assistant {
  height: calc(100vh - 64px);
  display: flex;
  gap: 20px;
  padding: 20px;
  background: #f8f9fb;
}

.workflow-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.canvas-area {
  flex: 1;
  background: #fff;
  border-radius: 16px;
  overflow-y: auto;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  scrollbar-width: thin;
  scrollbar-color: #c1c1c1 #f1f1f1;
}

/* 滚动条样式 */
.canvas-area::-webkit-scrollbar {
  width: 8px;
}
.canvas-area::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}
.canvas-area::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}
.canvas-area::-webkit-scrollbar-thumb:hover {
  background: #a1a1a1;
}

.chat-panel {
  width: 380px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.04);
}

/* Empty state */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #94a3b8;
}

.empty-icon {
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-title {
  margin: 0 0 8px 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #64748b;
}

.empty-desc {
  margin: 0;
  font-size: 0.9rem;
  color: #94a3b8;
}
</style>