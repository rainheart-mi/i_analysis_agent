import apiClient from './index'

// URL 模板：用 {task_id} {node_id} 占位，运行时 replace。
// query string 已带 stream=true，与后端 trigger_post_action 的 Query 参数对齐。
// 走与 src/api/chat.js 同一 baseURL 来源（apiClient.defaults.baseURL），
// dev/prod 一致，避免 Vite dev server 无 proxy 时 404。
const STREAM_URL_TEMPLATE =
  `${apiClient.defaults.baseURL}/tasks/{task_id}/nodes/{node_id}/post-action/trigger?stream=true`

// 直连模式的 proxy 端点模板
const ARTIFACT_URL_TEMPLATE =
  `${apiClient.defaults.baseURL}/tasks/{task_id}/nodes/{node_id}/artifact`

// ★ 重试策略
// - 网络错 / 5xx / timeout：自动重试，最多 3 次
// - 4xx 业务错：不重试（参数错误，重试无意义）
// - 用户主动 abort：不重试
// - AgentScope 不支持 session resume，所以 retry = 重跑整个分析
//   接受 latency 翻倍 + AgentScope 资源消耗，换更高的容错率
const MAX_RETRIES = 3
const BACKOFF_MS = [1000, 3000, 9000]  // 1s, 3s, 9s（递增避雪崩）

// 流式超时（保留上一版）
const PING_TIMEOUT_MS = 30_000
const TOTAL_TIMEOUT_MS = 5 * 60_000

/**
 * 订阅 agent SSE 流（含自动重试）。
 *
 * 解析的 5 类事件：start / intermediate / final / error / ping
 *  - ping: keepalive，自动重置 ping 超时计时器，不回调 onEvent
 *  - 其他: 回调 onEvent(ev)
 *  - final: resolve 为 { ok: true, snapshot }，结束流（终止帧）
 *  - error.fatal: resolve 为 { ok: false, error }，结束流（不重试）
 *
 * @param {object} args
 * @param {string} args.taskId
 * @param {string} args.nodeId
 * @param {(ev: {type: string, [k: string]: any}) => void} args.onEvent
 * @param {AbortSignal} [args.signal]
 * @param {(info: {attempt: number, max: number, nextDelayMs: number}) => void} [args.onRetry]
 * @param {boolean} [args.directStream=false] true 时前端直连 Java SSE 端点，不再经 proxy 转发
 * @returns {Promise<{ok: boolean, error?: string}>}
 */
export async function startAgentStream({
  taskId, nodeId, onEvent, signal, onRetry,
  directStream = false,
}) {
  console.debug('[agentStream] startAgentStream called', { taskId, nodeId, directStream })

  if (directStream) {
    console.debug('[agentStream] directStream=true, calling startDirectAgentStream')
    return await startDirectAgentStream({ taskId, nodeId, onEvent, signal, onRetry })
  }

  console.debug('[agentStream] directStream=false, using proxy path (OLD code!)')
  const url = STREAM_URL_TEMPLATE
    .replace('{task_id}', encodeURIComponent(taskId))
    .replace('{node_id}', encodeURIComponent(nodeId))

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    if (signal?.aborted) throw makeAbortError()

    try {
      return await runOne({
        url, onEvent, externalSignal: signal,
        totalTimeoutMs: TOTAL_TIMEOUT_MS,
        pingTimeoutMs: PING_TIMEOUT_MS,
      })
    } catch (e) {
      // 用户主动 abort：不重试
      if (signal?.aborted || e.name === 'AbortError') throw e

      // ★ 重试决策：仅网络错 / 5xx / timeout 重试；4xx 业务错不重试
      const isRetryable =
        (e.isNetworkError || e.isServerError || e.isTimeout) && !e.notRetryable

      if (isRetryable && attempt < MAX_RETRIES) {
        const delayMs = BACKOFF_MS[attempt]
        if (onRetry) {
          try {
            onRetry({ attempt: attempt + 1, max: MAX_RETRIES, nextDelayMs: delayMs })
          } catch { /* swallow */ }
        }
        await sleep(delayMs, signal)
        continue
      }
      throw e
    }
  }
}

/**
 * 直连模式：前端直接调用 Java 后端的 SSE 端点，绕过 proxy 转发。
 * 1. 先调 proxy 的 trigger_post_action?stream=true&direct_stream=true 获取 Java URL + token
 * 2. 直连 Java SSE 端点拉流
 * 3. 收到 final/fatal 事件后，调 proxy 的 artifact 端点落库
 */
