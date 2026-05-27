import { create } from 'zustand'

export const useChatStore = create((set) => ({
  messages: [],
  selectedWorkflow: null,
  isLoading: false,

  addMessage: (message) => set(state => ({
    messages: [...state.messages, {
      id: Date.now(),
      ...message,
      timestamp: new Date().toISOString()
    }]
  })),

  setSelectedWorkflow: (workflow) => set({ selectedWorkflow: workflow }),
  clearMessages: () => set({ messages: [] })
}))