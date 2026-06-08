import { useEffect, useRef } from 'react'
import { useChatStore } from '@/store/chat'
import { chatHistory } from '@/api/chat'

let histMid = 0
const genId = () => `hist-${Date.now()}-${++histMid}`

/**
 * 把 AgentScope 返回的 message 形态转成 store 形态。
 * 过滤规则（按新设计）：
 *  - system：被 agentscope_proxy 在请求时注入，对用户透明不展示
 *  - user / assistant：保留
 *  - tool：保留（揭示 AI 调过什么工具），提取 name / toolCallId 用于渲染
 *  - assistant.tool_calls：保留并标准化为 { id, name, arguments }
 */
function transform(messages) {
  if (!Array.isArray(messages)) return []
  const now = new Date().toISOString()
  return messages
    .filter(m => m && ['user', 'assistant', 'tool'].includes(m.role))
    .map(m => {
      const base = {
        id: genId(),
        type: m.role,                            // 'user' | 'assistant' | 'tool'
        content: typeof m.content === 'string' ? m.content : '',
        thinking: '',
        feedback: null,
        timestamp: now,
        streaming: false,
      }
      if (m.role === 'tool') {
        base.toolName = m.name
        base.toolCallId = m.tool_call_id
      }
      if (m.role === 'assistant' && Array.isArray(m.tool_calls) && m.tool_calls.length > 0) {
        base.toolCalls = m.tool_calls.map(tc => ({
          id: tc.id,
          name: tc?.function?.name,
          arguments: tc?.function?.arguments,
        }))
      }
      return base
    })
}

/**
 * 监听 activeNodeExecutionId 变化时拉取历史会话并覆盖 messages。
 *
 * 守卫：
 *  - activeId 为 null → 清空（用户进入「新对话」/切到无节点状态）
 *  - activeId 不变 → 跳过（避免重复拉取 / 覆盖正在流的内容）
 *  - isStreaming → 跳过（用户刚发消息还在收尾，不要用历史覆盖正在打字的内容）
 *
 * 失败时把错误写入 store 的 error 字段，UI 已在 useChatBinding 里有错误展示。
 */
export function useChatHistory() {
  const activeId = useChatStore(s => s.activeNodeExecutionId)
  const isStreaming = useChatStore(s => s.isStreaming)
  const setMessages = useChatStore(s => s.setMessages)
  const setError = useChatStore(s => s.setError)
  const lastLoadedRef = useRef(null)

  useEffect(() => {
    if (!activeId) {
      setMessages([])
      lastLoadedRef.current = null
      return
    }
    if (isStreaming) return
    if (lastLoadedRef.current === activeId) return

    let cancelled = false
    ;(async () => {
      try {
        const data = await chatHistory(activeId)
        if (cancelled) return
        if (data?.error) {
          setError(new Error(data.error))
          setMessages([])
          lastLoadedRef.current = activeId
          return
        }
        setMessages(transform(data?.messages))
        lastLoadedRef.current = activeId
      } catch (e) {
        if (cancelled) return
        console.error('[useChatHistory] load failed:', e)
        setError(e instanceof Error ? e : new Error(String(e)))
      }
    })()
    return () => { cancelled = true }
  }, [activeId, isStreaming, setMessages, setError])
}
