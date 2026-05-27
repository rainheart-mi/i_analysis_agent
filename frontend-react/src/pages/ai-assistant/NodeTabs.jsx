import { Tabs } from 'antd'
import { useTaskStore } from '@/store/task'

function NodeTabs() {
  const currentTask = useTaskStore(s => s.currentTask)
  const currentNodeId = useTaskStore(s => s.currentNodeId)
  const setCurrentNode = useTaskStore(s => s.setCurrentNode)

  if (!currentTask?.node_executions?.length) return null

  const items = currentTask.node_executions.map((node, index) => ({
    key: node.node_id,
    label: node.node_name || `节点 ${index + 1}`
  }))

  return (
    <div style={{
      padding: '0 4px',
      borderBottom: '1px solid #E5E6EB',
      background: '#FFFFFF'
    }}>
      <Tabs
        items={items}
        activeKey={currentNodeId}
        onChange={setCurrentNode}
        size="small"
        tabBarStyle={{ marginBottom: 0 }}
        style={{ padding: '0 16px' }}
      />
    </div>
  )
}

export default NodeTabs