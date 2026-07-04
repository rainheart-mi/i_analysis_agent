import apiClient from './index'

// chatStream 已迁移到 pages/ai-assistant/providers/AgentScopeChatProvider.js
// （基于 @ant-design/x-sdk 的 XRequest + AbstractChatProvider）

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
export function chatSessions() {
  return apiClient.get('/chat/sessions')
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
export function chatHistory(nodeExecutionId) {
  return apiClient.get('/chat/history', { params: { node_execution_id: nodeExecutionId } })
}
