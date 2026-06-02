# Vue 3 → React 前端迁移计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将前端技术栈从 Vue 3 + Element Plus 迁移到 React 18 + Ant Design，同时集成 amis 作为动态表单渲染引擎

**Architecture:** 
- 新建 React 项目结构于 `frontend-react/`
- 复用后端 API，保持数据库不变
- 使用 Zustand 替代 Pinia 作为状态管理
- 使用 Ant Design 5 替代 Element Plus
- 使用 amis SDK 原生集成动态表单

**Tech Stack:** React 18, Ant Design 5, React Router 6, Zustand, amis SDK, TypeScript, Vite

---

## 文件结构

```
frontend-react/                    → 新建 React 项目
├── src/
│   ├── api/
│   │   ├── auth.js               → 登录API
│   │   ├── index.js              → API客户端
│   │   └── workflow.js           → 工作流API
│   ├── components/
│   │   └── layout/
│   │       ├── AppLayout.jsx     → 主布局
│   │       ├── Header.jsx        → 顶部导航
│   │       └── Sidebar.jsx       → 侧边栏
│   ├── pages/
│   │   ├── login/
│   │   │   └── Login.jsx         → 登录页
│   │   ├── dashboard/
│   │   │   └── Dashboard.jsx     → 仪表盘
│   │   ├── ai-assistant/
│   │   │   ├── AIAssistant.jsx   → AI助手主页
│   │   │   ├── WorkflowSidebar.jsx   → 工作流列表
│   │   │   ├── WorkflowSelector.jsx   → 工作流选择器
│   │   │   ├── NodeTabs.jsx      → 节点标签
│   │   │   ├── NodeContent.jsx   → 节点内容
│   │   │   ├── ChatPanel.jsx     → 聊天面板
│   │   │   ├── ChatMessage.jsx    → 聊天消息
│   │   │   └── AmISForm.jsx      → amis表单组件
│   │   └── workflow-config/
│   │       ├── index.jsx         → 工作流配置主页
│   │       ├── EnvironmentList.jsx   → 环境列表
│   │       ├── WorkflowRoutes.jsx    → 工作流路由
│   │       └── NodeMappings.jsx      → 节点映射
│   ├── store/
│   │   ├── userStore.js          → 用户状态
│   │   ├── workflowStore.js      → 工作流状态
│   │   ├── taskStore.js          → 任务状态
│   │   └── chatStore.js          → 聊天状态
│   ├── styles/
│   │   └── global.css            → 全局样式
│   ├── App.jsx                   → 根组件
│   ├── main.jsx                  → 入口文件
│   └── router.jsx                → 路由配置
```

---

## Phase 1: 项目初始化

### Task 1: 创建 React 项目结构

**Files:**
- Create: `frontend-react/package.json`
- Create: `frontend-react/vite.config.js`
- Create: `frontend-react/index.html`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "i-analysis-agent-react",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "amis": "^6.13.0",
    "antd": "^5.15.0",
    "axios": "^1.6.7",
    "dayjs": "^1.11.10",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.22.0",
    "zustand": "^4.5.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.1.4"
  }
}
```

- [ ] **Step 2: 运行 npm install**

```bash
cd frontend-react && npm install
```

- [ ] **Step 3: 创建 vite.config.js**

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': '/src'
    }
  }
})
```

- [ ] **Step 4: 提交**

```bash
git add frontend-react/
git commit -m "feat: init React project with Ant Design and amis"
```

---

### Task 2: 创建入口文件和路由配置

**Files:**
- Create: `frontend-react/index.html`
- Create: `frontend-react/src/main.jsx`
- Create: `frontend-react/src/App.jsx`
- Create: `frontend-react/src/router.jsx`

- [ ] **Step 1: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>智能分析助手</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 2: 创建 main.jsx**

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>
)
```

- [ ] **Step 3: 创建 App.jsx**

```jsx
import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import Login from './pages/login/Login'
import Dashboard from './pages/dashboard/Dashboard'
import AIAssistant from './pages/ai-assistant/AIAssistant'
import WorkflowConfig from './pages/workflow-config'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<AppLayout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="ai-assistant" element={<AIAssistant />} />
        <Route path="workflow-config" element={<WorkflowConfig />} />
      </Route>
    </Routes>
  )
}

export default App
```

- [ ] **Step 4: 提交**

---

## Phase 2: 布局和路由

### Task 3: 创建全局样式

**Files:**
- Create: `frontend-react/src/styles/global.css`

- [ ] **Step 1: 创建 global.css**

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  background: #f8f9fb;
  color: #1a1a2e;
}

#root {
  min-height: 100vh;
}
```

