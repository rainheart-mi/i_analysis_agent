import apiClient from './index'

export const authApi = {
  login(username, password) {
    return apiClient.post('/auth/login', { username, password })
  },

  refreshToken(refreshToken) {
    return apiClient.post('/auth/refresh', { refresh_token: refreshToken })
  },

  getCurrentUser() {
    return apiClient.get('/auth/me')
  }
}