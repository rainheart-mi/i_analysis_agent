import { Prompts } from '@ant-design/x'
import { ExperimentOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useWorkflowStore } from '@/store/workflow'
import { useChatStore } from '@/store/chat'

/**
 * AI 智能体 tab 内的「工作流选择」视图。
 * 用 Ant Design X Prompts 组件把可用工作流渲染成卡片集。
 * 点击卡片 → setSelectedWorkflow(wf) → AIAssistant 中央子视图路由切到 IntentFormPreview。
 */
function WorkflowPromptsView() {
  const workflows = useWorkflowStore(s => s.workflows)
  const setSelectedWorkflow = useChatStore(s => s.setSelectedWorkflow)

  const items = workflows.map((w, idx) => ({
    key: w.id,
    label: w.title || w.name || '未命名工作流',
    description: w.description || '点击进入意图表单填写与执行',
    icon: idx % 2 === 0 ? <ExperimentOutlined /> : <ThunderboltOutlined />,
  }))

  return (
    <div style={{
      height: '100%',
      overflow: 'auto',
      padding: '32px 24px',
      background: '#FAFAFA',
    }}>
      <div style={{ maxWidth: 920, margin: '0 auto' }}>
        <Prompts
          title="🚀 选择工作流开始分析"
          items={items}
          wrap
          onItemClick={({ data }) => {
            const wf = workflows.find(w => w.id === data.key)
            if (wf) setSelectedWorkflow(wf)
          }}
          styles={{
            title: { fontSize: 16, fontWeight: 600, color: '#1D2129', marginBottom: 16 },
            list: {
              gap: 12,
              padding: 0,
              border: 'none',
              background: 'transparent',
            },
            item: {
              background: '#FFFFFF',
              border: '1px solid #E5E6EB',
              borderRadius: 10,
              padding: '14px 16px',
              minWidth: 260,
            },
            itemContent: { color: '#1D2129' },
          }}
        />
        {items.length === 0 && (
          <div style={{
            textAlign: 'center',
            padding: 48,
            color: '#86909C',
            fontSize: 13,
          }}>
            暂无可用工作流，请联系管理员配置
          </div>
        )}
      </div>
    </div>
  )
}

export default WorkflowPromptsView
