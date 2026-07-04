import { useState, useEffect, useRef, useCallback } from 'react'
import { Button, Popconfirm, Divider, App, Spin } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { useWorkflowStore } from '@/store/workflow'
import { useTaskStore } from '@/store/task'
import { useChatStore } from '@/store/chat'
import { fileApi } from '@/api/file'
import AmISForm from './AmISForm'

function IntentFormPreview() {
  const [formData, setFormData] = useState({})
  // 重置时用 key 强制 AmISForm remount（amis 内部表单 state 不会响应外部 updateProps(data: {})）
  const [formKey, setFormKey] = useState(0)
  const currentIntentSchema = useWorkflowStore(s => s.currentIntentSchema)
  const currentWorkflow = useChatStore(s => s.selectedWorkflow)
  const setSelectedWorkflow = useChatStore(s => s.setSelectedWorkflow)
  const createTask = useTaskStore(s => s.createTask)
  const executeNode = useTaskStore(s => s.executeNode)
  const fetchIntentSchema = useWorkflowStore(s => s.fetchIntentSchema)
  // App.useApp() 拿 message 实例，做 toast 通知（不再往 chat 区塞消息）
  const { message: toast } = App.useApp()

  // 跟踪本会话（一次 IntentFormPreview 挂载）内所有已上传的文件 file_id。
  // 重置 / 返回时统一 DELETE，避免脏文件残留后端。
  // 用 ref 而不是 state：跟踪是副作用，不参与渲染。
  // 注意：执行工作流后 formData 被清空、组件卸载，ref 自然随组件 GC，不需要手动清。
  const trackedFileIdsRef = useRef(new Set())
  // 防止「同一 file_id 被并发清理两次」（重置 + 卸载时的 React 18 strict-mode 副作用）
  const cleanedUpRef = useRef(false)

  // 深度遍历 formData，提取所有 file_id（input-file 字段值结构：{value, file_id, name, ...}）。
  // 处理嵌套对象 + 数组（multiple: true 时是数组）。
  const extractFileIds = (value, found = []) => {
    if (value == null || typeof value !== 'object') return found
    if (Array.isArray(value)) {
      value.forEach(v => extractFileIds(v, found))
      return found
    }
    if (typeof value.file_id === 'string' && value.file_id) {
      found.push(value.file_id)
    }
    Object.values(value).forEach(v => extractFileIds(v, found))
    return found
  }

  // 监听 formData 变化，把新出现的 file_id 加入跟踪集
  useEffect(() => {
    extractFileIds(formData).forEach(id => trackedFileIdsRef.current.add(id))
  }, [formData])

  // 清空本会话内所有跟踪文件（fire-and-forget：失败不阻塞 UI 流转）
  // 用 Promise.allSettled：单个失败不影响其他文件清理
  const cleanupUploadedFiles = useCallback(async () => {
    if (cleanedUpRef.current) return
    cleanedUpRef.current = true
    const ids = Array.from(trackedFileIdsRef.current)
    trackedFileIdsRef.current = new Set()
    if (ids.length === 0) return
    console.log('[IntentFormPreview] 清理未提交文件:', ids)
    const results = await Promise.allSettled(
      ids.map(id => fileApi.delete(id).catch(e => {
        // 404 视为幂等成功（用户可能手动点过 ×）
        if (e?.response?.status === 404) return { status: 0 }
        throw e
      }))
    )
    const failed = results.filter(r => r.status === 'rejected')
    if (failed.length > 0) {
      console.warn('[IntentFormPreview] 部分文件清理失败:', failed)
    }
  }, [])

  // 当工作流变化时，获取对应的意图schema；同时 remount 表单以匹配新 schema
  useEffect(() => {
    if (currentWorkflow?.id) {
      fetchIntentSchema(currentWorkflow.id)
      setFormKey(k => k + 1)
      setFormData({})
      // 切换工作流：清空上一会话的文件跟踪（如果上一会话没主动清理过）
      trackedFileIdsRef.current = new Set()
      cleanedUpRef.current = false
    }
  }, [currentWorkflow])

  const handleReset = async () => {
    await cleanupUploadedFiles()
    setFormData({})
    setFormKey(k => k + 1)
  }

  // 「脏表单」判断：空字符串/null/undefined/空数组视为未填，其余视为已填
  const isFormDirty = Object.values(formData).some(v => {
    if (v === null || v === undefined || v === '') return false
    if (Array.isArray(v) && v.length === 0) return false
    return true
  })

  // 三态语义，区分"加载中"和"已加载但空"：
  //  - currentIntentSchema === null   → useEffect 还没跑完（loading）
  //  - {} 或 {body: []}             → 后端确认无 schema（占位"无需填写"）
  //  - {body: [...]}                → 有 schema，渲染 AmISForm
  //
  // 旧实现把 null 错误地归类成"无 schema"，导致首次进入时闪现"此工作流不需要填写意图表单"
  // 的占位文案，然后 fetchIntentSchema 完成才显示真表单。修：拆 isSchemaLoading。
  const isSchemaLoading = currentIntentSchema == null
  const isEmptySchema = !isSchemaLoading
    && (!currentIntentSchema.body || currentIntentSchema.body.length === 0)

  // 返回工作流选择：清空 selectedWorkflow 即可，AIAssistant 路由会自动切回 WorkflowPromptsView
  // formData 是组件本地 state，卸载后自动 GC；currentIntentSchema 会在下次选择工作流时被覆盖
  const handleBack = async () => {
    await cleanupUploadedFiles()
    setSelectedWorkflow(null)
  }

  const handleExecute = async () => {
    if (!currentWorkflow) return

    try {
      const task = await createTask(currentWorkflow.id, currentWorkflow.title)

      if (task.node_executions?.length > 0) {
        const firstNode = task.node_executions.find(n => n.node_type !== 'agent')
        if (firstNode) {
          await executeNode(firstNode.node_id, formData, task.id)
        }
      }

      // 执行成功 → 已上传的文件「提交」给 task 持有，标记为已清理，
      // 防止后续 reset/back 误删（handleExecute 后 setFormData({}) 会让文件失联，但 ref 还在）
      trackedFileIdsRef.current = new Set()
      cleanedUpRef.current = true

      // 执行完成后清空所有界面缓存
      setFormData({})
      setSelectedWorkflow(null)
      // 注：不再调 useChatStore.clearMessages() —— messages 改由 useXChat 管理，
      // 跳转到 ChatContent 时 conversationKey 切到新 node，旧 messages 自然失联
    } catch (e) {
      toast.error(`执行失败: ${e.message}`)
    }
  }

  return (
    // 外层撑满 tabpane；内层卡片用 flex 列布局，让表单区独立滚动、按钮行始终可见
    // （修复：卡片原本 overflow:hidden 且无 flex 链，长表单会把按钮挤出可视区）
    <div style={{ padding: 20, height: '100%', boxSizing: 'border-box' }}>
      <div style={{
        background: '#fff',
        borderRadius: 12,
        boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        height: '100%',
      }}>
        <div style={{
          padding: '16px 20px',
          background: 'linear-gradient(135deg, rgba(102,126,234,0.04) 0%, rgba(118,75,162,0.04) 100%)',
          borderBottom: '1px solid rgba(0,0,0,0.04)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {isFormDirty ? (
              <Popconfirm
                title="已填写的内容将丢失"
                description="确定要返回选择工作流吗？"
                onConfirm={handleBack}
                okText="确定返回"
                cancelText="继续填写"
              >
                <Button
                  type="text"
                  icon={<ArrowLeftOutlined />}
                  style={{ padding: '0 8px', color: '#475569', fontWeight: 500 }}
                >
                  返回
                </Button>
              </Popconfirm>
            ) : (
              <Button
                type="text"
                icon={<ArrowLeftOutlined />}
                onClick={handleBack}
                style={{ padding: '0 8px', color: '#475569', fontWeight: 500 }}
              >
                返回
              </Button>
            )}
            <Divider type="vertical" style={{ margin: 0, height: 18 }} />
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
        <div style={{ padding: 20, flex: 1, overflow: 'auto', minHeight: 0 }}>
          {isSchemaLoading ? (
            // 首次进入 / 切换工作流：schema 还在拉，避免把"未加载"误判成"无 schema"
            <div style={{
              padding: '40px 20px',
              textAlign: 'center',
              color: '#86909C',
              fontSize: '14px',
            }}>
              <Spin />
              <div style={{ marginTop: 12 }}>正在加载意图表单...</div>
            </div>
          ) : isEmptySchema ? (
            // 空 schema 友好占位：执行链路对 formData={} 友好（createTask + executeNode 均支持）
            <div style={{
              padding: '40px 20px',
              textAlign: 'center',
              color: '#86909C',
              fontSize: '14px',
            }}>
              <div style={{
                width: 48, height: 48, margin: '0 auto 16px',
                borderRadius: '50%',
                background: 'rgba(82, 196, 26, 0.1)',
                color: '#52C41A',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 24, fontWeight: 600,
              }}>
                ✓
              </div>
              <div style={{ fontWeight: 500, color: '#1D2129', marginBottom: 8, fontSize: 15 }}>
                此工作流不需要填写意图表单
              </div>
              <div>直接点击下方"执行工作流"按钮开始</div>
            </div>
          ) : (
            <AmISForm
              key={formKey}
              schema={currentIntentSchema}
              value={formData}
              onChange={setFormData}
            />
          )}
        </div>
        <div style={{
          padding: '16px 20px',
          background: '#fafafa',
          borderTop: '1px solid rgba(0,0,0,0.04)',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: 12,
          flexShrink: 0,
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