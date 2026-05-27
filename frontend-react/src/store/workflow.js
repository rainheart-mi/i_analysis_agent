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
    const data = await workflowApi.getIntentSchema(workflowId)
    set({ currentIntentSchema: data })
    return data
  },

  fetchArtifactSchema: async (workflowId) => {
    const data = await workflowApi.getArtifactSchema(workflowId)
    set({ currentArtifactSchema: data })
    return data
  }
}))