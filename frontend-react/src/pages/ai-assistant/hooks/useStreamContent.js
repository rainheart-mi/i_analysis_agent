import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * 打字机效果 hook —— 借鉴 @ant-design/x 官方 streaming demo 的设计模式。
 *
 * 设计思想：
 * - 完整 `content`（来自 store / SSE 推送）是 source-of-truth
 * - 本 hook 派生出一个"展示切片" `streamContent`，按 step/interval 节奏推进
 * - DOM 只渲染 `streamContent`（部分内容），用户感受到逐字出现的打字机效果
 * - 流自然结束（content 稳定）时，`streamContent` 最终追上 `content`，done=true
 *
 * SSE 场景下的关键修复（vs 官方 demo 的"模拟数据一次性设值"）：
 * - 官方 demo 的 data 一次性设值后不再变化；SSE 场景下 content 在打字机推进期间
 *   会持续追加。startStream 闭包若固化 `text`，interval 跑完旧 text 长度后会立即
 *   done=true 并丢字符。
 * - 解决：用 `textRef` 替代闭包变量，每次 content 变化都同步更新；并在 useEffect
 *   中检测"done=true 但 content 又涨"的情况重启打字机。
 *
 * @param {string} content - 当前最新的完整内容（source-of-truth）
 * @param {object} [options]
 * @param {number} [options.step=2] - 每帧推进的字符数
 * @param {number} [options.interval=30] - 每帧间隔毫秒
 * @returns {[string, boolean]} [streamContent, isDone]
 */
export function useStreamContent(content, { step = 2, interval = 30 } = {}) {
  const [streamContent, setStreamContent] = useState('')
  const streamRef = useRef('')
  // 永远指向最新的 content（避免 startStream 闭包固化旧值）
  const textRef = useRef(content)
  const doneRef = useRef(true)
  const timerRef = useRef(-1)
  const stepRef = useRef(step)
  stepRef.current = step
  const intervalRef = useRef(interval)
  intervalRef.current = interval

  const setBoth = useCallback((next) => {
    setStreamContent(next)
    streamRef.current = next
  }, [])

  // 每次 content 变化都同步 textRef；startStream 的闭包从 ref 读取，永远是最新
  textRef.current = content

  useEffect(() => {
    // 1) content 长度未变（首字符/重复推送），什么都不做
    if (content.length === streamRef.current.length && content.length === 0) return
    if (content === streamRef.current) return

    // 2) content 变短（被截断/切会话），清空并重启
    if (content.length < streamRef.current.length) {
      setBoth('')
      doneRef.current = true
      clearInterval(timerRef.current)
      // 继续走到下面的"首帧"分支，启动新一轮
    }

    // 3) 首帧：streamRef 还没追上 content（空或刚清空），启动打字机
    if (!streamRef.current && content) {
      clearInterval(timerRef.current)
      startStream()
      return
    }

    // 4) content 增长但 streamRef 已追上（done=true）—— 后续 SSE 又追加了内容，重启
    if (content.indexOf(streamRef.current) === 0 && doneRef.current) {
      clearInterval(timerRef.current)
      startStream()
      return
    }

    // 5) content 增长且当前 timer 还在跑（content 是 streamRef 的扩展）：
    //    textRef 已在上方同步，interval 下次 tick 会读到最新 textRef，自然追赶
    if (content.indexOf(streamRef.current) === 0 && !doneRef.current) {
      return
    }

    // 6) content 被完全替换（不是 streamRef 的扩展），重启
    if (content.indexOf(streamRef.current) !== 0) {
      clearInterval(timerRef.current)
      startStream()
    }

    function startStream() {
      doneRef.current = false
      streamRef.current = ''
      timerRef.current = setInterval(() => {
        const len = streamRef.current.length + stepRef.current
        // 闭包不再用 text 变量，全部从 textRef 读最新 content
        if (len <= textRef.current.length - 1) {
          setBoth(textRef.current.slice(0, len))
        } else {
          setBoth(textRef.current)
          doneRef.current = true
          clearInterval(timerRef.current)
        }
      }, intervalRef.current)
    }
  }, [content, setBoth])

  // 组件卸载时清理 interval
  useEffect(() => () => clearInterval(timerRef.current), [])

  return [streamContent, doneRef.current]
}
