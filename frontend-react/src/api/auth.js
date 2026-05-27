import apiClient from './index'

export const authApi = {
  login: (username, password) =>
    apiClient.post('/auth/login', { username, password }),
  logout: () =>
    apiClient.post('/auth/logout'),
  getCurrentUser: () =>
    apiClient.get('/auth/me')
}
