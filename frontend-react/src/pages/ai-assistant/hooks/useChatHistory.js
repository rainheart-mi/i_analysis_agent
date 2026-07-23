import { useEffect, useRef } from 'react'
import { useXChat } from '@ant-design/x-sdk'
import { useChatStore } from '@/store/chat'
import { chatHistory } from '@/api/chat'
import { createAgentScopeProvider } from '../providers/AgentScopeChatProvider'

// 单例 provider：与 useChatBinding 共享同一实例，确保 useXChat 内部 _request 引用稳定
const provider = createAgentScopeProvider()

let histMid = 0
const genId = () => `hist-${Date.now()}-${++histMid}`

/**
 * 把 AgentScope 返回的 message 形态转成 useXChat 的 MessageInfo[] 形态。
 *
 * MessageInfo = { id, message: ChatMessage, status, extraInfo? }
 * ChatMessage  = { content, thinking, role, toolName?, toolCalls? }
 *
 * 过滤规则（按新设计）：
 *  - system：被 agentscope_proxy 在请求时注入，对用户透明不展示
 *  - user / assistant：保留
 *  - tool：保留（揭示 AI 调过什么工具），提取 name / toolCallId 用于渲染
 *  - assistant.tool_calls：保留并标准化为 { id, name, arguments }
 */
function transformToMessageInfos(messages) {
  if (!Array.isArray(messages)) return []
  return messages
    .filter(m => m && ['user', 'assistant', 'tool'].includes(m.role))
    .map(m => {
      const chatMessage = {
        content: typeof m.content === 'string' ? m.content : '',
        thinking: '',
        role: m.role,
      }
      if (m.role === 'tool') {
        chatMessage.toolName = m.name
        chatMessage.toolCallId = m.tool_call_id
      }
      if (m.role === 'assistant' && Array.isArray(m.tool_calls) && m.tool_calls.length > 0) {
        chatMessage.toolCalls = m.tool_calls.map(tc => ({
          id: tc.id,
          name: tc?.function?.name,
          arguments: tc?.function?.arguments,
        }))
      }
      return {
        id: genId(),
        message: chatMessage,
        status: 'success',
      }
    })
}

/**
 * 监听 activeNodeExecutionId 变化时拉取历史会话并覆盖 messages。
 *
 * 守卫：
 *  - activeId 为 null → 清空（用户进入「新对话」/切到无节点状态）
 *  - activeId 不变 → 跳过（避免重复拉取 / 覆盖正在流的内容）
 *  - isRequesting → 跳过（用户刚发消息还在收尾，不要用历史覆盖正在打字的内容）
 *
 * 失败时把错误写入 store 的 error 字段，UI 已在 useChatBinding 里有错误展示。
 */
export function useChatHistory() {
  const activeId = useChatStore(s => s.activeNodeExecutionId)
  const setError = useChatStore(s => s.setError)
  const lastLoadedRef = useRef(null)

  const { isRequesting, setMessages } = useXChat({
    provider,
    conversationKey: activeId || 'default',
  })

  // activeId 变化时重置缓存，强制下次 effect 重拉
  // 否则 lastLoadedRef 仍等于旧 activeId，stale 错误会一直停在 UI 上
  useEffect(() => {
    if (!activeId) {
      setMessages([])
      lastLoadedRef.current = null
      return
    }
    if (isRequesting) return
    if (lastLoadedRef.current === activeId) return

    let cancelled = false
    ;(async () => {
      // ★ 同步标记 lastLoadedRef，防止 await 期间 effect 重跑导致重复请求
      //   （useXChat 在 conversationKey 变化时会返回新的 setMessages / isRequesting 引用，
      //    触发 effect deps 变化 → 在 fetch 完成前再次进入这个分支）
      lastLoadedRef.current = activeId
      try {
        const data = await chatHistory(activeId)
        if (cancelled) return
        if (data?.error) {
          setError(new Error(data.error))
          setMessages([])
          lastLoadedRef.current = activeId
          return
        }
        setMessages(transformToMessageInfos(data?.messages))
        lastLoadedRef.current = activeId
      } catch (e) {
        if (cancelled) return
        // 404 表示该节点尚未产生聊天记录（agent 刚完成但没人聊过），正常降级为空历史
        if (e.message?.includes('HTTP 404') || e.message?.includes('404')) {
          setMessages([])
          setError(null)
          lastLoadedRef.current = activeId
          return
        }
        console.error('[useChatHistory] load failed:', e)
        setError(e instanceof Error ? e : new Error(String(e)))
      }
    })()
    return () => { cancelled = true }
  }, [activeId, isRequesting, setMessages, setError])
}
