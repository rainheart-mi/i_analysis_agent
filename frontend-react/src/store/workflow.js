import { create } from 'zustand'
import { workflowApi } from '@/api/workflow'

export const useWorkflowStore = create((set, get) => ({
  environments: [],
  workflows: [],
  currentWorkflow: null,
  currentIntentSchema: null,
  currentArtifactSchema: null,
  mappings: [],

  fetchEnvironments: async () => {
    const res = await workflowApi.getEnvironments()
    set({ environments: res.data })
  },

  fetchWorkflows: async () => {
    const data = await workflowApi.getWorkflows()
    set({ workflows: Array.isArray(data) ? data : (data?.items || []) })
  },

  fetchIntentSchema: async (workflowId) => {
    const workflows = get().workflows
    const workflow = workflows.find(w => w.id === workflowId)
    set({ currentWorkflow: workflow })
    try {
      const data = await workflowApi.getIntentSchema(workflowId)
      // 兜底 null/undefined → {}：空 schema 时 UI 显示"无需填写"占位
      set({ currentIntentSchema: data || {} })
      return data || {}
    } catch (e) {
      // 网络/后端异常：视为"无 schema"，不阻塞 UI 渲染和后续执行
      console.warn('[workflowStore] fetchIntentSchema 失败，降级为空 schema:', e?.message)
      set({ currentIntentSchema: {} })
      return {}
    }
  },

  fetchArtifactSchema: async (workflowId) => {
    try {
      const data = await workflowApi.getArtifactSchema(workflowId)
      set({ currentArtifactSchema: data || {} })
      return data || {}
    } catch (e) {
      console.warn('[workflowStore] fetchArtifactSchema 失败，降级为空 schema:', e?.message)
      set({ currentArtifactSchema: {} })
      return {}
    }
  }
}))