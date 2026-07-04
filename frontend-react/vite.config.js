import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// 读取后端地址（开发时转发 amis 上传等不走 axios 的请求）
const BACKEND = process.env.VITE_API_BACKEND || 'http://localhost:6000'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 6001,
    host: true,
    // 转发 /api/* 到后端（让 amis / fetch / SSE 共享同一套路径）
    // 注意：上传 multipart/form-data 需要 changeOrigin + 不重写 path
    proxy: {
      '/api': {
        target: BACKEND,
        changeOrigin: true,
        // secure: false,  // 调试 https 后端时打开
      },
      // 直连 Java SSE 端点（debug://localhost:8080）
      // 前端通过相对路径 /v1/price-band/... 访问，Vite 转发到 Java 后端
      '/v1/price-band': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        // SSE 流需禁用缓冲，否则事件被 Node.js http-proxy 攒到 buffer 满才转发给浏览器
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('Connection', 'keep-alive')
          })
          proxy.on('proxyRes', (proxyRes) => {
            proxyRes.headers['Cache-Control'] = 'no-cache'
            proxyRes.headers['X-Accel-Buffering'] = 'no'
            proxyRes.headers['Connection'] = 'keep-alive'
          })
        },
      }
    }
  }
})
