import { useEffect } from 'react'
import { useWorkflowStore } from '@/store/workflow'
import { useTaskStore } from '@/store/task'
import { useChatStore } from '@/store/chat'
import WorkflowSidebar from './WorkflowSidebar'
import NodeTabs from './NodeTabs'
import NodeContent from './NodeContent'
import CanvasArea from './CanvasArea'
import IntentFormPreview from './IntentFormPreview'
import ChatPanel from './ChatPanel'

function AIAssistant() {
  const fetchWorkflows = useWorkflowStore(s => s.fetchWorkflows)
  const fetchTasks = useTaskStore(s => s.fetchTasks)
  const currentTask = useTaskStore(s => s.currentTask)
  const selectedWorkflow = useChatStore(s => s.selectedWorkflow)
  const currentIntentSchema = useWorkflowStore(s => s.currentIntentSchema)

  useEffect(() => {
    fetchWorkflows()
    fetchTasks()
  }, [])

  return (
    <div style={{
      height: 'calc(100vh - 104px)',
      display: 'flex',
      gap: 20,
      padding: '0 0 20px 0'
    }}>
      {/* Left - Workflow Sidebar */}
      <div style={{ width: 280, flexShrink: 0 }}>
        <WorkflowSidebar />
      </div>

      {/* Center - Canvas */}
      <div style={{
        flex: 1,
        background: '#FFFFFF',
        borderRadius: 14,
        border: '1px solid #E5E6EB',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {currentTask ? (
          <>
            <NodeTabs />
            <NodeContent />
          </>
        ) : selectedWorkflow ? (
          <IntentFormPreview />
        ) : (
          <CanvasArea
            workflow={null}
            intentSchema={null}
            artifactSchema={null}
            executionResult={null}
          />
        )}
      </div>

      {/* Right - Chat Panel */}
      <div style={{ width: 360, flexShrink: 0 }}>
        <ChatPanel />
      </div>
    </div>
  )
}

export default AIAssistant