- [ ] **Step 2: 提交**

---

### Task 4: 创建布局组件

**Files:**
- Create: `frontend-react/src/components/layout/AppLayout.jsx`
- Create: `frontend-react/src/components/layout/Header.jsx`
- Create: `frontend-react/src/components/layout/Sidebar.jsx`

- [ ] **Step 1: 创建 AppLayout.jsx**

```jsx
import { Outlet } from 'react-router-dom'
import { Layout } from 'antd'
import Header from './Header'
import Sidebar from './Sidebar'

const { Content } = Layout

function AppLayout() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header />
      <Layout>
        <Sidebar />
        <Content style={{ padding: '20px' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default AppLayout
```

- [ ] **Step 2: 创建 Header.jsx**

```jsx
import { Layout, Dropdown, Avatar } from 'antd'
import { UserOutlined } from '@ant-design/icons'

const { Header: AntHeader } = Layout

function Header() {
  const items = [
    { key: 'logout', label: '退出登录' }
  ]

  return (
    <AntHeader style={{ 
      background: '#fff', 
      padding: '0 20px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'flex-end',
      borderBottom: '1px solid rgba(0,0,0,0.04)'
    }}>
      <Dropdown menu={{ items }} placement="bottomRight">
        <Avatar icon={<UserOutlined />} style={{ cursor: 'pointer' }} />
      </Dropdown>
    </AntHeader>
  )
}

export default Header
```

- [ ] **Step 3: 创建 Sidebar.jsx**

```jsx
import { Layout, Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import { DashboardOutlined, RobotOutlined, SettingOutlined } from '@ant-design/icons'

const { Sider } = Layout

function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()

  const items = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: '/ai-assistant', icon: <RobotOutlined />, label: '智能分析' },
    { key: '/workflow-config', icon: <SettingOutlined />, label: '工作流配置' }
  ]

  return (
    <Sider 
      width={220} 
      style={{ 
        background: '#fff',
        borderRight: '1px solid rgba(0,0,0,0.04)'
      }}
    >
      <div style={{ 
        height: 64, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        borderBottom: '1px solid rgba(0,0,0,0.04)'
      }}>
        <span style={{ fontSize: '1.1rem', fontWeight: 600 }}>智能分析平台</span>
      </div>
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={items}
        onClick={({ key }) => navigate(key)}
        style={{ border: 'none' }}
      />
    </Sider>
  )
}

export default Sidebar
```

- [ ] **Step 4: 提交**

---

## Phase 3: 状态管理 (Zustand)

### Task 5: 创建 Zustand stores

**Files:**
- Create: `frontend-react/src/store/userStore.js`
- Create: `frontend-react/src/store/workflowStore.js`
- Create: `frontend-react/src/store/taskStore.js`
- Create: `frontend-react/src/store/chatStore.js`

- [ ] **Step 1: 创建 userStore.js**

```javascript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useUserStore = create(
  persist(
    (set) => ({
      user: null,
      token: null,
      setUser: (user) => set({ user }),
      setToken: (token) => set({ token }),
      logout: () => set({ user: null, token: null })
    }),
    { name: 'user-storage' }
  )
)
```

- [ ] **Step 2: 创建 workflowStore.js**

```javascript
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
    const res = await workflowApi.getWorkflows()
    set({ workflows: res.data.items })
  },

  fetchIntentSchema: async (workflowId) => {
    const workflows = get().workflows
    const workflow = workflows.find(w => w.id === workflowId)
    set({ currentWorkflow: workflow })
    const res = await workflowApi.getIntentSchema(workflowId)
    set({ currentIntentSchema: res.data })
    return res.data
  },

  fetchArtifactSchema: async (workflowId) => {
    const res = await workflowApi.getArtifactSchema(workflowId)
    set({ currentArtifactSchema: res.data })
    return res.data
  }
}))
```

- [ ] **Step 3: 创建 taskStore.js**

