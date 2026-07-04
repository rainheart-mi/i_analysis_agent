import { useCallback, useRef, useState } from 'react'
import { useTaskStore } from '@/store/task'
import { message } from 'antd'
import { startAgentStream } from '@/api/agentStream'

/**
 * Agent SSE 流式执行 Hook。
 *
 * 事件统一处理（intermediate 与 final 结构一致）：
 *   - start         : toast + 清空 artifact_schema（重置上一轮遗留）
 *   - intermediate  : 把 schema 写入 currentNode.artifact_schema（流式过程渲染）
 *   - final         : 全部落库到 currentNode.artifact_data + artifact_schema + status='completed'
 *   - error / ping  : 不处理
 *
 * 不维护本地 schema state——全部数据都进 store，渲染只读 currentNode.*，
 * 避免 local/global 双数据源导致视觉跳变。
 *
 * @returns {{ start, cancel, isStreaming }}
 */
export function useAgentStream() {
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef(null)

  const start = useCallback(async (taskId, nodeId) => {
    setIsStreaming(true)
    abortRef.current = new AbortController()

    // ★ 流式启动时暂停 status polling：final 事件已 commit completed 状态
    useTaskStore.getState().stopPolling()
    useTaskStore.getState().setStreamingNodeId(nodeId, true)

    // 重置上一轮的 schema（artifact_data 保留，避免流过程中短暂空白）
    useTaskStore.getState().updateNodeArtifact(nodeId, { artifact_schema: null })

    const handleEvent = (ev) => {
      const evType = ev?.type
      if (evType === 'start') {
        message.success('开始执行')
        return
      }

      // intermediate / final 统一从 ev.data.artifact_schemas 取 schema
      // （intermediate 与 final 结构已统一；fallback 到 ev.schema 兼容老格式）
      if (evType === 'intermediate') {
        const schema =
          ev.data?.artifact_schemas ??
          (Array.isArray(ev.data?.artifact_schemas) ? ev.data.artifact_schemas : null) ??
          ev.schema ??
          null
        if (schema) {
          useTaskStore.getState().updateNodeArtifact(nodeId, { artifact_schema: schema })
        }
        return
      }

      // final 事件不在 handleEvent 里处理；startAgentStream 拿到 snapshot 后统一落库
    }

    try {
      const result = await startAgentStream({
        taskId,
        nodeId,
        onEvent: handleEvent,
        signal: abortRef.current.signal,
        directStream: true,
      })
      // 流成功后同步前端 state：把 final.data 写入 currentNode
      if (result?.ok && result.snapshot?.data) {
        const finalData = result.snapshot.data
        useTaskStore.getState().updateNodeArtifact(nodeId, {
          artifact_data: finalData,
          artifact_schema: finalData.artifact_schemas ?? null,
          status: 'completed',
        })
      }
    } finally {
      setIsStreaming(false)
      abortRef.current = null
      useTaskStore.getState().setStreamingNodeId(nodeId, false)
    }
  }, [])

  const cancel = useCallback(() => {
    abortRef.current?.abort('user_cancelled')
  }, [])

  return { start, cancel, isStreaming }
}