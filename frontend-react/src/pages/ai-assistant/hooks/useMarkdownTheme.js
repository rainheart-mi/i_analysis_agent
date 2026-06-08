import { useMemo } from 'react'
import { theme } from 'antd'

/**
 * 返回 markdown 主题类名（'x-markdown-light' / 'x-markdown-dark'）。
 * 当前 app 仅亮色模式，默认返回 light；预留 dark 检测位以便后续扩展。
 */
export function useMarkdownTheme() {
  const { token } = theme.useToken()
  const isDark = useMemo(() => {
    // 简单判定：背景色亮度 < 128 视为暗色
    if (!token?.colorBgContainer) return false
    const hex = token.colorBgContainer.replace('#', '')
    if (hex.length !== 6) return false
    const r = parseInt(hex.slice(0, 2), 16)
    const g = parseInt(hex.slice(2, 4), 16)
    const b = parseInt(hex.slice(4, 6), 16)
    return (r * 299 + g * 587 + b * 114) / 1000 < 128
  }, [token])
  return [isDark ? 'x-markdown-dark' : 'x-markdown-light']
}
