import apiClient from './index'

export const taskApi = {
  create: (workflowId, name) => apiClient.post('/tasks', { workflow_id: workflowId, name }),
  list: () => apiClient.get('/tasks'),
  getDetail: (taskId) => apiClient.get(`/tasks/${taskId}`),
  executeNode: (taskId, nodeId, intentData) =>
    apiClient.patch(`/tasks/${taskId}/nodes/${nodeId}/execute`, { intent_data: intentData }),
  updateNode: (taskId, nodeId, data) =>
    apiClient.patch(`/tasks/${taskId}/nodes/${nodeId}`, data),
  mockCompleteNode: (taskId, nodeId) =>
    apiClient.post(`/tasks/${taskId}/nodes/${nodeId}/mock-complete`)
}

export const workflowApi = {
  // Environments
  getEnvironments() {
    return apiClient.get('/n8n-environments')
  },

  createEnvironment(data) {
    return apiClient.post('/n8n-environments', data)
  },

  updateEnvironment(id, data) {
    return apiClient.put(`/n8n-environments/${id}`, data)
  },

  deleteEnvironment(id) {
    return apiClient.delete(`/n8n-environments/${id}`)
  },

  testEnvironment(id) {
    return apiClient.post(`/n8n-environments/${id}/test`)
  },

  // Workflows
  getWorkflows() {
    return apiClient.get('/workflows')
  },

  createWorkflow(data) {
    return apiClient.post('/workflows', data)
  },

  updateWorkflow(id, data) {
    return apiClient.put(`/workflows/${id}`, data)
  },

  deleteWorkflow(id) {
    return apiClient.delete(`/workflows/${id}`)
  },

  getIntentSchema(workflowId) {
    return apiClient.get(`/workflows/${workflowId}/intents`)
  },

  getArtifactSchema(workflowId) {
    return apiClient.get(`/workflows/${workflowId}/artifacts`)
  },

  // Mappings
  getMappings(routeId) {
    return apiClient.get(`/mappings/workflow/${routeId}`)
  },

  createMapping(routeId, data) {
    return apiClient.post(`/mappings/workflow/${routeId}`, data)
  },

  updateMapping(id, data) {
    return apiClient.put(`/mappings/${id}`, data)
  },

  deleteMapping(id) {
    return apiClient.delete(`/mappings/${id}`)
  },

  // Execute
  executeWorkflow(workflowId, data) {
    return apiClient.post(`/execute/${workflowId}`, data)
  },

  getExecutionStatus(workflowId, taskId) {
    return apiClient.get(`/execute/${workflowId}/status/${taskId}`)
  }
}