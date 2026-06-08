import apiClient from './index'

/**
 * 从 zustand persist 的 localStorage 键直读 token。
 *
 * 绕开 zustand store 的必要性：axios 拦截器（api/index.js:22-24）在 401 时
 * 会调用 store.logout() 把 token 置 null。即便 chatStream 走的是 fetch 不受
 * 拦截器直接影响，但 chatStream 仍然从 store 读 token，会被"污染后的"空 store
 * 影响。localStorage 是 zustand persist 的唯一物理存储，绕开 store 直读可保证
 * 只要磁盘上还有 token，就一定能被 chatStream 用到。
 */
function readTokenFromStorage() {
  try {
    const raw = localStorage.getItem('user-storage')
    if (!raw) return ''
    const parsed = JSON.parse(raw)
    return parsed?.state?.token || ''
  } catch {
    return ''
  }
}

/**
 * 调用 FastAPI /chat/stream，发起对 AgentScope 后端的 SSE 流式调用。
 *
 * @param {object} params
 * @param {string} params.nodeExecutionId - 节点执行 ID（= AgentScope sessionId）
 * @param {Array<{role:string, content:string}>} params.messages - 完整聊天历史（含最新 user 消息）
 * @param {(delta:string) => void} params.onDelta - 每收到一段主内容增量时回调
 * @param {(delta:string) => void} [params.onThinkingDelta] - 每收到一段思考过程增量时回调（SSE 扩展字段 delta.thinking）
 * @param {() => void} params.onDone - 流结束时回调
 * @param {(err:Error) => void} params.onError - 出错时回调
 * @returns {() => void} abort 函数
 */
export function chatStream({ nodeExecutionId, messages, onDelta, onThinkingDelta, onDone, onError }) {
  const controller = new AbortController()

  const baseURL = apiClient.defaults.baseURL
  // 从 localStorage 直读（不走 store），避免 axios 拦截器 401 → logout() 副作用
  // 详见 readTokenFromStorage 注释
  const token = readTokenFromStorage()

  fetch(`${baseURL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'jwt': token
    },
    body: JSON.stringify({
      node_execution_id: nodeExecutionId,
      messages,
      stream: true
    }),
    signal: controller.signal
  })
    .then(async (resp) => {
      if (!resp.ok) {
        let detail = `HTTP ${resp.status}`
        try {
          const j = await resp.json()
          detail = j.detail || j.error || detail
        } catch (_) { /* ignore */ }
        throw new Error(detail)
      }
      if (!resp.body) {
        throw new Error('empty response body')
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      // 解析 OpenAI 风格 SSE：每条消息以 "\n\n" 分隔；每行 "data: {...}" 是 chunk
      const flushEvents = (text) => {
        const events = text.split('\n\n')
        for (const ev of events) {
          if (!ev.trim()) continue
          const line = ev.split('\n').find(l => l.startsWith('data:'))
          if (!line) continue
          const payload = line.slice(5).trim()
          if (payload === '[DONE]') {
            onDone && onDone()
            return true
          }
          try {
            const chunk = JSON.parse(payload)
            // 提取增量文本（OpenAI 风格：choices[0].delta.content / .thinking）
            const delta = chunk?.choices?.[0]?.delta
            if (delta?.content) {
              onDelta && onDelta(delta.content)
            }
            if (delta?.thinking) {
              onThinkingDelta && onThinkingDelta(delta.thinking)
            }
            // 错误事件
            if (chunk?.error) {
              onError && onError(new Error(String(chunk.error)))
            }
          } catch (e) {
            // 忽略非 JSON 错误
            console.warn('[chatStream] failed to parse chunk:', payload.slice(0, 80))
          }
        }
        return false
      }

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        // 处理完整的 SSE 事件
        const lastSep = buffer.lastIndexOf('\n\n')
        if (lastSep >= 0) {
          const complete = buffer.slice(0, lastSep)
          buffer = buffer.slice(lastSep + 2)
          const doneReceived = flushEvents(complete)
          if (doneReceived) return
        }
      }
      // 处理剩余 buffer
      if (buffer.trim()) {
        flushEvents(buffer)
      } else {
        onDone && onDone()
      }
    })
    .catch((err) => {
      if (err.name === 'AbortError') {
        onDone && onDone()
      } else {
        console.error('[chatStream] error:', err)
        onError && onError(err)
      }
    })

  return () => controller.abort()
}

/** 探活 AgentScope 后端（GET /chat/health）。 */
export function chatHealth() {
  return apiClient.get('/chat/health')
}

/**
 * 列出当前用户的所有 AgentScope session（GET /chat/sessions）。
 *
 * 用于侧边栏「历史会话」分组。每个 session 的 sessionId 与 i_analysis_agent 的
 * node_execution_id 是同一 UUID（chat 写入时 X-Session-Id = node_execution.id），
 * 所以点击 session 可以直接复用 setActiveNodeExecution(sessionId) 触发历史加载。
 *
 * @returns {Promise<{userId: string, count: number, sessions: Array<{userId: string, sessionId: string, sessionKey: string, exists: boolean}>, error?: string}>}
 */
export async function chatSessions() {
  const baseURL = apiClient.defaults.baseURL
  const token = readTokenFromStorage()
  const resp = await fetch(`${baseURL}/chat/sessions`, {
    headers: { 'jwt': token },
  })
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      const j = await resp.json()
      detail = j.detail || j.error || detail
    } catch (_) { /* ignore */ }
    throw new Error(detail)
  }
  return resp.json()
}

/**
 * 拉取指定节点执行的历史 AI 对话（GET /chat/history）。
 *
 * 数据源是 AgentScope 服务端（按 X-Session-Id = node_execution.id 落库），
 * i_analysis_agent 后端仅做 tenant 隔离 + 代理。
 *
 * @param {string} nodeExecutionId - 节点执行 ID（= AgentScope sessionId）
 * @returns {Promise<{node_execution_id: string, messages: Array<{role:string, content:string, name?:string, tool_calls?:any[], tool_call_id?:string}>, source?: string, error?: string}>}
 * @throws {Error} HTTP 非 2xx 时抛错，detail 为后端 detail 字段或 'HTTP {status}'
 */
export async function chatHistory(nodeExecutionId) {
  const baseURL = apiClient.defaults.baseURL
  const token = readTokenFromStorage()
  const resp = await fetch(
    `${baseURL}/chat/history?node_execution_id=${encodeURIComponent(nodeExecutionId)}`,
    { headers: { 'jwt': token } }
  )
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      const j = await resp.json()
      detail = j.detail || j.error || detail
    } catch (_) { /* ignore */ }
    throw new Error(detail)
  }
  return resp.json()
}