```javascript
import { create } from 'zustand'
import { taskApi } from '@/api/workflow'

export const useTaskStore = create((set, get) => ({
  tasks: [],
  currentTask: null,
  currentNodeId: null,
  isExecuting: false,

  fetchTasks: async () => {
    const res = await taskApi.list()
    set({ tasks: res.data })
  },

  createTask: async (workflowId, name) => {
    const res = await taskApi.create(workflowId, name)
    const task = res.data
    const detail = await taskApi.getDetail(task.id)
    const innerTask = detail.data.task
    innerTask.node_executions = detail.data.nodes
    set(state => ({
      tasks: [innerTask, ...state.tasks],
      currentTask: innerTask
    }))
    if (detail.data.nodes?.length > 0) {
      set({ currentNodeId: detail.data.nodes[0].node_id })
    }
    return innerTask
  },

  executeNode: async (nodeId, intentData, taskIdOverride) => {
    const taskId = taskIdOverride || get().currentTask?.id
    if (!taskId) return
    set({ isExecuting: true, currentNodeId: nodeId })
    try {
      const res = await taskApi.executeNode(taskId, nodeId, intentData)
      return res.data
    } finally {
      set({ isExecuting: false })
    }
  },

  mockCompleteNode: async (nodeId) => {
    const taskId = get().currentTask?.id
    if (!taskId) return
    await taskApi.mockCompleteNode(taskId, nodeId)
    const detail = await taskApi.getDetail(taskId)
    set({ currentTask: { ...detail.data.task, node_executions: detail.data.nodes } })
  },

  setCurrentNode: (nodeId) => set({ currentNodeId: nodeId }),
  clearCurrentTask: () => set({ currentTask: null, currentNodeId: null })
}))
```

- [ ] **Step 4: 创建 chatStore.js**

```javascript
import { create } from 'zustand'

export const useChatStore = create((set) => ({
  messages: [],
  selectedWorkflow: null,
  isLoading: false,

  addMessage: (message) => set(state => ({
    messages: [...state.messages, {
      id: Date.now(),
      ...message,
      timestamp: new Date().toISOString()
    }]
  })),

  setSelectedWorkflow: (workflow) => set({ selectedWorkflow: workflow }),
  clearMessages: () => set({ messages: [] })
}))
```

- [ ] **Step 5: 提交**

---

## Phase 4: API 层

### Task 6: 创建 API 客户端

**Files:**
- Create: `frontend-react/src/api/index.js`
- Create: `frontend-react/src/api/auth.js`
- Create: `frontend-react/src/api/workflow.js`

- [ ] **Step 1: 创建 index.js (axios 封装)**

```javascript
import axios from 'axios'
import { useUserStore } from '@/store/userStore'

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
```

- [ ] **Step 2: 创建 auth.js**

```javascript
import apiClient from './index'

export const authApi = {
  login: (username, password) => 
    apiClient.post('/auth/login', { username, password }),
  logout: () => 
    apiClient.post('/auth/logout'),
  getCurrentUser: () => 
    apiClient.get('/auth/me')
}
```

- [ ] **Step 3: 创建 workflow.js**

```javascript
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
```

- [ ] **Step 4: 提交**

---

## Phase 5: 登录页面

### Task 7: 创建登录页面

**Files:**
- Create: `frontend-react/src/pages/login/Login.jsx`

- [ ] **Step 1: 创建 Login.jsx**

```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Button, Card, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { authApi } from '@/api/auth'
import { useUserStore } from '@/store/userStore'

function Login() {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const setUser = useUserStore(state => state.setUser)
  const setToken = useUserStore(state => state.setToken)

  const onFinish = async (values) => {
    setLoading(true)
    try {
      const res = await authApi.login(values.username, values.password)
      setUser(res.data.user)
      setToken(res.data.token)
      message.success('登录成功')
      navigate('/dashboard')
    } catch (e) {
      message.error('登录失败：' + e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ 
      height: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      <Card style={{ width: 400, borderRadius: 16, boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600 }}>智能分析助手</h1>
          <p style={{ color: '#64748b', marginTop: 8 }}>请登录您的账号</p>
        </div>
        <Form
          name="login"
          onFinish={onFinish}
          layout="vertical"
          requiredMark={false}
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input 
              prefix={<UserOutlined />}
              placeholder="用户名"
              size="large"
            />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password 
              prefix={<LockOutlined />}
              placeholder="密码"
              size="large"
            />
          </Form.Item>
          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              block
              size="large"
              style={{ borderRadius: 10, height: 48 }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default Login
```

- [ ] **Step 2: 提交**

---

## Phase 6: 仪表盘

### Task 8: 创建仪表盘页面

**Files:**
- Create: `frontend-react/src/pages/dashboard/Dashboard.jsx`

- [ ] **Step 1: 创建 Dashboard.jsx**

```jsx
import { Card, Row, Col } from 'antd'

function Dashboard() {
  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: 24 }}>仪表盘</h1>
      <Row gutter={[20, 20]}>
        <Col span={6}>
          <Card>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#667eea' }}>0</div>
            <div style={{ color: '#64748b', marginTop: 8 }}>总任务数</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#10B981' }}>0</div>
            <div style={{ color: '#64748b', marginTop: 8 }}>进行中</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#F59E0B' }}>0</div>
            <div style={{ color: '#64748b', marginTop: 8 }}>待处理</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div style={{ fontSize: '2rem', fontWeight: 700, color: '#EF4444' }}>0</div>
            <div style={{ color: '#64748b', marginTop: 8 }}>已完成</div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
```

