import XMarkdown from '@ant-design/x-markdown'
import { useMarkdownTheme } from '@/pages/ai-assistant/hooks/useMarkdownTheme'
import './markdown-theme.css'

/**
 * 统一的 Markdown 渲染包装（基于 @ant-design/x-markdown）。
 * 支持流式动画、亮/暗主题。配套 markdown-theme.css。
 *
 * streaming=true 时透传官方 streaming 对象：
 *  - tail: '▋'  末尾光标，体现"正在打字"
 *  - hasNextChunk: true  启用 incomplete token 占位（未闭合 link/code block）
 *  字符级推进（typewriter）由 ChatContent.jsx 的 useTypewriter 完成
 *  —— 与官方 demo 的 setTimeout 推进模式一致；本组件不再做块级淡入，避免叠加。
 * 调用侧只需要 boolean 即可，无需关心对象细节。
 */
export default function Markdown({ children, streaming = false }) {
  const [mdClass] = useMarkdownTheme()
  return (
    <XMarkdown
      content={children || ''}
      className={mdClass}
      streaming={streaming ? {
        hasNextChunk: true,
        tail: { content: '▋' },
      } : undefined}
      components={{
        a: ({ node: _node, ...props }) => <a target="_blank" rel="noopener noreferrer" {...props} />,
      }}
    />
  )
}
