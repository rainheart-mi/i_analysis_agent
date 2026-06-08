import { useRef, useEffect, useMemo, useState } from 'react'
import { Select, Button, Tooltip, Space, theme, Tag } from 'antd'
import {
  CompressOutlined, LockOutlined, ExclamationCircleOutlined,
  ShareAltOutlined, MoreOutlined, HeartOutlined, SmileOutlined,
  ScheduleOutlined, ProductOutlined, FileSearchOutlined, AppstoreAddOutlined,
  BulbOutlined, LoadingOutlined, ToolOutlined,
} from '@ant-design/icons'
import { Bubble, Sender, Welcome, Prompts, Think } from '@ant-design/x'
import { createStyles } from 'antd-style'
import { useChatStore } from '@/store/chat'
import { useWorkflowStore } from '@/store/workflow'
import { useChatBinding } from './hooks/useChatBinding'
import { useChatHistory } from './hooks/useChatHistory'
import { useStreamContent } from './hooks/useStreamContent'
import Markdown from '@/components/markdown/Markdown'
import MessageActions from './components/bubbleActions'

// 空状态下的快捷提示词
const HOT_TOPICS = [
  { key: '1', label: '总结本节点结果', description: '请总结本节点的关键指标与核心发现' },
  { key: '2', label: '指出异常数据', description: '请指出本节点输出中的下滑品类或失能货架' },
  { key: '3', label: '给出 3 条优化建议', description: '基于本节点数据给出 3 条具体可执行的优化建议' },
  { key: '4', label: '对比 TOP5 货架', description: '对比 TOP5 货架的坪效与饱和度，给出排名解读' },
]

const DESIGN_GUIDE = [
  { key: '1', icon: <HeartOutlined />, label: '意图理解', description: '请基于上下文理解用户真实意图并提供解决方案' },
  { key: '2', icon: <SmileOutlined />, label: 'AI 角色', description: '请以资深品类分析师的身份回答后续问题' },
]

// Sender 上方的快捷 chip（始终显示）
const SENDER_PROMPTS = [
  { key: '1', icon: <ScheduleOutlined />, label: '动态' },
  { key: '2', icon: <ProductOutlined />, label: '组件' },
  { key: '3', icon: <FileSearchOutlined />, label: '指南' },
  { key: '4', icon: <AppstoreAddOutlined />, label: '教程' },
]

// 对照 Ant Design X 百宝箱 demo 的样式系统
const useStyle = createStyles(({ token, css }) => ({
  sender: css`
    width: 100%;
    max-width: 1100px;
    margin: 0 auto;
    .ant-sender-content,
    .ant-sender-input {
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
    }
    .ant-sender-input textarea,
    .ant-sender-input .ant-input {
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      outline: none !important;
      padding: 0 !important;
      resize: none !important;
    }
  `,
  senderPrompt: css`
    width: 100%;
    max-width: 1100px;
    margin: 0 auto;
    color: ${token.colorText};
  `,
  chatPrompt: css`
    .ant-prompts-label { color: #000000e0 !important; }
    .ant-prompts-desc  { color: #000000a6 !important; width: 100%; }
    .ant-prompts-icon  { color: #000000a6 !important; }
  `,
  chat: css`
    height: 100%;
    width: 100%;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    .ant-bubble-content-updating {
      background-image: linear-gradient(90deg, #ff6b23 0%, #af3cb8 31%, #53b6ff 89%);
      background-size: 100% 2px;
      background-repeat: no-repeat;
      background-position: bottom;
    }
    /* AI 气泡占满容器宽度，减少左右空白 */
    .ant-bubble.ant-bubble-start {
      max-width: 95%;
    }
    .ant-bubble.ant-bubble-start .ant-bubble-content-wrapper {
      max-width: 100%;
    }
    .ant-bubble.ant-bubble-start .ant-bubble-content {
      max-width: 100%;
      overflow: hidden;
    }
    /* 对话区容器：与 Sender 共享 1100px 中央通道，左右边线对齐。
       ！important 是必需的：BubbleList 内部 style/list.js:8 强制 width:100%，
       普通类选择器的 max-width 优先级不足以覆盖它。 */
    .ant-bubble-list {
      max-width: 1100px !important;
      width: 100% !important;
      margin-left: auto !important;
      margin-right: auto !important;
      padding: 0 24px 8px;
    }
  `,
  thinkPanel: css`
    margin-bottom: 12px;
  `,
}))

/**
 * AI 气泡内容渲染：Think 面板 + 打字机切片后的 Markdown。
 * 把 useStreamContent 隔离在子组件里，避免每条消息都创建 hook 闭包。
 */
function AssistantBubble({ fullContent, thinking, isUpdating }) {
  // 完整文本 + 流式标志 → 派生打字机切片（store 里的 content 始终是 source-of-truth）
  const [streamContent] = useStreamContent(fullContent, { step: 2, interval: 30 })
  // 历史/已完成的 assistant 消息直接渲染 fullContent；仅 SSE 流式期间用打字机切片
  const displayContent = isUpdating ? streamContent : fullContent
  return (
    <>
      {thinking && (
        <ThinkingPanel thinking={thinking} streaming={isUpdating} />
      )}
      <Markdown streaming={isUpdating}>{displayContent}</Markdown>
    </>
  )
}

