import { defineStore } from 'pinia'
import { taskApi } from '@/api/workflow'

export const useTaskStore = defineStore('task', {
  state: () => ({
    tasks: [],
    currentTask: null,
    currentNodeId: null,
    isExecuting: false
  }),

  getters: {
    currentNode(state) {
      if (!state.currentTask || !state.currentNodeId) return null
      const executions = state.currentTask.node_executions || []
      return executions.find(n => n.node_id === state.currentNodeId) || null
    },

    nodes(state) {
      if (!state.currentTask) return []
      return state.currentTask.node_executions || []
    }
  },

  actions: {
    async fetchTasks() {
      const res = await taskApi.list()
      this.tasks = res.data
    },

    async createTask(workflowId, name) {
      const res = await taskApi.create(workflowId, name)
      const task = res.data
      // Fetch full task detail with node_executions
      const detail = await taskApi.getDetail(task.id)

      // detail.data is TaskDetailResponse: {task: {id, ...}, nodes: [...], workflow_title}
      // Extract inner task object and attach node_executions
      const innerTask = detail.data.task
      innerTask.node_executions = detail.data.nodes

      // Add to the beginning of the tasks list
      this.tasks.unshift(innerTask)
      this.currentTask = innerTask
      if (detail.data.nodes?.length > 0) {
        this.currentNodeId = detail.data.nodes[0].node_id
      }
      // Return the innerTask so callers get the expected {id, node_executions} structure
      return innerTask
    },

    async fetchTask(taskId) {
      const res = await taskApi.getDetail(taskId)
      // res.data is TaskDetailResponse: {task, nodes, workflow_title}
      // Extract inner task and attach node_executions
      const innerTask = res.data.task
      innerTask.node_executions = res.data.nodes
      this.currentTask = innerTask
      if (res.data.nodes?.length > 0) {
        this.currentNodeId = res.data.nodes[0].node_id
      }
      return innerTask
    },

    async executeNode(nodeId, intentData, taskIdOverride) {
      const taskId = taskIdOverride || this.currentTask?.id
      if (!taskId) return
      this.isExecuting = true
      this.currentNodeId = nodeId

      try {
        const res = await taskApi.executeNode(taskId, nodeId, intentData)
        const execution = res.data

        // Update node execution in currentTask, preserving existing fields like intent_schema
        const executions = this.currentTask.node_executions || []
        const index = executions.findIndex(n => n.node_id === nodeId)
        if (index >= 0) {
          // Merge: keep existing node data, only update status/intent_data
          executions[index] = {
            ...executions[index],
            status: execution.status || 'running',
            intent_data: intentData || executions[index].intent_data
          }
        } else {
          executions.push(execution)
        }
        this.currentTask = { ...this.currentTask, node_executions: executions }

        return execution
      } finally {
        this.isExecuting = false
      }
    },

    async updateIntentData(nodeId, intentData) {
      const taskId = this.currentTask?.id
      if (!taskId) return

      try {
        await taskApi.updateNode(taskId, nodeId, { intent_data: intentData })

        // Update local state
        const executions = this.currentTask.node_executions || []
        const index = executions.findIndex(n => n.node_id === nodeId)
        if (index >= 0) {
          executions[index] = {
            ...executions[index],
            intent_data: intentData
          }
        }
        this.currentTask = { ...this.currentTask, node_executions: executions }
      } catch (e) {
        console.error('updateIntentData error:', e)
      }
    },

    async mockCompleteNode(nodeId) {
      const taskId = this.currentTask?.id
      if (!taskId) return

      try {
        await taskApi.mockCompleteNode(taskId, nodeId)

        // Refetch task detail to get updated node with artifact_data
        const res = await taskApi.getDetail(taskId)
        const detail = res.data
        const innerTask = detail.task
        innerTask.node_executions = detail.nodes
        this.currentTask = innerTask
        if (detail.nodes?.length > 0) {
          this.currentNodeId = detail.nodes[0].node_id
        }
      } catch (e) {
        console.error('mockCompleteNode error:', e)
      }
    },

    setCurrentNode(nodeId) {
      this.currentNodeId = nodeId
    },

    clearCurrentTask() {
      this.currentTask = null
      this.currentNodeId = null
      this.isExecuting = false
    }
  }
})