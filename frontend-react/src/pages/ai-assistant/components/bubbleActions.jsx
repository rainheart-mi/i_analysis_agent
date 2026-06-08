import { Actions } from '@ant-design/x'
import { App } from 'antd'
import { CopyOutlined, LikeOutlined, DislikeOutlined } from '@ant-design/icons'

/**
 * 消息气泡底部 Actions 组件。
 *
 * 行为：
 * - user 消息：复制
 * - assistant 消息：复制 + 点赞/点踩（用 Actions.Feedback 内置子组件，like/dislike 互斥）
 * - 流式中（message.streaming === true）不渲染，避免对未完成内容做反馈
 * - 复制成功后用 antd message 弹「已复制」toast（通过 App context 拿 message 实例）
 *
 * 数据契约：
 * - message.feedback: 'like' | 'dislike' | null
 * - onFeedback(messageId, value): 由调用方把反馈写入 store（持久化）
 */
function MessageActions({ message, onFeedback }) {
  const { message: toast } = App.useApp()
  const text = message.content || ''

  if (message.streaming === true) return null

  const handleCopy = () => {
    if (!text) return
    navigator.clipboard.writeText(text).then(
      () => toast.success('已复制'),
      () => toast.error('复制失败')
    )
  }

  if (message.type === 'user') {
    return (
      <Actions
        items={[
          {
            key: 'copy',
            label: '复制',
            icon: <CopyOutlined />,
            onItemClick: handleCopy,
          },
        ]}
        fadeIn
      />
    )
  }

  return (
    <Actions
      items={[
        {
          key: 'copy',
          label: '复制',
          icon: <CopyOutlined />,
          onItemClick: handleCopy,
        },
        {
          key: 'feedback',
          label: '反馈',
          icon: <LikeOutlined />,
          children: (
            <Actions.Feedback
              value={message.feedback || 'default'}
              onChange={(v) => onFeedback(message.id, v)}
            />
          ),
        },
      ]}
      fadeIn
    />
  )
}

export default MessageActions