/**
 * 思考过程面板：流式期间强制展开（blink + loading），
 * 流结束后切换到用户受控模式（允许折叠）。
 */
function ThinkingPanel({ thinking, streaming }) {
  const { styles } = useStyle()
  const [expanded, setExpanded] = useState(true)
  const effectiveExpanded = streaming || expanded
  return (
    <Think
      className={styles.thinkPanel}
      title={streaming ? '深度思考中…' : '已完成思考'}
      icon={streaming ? <LoadingOutlined spin /> : <BulbOutlined />}
      loading={streaming}
      blink={streaming}
      expanded={effectiveExpanded}
      onExpand={setExpanded}
    >
      {thinking}
    </Think>
  )
}

/**
 * 展开态 AI 对话视图：完全对齐 Ant Design X 百宝箱 demo 视觉。
 * 居中 max-width 容器、主题色 token、Welcome 左对齐、Prompts 卡片 + chips、
 * 流式渐变动画、圆形发送按钮；集成 Think 组件展示大模型思考过程。
 */
function ChatContent({ onCollapse }) {
  const { token } = theme.useToken()
  const { styles } = useStyle()

  const messages = useChatStore(s => s.messages)
  const selectedWorkflow = useChatStore(s => s.selectedWorkflow)
  const setSelectedWorkflow = useChatStore(s => s.setSelectedWorkflow)
  const setActiveNodeExecution = useChatStore(s => s.setActiveNodeExecution)
  const activeNodeExecutionId = useChatStore(s => s.activeNodeExecutionId)
  const setFeedback = useChatStore(s => s.setFeedback)
  const workflows = useWorkflowStore(s => s.workflows)

  const { currentNode, isNodeReady, inputDisabled, isStreaming, nodeStatusLabel, lockMessage,
          error, handleSend, cancel } = useChatBinding()

  // 监听 activeNodeExecutionId 变化，拉取 AgentScope 历史并填充 messages
  useChatHistory()

  const senderRef = useRef(null)

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

  // 2.x Bubble.List items：含 status / extraInfo / streaming 三个关键字段
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
          status: 'local',
        }
      }
      const isMsgStreaming = m.streaming === true
      const item = {
        key: m.id,
        role: m.type === 'user' ? 'user' : 'assistant',
        content: m.content,
        // status 决定 contentRender 中 info.status；Bubble 自身据此切换 loading / 内容态
        status: isMsgStreaming
          ? 'updating'
          : (m.type === 'assistant' ? 'success' : 'local'),
        // 把 thinking 内容塞 extraInfo，contentRender 里通过 info.extraInfo 取出
        extraInfo: m.type === 'assistant' ? { thinking: m.thinking || '' } : undefined,
        // 2.x streaming prop：true 时即使 content 变化也只触发一次 onTypingComplete
        streaming: isMsgStreaming,
        // 仅在等待首 chunk（content 与 thinking 都为空）时显示 loading spinner
        loading: isMsgStreaming && !m.content && !(m.thinking || ''),
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

  // 自定义 AI 图标：紫色渐变 + ✨ + 阴影
  const aiIcon = (
    <div style={{
      width: 64, height: 64, borderRadius: 18,
      background: 'linear-gradient(135deg, #5B21B6 0%, #7C3AED 50%, #EC4899 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: '0 8px 24px rgba(124, 58, 237, 0.35)',
      fontSize: 32, flexShrink: 0,
    }}>✨</div>
  )

  return (
    <div
      className={styles.chat}
      style={{
        background: token.colorBgContainer,
        overflow: 'hidden'
      }}
    >
      {/* Top bar: workflow selector + collapse button */}
      <div style={{
        padding: '12px 24px',
        borderBottom: `1px solid ${token.colorBorderSecondary}`,
        display: 'flex',
        alignItems: 'center',
        gap: 12
      }}>
        <Select
          value={selectedWorkflow?.id}
          onChange={(val) => {
            const wf = workflows.find(w => w.id === val)
            setSelectedWorkflow(wf || null)
          }}
          placeholder="选择工作流"
          options={workflowOptions}
          style={{ width: 280 }}
          size="middle"
        />
        {currentNode && (
          <Tooltip title={currentNode.node_name || currentNode.node_id}>
            {isNodeReady ? (
              <span style={{
                fontSize: '12px', color: '#52C41A', background: '#F6FFED',
                padding: '2px 8px', borderRadius: 10
              }}>● 已就绪</span>
            ) : (
              <span style={{
                fontSize: '12px', color: token.colorTextTertiary, background: token.colorFillTertiary,
                padding: '2px 8px', borderRadius: 10
              }}>
                <LockOutlined style={{ fontSize: '11px', marginRight: 2 }} />{nodeStatusLabel}
              </span>
            )}
          </Tooltip>
        )}
        <Button
          type="text"
          icon={<CompressOutlined />}
          onClick={onCollapse}
          style={{ marginLeft: 'auto', color: token.colorTextTertiary }}
        >
          收起
        </Button>
      </div>

      {/* Messages / Empty state - centered with max-width */}
      <div style={{ flex: 1, overflow: 'auto', padding: '24px 0' }}>
        {error && (
          <div style={{ maxWidth: 940, margin: '0 auto 12px', padding: '0 24px' }}>
            <div style={{
              background: token.colorErrorBg, border: `1px solid ${token.colorErrorBorder}`,
              color: token.colorError, padding: '8px 12px', borderRadius: 8,
              fontSize: '12px', display: 'flex', alignItems: 'center', gap: 6
            }}>
              <ExclamationCircleOutlined />
              <span>{error}</span>
            </div>
          </div>
        )}
        {messages.length === 0 ? (
          <div style={{
            maxWidth: 840, margin: '0 auto', padding: '32px 24px 0',
            display: 'flex', flexDirection: 'column', gap: 24
          }}>
            {/* Welcome - 左对齐 */}
            <Welcome
              variant="borderless"
              icon={aiIcon}
              title="你好，我是工作流 AI 助手"
              description={isNodeReady
                ? '基于工作流节点的 AI 助手，可针对节点执行结果进行多轮对话分析。'
                : '请先在画布中执行工作流节点，完成后即可在此发起对话。'}
              extra={
                <Space>
                  <Button type="text" icon={<ShareAltOutlined />} />
                  <Button type="text" icon={<MoreOutlined />} />
                </Space>
              }
              style={{ textAlign: 'left', alignItems: 'flex-start' }}
            />

            {/* Prompts 卡片 - 两栏 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Prompts
                title="最热话题"
                items={HOT_TOPICS}
                wrap
                onItemClick={(info) => handleSend(info.data.description)}
                className={styles.chatPrompt}
                styles={{
                  list: { background: 'linear-gradient(135deg, #EEF2FF 0%, #F3E8FF 100%)', borderRadius: 12, padding: 12 },
                  item: { background: '#fff', border: 'none', borderRadius: 8, marginBottom: 4 },
                  title: { color: '#1D2129', fontSize: 14, fontWeight: 600 },
                }}
              />
              <Prompts
                title="设计指南"
                items={DESIGN_GUIDE}
                wrap
                onItemClick={(info) => handleSend(info.data.description)}
                className={styles.chatPrompt}
                styles={{
                  list: { background: 'linear-gradient(135deg, #F0F9FF 0%, #FAE8FF 100%)', borderRadius: 12, padding: 12 },
                  item: { background: '#fff', border: 'none', borderRadius: 8, marginBottom: 4 },
                  title: { color: '#1D2129', fontSize: 14, fontWeight: 600 },
                }}
              />
            </div>
          </div>
        ) : (
          <Bubble.List
            items={bubbleItems}
            autoScroll
            role={{
              user: { placement: 'end' },
              assistant: {
                placement: 'start',
                contentRender: (content, info) => {
                  const thinking = info?.extraInfo?.thinking
                  const isUpdating = info?.status === 'updating'
                  return (
                    <AssistantBubble
                      fullContent={content || ''}
                      thinking={thinking}
                      isUpdating={isUpdating}
                    />
                  )
                },
              },
              tool: {
                placement: 'start',
                variant: 'borderless',
                style: { background: token.colorFillTertiary, maxWidth: '92%', color: token.colorTextSecondary },
              },
            }}
          />
        )}
      </div>

      {/* Input area */}
      {isNodeReady ? (
        <div style={{
          padding: '12px 0 20px', borderTop: `1px solid ${token.colorBorderSecondary}`,
          background: token.colorBgContainer
        }}>
          {/* Sender 上方快捷 chips */}
          <div style={{ maxWidth: 1100, margin: '0 auto 12px', padding: '0 24px' }}>
            <Prompts
              items={SENDER_PROMPTS}
              wrap
              onItemClick={(info) => handleSend(`请介绍 ${info.data.label} 相关内容`)}
              className={styles.senderPrompt}
              styles={{
                list: { gap: 8, border: 'none', padding: 0 },
                item: { padding: '6px 12px', borderRadius: 16, border: `1px solid ${token.colorBorderSecondary}` },
                title: { color: token.colorTextSecondary, fontSize: 13 },
              }}
            />
          </div>
          {/* Sender */}
          <Sender
            ref={senderRef}
            className={styles.sender}
            placeholder={placeholder}
            loading={isStreaming}
            disabled={inputDisabled && isNodeReady}
            onSubmit={(val) => {
              handleSend(val)
              senderRef.current?.clear?.()
            }}
            onCancel={cancel}
            actions={(ori, { components: { SendButton } }) => <SendButton />}
          />
        </div>
      ) : (
        <div style={{
          padding: '24px', borderTop: `1px solid ${token.colorBorderSecondary}`,
          background: token.colorFillAlter, display: 'flex',
          alignItems: 'center', justifyContent: 'center', gap: 8
        }}>
          <LockOutlined style={{ color: token.colorTextTertiary, fontSize: 14 }} />
          <span style={{ fontSize: '13px', color: token.colorTextTertiary }}>{lockMessage}</span>
        </div>
      )}
    </div>
  )
}

export default ChatContent
