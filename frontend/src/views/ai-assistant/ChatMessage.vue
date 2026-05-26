<template>
  <div class="chat-message" :class="[`message-${message.type}`]">
    <div class="message-avatar">
      <div class="avatar-inner">
        <svg v-if="message.type === 'user'" width="18" height="18" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="2"/>
          <path d="M4 20c0-4 4-6 8-6s8 2 8 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" fill="currentColor" fill-opacity="0.2"/>
          <path d="M8 10h8M8 14h5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </div>
    </div>
    <div class="message-content">
      <div class="message-bubble">
        <template v-if="message.type === 'user'">
          {{ message.content }}
        </template>
        <template v-else>
          <div class="ai-response">
            <p>{{ message.content }}</p>
          </div>
        </template>
      </div>
      <div class="message-time">
        {{ formatTime(message.timestamp) }}
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  message: {
    type: Object,
    required: true
  }
})

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const dateStr = timestamp.endsWith('Z') ? timestamp : timestamp + 'Z'
  return new Date(dateStr).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 10px;
  animation: messageIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes messageIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.avatar-inner {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message-user .avatar-inner {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
}

.message-ai .avatar-inner {
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
}

.message-content {
  max-width: 75%;
  display: flex;
  flex-direction: column;
}

.message-user .message-content {
  align-items: flex-end;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 0.9rem;
  line-height: 1.5;
  word-break: break-word;
}

.message-user .message-bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-ai .message-bubble {
  background: #f4f4f5;
  color: #1a1a2e;
  border-bottom-left-radius: 4px;
}

.message-time {
  font-size: 0.7rem;
  color: #94a3b8;
  margin-top: 4px;
  padding: 0 4px;
}

.ai-response {
  min-width: 180px;
}

.ai-response p {
  margin: 0;
}
</style>