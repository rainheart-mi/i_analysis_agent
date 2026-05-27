import { create } from 'zustand'

const POLLING_INTERVAL = 2000 // 2秒轮询一次

export const useTaskStore = create((set, get) => ({
  tasks: [],
  currentTask: null,
  currentNodeId: null,
  isExecuting: false,
  pollingTimer: null,

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

  fetchTask: async (taskId) => {
    const { taskApi } = await import('@/api/workflow')
    const detail = await taskApi.getDetail(taskId)
    const innerTask = detail.task
    innerTask.node_executions = detail.nodes
    set({ currentTask: innerTask })
    if (detail.nodes?.length > 0) {
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

  mockCompleteNode: async (nodeId) => {
    const taskId = get().currentTask?.id
    if (!taskId) return
    const { taskApi } = await import('@/api/workflow')

    set({ isExecuting: true })

    try {
      const result = await taskApi.mockCompleteNode(taskId, nodeId)
      // 重新获取任务详情
      const detail = await taskApi.getDetail(taskId)
      const updatedTask = {
        ...detail.task,
        node_executions: detail.nodes
      }
      set(state => ({
        currentTask: updatedTask,
        // 更新 tasks 列表中的任务状态
        tasks: state.tasks.map(t =>
          t.id === taskId ? updatedTask : t
        )
      }))
      // 如果有下一个节点，切换到它
      if (result.next_node_id) {
        set({ currentNodeId: result.next_node_id })
      }
      return result
    } finally {
      set({ isExecuting: false })
    }
  },

  startPolling: (taskId, nodeId) => {
    // 停止之前的轮询
    get().stopPolling()

    const poll = async () => {
      try {
        const status = await get().fetchNodeStatus(taskId, nodeId)

        // 更新当前节点的执行数据
        const currentTask = get().currentTask
        if (currentTask) {
          const updatedNodes = currentTask.node_executions.map(n =>
            n.node_id === nodeId ? { ...n, ...status } : n
          )
          set({ currentTask: { ...currentTask, node_executions: updatedNodes } })
        }

        // 检查是否完成
        if (status.status === 'completed' || status.status === 'failed') {
          get().stopPolling()
          set({ isExecuting: false })
        }
      } catch (e) {
        console.error('Polling error:', e)
      }
    }

    // 立即执行一次
    poll()

    // 设置轮询定时器
    const timer = setInterval(poll, POLLING_INTERVAL)
    set({ pollingTimer: timer })
  },

  stopPolling: () => {
    const timer = get().pollingTimer
    if (timer) {
      clearInterval(timer)
      set({ pollingTimer: null })
    }
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

  clearCurrentTask: () => {
    get().stopPolling()
    set({ currentTask: null, currentNodeId: null })
  }
}))