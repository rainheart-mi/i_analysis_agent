import { defineStore } from 'pinia'
import { workflowApi } from '@/api/workflow'

export const useWorkflowStore = defineStore('workflow', {
  state: () => ({
    environments: [],
    workflows: [],
    currentWorkflow: null,
    currentIntentSchema: null,
    currentArtifactSchema: null,
    mappings: []
  }),

  actions: {
    async fetchEnvironments() {
      const res = await workflowApi.getEnvironments()
      this.environments = res.data
    },

    async fetchWorkflows() {
      const res = await workflowApi.getWorkflows()
      this.workflows = res.data.items
    },

    async fetchWorkflow(id) {
      const res = await workflowApi.getWorkflows()
      // Find by id if already fetched
      this.currentWorkflow = this.workflows.find(w => w.id === id)
    },

    async fetchIntentSchema(workflowId) {
      this.currentWorkflow = this.workflows.find(w => w.id === workflowId) || null
      const res = await workflowApi.getIntentSchema(workflowId)
      this.currentIntentSchema = res.data
      return res.data
    },

    async fetchArtifactSchema(workflowId) {
      const res = await workflowApi.getArtifactSchema(workflowId)
      this.currentArtifactSchema = res.data
      return res.data
    },

    async executeWorkflow(workflowId, data) {
      return await workflowApi.executeWorkflow(workflowId, data)
    }
  }
})