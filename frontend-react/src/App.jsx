import { Routes, Route, Navigate } from 'react-router-dom'
import { App as AntdApp } from 'antd'
import AppLayout from './components/layout/AppLayout'
import Dashboard from './pages/dashboard/Dashboard'
import AIAssistant from './pages/ai-assistant/AIAssistant'
import WorkflowConfig from './pages/workflow-config'
import AmisPreview from './pages/debug/AmisPreview'

function App() {
  return (
    <AntdApp>
      <Routes>
        <Route path="/debug/amis-preview" element={<AmisPreview />} />
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="ai-assistant" element={<AIAssistant />} />
          <Route path="workflow-config" element={<WorkflowConfig />} />
        </Route>
      </Routes>
    </AntdApp>
  )
}

export default App