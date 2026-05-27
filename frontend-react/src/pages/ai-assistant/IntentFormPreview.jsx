import { useState, useEffect } from 'react'
import { Button } from 'antd'
import { useWorkflowStore } from '@/store/workflow'
import { useTaskStore } from '@/store/task'
import { useChatStore } from '@/store/chat'
import AmISForm from './AmISForm'

function IntentFormPreview() {
  const [formData, setFormData] = useState({})
  const currentIntentSchema = useWorkflowStore(s => s.currentIntentSchema)
  const currentWorkflow = useChatStore(s => s.selectedWorkflow)
  const setSelectedWorkflow = useChatStore(s => s.setSelectedWorkflow)
  const createTask = useTaskStore(s => s.createTask)
  const executeNode = useTaskStore(s => s.executeNode)
  const addMessage = useChatStore(s => s.addMessage)
  const fetchIntentSchema = useWorkflowStore(s => s.fetchIntentSchema)

  // 当工作流变化时，获取对应的意图schema
  useEffect(() => {
    if (currentWorkflow?.id) {
      fetchIntentSchema(currentWorkflow.id)
    }
  }, [currentWorkflow])

  const handleReset = () => setFormData({})

  const handleExecute = async () => {
    if (!currentWorkflow) return

    try {
      const task = await createTask(currentWorkflow.id, currentWorkflow.title)
      addMessage({ type: 'user', content: `执行工作流: ${currentWorkflow.title}` })

      if (task.node_executions?.length > 0) {
        await executeNode(task.node_executions[0].node_id, formData, task.id)
      }

      // 执行完成后清空选择的工作流，让界面切换到任务详情
      setSelectedWorkflow(null)

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
          <Button onClick={handleReset}>重置</Button>
          <Button
            type="primary"
            onClick={handleExecute}
            style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              border: 'none'
            }}
          >
            执行工作流
          </Button>
        </div>
      </div>
    </div>
  )
}

export default IntentFormPreview