- [ ] **Step 2: 提交**

---

## Phase 7: AI 助手核心页面

### Task 9: 创建 AmISForm 表单组件

**Files:**
- Create: `frontend-react/src/pages/ai-assistant/AmISForm.jsx`

- [ ] **Step 1: 创建 AmISForm.jsx**

```jsx
import { useRef, useEffect, useState } from 'react'

function AmISForm({ schema, value, onChange, readonly }) {
  const containerRef = useRef(null)
  const [amisInstance, setAmisInstance] = useState(null)

  useEffect(() => {
    let mounted = true

    const initAmis = async () => {
      if (!schema || !containerRef.current) return

      const { embed } = await import('amis')
      
      if (!mounted) return

      // 清除旧内容
      containerRef.current.innerHTML = ''

      const amisSchema = readonly && schema.type === 'form'
        ? { ...schema, mode: 'readonly' }
        : schema

      const instance = embed(containerRef.current, amisSchema, {
        locale: 'zh-CN',
        data: value,
        readOnly: readonly,
        onChange: (val) => {
          if (onChange) onChange(val)
        }
      })

      setAmisInstance(instance)
    }

    initAmis()

    return () => {
      mounted = false
      setAmisInstance(null)
    }
  }, [schema, readonly])

  useEffect(() => {
    if (amisInstance && value) {
      const component = amisInstance.getComponentByName?.()
      if (component?.props) {
        component.props.data = value
      }
    }
  }, [value, amisInstance])

  return <div ref={containerRef} style={{ width: '100%', minHeight: 100 }} />
}

export default AmISForm
```

- [ ] **Step 2: 提交**

---

### Task 10: 创建 AIAssistant 主页面

**Files:**
- Create: `frontend-react/src/pages/ai-assistant/AIAssistant.jsx`

- [ ] **Step 1: 创建 AIAssistant.jsx**

```jsx
import { useEffect, useState } from 'react'
import { useWorkflowStore } from '@/store/workflow'
import { useTaskStore } from '@/store/task'
import { useChatStore } from '@/store/chat'
import WorkflowSidebar from './WorkflowSidebar'
import NodeTabs from './NodeTabs'
import NodeContent from './NodeContent'
import IntentFormPreview from './IntentFormPreview'
import ChatPanel from './ChatPanel'

function AIAssistant() {
  const fetchWorkflows = useWorkflowStore(s => s.fetchWorkflows)
  const fetchTasks = useTaskStore(s => s.fetchTasks)
  const currentTask = useTaskStore(s => s.currentTask)
  const selectedWorkflow = useChatStore(s => s.selectedWorkflow)

  useEffect(() => {
    fetchWorkflows()
    fetchTasks()
  }, [])

  return (
    <div style={{ 
      height: 'calc(100vh - 64px)', 
      display: 'flex', 
      gap: 20,
      background: '#f8f9fb'
    }}>
      <div style={{ width: 260, flexShrink: 0 }}>
        <WorkflowSidebar />
      </div>
      <div style={{ flex: 1, background: '#fff', borderRadius: 16, overflow: 'hidden' }}>
        {currentTask ? (
          <>
            <NodeTabs />
            <NodeContent />
          </>
        ) : selectedWorkflow ? (
          <IntentFormPreview />
        ) : (
          <div style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            justifyContent: 'center',
            height: '100%'
          }}>
            <div style={{ fontSize: 64, marginBottom: 16 }}>📋</div>
            <h3 style={{ color: '#64748b' }}>暂无选中任务</h3>
            <p style={{ color: '#94a3b8' }}>请从右侧选择一个工作流开始对话</p>
          </div>
        )}
      </div>
      <div style={{ width: 380, flexShrink: 0 }}>
        <ChatPanel />
      </div>
    </div>
  )
}

export default AIAssistant
```

- [ ] **Step 2: 提交**

---

### Task 11: 创建 WorkflowSidebar

**Files:**
- Create: `frontend-react/src/pages/ai-assistant/WorkflowSidebar.jsx`

- [ ] **Step 1: 创建 WorkflowSidebar.jsx**

