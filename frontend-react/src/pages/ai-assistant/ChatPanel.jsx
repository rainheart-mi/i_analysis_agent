import { useState, useRef, useEffect } from 'react'
import { Input, Button, Select, Empty } from 'antd'
import { SendOutlined, ExpandOutlined } from '@ant-design/icons'
import { useChatStore } from '@/store/chat'
import { useWorkflowStore } from '@/store/workflow'
import ChatMessage from './ChatMessage'

function ChatPanel() {
  const [input, setInput] = useState('')
  const messages = useChatStore(s => s.messages)
  const addMessage = useChatStore(s => s.addMessage)
  const clearMessages = useChatStore(s => s.clearMessages)
  const selectedWorkflow = useChatStore(s => s.selectedWorkflow)
  const setSelectedWorkflow = useChatStore(s => s.setSelectedWorkflow)
  const workflows = useWorkflowStore(s => s.workflows)
  const messagesEndRef = useRef(null)

  // 监听 messages 变化，当被清空时同时清空 input
  useEffect(() => {
    if (messages.length === 0) {
      setInput('')
    }
  }, [messages])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim()) return
    addMessage({ type: 'user', content: input })
    setInput('')
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const workflowOptions = workflows.map(w => ({
    value: w.id,
    label: w.title || w.name || '未命名工作流'
  }))

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
        justifyContent: 'space-between'
      }}>
        <span style={{ fontWeight: 600, fontSize: '15px', color: '#1D2129' }}>
          AI 对话
        </span>
        <Button
          type="text"
          icon={<ExpandOutlined />}
          size="small"
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
          dropdownStyle={{ borderRadius: 10 }}
        />
      </div>

      {/* Messages Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
        {messages.length === 0 ? (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: '#86909C'
          }}>
            <div style={{
              width: 64,
              height: 64,
              borderRadius: 16,
              background: '#F5F7FA',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 28,
              marginBottom: 12
            }}>
              💬
            </div>
            <span style={{ fontSize: '13px' }}>开始和 AI 对话吧</span>
          </div>
        ) : (
          messages.map((msg, index) => (
            <ChatMessage key={index} message={msg} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div style={{
        padding: '12px 16px',
        borderTop: '1px solid #E5E6EB',
        display: 'flex',
        gap: 10,
        alignItems: 'flex-end'
      }}>
        <Input.TextArea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="输入消息..."
          autoSize={{ minRows: 1, maxRows: 3 }}
          style={{
            flex: 1,
            borderRadius: 10,
            resize: 'none',
            border: '1px solid #E5E6EB'
          }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSend}
          style={{
            borderRadius: 10,
            height: 36,
            width: 36,
            padding: 0,
            background: '#5C7CFF',
            border: 'none'
          }}
        />
      </div>
    </div>
  )
}

export default ChatPanel