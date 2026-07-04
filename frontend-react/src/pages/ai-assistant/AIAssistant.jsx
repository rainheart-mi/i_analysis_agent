import { useEffect, useState, useMemo, useRef } from 'react'
import { Tabs } from 'antd'
import { createStyles } from 'antd-style'
import { useWorkflowStore } from '@/store/workflow'
import { useTaskStore } from '@/store/task'
import { useChatStore } from '@/store/chat'
import WorkflowSidebar from './WorkflowSidebar'
import NodeContent from './NodeContent'
import IntentFormPreview from './IntentFormPreview'
import ChatContent from './ChatContent'
import WorkflowPromptsView from './components/WorkflowPromptsView'
import WaitingView from './components/WaitingView'

const CHAT_TAB_KEY = '__chat__'

/**
 * 修复 antd Tabs 内部高度链：
 * - 让 .ant-tabs 自身成为 flex column，激活 .rc-tabs-content-holder 的 flex:auto
 * - 把 height 一路传到 .ant-tabs-tabpane，使子组件（ChatContent/NodeContent）
 *   的 `height: 100%` 能解析，消息区 `flex:1, overflow:auto` 才能约束滚动
 */
const useStyle = createStyles(() => ({
  tabsBox: {
    height: '100%',
    '& .ant-tabs': {
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
    },
    '& .ant-tabs-nav': { flexShrink: 0 },
    '& .ant-tabs-content-holder': { flex: '1 1 0', minHeight: 0 },
    '& .ant-tabs-content': { height: '100%' },
    '& .ant-tabs-tabpane': { height: '100%' },
    '& .ant-tabs-tabpane-active': { height: '100%' },
  },
}))

/**
 * AIAssistant 主框架。
 *
 * 重构后布局：
 * - 左：WorkflowSidebar（任务列表 + 历史会话入口 + 工作流操作）
 * - 中：统一 Tabs 容器
 *   - "✨ AI 智能体"（常驻）— 子视图按 currentTask/selectedWorkflow 路由
 *   - 节点 tabs（currentTask 创建后自动出现）
 *
 * 中央子视图路由（AI 智能体 tab 内）：
 *   - 无 currentTask + 无 selectedWorkflow → <WorkflowPromptsView />（Prompts 卡片集）
 *   - 有 selectedWorkflow + 无 currentTask   → <IntentFormPreview />（填表 → 执行）
 *   - currentTask.status === 'completed'     → <ChatContent />（已是最大化）
 *   - currentTask.status 为 running/failed   → <WaitingView />（提示去节点 tab）
 */