```jsx
import { List, Tag, Empty } from 'antd'
import { ClockCircleOutlined, CheckCircleFilled, SyncSpin } from '@ant-design/icons'
import { useTaskStore } from '@/store/task'
import { useChatStore } from '@/store/chat'

const statusMap = {
  pending: { text: '待执行', color: '#64748b' },
  running: { text: '执行中', color: '#667eea' },
  completed: { text: '已完成', color: '#10B981' },
  failed: { text: '失败', color: '#EF4444' }
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp.endsWith('Z') ? timestamp : timestamp + 'Z')
  const now = new Date()
  const diff = now - date
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function WorkflowSidebar() {
  const tasks = useTaskStore(s => s.tasks)
  const currentTask = useTaskStore(s => s.currentTask)
  const setCurrentNode = useTaskStore(s => s.setCurrentNode)
  const setSelectedWorkflow = useChatStore(s => s.setSelectedWorkflow)

  const handleSelectTask = (task) => {
    setSelectedWorkflow(null)
    if (task.node_executions?.length > 0) {
      setCurrentNode(task.node_executions[0].node_id)
    }
  }

  return (
    <div style={{ background: '#fff', borderRadius: 16, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(0,0,0,0.04)' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>工作流实例</h3>
      </div>
      <List
        style={{ flex: 1, overflow: 'auto', padding: '12px' }}
        dataSource={tasks}
        locale={{ emptyText: <Empty description="暂无任务" /> }}
        renderItem={(item) => (
          <List.Item
            onClick={() => handleSelectTask(item)}
            style={{ 
              padding: '12px', 
              borderRadius: 12, 
              marginBottom: 8,
              cursor: 'pointer',
              border: currentTask?.id === item.id ? '1px solid #667eea' : '1px solid transparent',
              background: currentTask?.id === item.id ? 'rgba(102,126,234,0.04)' : '#fafafa'
            }}
          >
            <div style={{ width: '100%' }}>
              <div style={{ fontWeight: 500, marginBottom: 4 }}>{item.name}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Tag color={statusMap[item.status]?.color} style={{ fontSize: '0.7rem' }}>
                  {item.status === 'running' ? <SyncSpin /> : null}
                  {statusMap[item.status]?.text}
                </Tag>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  <ClockCircleOutlined /> {formatTime(item.updated_at)}
                </span>
              </div>
            </div>
          </List.Item>
        )}
      />
    </div>
  )
}

export default WorkflowSidebar
```

- [ ] **Step 2: 提交**

---

### Task 12: 创建 NodeTabs

**Files:**
- Create: `frontend-react/src/pages/ai-assistant/NodeTabs.jsx`

- [ ] **Step 1: 创建 NodeTabs.jsx**

```jsx
import { Tabs } from 'antd'
import { useTaskStore } from '@/store/task'

function NodeTabs() {
  const currentTask = useTaskStore(s => s.currentTask)
  const currentNodeId = useTaskStore(s => s.currentNodeId)
  const setCurrentNode = useTaskStore(s => s.setCurrentNode)

  if (!currentTask?.node_executions) return null

  const items = currentTask.node_executions.map((node, index) => ({
    key: node.node_id,
    label: node.node_name || `节点 ${index + 1}`
  }))

  return (
    <div style={{ 
      padding: '0 20px', 
      borderBottom: '1px solid rgba(0,0,0,0.04)',
      background: '#fafafa'
    }}>
      <Tabs
        items={items}
        activeKey={currentNodeId}
        onChange={setCurrentNode}
        size="small"
      />
    </div>
  )
}

export default NodeTabs
```

- [ ] **Step 2: 提交**

---

### Task 13: 创建 NodeContent

**Files:**
- Create: `frontend-react/src/pages/ai-assistant/NodeContent.jsx`

- [ ] **Step 1: 创建 NodeContent.jsx**

