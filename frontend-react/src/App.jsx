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