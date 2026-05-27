import axios from 'axios'
import { useUserStore } from '@/store/user'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api/v1',
  timeout: 30000
})

apiClient.interceptors.request.use(config => {
  const token = useUserStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      useUserStore.getState().logout()
    }
    return Promise.reject(error)
  }
)

export default apiClient
