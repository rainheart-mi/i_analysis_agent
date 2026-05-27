import { createBrowserRouter } from 'react-router-dom'
import App from './App'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, path: '/dashboard', element: <Dashboard /> },
      { path: '/ai-assistant', element: <AIAssistant /> },
      { path: '/workflow-config', element: <WorkflowConfig /> }
    ]
  },
  { path: '/login', element: <Login /> }
])