```jsx
import { useState, useEffect } from 'react'
import { Button, Tag, Spin } from 'antd'
import { useTaskStore } from '@/store/task'
import AmISForm from './AmISForm'

function NodeContent() {
  const currentTask = useTaskStore(s => s.currentTask)
  const currentNodeId = useTaskStore(s => s.currentNodeId)
  const isExecuting = useTaskStore(s => s.isExecuting)
  const executeNode = useTaskStore(s => s.executeNode)
  const mockCompleteNode = useTaskStore(s => s.mockCompleteNode)

  const [intentData, setIntentData] = useState({})
  const [artifactData, setArtifactData] = useState({})

  const currentNode = currentTask?.node_executions?.find(n => n.node_id === currentNodeId)

  const statusMap = {
    pending: { text: '待执行', color: '#64748b' },
    running: { text: '执行中', color: '#667eea' },
    completed: { text: '已完成', color: '#10B981' },
    failed: { text: '失败', color: '#EF4444' }
  }

  const isExecuted = currentNode && ['completed', 'running'].includes(currentNode.status)

  useEffect(() => {
    if (currentNode?.intent_data) {
      setIntentData(currentNode.intent_data)
    }
  }, [currentNode])

  useEffect(() => {
    if (currentNode?.artifact_data) {
      setArtifactData(currentNode.artifact_data)
    }
  }, [currentNode])

  const handleExecute = async () => {
    await executeNode(currentNodeId, intentData)
  }

  const handleMockComplete = async () => {
    await mockCompleteNode(currentNodeId)
  }

  return (
    <div style={{ padding: 20, overflow: 'auto', height: 'calc(100% - 48px)' }}>
      {/* Intent Section */}
      <div style={{ 
        background: '#fff', 
        borderRadius: 12, 
        boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
        marginBottom: 20,
        overflow: 'hidden'
      }}>
        <div style={{ 
          padding: '16px 20px', 
          background: 'linear-gradient(135deg, rgba(102,126,234,0.04) 0%, rgba(118,75,162,0.04) 100%)',
          borderBottom: '1px solid rgba(0,0,0,0.04)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontWeight: 600 }}>意图澄清</span>
            {currentNode && (
              <Tag color={statusMap[currentNode.status]?.color}>
                {statusMap[currentNode.status]?.text}
              </Tag>
            )}
          </div>
        </div>
        <div style={{ padding: 20 }}>
          <AmISForm 
            schema={currentNode?.intent_schema} 
            value={intentData}
            onChange={setIntentData}
            readonly={isExecuted}
          />
        </div>
        {!isExecuted && !isExecuting && (
          <div style={{ 
            padding: '16px 20px', 
            background: '#fafafa',
            borderTop: '1px solid rgba(0,0,0,0.04)',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 12
          }}>
            <Button onClick={() => setIntentData({})}>重置</Button>
            <Button type="primary" onClick={handleExecute}>执行工作流</Button>
          </div>
        )}
        {isExecuting && (
          <div style={{ 
            padding: '16px 20px', 
            background: '#fafafa',
            borderTop: '1px solid rgba(0,0,0,0.04)',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 12
          }}>
            <Button type="primary" onClick={handleMockComplete}>Mock 完成</Button>
          </div>
        )}
      </div>

      {/* Artifact Section */}
      {currentNode?.artifact_data && Object.keys(currentNode.artifact_data).length > 0 && (
        <>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 16, 
            padding: '0 20px',
            marginBottom: 16
          }}>
            <div style={{ flex: 1, height: 1, background: 'linear-gradient(90deg, transparent, rgba(102,126,234,0.3), transparent)' }} />
            <span style={{ 
              padding: '6px 14px', 
              background: 'rgba(102,126,234,0.1)',
              borderRadius: 20,
              fontSize: '0.75rem',
              fontWeight: 600,
              color: '#667eea'
            }}>数据输出</span>
            <div style={{ flex: 1, height: 1, background: 'linear-gradient(90deg, transparent, rgba(102,126,234,0.3), transparent)' }} />
          </div>
          <div style={{ 
            background: '#fff', 
            borderRadius: 12, 
            boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
            overflow: 'hidden'
          }}>
            <div style={{ 
              padding: '16px 20px', 
              background: 'linear-gradient(135deg, rgba(102,126,234,0.04) 0%, rgba(118,75,162,0.04) 100%)',
              borderBottom: '1px solid rgba(0,0,0,0.04)'
            }}>
              <span style={{ fontWeight: 600 }}>生成物展示</span>
            </div>
            <div style={{ padding: 20 }}>
              <AmISForm 
                schema={currentNode?.artifact_schema} 
                value={artifactData}
                readonly
              />
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default NodeContent
```

- [ ] **Step 2: 提交**

---

### Task 14: 创建 IntentFormPreview

**Files:**
- Create: `frontend-react/src/pages/ai-assistant/IntentFormPreview.jsx`

- [ ] **Step 1: 创建 IntentFormPreview.jsx**

