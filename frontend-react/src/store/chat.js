import { create } from 'zustand'

/**
 * AI 对话面板业务态 store。
 *
 * 数据流分工（2026-06-09 重构后）：
 *  - useXChat (pages/ai-assistant/providers/AgentScopeChatProvider)  接管 messages
 *    + 流式增量 + abort；本 store 不再持有 messages 字段
 *  - 本 store 只保留业务态：activeNodeExecutionId / selectedWorkflow / error
 *
 * 反馈（feedback）：用 useXChat.setMessage(id, { extraInfo: { feedback: v } }) 写入；
 *  不在本 store 维护。
 */
export const useChatStore = create((set) => ({
  activeNodeExecutionId: null,
  error: null,
  selectedWorkflow: null,

  setActiveNodeExecution: (id) => set({
    activeNodeExecutionId: id,
    error: null,
  }),

  setError: (err) => set({
    error: err ? (err.message || String(err)) : null,
  }),

  setSelectedWorkflow: (workflow) => set({ selectedWorkflow: workflow }),
}))
