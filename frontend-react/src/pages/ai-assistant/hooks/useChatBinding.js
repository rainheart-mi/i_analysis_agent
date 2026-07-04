import { useMemo, useCallback } from 'react'
import { useXChat } from '@ant-design/x-sdk'
import { useChatStore } from '@/store/chat'
import { useTaskStore } from '@/store/task'
import { useNodeState } from './useNodeState'
import { createAgentScopeProvider } from '../providers/AgentScopeChatProvider'

// 单例 provider：避免 React 组件重渲染时反复 new，导致 AbstractChatProvider 内部
// _request 引用变化、useXChat 内部 onUpdate/onSuccess/onError 回调链断裂
const provider = createAgentScopeProvider()

const STATUS_LABEL = {
  pending: '待执行',
  running: '执行中',
  completed: '已就绪',
  failed: '已失败'
}

const LOCK_MESSAGE = {
  noTask: '请先在节点工作流页启动并完成工作流执行',
  pending: '工作流尚未启动，请先在节点 tab 执行',
  running: '工作流执行中，请等待完成后再发起对话',
  failed: '工作流执行失败，无法基于该结果发起对话',
  unknown: '工作流未完成，无法发起对话'
}

/**
 * 共享 chat 行为 hook：供 ChatContent（默认态）使用。
 * 返回：当前节点状态、锁状态、发送函数、取消函数、错误信息、useXChat 实例引用。
 *
 * 数据流：
 *  - useXChat 接管 messages + isRequesting + abort；store 不再持有流式粘合代码
 *  - 字符级打字机由 ChatContent 内的 useTypewriter 提供（与数据层正交）
 */
export function useChatBinding() {
  const { currentNode } = useNodeState()
  const currentTask = useTaskStore(s => s.currentTask)

  const activeNodeExecutionId = useChatStore(s => s.activeNodeExecutionId)
  const error = useChatStore(s => s.error)
  const setError = useChatStore(s => s.setError)

  // 多 hook 共享 useXChat store：用 activeNodeExecutionId 作为 conversationKey
  // 切节点 → 自动切 store 实例；无节点时回退到 'default'（用 ChatContent 的渲染条件保证）
  const { onRequest, abort, isRequesting, messages, setMessages, setMessage } = useXChat({
    provider,
    conversationKey: activeNodeExecutionId || 'default',
  })

  // 重构后约束：必须整个工作流任务（currentTask）completed 才能发起对话
  // 兜底：如果 task 顶层 status 没及时更新，但所有 node_executions 都 completed，也视为就绪
  const isTaskDone = useMemo(() => {
    if (currentTask?.status === 'completed') return true
    const nodes = currentTask?.node_executions
    return !!nodes?.length && nodes.every(n => n.status === 'completed')
  }, [currentTask?.status, currentTask?.node_executions])
  const isNodeReady = isTaskDone
  const inputDisabled = !isNodeReady || isRequesting

  const nodeStatusLabel = STATUS_LABEL[currentNode?.status] || '未开始'
  const lockMessage = useMemo(() => {
    if (!currentTask) return LOCK_MESSAGE.noTask
    if (isTaskDone) return null
    return LOCK_MESSAGE[currentTask.status] || LOCK_MESSAGE.unknown
  }, [currentTask, isTaskDone])

  const handleSend = useCallback((text) => {
    const content = (text || '').trim()
    if (!content || inputDisabled || !activeNodeExecutionId) return

    // history 由 provider.transformParams → this.getMessages() 自动注入
    // （OpenAIChatProvider 同款做法；getMessages 已 filter 掉 loading 态）
    onRequest({
      query: content,
      node_execution_id: activeNodeExecutionId,
    })
  }, [inputDisabled, activeNodeExecutionId, onRequest])

  const cancel = useCallback(() => {
    abort()
  }, [abort])

  /**
   * 反馈写入：useXChat.setMessage(id, partial) 更新单条消息的 extraInfo
   * 模板：setMessage(id, (m) => ({ extraInfo: { ...(m.extraInfo || {}), feedback: v } }))
   */
  const setFeedback = useCallback((messageId, value) => {
    setMessage(messageId, (m) => ({
      extraInfo: { ...(m.extraInfo || {}), feedback: value },
    }))
  }, [setMessage])

  return {
    currentNode,
    currentTask,
    isNodeReady,
    inputDisabled,
    nodeStatusLabel,
    lockMessage,
    activeNodeExecutionId,
    isStreaming: isRequesting,
    error,
    setError,
    handleSend,
    cancel,
    // 暴露 useXChat 实例给上层（ChatContent 渲染 bubbleItems / useChatHistory 拉历史）
    messages,
    setMessages,
    setFeedback,
  }
}