```jsx
import { useState } from 'react'
import { Button } from 'antd'
import { useWorkflowStore } from '@/store/workflow'
import { useTaskStore } from '@/store/task'
import { useChatStore } from '@/store/chat'
import AmISForm from './AmISForm'

function IntentFormPreview() {
  const [formData, setFormData] = useState({})
  const currentIntentSchema = useWorkflowStore(s => s.currentIntentSchema)
  const currentWorkflow = useChatStore(s => s.selectedWorkflow)
  const createTask = useTaskStore(s => s.createTask)
  const executeNode = useTaskStore(s => s.executeNode)
  const addMessage = useChatStore(s => s.addMessage)

  const handleExecute = async () => {
    if (!currentWorkflow) return

    try {
      const task = await createTask(currentWorkflow.id, currentWorkflow.title)
      addMessage({ type: 'user', content: `执行工作流: ${currentWorkflow.title}` })

      if (task.node_executions?.length > 0) {
        await executeNode(task.node_executions[0].node_id, formData, task.id)
      }

      addMessage({ type: 'ai', content: `工作流 "${currentWorkflow.title}" 执行完成` })
    } catch (e) {
      addMessage({ type: 'ai', content: `执行失败: ${e.message}` })
    }
  }

  return (
    <div style={{ padding: 20 }}>
      <div style={{ 
        background: '#fff', 
        borderRadius: 12, 
        boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
        overflow: 'hidden'
      }}>
        <div style={{ 
          padding: '16px 20px', 
          background: 'linear-gradient(135deg, rgba(102,126,234,0.04) 0%, rgba(118,75,162,0.04) 100%)',
          borderBottom: '1px solid rgba(0,0,0,0.04)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontWeight: 600 }}>意图澄清</span>
            <span style={{ 
              padding: '4px 10px', 
              borderRadius: 20, 
              fontSize: '0.75rem',
              fontWeight: 600,
              background: 'rgba(102,126,234,0.1)',
              color: '#667eea'
            }}>草稿</span>
          </div>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            {currentWorkflow?.title}
          </span>
        </div>
        <div style={{ padding: 20 }}>
          <AmISForm 
            schema={currentIntentSchema}
            value={formData}
            onChange={setFormData}
          />
        </div>
        <div style={{ 
          padding: '16px 20px', 
          background: '#fafafa',
          borderTop: '1px solid rgba(0,0,0,0.04)',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 12
        }}>
          <Button onClick={() => setFormData({})>重置</Button>
          <Button type="primary" onClick={handleExecute}>执行工作流</Button>
        </div>
      </div>
    </div>
  )
}

export default IntentFormPreview
```

- [ ] **Step 2: 提交**

---

### Task 15: 创建 ChatPanel 和 ChatMessage

**Files:**
- Create: `frontend-react/src/pages/ai-assistant/ChatPanel.jsx`
- Create: `frontend-react/src/pages/ai-assistant/ChatMessage.jsx`

- [ ] **Step 1: 创建 ChatMessage.jsx**

```jsx
function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp.endsWith('Z') ? timestamp : timestamp + 'Z')
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function ChatMessage({ message }) {
  const isUser = message.type === 'user'
  
  return (
    <div style={{ 
      display: 'flex', 
      gap: 10, 
      alignItems: 'flex-start',
      justifyContent: isUser ? 'flex-end' : 'flex-start'
    }}>
      {!isUser && (
        <div style={{ 
          width: 36, 
          height: 36, 
          borderRadius: '50%', 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontSize: '0.9rem'
        }}>AI</div>
      )}
      <div style={{ 
        maxWidth: '70%',
        padding: '12px 16px',
        borderRadius: 16,
        background: isUser ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#fff',
        color: isUser ? '#fff' : '#1a1a2e',
        boxShadow: '0 2px 12px rgba(0,0,0,0.04)'
      }}>
        <div>{message.content}</div>
        <div style={{ 
          fontSize: '0.7rem', 
          marginTop: 4, 
          opacity: 0.7,
          textAlign: 'right'
        }}>{formatTime(message.timestamp)}</div>
      </div>
    </div>
  )
}

export default ChatMessage
```

- [ ] **Step 2: 创建 ChatPanel.jsx**

```jsx
import { useState, useRef, useEffect } from 'react'
import { Input, Button, List } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import { useChatStore } from '@/store/chat'
import { useWorkflowStore } from '@/store/workflow'
import ChatMessage from './ChatMessage'

function ChatPanel() {
  const [input, setInput] = useState('')
  const messages = useChatStore(s => s.messages)
  const workflows = useWorkflowStore(s => s.workflows)
  const addMessage = useChatStore(s => s.addMessage)
  const setSelectedWorkflow = useChatStore(s => s.setSelectedWorkflow)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim()) return
    addMessage({ type: 'user', content: input })
    setInput('')
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={{ 
      background: '#fff', 
      borderRadius: 16, 
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '0 2px 12px rgba(0,0,0,0.04)'
    }}>
      <div style={{ 
        padding: '16px 20px', 
        borderBottom: '1px solid rgba(0,0,0,0.04)',
        fontWeight: 600
      }}>
        工作流选择
      </div>
      <List
        style={{ flex: 1, overflow: 'auto', padding: '12px' }}
        dataSource={workflows}
        renderItem={(item) => (
          <List.Item
            onClick={() => setSelectedWorkflow(item)}
            style={{ 
              cursor: 'pointer', 
              borderRadius: 12, 
              marginBottom: 8,
              padding: '12px'
            }}
          >
            <List.Item.Meta
              title={item.title}
              description={item.description || '暂无描述'}
            />
          </List.Item>
        )}
      />
      <div style={{ 
        padding: '16px 20px', 
        borderTop: '1px solid rgba(0,0,0,0.04)'
      }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <Input.TextArea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="输入消息..."
            autoSize={{ minRows: 1, maxRows: 3 }}
            style={{ borderRadius: 10 }}
          />
          <Button 
            type="primary" 
            icon={<SendOutlined />}
            onClick={handleSend}
            style={{ borderRadius: 10 }}
          />
        </div>
      </div>
    </div>
  )
}

export default ChatPanel
```

