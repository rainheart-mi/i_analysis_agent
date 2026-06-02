import { useState, useEffect, useMemo } from 'react'
import { Button } from 'antd'
import { useTaskStore } from '@/store/task'
import AmISForm from './AmISForm'

function NodeContent() {
  const currentTask = useTaskStore(s => s.currentTask)
  const currentNodeId = useTaskStore(s => s.currentNodeId)
  const isExecuting = useTaskStore(s => s.isExecuting)
  const executeNode = useTaskStore(s => s.executeNode)
  const mockCompleteNode = useTaskStore(s => s.mockCompleteNode)
  const mockerMode = useTaskStore(s => s.mockerMode)
  const fetchAppConfig = useTaskStore(s => s.fetchAppConfig)

  const [intentData, setIntentData] = useState({})
  const [artifactData, setArtifactData] = useState({})

  const currentNode = useMemo(() => {
    return currentTask?.node_executions?.find(n => n.node_id === currentNodeId)
  }, [currentTask?.node_executions, currentNodeId])

  useEffect(() => {
    if (currentNode?.intent_data) {
      setIntentData(currentNode.intent_data)
    }
  }, [currentNode?.intent_data])

  useEffect(() => {
    if (currentNode?.artifact_data) {
      setArtifactData(currentNode.artifact_data)
    }
  }, [currentNode?.artifact_data])

  useEffect(() => {
    fetchAppConfig()
  }, [fetchAppConfig])

  const statusMap = {
    pending: { text: '待执行', color: '#86909C', bg: '#F5F7FA' },
    running: { text: '执行中', color: '#FF8C00', bg: '#FFF4E6' },
    completed: { text: '已完成', color: '#52C41A', bg: '#F6FFED' },
    failed: { text: '失败', color: '#FF4D4F', bg: '#FFF2F0' }
  }

  const isRunning = currentNode?.status === 'running'
  const isPending = currentNode?.status === 'pending'
  const isCompleted = currentNode?.status === 'completed'
  const isFailed = currentNode?.status === 'failed'
  const isNodeRunning = isRunning || isExecuting
  const isExecuted = isCompleted || isFailed

  console.log('[NodeContent] Node state:', {
    status: currentNode?.status,
    isRunning,
    isNodeRunning,
    isExecuting,
    isExecuted
  })
  const hasArtifact = currentNode?.artifact_data && Object.keys(currentNode.artifact_data).length > 0
  const hasArtifactSchema = !!currentNode?.artifact_schema

  const handleExecute = async () => {
    await executeNode(currentNodeId, intentData)
  }

  const handleMockComplete = async () => {
    await mockCompleteNode(currentNodeId)
  }

  const status = statusMap[currentNode?.status] || statusMap.pending

  // 执行中状态的旋转动画 SVG
  const SpinnerIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ animation: 'spin 1s linear infinite' }}>
      <path d="M21 12a9 9 0 11-6.219-8.56" />
    </svg>
  )

  return (
    <div style={{
      padding: 20,
      overflow: 'auto',
      flex: 1,
      background: '#F5F7FA'
    }}>
      {/* Intent Section */}
      <div style={{
        background: '#FFFFFF',
        borderRadius: 12,
        border: '1px solid #E5E6EB',
        marginBottom: 20,
        overflow: 'hidden'
      }}>
        <div style={{
          padding: '16px 20px',
          background: '#FAFAFA',
          borderBottom: '1px solid #E5E6EB',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontWeight: 600, fontSize: '14px', color: '#1D2129' }}>意图澄清</span>
            <span style={{
              fontSize: '11px',
              color: '#5C7CFF',
              background: '#F0F1FF',
              padding: '2px 8px',
              borderRadius: 4
            }}>
              输入
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {(isExecuting || isRunning) && (
              <span style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontSize: '12px',
                color: '#FF8C00',
                fontWeight: 500
              }}>
                <SpinnerIcon />
                执行中...
              </span>
            )}
            <span style={{
              fontSize: '12px',
              color: status.color,
              background: status.bg,
              padding: '4px 12px',
              borderRadius: 20
            }}>
              {status.text}
            </span>
          </div>
        </div>
        <div style={{ padding: 20 }}>
          <AmISForm
            schema={currentNode?.intent_schema}
            value={intentData}
            onChange={setIntentData}
            readonly={isExecuted}
          />
        </div>
        {!isExecuted && !isExecuting && (
          <div style={{
            padding: '16px 20px',
            background: '#FAFAFA',
            borderTop: '1px solid #E5E6EB',
            display: 'flex',
            justifyContent: 'flex-end',
            gap: 12
          }}>
            <Button style={{ borderRadius: 8 }}>重置</Button>
            <Button
              type="primary"
              onClick={handleExecute}
              style={{
                borderRadius: 8,
                background: '#5C7CFF',
                border: 'none'
              }}
            >
              执行工作流
            </Button>
          </div>
        )}
        {(isExecuting || isRunning) && mockerMode === 'mocker' && (
          <div style={{
            padding: '16px 20px',
            background: '#FAFAFA',
            borderTop: '1px solid #E5E6EB',
            display: 'flex',
            justifyContent: 'flex-end'
          }}>
            <Button
              type="primary"
              onClick={handleMockComplete}
              style={{ borderRadius: 8, background: '#5C7CFF', border: 'none' }}
            >
              Mock 完成
            </Button>
          </div>
        )}
      </div>

      {/* Artifact Section */}
      {(hasArtifactSchema || hasArtifact) && (
        <>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            marginBottom: 16
          }}>
            <div style={{ flex: 1, height: 1, background: '#E5E6EB' }} />
            <span style={{
              padding: '6px 14px',
              background: '#F0F1FF',
              borderRadius: 20,
              fontSize: '12px',
              fontWeight: 600,
              color: '#5C7CFF'
            }}>
              数据输出
            </span>
            <div style={{ flex: 1, height: 1, background: '#E5E6EB' }} />
          </div>
          <div style={{
            background: '#FFFFFF',
            borderRadius: 12,
            border: '1px solid #E5E6EB',
            overflow: 'hidden'
          }}>
            <div style={{
              padding: '16px 20px',
              background: '#FAFAFA',
              borderBottom: '1px solid #E5E6EB',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span style={{ fontWeight: 600, fontSize: '14px', color: '#1D2129' }}>生成物展示</span>
              <span style={{
                fontSize: '11px',
                color: '#52C41A',
                background: '#F6FFED',
                padding: '2px 8px',
                borderRadius: 4
              }}>
                输出
              </span>
            </div>

            {/* Loading State - 显示在生成物区域内部 */}
            {isNodeRunning && (
              <div style={{
                padding: 60,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                {/* Animated arc icon */}
                <div style={{
                  width: 48,
                  height: 48,
                  borderRadius: '50%',
                  border: '3px solid #F0F1FF',
                  borderTopColor: '#667eea',
                  animation: 'spin 1s linear infinite',
                  marginBottom: 20,
                  position: 'relative'
                }}>
                  <div style={{
                    position: 'absolute',
                    inset: 4,
                    borderRadius: '50%',
                    border: '3px solid #F0F1FF',
                    borderTopColor: '#764ba2',
                    animation: 'spin 0.8s linear infinite reverse'
                  }} />
                </div>

                <p style={{
                  fontSize: '14px',
                  color: '#1D2129',
                  fontWeight: 500,
                  marginBottom: 8,
                  margin: 0
                }}>
                  节点数据查询中，请稍候...
                </p>

                {/* Progress bar */}
                <div style={{
                  width: 240,
                  height: 4,
                  background: '#F0F1FF',
                  borderRadius: 2,
                  overflow: 'hidden',
                  marginBottom: 12
                }}>
                  <div style={{
                    height: '100%',
                    width: '60%',
                    background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
                    borderRadius: 2,
                    animation: 'progress 2s ease-in-out infinite'
                  }} />
                </div>

                <p style={{
                  fontSize: '12px',
                  color: '#86909C',
                  margin: 0
                }}>
                  正在从数据源获取数据...
                </p>
              </div>
            )}

            {/* Artifact Form */}
            {!isNodeRunning && hasArtifact && artifactData && Object.keys(artifactData).length > 0 && (
              <div style={{ padding: 20 }}>
                <AmISForm
                  schema={currentNode?.artifact_schema}
                  value={artifactData}
                  readonly
                />
              </div>
            )}

            {/* Empty state when no artifact */}
            {!isNodeRunning && !hasArtifact && hasArtifactSchema && (
              <div style={{
                padding: 40,
                textAlign: 'center',
                color: '#86909C',
                fontSize: '13px'
              }}>
                暂无生成物数据
              </div>
            )}
          </div>
        </>
      )}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes progress {
          0% { width: 0%; opacity: 0.5; }
          50% { width: 100%; opacity: 1; }
          100% { width: 0%; opacity: 0.5; }
        }
      `}</style>
    </div>
  )
}

export default NodeContent