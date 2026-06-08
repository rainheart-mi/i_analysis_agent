import axios from 'axios'
import { useUserStore } from '@/store/user'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 30000
})

apiClient.interceptors.request.use(config => {
  const token = useUserStore.getState().token
  if (token) {
    // 对齐后端：默认走 `jwt` header（与 Java 项目 TokenManager 一致）
    // 后端兜底仍兼容 `Authorization: Bearer`
    config.headers['jwt'] = token
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
