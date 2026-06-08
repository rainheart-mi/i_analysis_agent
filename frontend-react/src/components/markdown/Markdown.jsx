import XMarkdown from '@ant-design/x-markdown'
import { useMarkdownTheme } from '@/pages/ai-assistant/hooks/useMarkdownTheme'
import './markdown-theme.css'

/**
 * 统一的 Markdown 渲染包装（基于 @ant-design/x-markdown）。
 * 支持流式动画、亮/暗主题。配套 markdown-theme.css。
 */
export default function Markdown({ children, streaming = false }) {
  const [mdClass] = useMarkdownTheme()
  return (
    <XMarkdown
      content={children || ''}
      className={mdClass}
      streaming={streaming ? { hasNextChunk: true, tail: true } : undefined}
      components={{
        a: ({ node: _node, ...props }) => <a target="_blank" rel="noopener noreferrer" {...props} />,
      }}
    />
  )
}
