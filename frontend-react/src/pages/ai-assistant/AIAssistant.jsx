import { useEffect, useState } from 'react'
import { Tabs } from 'antd'
import { useWorkflowStore } from '@/store/workflow'
import { useTaskStore } from '@/store/task'
import { useChatStore } from '@/store/chat'
import WorkflowSidebar from './WorkflowSidebar'
import NodeTabs from './NodeTabs'
import NodeContent from './NodeContent'
import CanvasArea from './CanvasArea'
import IntentFormPreview from './IntentFormPreview'
import ChatPanel from './ChatPanel'
import ChatContent from './ChatContent'

function AIAssistant() {
  const fetchWorkflows = useWorkflowStore(s => s.fetchWorkflows)
  const fetchTasks = useTaskStore(s => s.fetchTasks)
  const currentTask = useTaskStore(s => s.currentTask)
  const currentNodeId = useTaskStore(s => s.currentNodeId)
  const selectedWorkflow = useChatStore(s => s.selectedWorkflow)
  const currentIntentSchema = useWorkflowStore(s => s.currentIntentSchema)
  const setCurrentNode = useTaskStore(s => s.setCurrentNode)

  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    fetchWorkflows()
    fetchTasks()
  }, [])

  // 计算 tab items：节点 tab + AI 对话 tab
  const nodeTabItems = (currentTask?.node_executions || []).map((node, index) => ({
    key: node.node_id,
    label: node.node_name || `节点 ${index + 1}`,
    children: null, // 实际渲染由下方 switch 控制
  }))

  const chatTabKey = '__chat__'
  const allTabs = [
    ...nodeTabItems,
    { key: chatTabKey, label: '💬 AI 对话', children: null },
  ]

  // 决定中栏渲染什么
  let centerContent
  if (expanded) {
    // 展开态：tabs 选中 AI 对话 → 渲染 ChatContent
    centerContent = <ChatContent onCollapse={() => setExpanded(false)} />
  } else if (currentTask) {
    centerContent = (
      <>
        <NodeTabs />
        <NodeContent />
      </>
    )
  } else if (selectedWorkflow) {
    centerContent = <IntentFormPreview />
  } else {
    centerContent = (
      <CanvasArea
        workflow={null}
        intentSchema={null}
        artifactSchema={null}
        executionResult={null}
      />
    )
  }

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

      {/* Center - Canvas / Chat */}
      <div style={{
        flex: 1,
        background: '#FFFFFF',
        borderRadius: 14,
        border: '1px solid #E5E6EB',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {centerContent}
      </div>

      {/* Right - Chat Panel (默认态) */}
      {!expanded && (
        <div style={{ width: 360, flexShrink: 0 }}>
          <ChatPanel onExpand={() => setExpanded(true)} />
        </div>
      )}
    </div>
  )
}

export default AIAssistant