async function startDirectAgentStream({ taskId, nodeId, onEvent, signal, onRetry }) {
  console.debug('[agentStream] startDirectAgentStream entered', { taskId, nodeId })

  // Step 1: 调 proxy 获取直连元数据
  const metaUrl = STREAM_URL_TEMPLATE
    .replace('{task_id}', encodeURIComponent(taskId))
    .replace('{node_id}', encodeURIComponent(nodeId)) + '&direct_stream=true'
  console.debug('[agentStream] direct_stream metadata URL:', metaUrl)

  let meta
  try {
    const metaResp = await fetch(metaUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
      signal,
    })
    if (!metaResp.ok) {
      const detail = `HTTP ${metaResp.status}`
      const e = new Error(detail)
      e.notRetryable = true
      throw e
    }
    meta = await metaResp.json()
    if (!meta.ok || !meta.stream_url) {
      throw new Error('direct_stream setup failed: missing stream_url')
    }
  } catch (e) {
    if (signal?.aborted || e.name === 'AbortError') throw e
    // 直连设置失败：不再 fallback（后端 proxy 路径已废弃），
    // 直接抛出，让上层 useAgentStream.start 显示错误消息
    throw e
  }

  // Step 2: 直连 Java SSE —— 包 try/catch 保证 Step 3 落库逻辑必然执行
  let runResult = null
  let runError = null
  try {
    runResult = await runOne({
      url: meta.stream_url,
      onEvent,
      externalSignal: signal,
      totalTimeoutMs: TOTAL_TIMEOUT_MS,
      pingTimeoutMs: PING_TIMEOUT_MS,
      extraHeaders: { 'X-Internal-Token': meta.internal_token },
      requestBody: meta.body,  // 来自 proxy 模板渲染的完整 payload（含 userId, sessionId, salesData）
    })
  } catch (e) {
    runError = e
  }

  // Step 3: 不论 runOne 成功 / fatal error / 抛错，都回调 proxy 落库。
  //   否则后端节点状态永远停在 pending，后续 chat/history 等接口会 400。
  const artifactUrl = ARTIFACT_URL_TEMPLATE
    .replace('{task_id}', encodeURIComponent(taskId))
    .replace('{node_id}', encodeURIComponent(nodeId))

  try {
    if (runError) {
      // ★ 流被 abort / 网络错 / reader.read() 抛错 → 上报错误让后端把节点标记为 failed
      await fetch(artifactUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          artifact_data: null,
          artifact_schema: null,
          error_message: runError.message || 'stream_error',
        }),
        signal,
      })
    } else if (runResult.ok && runResult.snapshot) {
      const finalData = runResult.snapshot.data || {}
      await fetch(artifactUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          artifact_data: finalData,
          artifact_schema: finalData.artifact_schemas || null,
        }),
        signal,
      })
    } else if (!runResult.ok && runResult.error) {
      await fetch(artifactUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          artifact_data: null,
          artifact_schema: null,
          error_message: runResult.error,
        }),
        signal,
      })
    }
  } catch { /* 落库失败只记日志，不抛出——前端已渲染完成 */ }

  // 落库后再重新抛出原 error（让上层 useAgentStream 知道流失败了）
  if (runError) throw runError
  return runResult
}

function makeAbortError() {
  const e = new Error('aborted')
  e.name = 'AbortError'
  return e
}

/** 可被外部 signal 中断的 sleep */
function sleep(ms, signal) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(resolve, ms)
    if (signal) {
      const onAbort = () => {
        clearTimeout(t)
        reject(makeAbortError())
      }
      signal.addEventListener('abort', onAbort, { once: true })
    }
  })
}

/**
 * 核心 SSE 读取逻辑：fetch → ReadableStream → 逐帧解析。
 *
 * @param {object} args
 * @param {string} args.url  SSE 端点 URL
 * @param {(ev: object) => void} args.onEvent  事件回调
 * @param {AbortSignal} args.externalSignal  外部 abort 信号
 * @param {number} args.totalTimeoutMs  总超时
 * @param {number} args.pingTimeoutMs   无帧超时
 * @param {object} [args.extraHeaders={}]  额外请求头（如 X-Internal-Token）
 */
async function runOne({ url, onEvent, externalSignal, totalTimeoutMs, pingTimeoutMs, extraHeaders = {}, requestBody }) {
  const ctrl = new AbortController()
  const onExternalAbort = () => ctrl.abort()
  externalSignal?.addEventListener('abort', onExternalAbort, { once: true })

  const totalTimer = setTimeout(() => {
    const e = new Error('stream_total_timeout')
    e.isTimeout = true
    ctrl.abort(e)
  }, totalTimeoutMs)

  let pingTimer = null
  const armPing = () => {
    if (pingTimer) clearTimeout(pingTimer)
    pingTimer = setTimeout(() => {
      const e = new Error('stream_ping_timeout')
      e.isTimeout = true
      ctrl.abort(e)
    }, pingTimeoutMs)
  }

  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        ...extraHeaders,
      },
      body: JSON.stringify(requestBody || {}),
      signal: ctrl.signal,
    })
    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`
      try {
        const j = await resp.json()
        detail = j.detail || j.error || detail
      } catch { /* ignore */ }
      const e = new Error(detail)
      if (resp.status === 408) {
        e.isTimeout = true
      } else if (resp.status >= 500) {
        e.isServerError = true
      } else {
        e.isNetworkError = true
        e.notRetryable = true
      }
      throw e
    }

    armPing()
    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      // ★ 规范化换行：Java/Spring WebFlux 默认 SSE 用 \r\n\r\n，标准 SSE 用 \n\n
      buf += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

      let idx
      while ((idx = buf.indexOf('\n\n')) !== -1) {
        const frame = buf.slice(0, idx)
        buf = buf.slice(idx + 2)
        // ★ Java/Spring WebFlux 发的 SSE 格式是 `data:{...}`（无空格），
        //   也有可能 `data: {...}`（带空格）。兼容两种。
        const dataLine = frame.split('\n').find(l => l.startsWith('data:'))
        if (!dataLine) continue
        const jsonText = dataLine.replace(/^data:\s?/, '')
        let ev
        try { ev = JSON.parse(jsonText) } catch { continue }
        if (ev.type === 'ping') {
          armPing()
        } else {
          onEvent(ev)
          if (ev.type === 'final' && ev.ok) {
            return { ok: true, snapshot: ev }
          }
          if (ev.type === 'error' && ev.fatal) {
            return { ok: false, error: ev.error || ev.message }
          }
        }
      }
    }
    return { ok: false, error: 'stream_closed_without_final' }
  } finally {
    clearTimeout(totalTimer)
    if (pingTimer) clearTimeout(pingTimer)
    externalSignal?.removeEventListener('abort', onExternalAbort)
  }
}