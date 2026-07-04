import { useRef, useEffect, useMemo, useState, useCallback } from 'react'
import { Button, Tooltip, Space, theme, Tag } from 'antd'
import {
  ExclamationCircleOutlined,
  ShareAltOutlined, MoreOutlined, HeartOutlined, SmileOutlined,
  BulbOutlined, LoadingOutlined, ToolOutlined, ArrowDownOutlined, ArrowUpOutlined,
} from '@ant-design/icons'
import { Bubble, Sender, Welcome, Prompts, Think } from '@ant-design/x'
import { createStyles } from 'antd-style'
import { useChatStore } from '@/store/chat'
import { useChatBinding } from './hooks/useChatBinding'
import { useChatHistory } from './hooks/useChatHistory'
import Markdown from '@/components/markdown/Markdown'
import MessageActions from './components/bubbleActions'
import './aiAgentScroll.css'

// 发送按钮主题色（与项目主色一致）
const SEND_BTN_GREEN = '#12b329'
const SEND_BTN_GREEN_HOVER = '#0fa824'

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

// 对照 Ant Design X 百宝箱 demo 的样式系统（标准 ant- 前缀）
const useStyle = createStyles(({ token, css }) => {
  const sender = 'ant-sender'
  return {
  senderWrap: css`
    width: 100%;
    max-width: 1100px;
    margin: 0 auto;
  `,
  sendBtn: css`
    &&.${sender}-actions-btn {
      width: 40px !important;
      height: 40px !important;
      min-width: 40px !important;
      padding: 0 !important;
      border-radius: 50% !important;
      background: ${SEND_BTN_GREEN} !important;
      border-color: ${SEND_BTN_GREEN} !important;
      color: #fff !important;
      display: inline-flex !important;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      box-shadow: 0 2px 8px rgba(18, 179, 41, 0.35);

      &:hover:not(:disabled) {
        background: ${SEND_BTN_GREEN_HOVER} !important;
        border-color: ${SEND_BTN_GREEN_HOVER} !important;
        color: #fff !important;
      }

      .anticon {
        font-size: 18px;
      }
    }
  `,
  sender: css`
    width: 100%;

    &.${sender}-main {
      border-radius: 20px;
      border: 1px solid ${token.colorBorderSecondary};
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
      background: ${token.colorBgContainer};
      transition: border-color 0.2s, box-shadow 0.2s;

      &:focus-within {
        border-color: ${SEND_BTN_GREEN};
        box-shadow: 0 2px 16px rgba(18, 179, 41, 0.12);
      }
    }

    .${sender}-content {
      padding: 14px 16px;
      align-items: flex-end;
      gap: 12px;
    }

    .${sender}-input,
    .${sender}-input textarea,
    .${sender}-input .ant-input {
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      outline: none !important;
      padding: 0 !important;
      resize: none !important;
      font-size: 15px;
      line-height: 1.6;
    }

    .${sender}-actions-list {
      flex-shrink: 0;
    }
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
       普通类选择器的 max-width 优先级不足以覆盖它。
       ！flex 约束是必需的：.ant-bubble-list-scroll-box 内部用 max-height:100%，
       必须有确定的 flex 容器父级才能解析；否则长内容（如 summary）会把 scroll-box
       撑成 6 万像素，scrollHeight === clientHeight，autoScroll 完全失效。 */
    .ant-bubble-list {
      max-width: 1100px !important;
      width: 100% !important;
      margin-left: auto !important;
      margin-right: auto !important;
      padding: 0 24px 8px;
      flex: 1 1 0 !important;
      min-height: 0 !important;
      display: flex !important;
      flex-direction: column !important;
      overflow: hidden !important;
    }
  `,
  thinkPanel: css`
    margin-bottom: 12px;
  `,
  }})

/**
 * AI 气泡内容渲染：Think 面板 + Markdown。
 * 字符级打字机推进由 ChatContent 内的 visibleContent 控制。
 */
