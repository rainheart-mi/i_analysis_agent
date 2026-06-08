import { create } from 'zustand'

let nextMessageId = 0
const genId = () => `msg-${Date.now()}-${++nextMessageId}`

/**
 * AI 对话面板状态。
 *
 * - messages: 已固化的消息列表（user / assistant）
 * - streamingMessageId: 当前正在流式追加的 assistant 消息 id（null 表示无流）
 * - isStreaming: 是否在调用后端
 * - activeNodeExecutionId: 当前面板绑定的节点执行 ID（与 NodeExecution.id 对应）
 * - error: 最近一次错误
 */
export const useChatStore = create((set, get) => ({
  messages: [],
  streamingMessageId: null,
  isStreaming: false,
  activeNodeExecutionId: null,
  error: null,
  selectedWorkflow: null,

  setActiveNodeExecution: (id) => set({
    activeNodeExecutionId: id,
    // 切换节点时不再清空 messages —— 历史拉取交给 useChatHistory
    // 覆盖（AgentScope 是 source of truth），避免误清空正在流的内容
    streamingMessageId: null,
    isStreaming: false,
    error: null,
  }),

  addMessage: (message) => set(state => ({
    messages: [...state.messages, {
      id: genId(),
      feedback: null,
      ...message,
      timestamp: new Date().toISOString()
    }]
  })),

  /** 创建一条空 assistant 消息并返回 id；用于流式增量追加。 */
  startAssistantMessage: () => {
    const id = genId()
    set(state => ({
      messages: [...state.messages, {
        id,
        type: 'assistant',
        content: '',
        thinking: '',
        feedback: null,
        timestamp: new Date().toISOString(),
        streaming: true
      }],
      streamingMessageId: id,
      isStreaming: true,
      error: null,
    }))
    return id
  },

  /** 追加增量文本到当前流式消息（主内容）。 */
  appendDelta: (delta) => set(state => {
    if (!state.streamingMessageId) return state
    return {
      messages: state.messages.map(m =>
        m.id === state.streamingMessageId
          ? { ...m, content: m.content + delta }
          : m
      )
    }
  }),

  /** 追加增量文本到当前流式消息的 thinking 字段。 */
  appendThinking: (delta) => set(state => {
    if (!state.streamingMessageId) return state
    return {
      messages: state.messages.map(m =>
        m.id === state.streamingMessageId
          ? { ...m, thinking: (m.thinking || '') + delta }
          : m
      )
    }
  }),

  /** 流结束时固化消息（去掉 streaming 标记）。 */
  finalizeMessage: () => set(state => ({
    messages: state.messages.map(m =>
      m.id === state.streamingMessageId ? { ...m, streaming: false } : m
    ),
    streamingMessageId: null,
    isStreaming: false,
  })),

  setError: (err) => set({
    isStreaming: false,
    error: err ? (err.message || String(err)) : null,
  }),

  /** 设置某条消息的反馈状态：'like' | 'dislike' | null（清除）。 */
  setFeedback: (messageId, value) => set(state => ({
    messages: state.messages.map(m =>
      m.id === messageId ? { ...m, feedback: value } : m
    ),
  })),

  setSelectedWorkflow: (workflow) => set({ selectedWorkflow: workflow }),

  /** 整体覆盖 messages，用于历史拉取后的批量填充。同步清空流式状态。 */
  setMessages: (msgs) => set({
    messages: msgs,
    streamingMessageId: null,
    isStreaming: false,
  }),

  clearMessages: () => set({
    messages: [],
    streamingMessageId: null,
    isStreaming: false,
    error: null,
  }),
}))
