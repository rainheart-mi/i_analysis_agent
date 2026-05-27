import { Tabs } from 'antd'
import EnvironmentList from './EnvironmentList'
import WorkflowRoutes from './WorkflowRoutes'
import NodeMappings from './NodeMappings'

function WorkflowConfig() {
  const items = [
    { key: 'environments', label: '环境配置', children: <EnvironmentList /> },
    { key: 'routes', label: '工作流路由', children: <WorkflowRoutes /> },
    { key: 'mappings', label: '节点映射', children: <NodeMappings /> }
  ]

  return (
    <div style={{ padding: 24, background: '#F5F7FA', minHeight: '100%' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: 24, color: '#1D2129' }}>工作流配置</h1>
      <Tabs items={items} />
    </div>
  )
}

export default WorkflowConfig