import { useMemo, useRef, useCallback } from 'react'
import { useChatStore } from '@/store/chat'
import { useNodeState } from './useNodeState'
import { chatStream } from '@/api/chat'

const STATUS_LABEL = {
  pending: '待执行',
  running: '执行中',
  completed: '已就绪',
  failed: '已失败'
}

const LOCK_MESSAGE = {
  noNode: '请先在中间画布选择并执行一个工作流节点',
  pending: '请先点击「执行工作流」按钮启动该节点',
  running: '节点正在执行中，请等待完成后发起对话',
  failed: '节点执行失败，无法基于该结果发起对话',
  unknown: '节点未完成，无法发起对话'
}

/**
 * 共享 chat 行为 hook：供 ChatPanel（默认态）和 ChatContent（展开态）共用。
 * 返回：当前节点状态、锁状态、发送函数、取消函数、错误信息、清空函数。
 *
 * 注：流式"打字机"视觉效果由 ChatContent.jsx 通过 useStreamContent hook 实现，
 *     本 hook 不再做客户端切片 —— store 里的 content 始终是 source-of-truth。
 */
export function useChatBinding() {
  const { currentNode } = useNodeState()

  const activeNodeExecutionId = useChatStore(s => s.activeNodeExecutionId)
  const isStreaming = useChatStore(s => s.isStreaming)
  const error = useChatStore(s => s.error)
  const addMessage = useChatStore(s => s.addMessage)
  const startAssistantMessage = useChatStore(s => s.startAssistantMessage)
  const appendDelta = useChatStore(s => s.appendDelta)
  const appendThinking = useChatStore(s => s.appendThinking)
  const finalizeMessage = useChatStore(s => s.finalizeMessage)
  const setError = useChatStore(s => s.setError)
  const clearMessages = useChatStore(s => s.clearMessages)

  const abortRef = useRef(null)

  const isNodeReady = currentNode?.status === 'completed'
  const inputDisabled = !isNodeReady || isStreaming

  const nodeStatusLabel = STATUS_LABEL[currentNode?.status] || '未开始'
  const lockMessage = useMemo(() => {
    if (!currentNode) return LOCK_MESSAGE.noNode
    return LOCK_MESSAGE[currentNode.status] || LOCK_MESSAGE.unknown
  }, [currentNode])

  const handleSend = useCallback((text) => {
    const content = (text || '').trim()
    if (!content || inputDisabled || !activeNodeExecutionId) return

    // 取消上一次未完成的流（如有）
    abortRef.current?.()

    addMessage({ type: 'user', content })
    startAssistantMessage()

    const history = useChatStore.getState().messages
      .filter(m => m.type === 'user' || (m.type === 'assistant' && !m.streaming))
      .map(m => ({ role: m.type === 'user' ? 'user' : 'assistant', content: m.content }))

    const abort = chatStream({
      nodeExecutionId: activeNodeExecutionId,
      messages: history,
      onDelta: appendDelta,
      onThinkingDelta: appendThinking,
      onDone: () => {
        abortRef.current = null
        finalizeMessage()
      },
      onError: (err) => {
        abortRef.current = null
        finalizeMessage()
        setError(err)
      },
    })
    abortRef.current = abort || null
  }, [inputDisabled, activeNodeExecutionId, addMessage, startAssistantMessage, appendDelta, appendThinking, finalizeMessage, setError])

  const cancel = useCallback(() => {
    abortRef.current?.()
    abortRef.current = null
    finalizeMessage()
  }, [finalizeMessage])

  return {
    currentNode,
    isNodeReady,
    inputDisabled,
    nodeStatusLabel,
    lockMessage,
    activeNodeExecutionId,
    isStreaming,
    error,
    handleSend,
    cancel,
    clearMessages,
  }
}
