import { useState, useEffect, useMemo, useRef } from 'react'
import { Button, Alert, Tag } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { useTaskStore } from '@/store/task'
import AmISForm from './AmISForm'
import { useAgentStream } from './hooks/useAgentStream'

function NodeContent() {
  const currentTask = useTaskStore(s => s.currentTask)
  const currentNodeId = useTaskStore(s => s.currentNodeId)
  const isExecuting = useTaskStore(s => s.isExecuting)
  const executeNode = useTaskStore(s => s.executeNode)
  const mockCompleteNode = useTaskStore(s => s.mockCompleteNode)
  const triggerPostAction = useTaskStore(s => s.triggerPostAction)
  const mockerMode = useTaskStore(s => s.mockerMode)
  const fetchAppConfig = useTaskStore(s => s.fetchAppConfig)
  const pendingAutoStream = useTaskStore(s => s.pendingAutoStream)
  const clearAutoStream = useTaskStore(s => s.clearAutoStream)

  const {
    start: startStream,
    cancel,
    isStreaming,
    error: streamError,
  } = useAgentStream()

  const [intentData, setIntentData] = useState({})
  const [artifactData, setArtifactData] = useState({})

  const currentNode = useMemo(() => {
    return currentTask?.node_executions?.find(n => n.node_id === currentNodeId)
  }, [currentTask?.node_executions, currentNodeId])

  useEffect(() => {
    setIntentData(currentNode?.intent_data || {})
  }, [currentNode?.intent_data, currentNodeId])

  useEffect(() => {
    setArtifactData(currentNode?.artifact_data || {})
  }, [currentNode?.artifact_data, currentNodeId])

  useEffect(() => {
    fetchAppConfig()
  }, [fetchAppConfig])

  // ★ 自动触发去重锁：pendingAutoStream 竞态可能导致 effect 重复执行，
  //   用 ref 记录已自动启动的节点，防止同一个节点二次触发 startStream
  const launchLockRef = useRef(null)

  // ★ 自动触发流式：n8n 完成后 polling 设了 pendingAutoStream，
  //   本组件 mount（或 currentNodeId / currentNode.status 变化）时检测：
  //   - pendingAutoStream.taskId 匹配当前 task
  //   - pendingAutoStream.nodeId 匹配当前节点
  //   - 当前节点是 agent + status=pending 或 running（包括 WorkflowSidebar 对 running agent
  //     自动设 pendingAutoStream 的场景）
  //   → 自动 startStream，无需用户点按钮
  //   → 触发后 clearAutoStream 清空信号（避免重复触发 + 让其他节点不响应）
  //   → launchLockRef 防止信号清空后被 WorkflowSidebar 重新设置导致二次启动
  useEffect(() => {
    const lockKey = `${currentTask?.id}:${currentNodeId}`
    // 流结束后自动解锁，允许重新分析
    if (!isStreaming && launchLockRef.current === lockKey) {
      launchLockRef.current = null
    }
    if (
      pendingAutoStream
      && pendingAutoStream.taskId === currentTask?.id
      && pendingAutoStream.nodeId === currentNodeId
      && currentNode?.node_type === 'agent'
      && (currentNode?.status === 'pending' || currentNode?.status === 'running')
      && !isStreaming
      && launchLockRef.current !== lockKey   // ★ 去重：已启动的节点不再重复触发
    ) {
      launchLockRef.current = lockKey
      startStream(currentTask.id, currentNodeId)
      clearAutoStream()
    }
    // isStreaming 是 useAgentStream 内部 state，作为依赖项会在 stream 启动后让 effect 重跑一次（防止重复 trigger）
  }, [pendingAutoStream, currentTask?.id, currentNodeId, currentNode?.node_type, currentNode?.status, isStreaming, startStream, clearAutoStream])

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
  // 节点类型判定：post-action（agent）节点走"开始分析"流式分支，否则走普通意图表单
  // 必须在 isLiveStreaming 之前声明（TDZ：const 声明前不能访问）
  const isPostAction = currentNode?.node_type === 'agent'

  // ★ 流式渲染中：仅对 post-action 节点启用，覆盖 isNodeRunning 的 spinner 逻辑
  const isLiveStreaming = isPostAction && isStreaming

  // n8n 节点：从 store 读 artifact_data + artifact_schema
  const hasArtifactData = currentNode?.artifact_data && Object.keys(currentNode.artifact_data).length > 0
  const hasArtifactSchema = !!currentNode?.artifact_schema && Object.keys(currentNode.artifact_schema).length > 0
  const hasN8nArtifact = hasArtifactData || hasArtifactSchema
  const effectiveSchema = hasArtifactSchema ? currentNode.artifact_schema : null

  const handleExecute = async () => {
    await executeNode(currentNodeId, intentData)
  }

  const handleMockComplete = async () => {
    await mockCompleteNode(currentNodeId)
  }

  const handleTriggerPostAction = async () => {
    await triggerPostAction(currentNodeId)
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
      height: '100%',
      boxSizing: 'border-box',
      overflow: 'auto',
      background: '#F5F7FA'
    }}>
      {/* Post-Action Action Card - post_action 节点专属：跳过 Intent、直接展示触发面板 */}
      {isPostAction && (
        <div style={{
          background: '#FFFFFF',
          borderRadius: 12,
          border: '1px solid #E5E6EB',
          marginBottom: 20,
          padding: '20px 24px',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 12,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontWeight: 600, fontSize: '14px', color: '#1D2129' }}>
                AgentScope 调用
              </span>
              <span style={{
                fontSize: 11,
                color: '#5C7CFF',
                background: '#F0F1FF',
                padding: '2px 8px',
                borderRadius: 4,
              }}>
                post-action
              </span>
              <span style={{
                fontSize: 12,
                color: status.color,
                background: status.bg,
                padding: '4px 12px',
                borderRadius: 20,
              }}>
                {status.text}
              </span>
            </div>
            {(isPending || isFailed) && (
              <Button
                type="primary"
                icon={<ReloadOutlined />}
                onClick={() => startStream(currentTask.id, currentNodeId)}
                disabled={isStreaming || isExecuting}
                style={{ borderRadius: 8, background: '#5C7CFF', border: 'none' }}
              >
                {isStreaming ? '分析中...' : (isFailed ? '重新分析（流式）' : '开始分析（流式）')}
              </Button>
            )}
            {isStreaming && (
              <Button onClick={cancel} style={{ borderRadius: 8 }}>
                取消
              </Button>
            )}
          </div>
          <div style={{ fontSize: 12, color: '#86909C' }}>
            本节点由其父 n8n 节点完成后自动派发，调用 AgentScope HTTP 端点，
            请求体注入父节点 artifact_data，结果落库。
            点击「开始分析（流式）」可实时查看 6 阶段进度（start / stage / midcat / artifact / final）。
            失败可点击「重新分析（流式）」重试。
          </div>
          {isFailed && currentNode?.error_message && (
            <Alert
              type="error"
              showIcon
              style={{ marginTop: 12 }}
              message="调用失败"
              description={currentNode.error_message}
            />
          )}
          {streamError && (
            <Alert
              type="warning"
              showIcon
              style={{ marginTop: 12 }}
              message="流式异常"
              description={streamError}
              closable
              onClose={() => { /* 保留 error 直到下次 start */ }}
            />
          )}
        </div>
      )}

      {/* Intent Section - 卡片内部用 flex 列：表单区独立滚动、按钮行黏在底部 */}
      {!isPostAction && (
        <div style={{
        background: '#FFFFFF',
        borderRadius: 12,
        border: '1px solid #E5E6EB',
        marginBottom: 20,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '16px 20px',
          background: '#FAFAFA',
          borderBottom: '1px solid #E5E6EB',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexShrink: 0,
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
        <div style={{ padding: 20, flex: 1, overflow: 'auto', minHeight: 0 }}>
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
            gap: 12,
            flexShrink: 0,
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
      )}

      {/* Artifact Section */}
      {(isLiveStreaming || hasN8nArtifact) && (
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
            border: '1px solid #E5E6EB'
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

            {/* Live Streaming - 流式过程：实时渲染 store.artifact_schema（被 intermediate 事件逐步更新）
                流结束后由 hasN8nArtifact 路径渲染存储的 artifact（同一 AmISForm，只是 artifact_data 落库） */}
            {isPostAction && effectiveSchema && isLiveStreaming && (
              <div style={{ padding: 20 }}>
                <AmISForm
                  key={currentNodeId}
                  schema={effectiveSchema}
                  readonly
                />
                <div style={{
                  marginTop: 12, fontSize: 12, color: '#86909C',
                  display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  <SpinnerIcon />
                  正在从 AgentScope 流式接收报告...
                </div>
              </div>
            )}

            {/* agent 节点：等首条 intermediate 时的 spinner（artifact_schema 还没数据） */}
            {isPostAction && !effectiveSchema && isLiveStreaming && (
              <div style={{ padding: 20, fontSize: 12, color: '#86909C', display: 'flex', gap: 6 }}>
                <SpinnerIcon />
                正在从 AgentScope 流式接收报告...
              </div>
            )}

            {/* Loading State - 显示在生成物区域内部（流式时跳过，避免与流式区重叠） */}
            {!isLiveStreaming && isNodeRunning && (
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
            {/* 节点生成物（n8n 已完成 或 agent 流结束）：从 store 读 artifact_data + artifact_schema 渲染 */}
            {!isLiveStreaming && !isNodeRunning && hasN8nArtifact && (
              <div style={{ padding: 20 }}>
                {effectiveSchema ? (
                  <AmISForm schema={effectiveSchema} value={artifactData} readonly />
                ) : (
                  <AmISForm schema={artifactData} readonly />
                )}
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
        /* amis cxd-Tabs 主题：抹外框、内容区内边距、与外层卡片融合。
           注：.artifact-tabs 自身不再设 padding:0，间距交给外层 <div style={{padding:20}}> */
        .artifact-tabs {
          border: none !important;
          box-shadow: none !important;
          background: transparent !important;
        }
        /* tab 头链接区：去掉下划线、留 12px 间距 */
        .artifact-tabs .cxd-Tabs-links {
          border-bottom: none !important;
          margin: 0 0 12px 0 !important;
        }
        /* 内容区：去内边距（cxd-Tabs-content 是 amis 渲染的容器） */
        .artifact-tabs-content,
        .artifact-tabs .cxd-Tabs-content {
          padding: 0 !important;
        }
        /* 单个 Tab pane：去内边距 */
        .artifact-tabs .cxd-Tabs-pane {
          padding: 0 !important;
        }
        /* amis table-view：统一边框样式（解决"双重边框"问题） */
        .artifact-tabs .cxd-TableView {
          border-collapse: collapse !important;
          border: 1px solid #E5E6EB !important;
          width: 100% !important;
        }
        /* 覆盖 amis cxd-Wrapper--md 内层 padding 16px（解决表格与 Tabs 容器间隙，"两个框"核心问题） */
        .artifact-tabs .cxd-Wrapper--md {
          padding: 0 !important;
        }
        /* markdown 与前一个 body 元素（表格/wrapper）之间留间距，避免视觉积压 */
        .artifact-tabs .cxd-Markdown {
          margin-top: 16px;
        }
        /* 隐藏 page 自带的 title 标题（tab 标题栏已显示，避免重复） */
        .artifact-tabs .cxd-Page-title {
          display: none;
        }
      `}</style>
    </div>
  )
}

export default NodeContent