import apiClient from './index'

export const taskApi = {
  create: (workflowId, name) => apiClient.post('/tasks', { workflow_id: workflowId, name }),
  list: () => apiClient.get('/tasks'),
  getDetail: (taskId) => apiClient.get(`/tasks/${taskId}`),
  getNodeStatus: (taskId, nodeId) => apiClient.get(`/tasks/${taskId}/nodes/${nodeId}/status`),
  executeNode: (taskId, nodeId, intentData) =>
    apiClient.patch(`/tasks/${taskId}/nodes/${nodeId}/execute`, { intent_data: intentData }),
  updateNode: (taskId, nodeId, data) =>
    apiClient.patch(`/tasks/${taskId}/nodes/${nodeId}`, data),
  mockCompleteNode: (taskId, nodeId) =>
    apiClient.post(`/tasks/${taskId}/nodes/${nodeId}/mock-complete`),
  deleteTask: (taskId) => apiClient.delete(`/tasks/${taskId}`),
  deleteTasks: (taskIds) => apiClient.delete('/tasks', { data: taskIds })
}

export const workflowApi = {
  getAppConfig: () => apiClient.get('/config'),
  getEnvironments: () => apiClient.get('/n8n-environments'),
  createEnvironment: (data) => apiClient.post('/n8n-environments', data),
  updateEnvironment: (id, data) => apiClient.put(`/n8n-environments/${id}`, data),
  deleteEnvironment: (id) => apiClient.delete(`/n8n-environments/${id}`),
  testEnvironment: (id) => apiClient.post(`/n8n-environments/${id}/test`),
  getWorkflows: () => apiClient.get('/workflows'),
  createWorkflow: (data) => apiClient.post('/workflows', data),
  updateWorkflow: (id, data) => apiClient.put(`/workflows/${id}`, data),
  deleteWorkflow: (id) => apiClient.delete(`/workflows/${id}`),
  getIntentSchema: (workflowId) => apiClient.get(`/workflows/${workflowId}/intents`),
  getArtifactSchema: (workflowId) => apiClient.get(`/workflows/${workflowId}/artifacts`),
  getMappings: (routeId) => apiClient.get(`/mappings/workflow/${routeId}`),
  createMapping: (routeId, data) => apiClient.post(`/mappings/workflow/${routeId}`, data),
  updateMapping: (id, data) => apiClient.put(`/mappings/${id}`, data),
  deleteMapping: (id) => apiClient.delete(`/mappings/${id}`)
}
