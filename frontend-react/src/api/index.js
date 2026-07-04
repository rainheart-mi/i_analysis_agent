import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:6000/api/v1',
  timeout: 30000
})

// ★ Axios response interceptor: unwrap `response.data` so 调用方拿到的就是裸 body
//
// 原因：axios 的 `apiClient.get/post/...` 默认返回 `{ data, status, statusText, headers, config }`
// 包装对象，但前端所有 store / 组件都按"返回裸 body"约定写的（如 `const data = await ...
// ; set({ list: Array.isArray(data) ? data : (data?.items || []) })`）。一旦 axios 包装
// 没解开，`Array.isArray(data) === false` 且 `data?.items === undefined`，所有 list 接口
// 都会被静默兜底成空数组——UI 显示"暂无数据"。
//
// 在适配层统一 unwrap：调用方代码不需要改；axios 特有的"包装对象"行为收敛在 index.js 这一个
// 适配层里，关注点分离。
//
// 错误路径（4xx/5xx）保持 axios 默认 reject 行为，调用方 try/catch 拿到的 error 对象不变。
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error),
)

export default apiClient
