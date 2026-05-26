<template>
  <div class="chat-panel">
    <div class="chat-header">
      <div class="header-content">
        <h3 class="title">AI 助手</h3>
        <p class="subtitle">选择一个工作流开始对话</p>
      </div>
      <div class="header-icon">
        <div class="ai-avatar">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" fill="url(#aiGrad)"/>
            <path d="M8 10h8M8 14h5" stroke="white" stroke-width="2" stroke-linecap="round"/>
            <defs>
              <linearGradient id="aiGrad" x1="0" y1="0" x2="24" y2="24">
                <stop stop-color="#667eea"/>
                <stop offset="1" stop-color="#764ba2"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
      </div>
    </div>

    <div class="workflow-selector">
      <el-select
        v-model="selectedWorkflowId"
        placeholder="选择工作流"
        filterable
        clearable
        @change="handleWorkflowChange"
        class="workflow-select"
      >
        <el-option
          v-for="wf in workflows"
          :key="wf.id"
          :label="wf.title"
          :value="wf.id"
        >
          <div class="workflow-option">
            <span class="workflow-title">{{ wf.title }}</span>
            <span class="workflow-desc">{{ wf.description }}</span>
          </div>
        </el-option>
      </el-select>
    </div>

    <div class="messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <circle cx="24" cy="24" r="20" stroke="url(#emptyGrad)" stroke-width="2" stroke-dasharray="4 4"/>
            <path d="M18 20h12M18 28h8" stroke="#667eea" stroke-width="2" stroke-linecap="round"/>
            <defs>
              <linearGradient id="emptyGrad" x1="0" y1="0" x2="48" y2="48">
                <stop stop-color="#667eea"/>
                <stop offset="1" stop-color="#764ba2"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <p class="empty-text">选择一个工作流开始对话</p>
      </div>
      <transition-group name="message" tag="div" class="message-list">
        <chat-message
          v-for="msg in messages"
          :key="msg.id"
          :message="msg"
        />
      </transition-group>
    </div>

    <div class="chat-input">
      <el-input
        v-model="inputMessage"
        placeholder="输入消息，Enter发送"
        type="textarea"
        :rows="2"
        resize="none"
        @keydown.enter.exact.prevent="handleSend"
        class="message-input"
      />
      <el-button
        type="primary"
        @click="handleSend"
        :disabled="!inputMessage.trim()"
        class="send-button"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import ChatMessage from './ChatMessage.vue'

const props = defineProps({
  workflows: {
    type: Array,
    default: () => []
  },
  messages: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['select-workflow', 'send-message'])

const selectedWorkflowId = ref(null)
const inputMessage = ref('')
const messagesRef = ref(null)

const handleWorkflowChange = (workflowId) => {
  if (!workflowId) {
    selectedWorkflowId.value = null
    return
  }
  const workflow = props.workflows.find(w => w.id === workflowId)
  if (workflow) {
    emit('select-workflow', workflow)
  }
}

const handleSend = () => {
  if (!inputMessage.value.trim()) return
  emit('send-message', inputMessage.value)
  inputMessage.value = ''

  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.chat-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.chat-header {
  padding: 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.title {
  margin: 0 0 4px 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1a1a2e;
}

.subtitle {
  margin: 0;
  font-size: 0.8rem;
  color: #94a3b8;
}

.ai-avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(102, 126, 234, 0.08);
}

.workflow-selector {
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.workflow-select {
  width: 100%;
}

:deep(.workflow-select .el-input__wrapper) {
  border-radius: 12px !important;
  box-shadow: none !important;
  border: 1px solid rgba(0, 0, 0, 0.06) !important;
  padding: 2px 12px !important;
}

.workflow-option {
  display: flex;
  flex-direction: column;
  padding: 4px 0;
}

.workflow-title {
  font-weight: 500;
  color: #1a1a2e;
}

.workflow-desc {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-top: 2px;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.empty-icon {
  opacity: 0.6;
}

.empty-text {
  margin: 0;
  font-size: 0.85rem;
  color: #94a3b8;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.message-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.chat-input {
  padding: 16px 20px;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: #fafafa;
}

.message-input {
  flex: 1;
}

:deep(.message-input .el-textarea__inner) {
  border-radius: 16px !important;
  border: 1px solid rgba(0, 0, 0, 0.06) !important;
  padding: 12px 16px !important;
  font-size: 0.9rem !important;
  resize: none !important;
}

:deep(.message-input .el-textarea__inner:focus) {
  border-color: #667eea !important;
}

.send-button {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  transition: all 0.2s !important;
}

.send-button:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.send-button:disabled {
  opacity: 0.5;
}
</style>