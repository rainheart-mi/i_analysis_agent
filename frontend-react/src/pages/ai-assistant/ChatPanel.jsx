import { useRef, useEffect, useMemo } from 'react'
import { Select, Button, Tooltip, Tag, Space } from 'antd'
import { ExpandOutlined, LockOutlined, ExclamationCircleOutlined, ToolOutlined } from '@ant-design/icons'
import { Bubble, Sender } from '@ant-design/x'
import { useChatStore } from '@/store/chat'
import { useWorkflowStore } from '@/store/workflow'
import { useChatBinding } from './hooks/useChatBinding'
import { useChatHistory } from './hooks/useChatHistory'
import Markdown from '@/components/markdown/Markdown'
import MessageActions from './components/bubbleActions'

function ChatPanel({ onExpand }) {
  const messages = useChatStore(s => s.messages)
  const selectedWorkflow = useChatStore(s => s.selectedWorkflow)
  const setSelectedWorkflow = useChatStore(s => s.setSelectedWorkflow)
  const setActiveNodeExecution = useChatStore(s => s.setActiveNodeExecution)
  const activeNodeExecutionId = useChatStore(s => s.activeNodeExecutionId)
  const setFeedback = useChatStore(s => s.setFeedback)
  const workflows = useWorkflowStore(s => s.workflows)

  const { currentNode, isNodeReady, inputDisabled, isStreaming, nodeStatusLabel, lockMessage,
          error, handleSend, cancel, clearMessages } = useChatBinding()

  // 监听 activeNodeExecutionId 变化，拉取 AgentScope 历史并填充 messages
  useChatHistory()

  const senderRef = useRef(null)

  // 节点切换时同步 sessionId
  useEffect(() => {
    if (currentNode?.id && currentNode.id !== activeNodeExecutionId) {
      setActiveNodeExecution(currentNode.id)
    } else if (!currentNode?.id && activeNodeExecutionId) {
      setActiveNodeExecution(null)
    }
  }, [currentNode?.id, activeNodeExecutionId, setActiveNodeExecution])

  const workflowOptions = workflows.map(w => ({
    value: w.id,
    label: w.title || w.name || '未命名工作流'
  }))

  // Bubble.List 的 items 结构
  // - user: 用户消息
  // - assistant: AI 消息（含 toolCalls footer 角标）
  // - tool: 工具结果（V1 简化为单行徽标，V2 再加可折叠 JSON）
  const bubbleItems = useMemo(
    () => messages.map(m => {
      if (m.type === 'tool') {
        return {
          key: m.id,
          role: 'tool',
          content: `🔧 ${m.toolName || 'tool'}: ${(m.content || '').slice(0, 80)}${(m.content || '').length > 80 ? '…' : ''}`,
        }
      }
      const item = {
        key: m.id,
        role: m.type === 'user' ? 'user' : 'assistant',
        content: m.content,
        loading: m.streaming === true,
      }
      if (m.type === 'assistant' && Array.isArray(m.toolCalls) && m.toolCalls.length > 0) {
        const names = m.toolCalls.map(t => t.name).filter(Boolean).join(', ')
        const toolCallsTag = (
          <Tooltip title={names || '已调用工具'}>
            <Tag color="blue" icon={<ToolOutlined />} style={{ margin: 0, cursor: 'default' }}>
              🔧 {m.toolCalls.length} tool call{m.toolCalls.length > 1 ? 's' : ''}
            </Tag>
          </Tooltip>
        )
        item.footer = (
          <Space size={8} align="center">
            {toolCallsTag}
            <MessageActions message={m} onFeedback={setFeedback} />
          </Space>
        )
      } else {
        item.footer = <MessageActions message={m} onFeedback={setFeedback} />
      }
      return item
    }),
    [messages]
  )

  const placeholder = inputDisabled && isNodeReady ? 'AI 正在思考…' : '基于工作流结果提问…'

  return (
    <div style={{
      background: '#FFFFFF',
      borderRadius: 14,
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      border: '1px solid #E5E6EB',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid #E5E6EB',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 8
      }}>
        <span style={{ fontWeight: 600, fontSize: '15px', color: '#1D2129' }}>AI 对话</span>
        {currentNode && (
          <Tooltip title={currentNode.node_name || currentNode.node_id}>
            {isNodeReady ? (
              <span style={{
                fontSize: '11px', color: '#52C41A', background: '#F6FFED',
                padding: '2px 8px', borderRadius: 10
              }}>● 已就绪</span>
            ) : (
              <span style={{
                fontSize: '11px', color: '#86909C', background: '#F5F7FA',
                padding: '2px 8px', borderRadius: 10
              }}>
                <LockOutlined style={{ fontSize: '10px', marginRight: 2 }} />{nodeStatusLabel}
              </span>
            )}
          </Tooltip>
        )}
        <Button
          type="text"
          icon={<ExpandOutlined />}
          size="small"
          onClick={onExpand}
          style={{ color: '#86909C' }}
        />
      </div>

      {/* Workflow Selector */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #E5E6EB' }}>
        <Select
          value={selectedWorkflow?.id}
          onChange={(val) => {
            const wf = workflows.find(w => w.id === val)
            setSelectedWorkflow(wf || null)
          }}
          placeholder="选择工作流"
          options={workflowOptions}
          style={{ width: '100%' }}
          size="middle"
        />
      </div>

      {/* Messages Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
        {error && (
          <div style={{
            background: '#FFF2F0', border: '1px solid #FFCCC7', color: '#FF4D4F',
            padding: '8px 12px', borderRadius: 8, fontSize: '12px', marginBottom: 12,
            display: 'flex', alignItems: 'center', gap: 6
          }}>
            <ExclamationCircleOutlined />
            <span>{error}</span>
          </div>
        )}
        {messages.length === 0 ? (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', height: '100%', color: '#86909C'
          }}>
            <div style={{
              width: 64, height: 64, borderRadius: 16, background: '#F5F7FA',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 28, marginBottom: 12
            }}>💬</div>
            <span style={{ fontSize: '13px' }}>
              {isNodeReady ? '基于工作流结果开始提问' : '等待节点执行完成'}
            </span>
          </div>
        ) : (
          <Bubble.List
            items={bubbleItems}
            autoScroll
            style={{ paddingBottom: 8 }}
            role={{
              user: { placement: 'end' },
              assistant: { placement: 'start' },
              tool: {
                placement: 'start',
                variant: 'borderless',
                style: { background: '#F5F7FA', maxWidth: '92%', color: '#4E5969' },
              },
            }}
          />
        )}
      </div>

      {/* Input Area */}
      {isNodeReady ? (
        <div style={{
          padding: '12px 16px', borderTop: '1px solid #E5E6EB'
        }}>
          <Sender
            ref={senderRef}
            placeholder={placeholder}
            loading={isStreaming}
            disabled={inputDisabled && isNodeReady}
            onSubmit={(val) => {
              handleSend(val)
              senderRef.current?.clear?.()
            }}
            onCancel={cancel}
            style={{ borderRadius: 10 }}
          />
        </div>
      ) : (
        <div style={{
          padding: '20px 16px', borderTop: '1px solid #E5E6EB',
          background: '#FAFAFA', display: 'flex',
          alignItems: 'center', justifyContent: 'center', gap: 8
        }}>
          <LockOutlined style={{ color: '#86909C', fontSize: 14 }} />
          <span style={{ fontSize: '12px', color: '#86909C' }}>{lockMessage}</span>
        </div>
      )}
    </div>
  )
}

export default ChatPanel