function AIAssistant() {
  const { styles } = useStyle()
  const fetchWorkflows = useWorkflowStore(s => s.fetchWorkflows)
  const fetchTasks = useTaskStore(s => s.fetchTasks)
  const currentTask = useTaskStore(s => s.currentTask)
  const currentNodeId = useTaskStore(s => s.currentNodeId)
  const pendingAutoStream = useTaskStore(s => s.pendingAutoStream)
  const selectedWorkflow = useChatStore(s => s.selectedWorkflow)
  const setSelectedWorkflow = useChatStore(s => s.setSelectedWorkflow)
  const clearCurrentTask = useTaskStore(s => s.clearCurrentTask)

  const [centerTab, setCenterTab] = useState(CHAT_TAB_KEY)

  useEffect(() => {
    fetchWorkflows()
    fetchTasks()
  }, [fetchWorkflows, fetchTasks])

  // 工作流开始执行后自动切到第一个节点 tab（仅在任务首次变为 running 时触发一次）
  const taskStatusRef = useRef(null)
  useEffect(() => {
    if (currentTask?.node_executions?.length > 0) {
      const firstNodeId = currentTask.node_executions[0].node_id
      setCenterTab((prev) => prev === CHAT_TAB_KEY ? firstNodeId : prev)
      // 仅在任务从非 running 变为 running 时同步 currentNodeId，避免轮询刷新 node_executions
      // 时把用户手动切到的 agent tab 强制弹回第一个 n8n 节点。
      // ★ 不覆盖由 pendingAutoStream 设置的 currentNodeId（WorkflowSidebar 已正确指向 agent）
      if (currentTask.status === 'running' && taskStatusRef.current !== 'running'
        && !useTaskStore.getState().pendingAutoStream) {
        useTaskStore.getState().setCurrentNode(firstNodeId)
      }
      taskStatusRef.current = currentTask.status
    }
  }, [currentTask?.id, currentTask?.status, currentTask?.node_executions])

  // ★ 同步层：centerTab 跟随 currentNodeId 变化
  //   历史问题：centerTab（视觉状态）和 currentNodeId（NodeContent 查找键）原本只
  //   在 onChange handler 里同步；其它路径（fetchTask / 重试后重 fetch 等）改
  //   currentNodeId 时中心 tab 不更新 → 视觉高亮的是 A 节点，底下渲染的是 B 节点，
  //   agent badge 与内容（n8n 意图表单 / 等待视图）不一致。
  //   规则：
  //   1) 用户主动选 AI 智能体 tab（centerTab === CHAT_TAB_KEY）→ 不强制拉回
  //   2) currentNodeId 改变后，新 id 在当前 task 的 node_executions 中存在 → 跟随
  //   3) 不存在（任务切换/过期 id）→ 不更新（依赖 taskStatusRef 那条路径另行处理）
  useEffect(() => {
    if (!currentNodeId) return
    if (centerTab === CHAT_TAB_KEY) return
    if (centerTab === currentNodeId) return
    const exists = currentTask?.node_executions?.some(n => n.node_id === currentNodeId)
    if (exists) setCenterTab(currentNodeId)
  }, [currentNodeId, centerTab, currentTask?.node_executions])

  // ★ n8n 完成后自动切到下游 agent tab
  //   polling 检测到 n8n completed + 下游 agent pending → store 设 pendingAutoStream
  //   此 effect 监听信号 → 切到对应 tab（同时 setCurrentNode 让 NodeContent 拿得到 currentNode）
  //   NodeContent mount 后检查 pendingAutoStream 匹配则自动 startStream，无需用户点按钮
  useEffect(() => {
    if (pendingAutoStream && pendingAutoStream.taskId === currentTask?.id) {
      setCenterTab(pendingAutoStream.nodeId)
      useTaskStore.getState().setCurrentNode(pendingAutoStream.nodeId)
    }
  }, [pendingAutoStream, currentTask?.id])

  // 任务完成态：优先看 task 顶层 status；如未更新但所有 node_executions 都已 completed，
  // 也视为完成（兜底 store/task.js 轮询不更新 task 顶层 status 的历史 bug）
  const isTaskDone = useMemo(() => {
    if (currentTask?.status === 'completed') return true
    const nodes = currentTask?.node_executions
    return !!nodes?.length && nodes.every(n => n.status === 'completed')
  }, [currentTask?.status, currentTask?.node_executions])

  // AI 智能体 tab 内子视图路由
  const chatSubView = useMemo(() => {
    if (isTaskDone) return <ChatContent />
    if (currentTask && !isTaskDone) return <WaitingView />
    if (selectedWorkflow && !currentTask) return <IntentFormPreview />
    return <WorkflowPromptsView />
  }, [isTaskDone, currentTask, selectedWorkflow])

  // "新对话"按钮的等价行为：清空 task + 选中工作流 + 切回 AI 智能体 tab
  // 通过监听 selectedWorkflow 变化：如果从有值变 null，且当前在节点 tab，自动切回 chat
  useEffect(() => {
    if (!selectedWorkflow && !currentTask) {
      setCenterTab(CHAT_TAB_KEY)
    }
  }, [selectedWorkflow, currentTask])

  const tabItems = [
    {
      key: CHAT_TAB_KEY,
      label: '✨ AI 智能体',
      children: chatSubView,
    },
    ...((currentTask?.node_executions || []).map((n, i) => {
      const isAgent = n.node_type === 'agent'
      const label = (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <span>{n.node_name || `节点 ${i + 1}`}</span>
          {isAgent && (
            <span style={{
              fontSize: 10,
              padding: '1px 6px',
              borderRadius: 8,
              background: '#F0F1FF',
              color: '#5C7CFF',
              fontWeight: 500,
            }}>
              agent
            </span>
          )}
        </span>
      )
      return {
        key: n.node_id,
        label,
        children: <NodeContent />,
      }
    })),
  ]

  return (
    <div style={{
      height: 'calc(100vh - 104px)',
      display: 'flex',
      gap: 20,
      padding: '0 0 20px 0',
    }}>
      {/* Left - Workflow Sidebar */}
      <div style={{ width: 280, flexShrink: 0 }}>
        <WorkflowSidebar />
      </div>

      {/* Center - 统一 Tabs 容器（替代过去的 centerContent if/else + 右侧 ChatPanel） */}
      <div
        className={styles.tabsBox}
        style={{
          flex: 1,
          background: '#FFFFFF',
          borderRadius: 14,
          border: '1px solid #E5E6EB',
          overflow: 'hidden',
        }}
      >
        <Tabs
          activeKey={centerTab}
          onChange={(key) => {
            setCenterTab(key)
            // 同步 useTaskStore.currentNodeId：NodeContent 通过它找 currentNode，
            // 不同步的话 agent 节点的 tab 仍渲染 nodes[0]（即 n8n 节点）的内容。
            // CHAT_TAB_KEY 不是节点 tab，忽略。
            if (key !== CHAT_TAB_KEY) {
              useTaskStore.getState().setCurrentNode(key)
            }
          }}
          items={tabItems}
          size="middle"
          tabBarStyle={{
            margin: 0,
            padding: '0 16px',
            background: '#FAFAFA',
            borderBottom: '1px solid #E5E6EB',
          }}
          style={{ height: '100%' }}
          destroyOnHidden={false}
        />
      </div>
    </div>
  )
}

export default AIAssistant