function AssistantBubble({ fullContent, thinking, isUpdating }) {
  return (
    <>
      {thinking && (
        <ThinkingPanel thinking={thinking} streaming={isUpdating} />
      )}
      <Markdown streaming={isUpdating}>{fullContent}</Markdown>
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
function ChatContent() {
  const { token } = theme.useToken()
  const { styles } = useStyle()

  const selectedWorkflow = useChatStore(s => s.selectedWorkflow)
  const setActiveNodeExecution = useChatStore(s => s.setActiveNodeExecution)
  const activeNodeExecutionId = useChatStore(s => s.activeNodeExecutionId)

  const { currentNode, currentTask, isNodeReady, inputDisabled, isStreaming,
          error, handleSend, cancel, messages, setFeedback } = useChatBinding()

  // 监听 activeNodeExecutionId 变化，拉取 AgentScope 历史并填充 messages
  useChatHistory()

  const senderRef = useRef(null)
  const bubbleListRef = useRef(null)

  // 「回到底部」浮按钮：常驻显示，点击 → scrollTo({ top: 'bottom' })
  // 走 antd-x 官方 scrollTo：内部自动按 autoScroll 推算 column-reverse 偏移，
  // 并触发 useCompatibleScroll 的 scrolling 计时器，避免 ResizeObserver 在内容
  // 增长瞬间用 enforceScrollLock 把视窗抢回。
  const handleScrollToBottom = useCallback(() => {
    bubbleListRef.current?.scrollTo({ top: 'bottom', behavior: 'instant' })
  }, [])

  // 自动滚底（IO 处理 history 覆盖 / tab 切换重入）：
  // <Bubble.List autoScroll /> 已处理流式 append / 新消息 / smart lock，
  // 剩 history 覆盖式 setMessages + tab 来回切换这两种「视口已存在但内容换了」的场景
  // 需要靠监听 scroll-box 可见性 → 重新滚底。不用 done flag（切 tab 是高频行为）。
  useEffect(() => {
    if (messages.length === 0) return
    const sb = bubbleListRef.current?.scrollBoxNativeElement
    if (!sb) return

    const scrollToEnd = () => {
      if (sb.clientHeight === 0) return
      bubbleListRef.current?.scrollTo({ top: 'bottom', behavior: 'instant' })
    }

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          requestAnimationFrame(scrollToEnd)
        }
      },
      { threshold: 0.01 }
    )
    io.observe(sb)
    return () => io.disconnect()
  }, [activeNodeExecutionId, messages.length])

  useEffect(() => {
    if (currentNode?.id && currentNode.id !== activeNodeExecutionId) {
      setActiveNodeExecution(currentNode.id)
    } else if (!currentNode?.id && activeNodeExecutionId) {
      setActiveNodeExecution(null)
    }
  }, [currentNode?.id, activeNodeExecutionId, setActiveNodeExecution])

  // 2.x Bubble.List items：含 status / extraInfo / streaming 三个关键字段
  // - user: 用户消息
  // - assistant: AI 消息（含 toolCalls footer 角标）
  // - tool: 工具结果（V1 简化为单行徽标，V2 再加可折叠 JSON）
  //
  // useXChat 数据形态：messages: MessageInfo[]，每条形如
  //   { id, message: { content, thinking, role, toolName?, toolCalls? }, status, extraInfo? }
  // mapper 在这里把它"翻译"成 Bubble.List 期望的形态（含把 toolCalls 角标塞 footer），
  // 并把 legacy message 形态（m.type / m.streaming / m.feedback）适配给 MessageActions 用。
  const bubbleItems = useMemo(
    () => messages
      .filter(info => info?.message && ['user', 'assistant', 'tool'].includes(info.message.role))
      .map(info => {
      const m = info.message
      const mRole = m.role
      const isMsgStreaming = info.status === 'loading' || info.status === 'updating'

      if (mRole === 'tool') {
        const toolContent = m.content || ''
        return {
          key: info.id,
          role: 'tool',
          content: `🔧 ${m.toolName || 'tool'}: ${toolContent.slice(0, 80)}${toolContent.length > 80 ? '…' : ''}`,
          status: 'local',
        }
      }
      const item = {
        key: info.id,
        role: mRole === 'user' ? 'user' : 'assistant',
        content: m.content,
        // status 决定 contentRender 中 info.status；Bubble 自身据此切换 loading / 内容态
        status: isMsgStreaming
          ? 'updating'
          : (mRole === 'assistant' ? 'success' : 'local'),
        // 把 thinking 内容塞 extraInfo，contentRender 里通过 info.extraInfo 取出
        extraInfo: mRole === 'assistant' ? { thinking: m.thinking || '' } : undefined,
        // 2.x streaming prop：true 时即使 content 变化也只触发一次 onTypingComplete
        streaming: isMsgStreaming,
        // 仅在等待首 chunk（content 与 thinking 都为空）时显示 loading spinner
        loading: isMsgStreaming && !m.content && !(m.thinking || ''),
      }
      // 适配 MessageActions 的 legacy message 形态：把 useXChat 形态"投影"成老接口
      const legacyMessage = {
        id: info.id,
        type: mRole,
        content: m.content,
        feedback: info.extraInfo?.feedback || null,
        streaming: isMsgStreaming,
        toolCalls: m.toolCalls,
      }
      if (mRole === 'assistant' && Array.isArray(m.toolCalls) && m.toolCalls.length > 0) {
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
            <MessageActions message={legacyMessage} onFeedback={setFeedback} />
          </Space>
        )
      } else {
        item.footer = <MessageActions message={legacyMessage} onFeedback={setFeedback} />
      }
      return item
    }),
    [messages, setFeedback]
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
      {/* Top bar: 当前工作流 + 完成态摘要（AIAssistant 路由确保 ChatContent 只在 task completed 时渲染） */}
      <div style={{
        padding: '12px 24px',
        borderBottom: `1px solid ${token.colorBorderSecondary}`,
        display: 'flex',
        alignItems: 'center',
        gap: 12
      }}>
        <Tag color="purple" style={{ margin: 0 }}>AI 智能体</Tag>
        <span style={{ fontSize: 14, fontWeight: 500, color: token.colorText }}>
          {currentTask?.name || selectedWorkflow?.title || '工作流对话'}
        </span>
        {currentTask && (
          <Tag color="green" style={{ margin: 0 }}>● 已完成</Tag>
        )}
      </div>

      {/* Messages / Empty state - centered with max-width */}
      {/* ！minHeight: 0 关键：flex item 默认 min-height: auto，会被内容撑爆。
          没有这个，.ant-bubble-list 的 maxHeight:100% 解析不到 734，scroll-box 长到跟内容一样大，
          没有 overflow，scrollTo 就无效。
          position: relative 是为了浮动按钮（absolute）以本容器为定位锚。 */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '24px 0', position: 'relative' }}>
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
            ref={bubbleListRef}
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
        {/* 「回到底部」浮按钮：常驻，点击即滚底 */}
        <Button
          shape="circle"
          icon={<ArrowDownOutlined />}
          onClick={handleScrollToBottom}
          style={{
            position: 'absolute',
              bottom: 16,
              right: 24,
              boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
              zIndex: 10,
            }}
          />
      </div>

      {/* Input area：与消息列表同宽同边距（24px） */}
      <div style={{
        padding: '12px 24px 24px',
        borderTop: `1px solid ${token.colorBorderSecondary}`,
        background: token.colorBgContainer
      }}>
        <div className={styles.senderWrap}>
          <Sender
            ref={senderRef}
            className={`ai-agent-chat-sender ${styles.sender}`}
            placeholder={placeholder}
            loading={isStreaming}
            disabled={inputDisabled}
            autoSize={{ minRows: 2, maxRows: 8 }}
            onSubmit={(val) => {
              handleSend(val)
              senderRef.current?.clear?.()
            }}
            onCancel={cancel}
            suffix={(_, { components: { SendButton, LoadingButton } }) => (
              isStreaming ? <LoadingButton className={styles.sendBtn} /> : (
                <SendButton
                  color="primary"
                  variant="solid"
                  shape="circle"
                  icon={<ArrowUpOutlined />}
                  className={`ai-agent-send-btn ${styles.sendBtn}`}
                />
              )
            )}
          />
        </div>
      </div>
    </div>
  )
}

export default ChatContent
