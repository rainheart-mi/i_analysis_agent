import { defineStore } from 'pinia'

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [],
    selectedWorkflow: null,
    isLoading: false
  }),

  actions: {
    addMessage(message) {
      this.messages.push({
        id: Date.now(),
        ...message,
        timestamp: new Date().toISOString()
      })
    },

    setSelectedWorkflow(workflow) {
      this.selectedWorkflow = workflow
    },

    clearMessages() {
      this.messages = []
    }
  }
})