- [ ] **Step 3: 提交**

---

## Phase 8: 工作流配置页面

### Task 16: 创建工作流配置页面

**Files:**
- Create: `frontend-react/src/pages/workflow-config/index.jsx`
- Create: `frontend-react/src/pages/workflow-config/EnvironmentList.jsx`
- Create: `frontend-react/src/pages/workflow-config/WorkflowRoutes.jsx`
- Create: `frontend-react/src/pages/workflow-config/NodeMappings.jsx`

- [ ] **Step 1: 创建 index.jsx**

```jsx
import { Tabs } from 'antd'
import EnvironmentList from './EnvironmentList'
import WorkflowRoutes from './WorkflowRoutes'

function WorkflowConfig() {
  const items = [
    { key: 'environments', label: '环境配置', children: <EnvironmentList /> },
    { key: 'routes', label: '工作流路由', children: <WorkflowRoutes /> }
  ]

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: 24 }}>工作流配置</h1>
      <Tabs items={items} />
    </div>
  )
}

export default WorkflowConfig
```

- [ ] **Step 2: 创建 EnvironmentList.jsx**

```jsx
import { useEffect, useState } from 'react'
import { Table, Button, Modal, Form, Input, Select, Tag, message, Space } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { workflowApi } from '@/api/workflow'

function EnvironmentList() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingItem, setEditingItem] = useState(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await workflowApi.getEnvironments()
      setData(res.data)
    } catch (e) {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  const columns = [
    { title: '名称', dataIndex: 'name' },
    { title: '类型', dataIndex: 'type' },
    { title: 'URL', dataIndex: 'url' },
    { title: '状态', dataIndex: 'status', render: s => <Tag>{s}</Tag> },
    {
      title: '操作',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => { setEditingItem(record); setModalVisible(true) }} />
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)} />
        </Space>
      )
    }
  ]

  return (
    <div>
      <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingItem(null); setModalVisible(true) }} style={{ marginBottom: 16 }}>
        新增环境
      </Button>
      <Table columns={columns} dataSource={data} loading={loading} rowKey="id" />
    </div>
  )
}

export default EnvironmentList
```

- [ ] **Step 3: 创建 WorkflowRoutes.jsx**

```jsx
import { useEffect, useState } from 'react'
import { Table, Button, Switch, Tag, Space } from 'antd'
import { workflowApi } from '@/api/workflow'

function WorkflowRoutes() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await workflowApi.getWorkflows()
      setData(res.data.items || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  const columns = [
    { title: '名称', dataIndex: 'title' },
    { title: '描述', dataIndex: 'description' },
    { title: '是否激活', dataIndex: 'is_active', render: (v, r) => <Switch checked={v} onChange={() => toggleActive(r)} /> },
    { title: '节点数', dataIndex: 'node_count' },
    {
      title: '操作',
      render: (_, record) => (
        <Space>
          <Button size="small">配置节点</Button>
        </Space>
      )
    }
  ]

  return (
    <Table columns={columns} dataSource={data} loading={loading} rowKey="id" />
  )
}

export default WorkflowRoutes
```

- [ ] **Step 4: 提交**

---

## Phase 9: 收尾

### Task 17: 添加环境变量配置

**Files:**
- Create: `frontend-react/.env`
- Create: `frontend-react/.env.example`

- [ ] **Step 1: 创建 .env**

```
VITE_API_BASE_URL=http://localhost:8080/api/v1
```

- [ ] **Step 2: 提交**

---

### Task 18: 最终构建测试

**Files:**
- None (验证)

- [ ] **Step 1: 运行构建**

```bash
cd frontend-react && npm run build
```

- [ ] **Step 2: 提交**

---

## 自查清单

- [ ] React 项目结构创建完成
- [ ] 路由和布局组件工作正常
- [ ] Zustand stores 正确管理状态
- [ ] API 客户端正确调用后端
- [ ] 登录页面功能正常
- [ ] AIAssistant 核心流程完整
- [ ] 工作流配置页面可用
- [ ] 生产构建通过