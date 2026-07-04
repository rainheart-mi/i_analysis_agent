import { create } from 'zustand'

// ★ 轮询节流策略：指数退避（取代原固定 2 秒）
//
// 为什么从 2s 固定改成 2s→4s→8s→10s 退避：
//   - 节点启动后前 10s 状态变化密集（n8n 调用、agent 启动），短间隔保证 UI 及时反馈
//   - 之后节点进入稳态运行，状态变化慢（可能 30s+ 才有一次 status 推进）
//   - 继续用 2s 间隔 = 一次 5min 价格带任务 ~150 次 GET status 请求，对 server 压力大
//   - 退避后：2+4+8+10+10+... ≈ ~50 次（5min），减 67%
//
// 收益：长任务流量大幅减少；UX 上肉眼仍能感知状态变化（人眼对 10s 以内的轮询差异不敏感）
const POLL_BASE_MS = 2000
const POLL_MAX_MS = 10000

/** 根据已 poll 次数计算下一次间隔（指数退避，封顶 POLL_MAX_MS） */
const nextPollDelay = (attempt) => Math.min(POLL_BASE_MS * Math.pow(2, attempt), POLL_MAX_MS)

export const useTaskStore = create((set, get) => ({
  tasks: [],
  currentTask: null,
  currentNodeId: null,
  isExecuting: false,
  pollingTimer: null,
  // ★ 轮询代数（generation）：每次 startPolling / stopPolling 自增。
  //   setTimeout 回调执行前检查自己的 gen 是否仍是最新，否则放弃。
  //   解决 stopPolling 取消 timer 后，正在跑的 poll() 完成仍会 schedule 新 timer 的 race。
  pollingGeneration: 0,
  // ★ 正在 SSE 流式接收的节点集合
  //   stream 模式（useAgentStream.start）的 status 变化是 backend 主动通过
  //   SSE 帧推送的（start / final），前端不再需要 poll /nodes/.../status。
  //   维护这个 set 让 startPolling 在目标节点已在流中时直接 no-op，
  //   避免任何路径（select task / effect 重跑 / 兜底逻辑）误启 polling。
  streamingNodeIds: new Set(),
  // ★ 待自动触发的流式目标：polling 检测到 n8n 完成 + 下游 agent pending 时设置
  //   AIAssistant 监听它自动切到 agent tab；
  //   agent NodeContent mount 时检查匹配则自动 startStream（无需用户点按钮）。
  //   触发成功后由 NodeContent 调 clearAutoStream 清空（避免重复触发）。
  pendingAutoStream: null,  // { taskId, nodeId } | null

  /** 清除 pendingAutoStream（流式已开始 / 用户主动放弃时调用，避免重复触发） */
  clearAutoStream: () => set({ pendingAutoStream: null }),

  fetchTasks: async () => {
    const { taskApi } = await import('@/api/workflow')
    const data = await taskApi.list()
    set({ tasks: Array.isArray(data) ? data : [] })
  },

  createTask: async (workflowId, name) => {
    const { taskApi } = await import('@/api/workflow')
    const task = await taskApi.create(workflowId, name)
    const detail = await taskApi.getDetail(task.id)
    const innerTask = detail.task
    innerTask.node_executions = detail.nodes
    set(state => ({
      tasks: [innerTask, ...state.tasks],
      currentTask: innerTask
    }))
    if (detail.nodes?.length > 0) {
      set({ currentNodeId: detail.nodes[0].node_id })
    }
    return innerTask
  },

  fetchTask: async (taskId, { preserveNodeId = false } = {}) => {
    const { taskApi } = await import('@/api/workflow')
    const detail = await taskApi.getDetail(taskId)
    const innerTask = detail.task
    innerTask.node_executions = detail.nodes
    set({ currentTask: innerTask })
    if (!preserveNodeId && detail.nodes?.length > 0) {
      set({ currentNodeId: detail.nodes[0].node_id })
    }
    return innerTask
  },

  fetchNodeStatus: async (taskId, nodeId) => {
    const { taskApi } = await import('@/api/workflow')
    return await taskApi.getNodeStatus(taskId, nodeId)
  },

  executeNode: async (nodeId, intentData, taskIdOverride) => {
    const taskId = taskIdOverride || get().currentTask?.id
    if (!taskId) return
    const { taskApi } = await import('@/api/workflow')

    set({ isExecuting: true, currentNodeId: nodeId })

    try {
      await taskApi.executeNode(taskId, nodeId, intentData)
      // 更新 tasks 列表中的任务状态为 running
      set(state => ({
        tasks: state.tasks.map(t =>
          t.id === taskId ? { ...t, status: 'running' } : t
        )
      }))
      // 启动轮询监听状态变化
      get().startPolling(taskId, nodeId)
    } catch (e) {
      set({ isExecuting: false })
      throw e
    }
  },

  triggerPostAction: async (nodeId, taskIdOverride) => {
    const taskId = taskIdOverride || get().currentTask?.id
    if (!taskId) return
    const { taskApi } = await import('@/api/workflow')
    set({ isExecuting: true, currentNodeId: nodeId })
    try {
      await taskApi.triggerPostAction(taskId, nodeId)
      // 乐观更新节点状态为 pending，便于 UI 立刻反馈
      set(state => {
        if (!state.currentTask) return {}
        const updatedNodes = state.currentTask.node_executions.map(n =>
          n.node_id === nodeId
            ? { ...n, status: 'pending', error_message: null, completed_at: null }
            : n
        )
        return {
          currentTask: { ...state.currentTask, node_executions: updatedNodes },
        }
      })
      // 启动 polling 监听
      get().startPolling(taskId, nodeId)
    } finally {
      set({ isExecuting: false })
    }
  },

  startPolling: (taskId, nodeId) => {
    // ★ 节点在 SSE 流式接收中 → status 是 backend 通过 SSE 主动推的，
    //   /nodes/.../status 接口对流模式无意义，直接 no-op。
    //   防：WorkflowSidebar.handleSelectTask 在用户切换到 running 任务时调此函数，
    //   防止与 useAgentStream.start 的 SSE 流并行拉 status。
    if (get().streamingNodeIds.has(nodeId)) {
      console.debug(
        '[startPolling] skipped: node is in SSE stream mode: node_id=%s',
        nodeId,
      )
      return
    }

    // 停止之前的轮询（会自增 pollingGeneration，让所有在跑的旧回调作废）
    get().stopPolling()

    // 自己的 gen：本次 polling 的唯一标识。setTimeout 回调内检查，
    // 若已被新轮询 / 显式 stop 顶替则提前 return。
    const myGen = get().pollingGeneration + 1
    set({ pollingGeneration: myGen })
    let attempt = 0

    // ★ 改用递归 setTimeout 取代 setInterval，支持指数退避
    //   每次 poll 后根据 attempt 计数算下次间隔，到 completed/failed 立即终止链
    const schedule = () => {
      if (get().pollingGeneration !== myGen) return
      const delay = nextPollDelay(attempt)
      const timer = setTimeout(async () => {
        if (get().pollingGeneration !== myGen) return
        await poll()
        if (get().pollingGeneration !== myGen) return
        attempt += 1
        schedule()
      }, delay)
      set({ pollingTimer: timer })
    }

    const poll = async () => {
      try {
        const status = await get().fetchNodeStatus(taskId, nodeId)

        // 再次检查 gen（请求期间可能被 stopPolling）
        if (get().pollingGeneration !== myGen) return

        // 更新当前节点的执行数据
        const currentTask = get().currentTask
        if (currentTask) {
          const updatedNodes = currentTask.node_executions.map(n =>
            n.node_id === nodeId ? { ...n, ...status } : n
          )
          set({ currentTask: { ...currentTask, node_executions: updatedNodes } })
        }

        // 非终态：让 setTimeout 回调继续 schedule（带指数退避）
        if (status.status !== 'completed' && status.status !== 'failed') {
          return
        }

        // ★ 终态：不再立刻 stopPolling（避免 self-stop 自增 gen 让下方 fetchTask 检查误判）
        //   把 stopPolling 放到最后统一处理；下方 fetchTask + 下游接棒逻辑都在 myGen 有效期内执行
        set({ isExecuting: false })

        // 主动维护 task 顶层 status：所有节点都终态时，task 也要更新
        // （AIAssistant 路由会看 task.status；不更新会导致"节点完成但 AI 智能体还在等"）
        const nodesAfter = get().currentTask?.node_executions
        if (nodesAfter?.length > 0 && nodesAfter.every(n => n.status === 'completed' || n.status === 'failed')) {
          const hasFailed = nodesAfter.some(n => n.status === 'failed')
          const newStatus = hasFailed ? 'failed' : 'completed'
          set(state => ({
            tasks: state.tasks.map(t => t.id === taskId ? { ...t, status: newStatus } : t),
            currentTask: state.currentTask?.id === taskId
              ? { ...state.currentTask, status: newStatus }
              : state.currentTask,
          }))
        }

        // n8n 完成后接棒下游 agent + 设置自动流式信号：
        // 后端 n8n → _dispatch_next_node 不再自动派发 agent Celery
        // （agent 走前端 SSE 流式接管，Celery 任务保留作兜底）。
        //
        // ★ 前端独家接管：set pendingAutoStream → AIAssistant 切到 agent tab →
        //   NodeContent mount → useEffect 调 startStream → POST SSE
        //
        // 注意：删除此处的 get().startPolling(downstream)：
        //   - 旧实现 startPolling 内部立即 poll() 一次 → GET /nodes/agent/status
        //     （这个请求在网络传输中，useEffect 后调用的 stopPolling 取消不了）
        //   - 删除后让前端 useEffect 独家接管，避免那一次冗余 status 请求
        //   - 兜底仍由 useAgentStream.start finally 的 streamOk 检查覆盖（流失败时 restartPolling）
        if (status.status === 'completed' && status.node_type === 'n8n') {
          try {
            await get().fetchTask(taskId, { preserveNodeId: true })
            // fetchTask 后检查 gen（被外部 stopPolling 顶替才退出；self-stop 在末尾未执行）
            if (get().pollingGeneration !== myGen) return
            const refreshed = get().currentTask
            const downstream = refreshed?.node_executions?.find(
              n => n.node_type === 'agent'
                && (n.status === 'pending' || n.status === 'running')
            )
            if (downstream) {
              // ★ 仅设自动流式信号；不再启动下游 polling（避免冗余 status 请求）
              if (downstream.status === 'pending' && !get().pendingAutoStream) {
                // ★ 目标节点已在流式接收中 → 跳过（防竞态）
                if (!get().streamingNodeIds.has(downstream.node_id)) {
                  set({ pendingAutoStream: { taskId, nodeId: downstream.node_id } })
                }
              }
              // ★ 不再 startPolling(downstream) —— 前端 useEffect 独家接管
              // 不 return：让末尾 stopPolling 终止本轮 setTimeout 链
            }
          } catch (e) {
            console.error('Failed to set pendingAutoStream:', e)
          }
        }

        // ★ 统一在末尾 stop：让 setTimeout 回调的 "if (gen !== myGen) return" 自然终止下一轮
        //   无下游接棒 / 非 n8n 节点完成 / n8n 完成已设 pendingAutoStream 都走这里
        get().stopPolling()
      } catch (e) {
        console.error('Polling error:', e)
        // ★ 终止条件：task 被删（404）/ tenant 切换（410 Gone）→ 立即停
        //   旧逻辑：catch 后继续 schedule → 无限 404 循环（看到截图 21+ 次 status 请求全是 404）
        //   axios error 对象：response.status（4xx/5xx 才有），其他字段（config/request）一定有
        const httpStatus = e?.response?.status
        if (httpStatus === 404 || httpStatus === 410) {
          console.warn(
            '[startPolling] task/node gone, stop polling: status=%s',
            httpStatus,
          )
          get().stopPolling()
          return
        }
        // 其他错误（网络错、5xx）：继续 schedule 下一次（指数退避会自动拉长间隔，给 server 恢复时间）
      }
    }

    // 立即执行一次
    poll()

    // 启动第一次退避 schedule
    schedule()
  },

  stopPolling: () => {
    const timer = get().pollingTimer
    if (timer) {
      clearTimeout(timer)
    }
    // ★ 自增 generation：所有 setTimeout 回调执行前检查，发现自己已作废 → 提前 return
    set({ pollingTimer: null, pollingGeneration: get().pollingGeneration + 1 })
  },

  deleteTask: async (taskId) => {
    const { taskApi } = await import('@/api/workflow')
    await taskApi.deleteTask(taskId)
    set(state => ({
      tasks: state.tasks.filter(t => t.id !== taskId),
      currentTask: state.currentTask?.id === taskId ? null : state.currentTask
    }))
  },

  deleteTasks: async (taskIds) => {
    const { taskApi } = await import('@/api/workflow')
    await taskApi.deleteTasks(taskIds)
    set(state => ({
      tasks: state.tasks.filter(t => !taskIds.includes(t.id)),
      currentTask: taskIds.includes(state.currentTask?.id) ? null : state.currentTask
    }))
  },

  setCurrentNode: (nodeId) => set({ currentNodeId: nodeId }),

  /**
   * 标记 / 取消标记节点在 SSE 流式接收中。
   * useAgentStream.start → true；流终止（success / error / cancel）→ false。
   * startPolling 检查此 set，命中直接 no-op，避免与 SSE 并行 status polling。
   */
  setStreamingNodeId: (nodeId, isStreaming) => set(state => {
    const next = new Set(state.streamingNodeIds)
    if (isStreaming) {
      next.add(nodeId)
    } else {
      next.delete(nodeId)
    }
    return { streamingNodeIds: next }
  }),

  /** 流结束时直接设置当前节点的 artifact 数据（无需 fetchTask） */
  setCurrentNodeArtifact: (nodeId, artifactData, artifactSchema) => set(state => {
    if (!state.currentTask) return {}
    const updatedNodes = state.currentTask.node_executions.map(n =>
      n.node_id === nodeId
        ? {
            ...n,
            artifact_data: artifactData,
            artifact_schema: artifactSchema || n.artifact_schema,
            status: 'completed',
          }
        : n
    )
    // 检查 task 是否全部完成
    const allDone = updatedNodes.every(n => n.status === 'completed' || n.status === 'failed')
    const hasFailed = updatedNodes.some(n => n.status === 'failed')
    return {
      currentTask: {
        ...state.currentTask,
        status: allDone ? (hasFailed ? 'failed' : 'completed') : state.currentTask.status,
        node_executions: updatedNodes,
      },
    }
  }),

  /**
   * 部分更新节点的 artifact 字段（用于流式事件）：
   *   intermediate 事件：updateNodeArtifact(nodeId, { artifact_schema })
   *   final 事件     ：updateNodeArtifact(nodeId, { artifact_data, artifact_schema, status: 'completed' })
   *   stream start   ：updateNodeArtifact(nodeId, { artifact_schema: null })  // 重置
   *
   * 任何字段没传就保持现状（区分 "字段缺省" 和 "字段置 null"：
   *   - undefined：跳过该字段
   *   - null    ：显式置空（如重置 artifact_schema）
   */
  updateNodeArtifact: (nodeId, partial) => set(state => {
    if (!state.currentTask) return {}
    const updatedNodes = state.currentTask.node_executions.map(n => {
      if (n.node_id !== nodeId) return n
      const next = { ...n }
      if ('artifact_data' in partial) next.artifact_data = partial.artifact_data
      if ('artifact_schema' in partial) next.artifact_schema = partial.artifact_schema
      if ('status' in partial) next.status = partial.status
      return next
    })
    // 当 status 更新时同步检查 task 顶层状态
    const allDone = updatedNodes.every(n => n.status === 'completed' || n.status === 'failed')
    const hasFailed = updatedNodes.some(n => n.status === 'failed')
    return {
      currentTask: {
        ...state.currentTask,
        status: allDone ? (hasFailed ? 'failed' : 'completed') : state.currentTask.status,
        node_executions: updatedNodes,
      },
    }
  }),

  clearCurrentTask: () => {
    get().stopPolling()
    set({ currentTask: null, currentNodeId: null })
  }
}))