import { useState, useEffect } from 'react'
import { Checkbox, Button, Popconfirm, Divider } from 'antd'
import { DeleteOutlined, PlusOutlined, ClockCircleOutlined, MessageOutlined } from '@ant-design/icons'
import { useTaskStore } from '@/store/task'
import { useChatStore } from '@/store/chat'
import { chatSessions } from '@/api/chat'

const statusMap = {
  pending: { text: '待执行', color: '#86909C', bg: '#F5F7FA' },
  running: { text: '执行中', color: '#5C7CFF', bg: '#F0F1FF' },
  completed: { text: '已完成', color: '#52C41A', bg: '#F6FFED' },
  failed: { text: '失败', color: '#FF4D4F', bg: '#FFF2F0' }
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp.endsWith('Z') ? timestamp : timestamp + 'Z')
  const now = new Date()
  const diff = now - date
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatFullTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp.endsWith('Z') ? timestamp : timestamp + 'Z')
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

function WorkflowSidebar() {
  const tasks = useTaskStore(s => s.tasks)
  const currentTask = useTaskStore(s => s.currentTask)
  const setCurrentNode = useTaskStore(s => s.setCurrentNode)
  const clearCurrentTask = useTaskStore(s => s.clearCurrentTask)
  const setSelectedWorkflow = useChatStore(s => s.setSelectedWorkflow)
  const deleteTask = useTaskStore(s => s.deleteTask)
  const deleteTasks = useTaskStore(s => s.deleteTasks)

  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const [isSelectMode, setIsSelectMode] = useState(false)
  const [sessions, setSessions] = useState([])
  const activeNodeExecutionId = useChatStore(s => s.activeNodeExecutionId)

  // 拉取当前用户在 AgentScope 端的 session 列表（侧边栏历史会话）
  useEffect(() => {
    let cancelled = false
    chatSessions()
      .then(d => { if (!cancelled) setSessions(d?.sessions || []) })
      .catch(() => { if (!cancelled) setSessions([]) })
    return () => { cancelled = true }
  }, [])

  const handleSelectSession = (sessionId) => {
    if (isSelectMode) return
    // sessionId === node_execution_id（同一 UUID），
    // 复用 setActiveNodeExecution 触发 useChatHistory 拉历史
    setSelectedWorkflow(null)
    useChatStore.getState().setActiveNodeExecution(sessionId)
  }

  const handleSelectTask = async (task) => {
    if (isSelectMode) return
    setSelectedWorkflow(null)
    // 切换实例前：清理前一个实例的执行态与轮询，
    // 避免 isExecuting=true 泄漏到新实例的 NodeContent 渲染（"执行中..." 误显示）。
    useTaskStore.getState().stopPolling()
    useTaskStore.setState({ isExecuting: false })

    const detail = await useTaskStore.getState().fetchTask(task.id)

    let targetNodeId = null
    if (task.status === 'running' && task.current_node_id) {
      // 执行中状态 — 不区分节点类型，统一走 pendingAutoStream：
      // - agent 节点：SSE 流接管（currentNodeId 已在 agent tab，SSE 自动 start）
      // - n8n 节点：polling 检测到完成会再设 pendingAutoStream（带下有 agent 时）
      // ★ 关键：避免任何 startPolling 误启 — 已被 streamingNodeIds 防御；
      //   即便走到 else 分支，streamingNodeIds.has 也会 no-op
      targetNodeId = task.current_node_id
      const current = useTaskStore.getState()
      // ★ 目标节点已在流式接收中 → 不重设 pendingAutoStream
      if (current.streamingNodeIds?.has(task.current_node_id)) {
        useTaskStore.getState().setCurrentNode(task.current_node_id)
        return
      }
      if (!current.pendingAutoStream || current.pendingAutoStream.taskId !== task.id) {
        useTaskStore.setState({
          pendingAutoStream: { taskId: task.id, nodeId: task.current_node_id },
        })
      }
    } else if (detail.nodes?.length > 0) {
      // 其他状态 → 跳转到第一个节点
      targetNodeId = detail.nodes[0].node_id
    }

    if (targetNodeId) {
      useTaskStore.getState().setCurrentNode(targetNodeId)
    }
  }

  const handleNewConversation = () => {
    clearCurrentTask()
    setSelectedWorkflow(null)
    setIsSelectMode(false)
    setSelectedRowKeys([])
  }

  const handleDelete = async (taskId, e) => {
    e.stopPropagation()
    await deleteTask(taskId)
    setSelectedRowKeys(prev => prev.filter(id => id !== taskId))
  }

  const handleBatchDelete = async () => {
    await deleteTasks(selectedRowKeys)
    setSelectedRowKeys([])
    setIsSelectMode(false)
  }

  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedRowKeys(tasks.map(t => t.id))
    } else {
      setSelectedRowKeys([])
    }
  }

  const rowSelection = {
    selectedRowKeys,
    onChange: setSelectedRowKeys
  }

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
        padding: '18px 20px',
        borderBottom: '1px solid #E5E6EB',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <span style={{
          fontSize: '15px',
          fontWeight: 600,
          color: '#1D2129'
        }}>
          工作流实例
        </span>
        {tasks.length > 0 && (
          <Button
            type="text"
            size="small"
            onClick={() => {
              setIsSelectMode(!isSelectMode)
              if (isSelectMode) {
                setSelectedRowKeys([])
              }
            }}
            style={{ color: isSelectMode ? '#5C7CFF' : '#86909C' }}
          >
            {isSelectMode ? '取消' : '选择'}
          </Button>
        )}
      </div>

      {/* Batch Actions */}
      {isSelectMode && selectedRowKeys.length > 0 && (
        <div style={{
          padding: '8px 12px',
          background: '#F0F1FF',
          borderBottom: '1px solid #E5E6EB',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <Checkbox
            onChange={(e) => handleSelectAll(e.target.checked)}
            checked={selectedRowKeys.length === tasks.length && tasks.length > 0}
            indeterminate={selectedRowKeys.length > 0 && selectedRowKeys.length < tasks.length}
          >
            <span style={{ fontSize: '12px', color: '#5C7CFF' }}>
              已选 {selectedRowKeys.length} 项
            </span>
          </Checkbox>
          <Button
            type="text"
            danger
            size="small"
            icon={<DeleteOutlined />}
            onClick={handleBatchDelete}
          >
            批量删除
          </Button>
        </div>
      )}

      {/* Task List */}
      <div style={{ flex: 1, overflow: 'auto', padding: '8px 12px' }}>
        {/* "新对话" 虚拟条目 */}
        <div
          onClick={handleNewConversation}
          style={{
            display: 'flex',
            gap: 12,
            padding: '12px',
            borderRadius: 10,
            marginBottom: 6,
            cursor: 'pointer',
            background: !currentTask ? '#F0F1FF' : 'transparent',
            border: !currentTask ? '1px solid #7B91FF' : '1px solid transparent',
            transition: 'all 0.15s ease'
          }}
        >
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 6,
            background: !currentTask ? '#E0E7FF' : 'linear-gradient(135deg, rgba(92, 124, 255, 0.15) 0%, rgba(123, 145, 255, 0.15) 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: !currentTask ? '#5C7CFF' : '#667eea',
            flexShrink: 0
          }}>
            <PlusOutlined />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 500, fontSize: '13px', color: !currentTask ? '#5C7CFF' : '#374151', marginBottom: 6 }}>
              新对话
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '11px' }}>
              <span style={{ color: '#8b5cf6', background: 'rgba(139, 92, 246, 0.1)', padding: '2px 8px', borderRadius: 10 }}>
                草稿
              </span>
              <span style={{ color: '#9ca3af' }}>未开始执行</span>
            </div>
          </div>
        </div>

        {/* 已存在的任务实例 */}
        {tasks.map((task) => {
          const status = statusMap[task.status] || statusMap.pending
          const isActive = currentTask?.id === task.id
          const isSelected = selectedRowKeys.includes(task.id)

          return (
            <div
              key={task.id}
              onClick={() => handleSelectTask(task)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '12px',
                borderRadius: 10,
                marginBottom: 6,
                cursor: 'pointer',
                background: isActive ? '#F0F1FF' : isSelected ? '#E0E7FF' : 'transparent',
                border: isActive ? '1px solid #7B91FF' : isSelected ? '1px solid #5C7CFF' : '1px solid transparent',
                transition: 'all 0.15s ease'
              }}
            >
              {isSelectMode && (
                <Checkbox
                  checked={isSelected}
                  onClick={(e) => e.stopPropagation()}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedRowKeys([...selectedRowKeys, task.id])
                    } else {
                      setSelectedRowKeys(selectedRowKeys.filter(id => id !== task.id))
                    }
                  }}
                />
              )}
              <div style={{
                width: 32,
                height: 32,
                borderRadius: 6,
                background: isActive ? '#E0E7FF' : '#f1f5f9',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: isActive ? '#5C7CFF' : '#64748b',
                flexShrink: 0
              }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2"/>
                  <path d="M9 12l2 2 4-4"/>
                </svg>
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500, fontSize: '13px', color: isActive ? '#5C7CFF' : '#374151', marginBottom: 8 }}>
                  {task.name || '未命名任务'}
                </div>

                {/* Node Progress Indicator */}
                {task.node_executions?.length > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 6 }}>
                    {task.node_executions.map((node, index) => (
                      <div key={node.node_id} style={{ display: 'flex', alignItems: 'center' }}>
                        <div style={{
                          width: 8,
                          height: 8,
                          borderRadius: '50%',
                          background: node.status === 'completed' ? '#52C41A' : node.status === 'running' ? '#8b5cf6' : '#d1d5db',
                          flexShrink: 0,
                          animation: node.status === 'running' ? 'pulse 1.5s ease-in-out infinite' : 'none',
                          boxShadow: node.status === 'running' ? '0 0 0 0 rgba(139, 92, 246, 0.4)' : 'none'
                        }} />
                        {index < task.node_executions.length - 1 && (
                          <div style={{
                            width: 16,
                            height: 2,
                            background: node.status === 'completed' ? '#52C41A' : '#d1d5db',
                            margin: '0 2px'
                          }} />
                        )}
                      </div>
                    ))}
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{
                    fontSize: '11px',
                    color: status.color,
                    background: status.bg,
                    padding: '2px 8px',
                    borderRadius: 10
                  }}>
                    {status.text}
                  </span>
                  {task.node_executions?.[0] && (
                    <span style={{ fontSize: '11px', color: '#9ca3af', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <ClockCircleOutlined style={{ fontSize: 10 }} />
                      {formatFullTime(task.node_executions[0].started_at)}
                      {task.node_executions[0].completed_at && (
                        <> → {formatFullTime(task.node_executions[0].completed_at)}</>
                      )}
                    </span>
                  )}
                </div>
              </div>
              {!isSelectMode && (
                <Popconfirm
                  title="确定删除此任务？"
                  onConfirm={(e) => handleDelete(task.id, e)}
                  onCancel={(e) => e.stopPropagation()}
                  okText="确定"
                  cancelText="取消"
                  placement="left"
                >
                  <Button
                    type="text"
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={(e) => e.stopPropagation()}
                    style={{ opacity: 0.6 }}
                  />
                </Popconfirm>
              )}
            </div>
          )
        })}

        {tasks.length === 0 && (
          <div style={{ textAlign: 'center', padding: '32px 16px', color: '#9ca3af', fontSize: '13px' }}>
            暂无任务实例
          </div>
        )}

        {/* 历史会话分组（来自 AgentScope） */}
        {sessions.length > 0 && (
          <>
            <Divider style={{ margin: '16px 0 8px', fontSize: '12px', color: '#9ca3af' }}>
              历史会话
            </Divider>
            {sessions.map(s => {
              const isActive = activeNodeExecutionId === s.sessionId
              return (
                <div
                  key={s.sessionId}
                  onClick={() => handleSelectSession(s.sessionId)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '10px 12px',
                    borderRadius: 8,
                    marginBottom: 4,
                    cursor: 'pointer',
                    background: isActive ? '#F0F1FF' : 'transparent',
                    border: isActive ? '1px solid #7B91FF' : '1px solid transparent',
                  }}
                >
                  <MessageOutlined style={{ color: isActive ? '#5C7CFF' : '#94a3b8', fontSize: 14 }} />
                  <span style={{
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    color: isActive ? '#5C7CFF' : '#374151',
                    flex: 1,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }} title={s.sessionId}>
                    {s.sessionId.slice(0, 8)}…{s.sessionId.slice(-4)}
                  </span>
                  {s.exists
                    ? <span style={{ fontSize: '10px', color: '#52C41A' }}>✓</span>
                    : <span style={{ fontSize: '10px', color: '#9ca3af' }}>○</span>}
                </div>
              )
            })}
          </>
        )}
      </div>
      <style>{`
        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.4); }
          70% { box-shadow: 0 0 0 6px rgba(139, 92, 246, 0); }
          100% { box-shadow: 0 0 0 0 rgba(139, 92, 246, 0); }
        }
      `}</style>
    </div>
  )
}

export default WorkflowSidebar