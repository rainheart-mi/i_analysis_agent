import { AbstractChatProvider, XRequest } from '@ant-design/x-sdk'
import apiClient from '@/api/index'

// 走绝对 URL：与 apiClient.defaults.baseURL 同一来源，dev/prod 一致
// （不能用相对 URL：Vite dev server 无 server.proxy，会 404）
const CHAT_URL = `${apiClient.defaults.baseURL}/chat/stream`

/**
 * 自定义 ChatProvider：适配 FastAPI /chat/stream 的 OpenAI 风格 SSE +
 * AgentScope 扩展字段 delta.thinking。
 *
 * 三方法契约（与官方 CustomProvider 一致）：
 *  - transformParams:        构造 HTTP 请求体（合并 options.params + requestParams + history）
 *  - transformLocalMessage:  onRequest({ query, ... }) → 用户消息 ChatMessage
 *  - transformMessage:       每段 SSE chunk → 累加后的 assistant ChatMessage
 *
 * 字段：
 *  - chunk.data:     一行 SSE data: 之后的 JSON 字符串
 *  - chunk.data === '[DONE]' 视为流结束哨兵
 *  - data.error      视为业务错误，抛错让 useXChat 走 status: 'error'
 *  - data.choices[0].delta.content / .thinking  按位累加
 *
 * 注意：本项目已配置 TOKEN_VALIDATION_ENABLED=false，后端不读 jwt header，
 * 这里不再注入 token。
 */
export class AgentScopeChatProvider extends AbstractChatProvider {
  transformParams(requestParams, options) {
    return {
      ...(options?.params || {}),
      ...requestParams,
      // 与 OpenAIChatProvider 同样的做法：把 useXChat 当前所有"已固化"消息
      // （filter 掉 loading 态）作为 history 注入到请求体
      messages: this.getMessages(),
    }
  }

  transformLocalMessage(requestParams) {
    return {
      content: requestParams?.query || '',
      role: 'user',
    }
  }

  transformMessage(info) {
    const { originMessage, chunk } = info

    if (!chunk?.data) return originMessage
    if (chunk.data === '[DONE]') return originMessage

    let parsed
    try {
      parsed = JSON.parse(chunk.data)
    } catch {
      return originMessage
    }

    // 后端业务错误：data: {"error": "agentscope_timeout"}
    if (parsed?.error) {
      const errMsg = typeof parsed.error === 'string' ? parsed.error : 'agentscope_error'
      throw new Error(errMsg)
    }

    const delta = parsed?.choices?.[0]?.delta || {}
    return {
      ...(originMessage || {}),
      content: (originMessage?.content || '') + (delta.content || ''),
      thinking: (originMessage?.thinking || '') + (delta.thinking || ''),
      role: 'assistant',
    }
  }
}

/**
 * 工厂：构造 XRequest 实例。
 *
 * 注意：
 *  - XRequest(url, options) 返回 AbstractXRequestClass 实例（非函数），
 *    由 useXChat 内部调用 .run(params) 触发
 *  - options.fetch 签名是 (baseURL, options) => Promise<Response>，第一参是原 url
 *  - manual: true 必填，AbstractChatProvider 构造时校验
 */
export function createAgentScopeRequest() {
  return XRequest(CHAT_URL, {
    manual: true,
    fetch: async (baseURL, options) => {
      const resp = await fetch(baseURL, {
        method: options?.method || 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(options?.headers || {}),
        },
        body: options?.body,
        signal: options?.signal,
      })
      if (!resp.ok) {
        let detail = `HTTP ${resp.status}`
        try {
          const j = await resp.json()
          detail = j.detail || j.error || detail
        } catch { /* ignore */ }
        throw new Error(detail)
      }
      return resp
    },
  })
}

export function createAgentScopeProvider() {
  return new AgentScopeChatProvider({
    request: createAgentScopeRequest(),
  })
}
