import { useRef, useEffect } from 'react'

// 递归为 schema 中的所有字段设置 readOnly
function setFieldsReadOnly(schema, readOnly) {
  if (!schema) return schema
  const result = { ...schema }

  if (result.type === 'form' || result.type === 'input-group') {
    if (result.body) {
      result.body = result.body.map(item => setFieldsReadOnly(item, readOnly))
    }
  }

  const inputTypes = [
    'input-text', 'input-number', 'select', 'checkbox', 'switch', 'radios',
    'input-date', 'input-datetime', 'textarea', 'nested-select',
    'input-date-range', 'input-year', 'input-month', 'input-quarter',
    'input-week', 'input-time', 'input-tree'
  ]
  if (inputTypes.includes(result.type)) {
    result.readOnly = readOnly
    result.disabled = readOnly
    if (readOnly) {
      result.static = true
    }
  }

  if (result.type === 'input-date-range') {
    if (readOnly) {
      result.static = true
      result.mode = 'readonly'
    }
  }

  if (result.type === 'grid' || result.type === 'table' || result.type === 'list') {
    if (result.body) {
      result.body = result.body.map(item => setFieldsReadOnly(item, readOnly))
    }
    if (result.columns) {
      result.columns = result.columns.map(col => {
        if (col.body) {
          return { ...col, body: col.body.map(item => setFieldsReadOnly(item, readOnly)) }
        }
        return { ...col, readOnly: readOnly, disabled: readOnly }
      })
    }
  }

  if (result.columns) {
    result.columns = result.columns.map(col => setFieldsReadOnly(col, readOnly))
  }

  if (result.body) {
    if (Array.isArray(result.body)) {
      result.body = result.body.map(item => setFieldsReadOnly(item, readOnly))
    }
  }

  return result
}

/**
 * ★★★ 关键修复：强制关闭所有会触发 getBoundingClientRect 的 JS 特性
 * 并用 CSS 替代 JS 实现固顶效果
 */
function setTableSafeProps(schema) {
  if (!schema || typeof schema !== 'object') return schema
  const result = { ...schema }

  if (result.type === 'table' || result.type === 'table2' || result.type === 'crud') {
    // 1. 强制关闭固顶/固列（最核心的崩溃源）
    result.affixHeader = false
    result.affixColumns = false
    // 2. 强制关闭懒渲染（内部用 getBoundingClientRect 判断行可见性）
    result.lazyRender = false
    // 3. 强制关闭列宽拖拽（拖拽时频繁测量 DOM）
    result.resizable = false
    // 4. 强制使用固定布局（阻止 amis 在渲染后重新计算/同步列宽，这也是崩溃源之一）
    result.tableLayout = 'fixed'
    // 5. 注入自定义类名，用于后续 CSS 实现固顶替代方案
    result.className = result.className
      ? `${result.className} safe-sticky-table`
      : 'safe-sticky-table'
  }

  // 递归处理所有可能嵌套 table 的结构
  const recurseKeys = ['body', 'columns', 'tabs', 'items', 'header', 'footer', 'toolbar']
  for (const key of recurseKeys) {
    if (result[key]) {
      if (Array.isArray(result[key])) {
        result[key] = result[key].map(item => setTableSafeProps(item))
      } else if (typeof result[key] === 'object') {
        result[key] = setTableSafeProps(result[key])
      }
    }
  }

  if (result.columns) {
    result.columns = result.columns.map(col => {
      if (col && typeof col === 'object') {
        return setTableSafeProps(col)
      }
      return col
    })
  }

  if (Array.isArray(result.tabs)) {
    result.tabs = result.tabs.map(tab => {
      if (tab && typeof tab === 'object') {
        const safeTab = { ...tab }
        if (safeTab.body) {
          if (Array.isArray(safeTab.body)) {
            safeTab.body = safeTab.body.map(item => setTableSafeProps(item))
          } else if (typeof safeTab.body === 'object') {
            safeTab.body = setTableSafeProps(safeTab.body)
          }
        }
        return safeTab
      }
      return tab
    })
  }

  return result
}

function formatDateRange(dateRange) {
  if (!dateRange) return ''
  if (typeof dateRange === 'string') return dateRange
  if (Array.isArray(dateRange) && dateRange.length === 2) {
    const [start, end] = dateRange
    const startDate = new Date(parseInt(start) * 1000)
    const endDate = new Date(parseInt(end) * 1000)
    const formatDate = (d) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    return `${formatDate(startDate)} 至 ${formatDate(endDate)}`
  }
  return String(dateRange)
}

function AmISForm({ schema, value, onChange, readonly }) {
  const containerRef = useRef(null)
  const amisScopedRef = useRef(null)
  const prevSchemaRef = useRef(null)
  const prevReadonlyRef = useRef(null)
  const prevValueRef = useRef(null)
  const isMountedRef = useRef(true)
  const isInternalChangeRef = useRef(false)
  const initVersionRef = useRef(0)
  const debounceTimerRef = useRef(null)

  // ★ 新增：注入 CSS Sticky 固顶样式，替代原生的 JS Affix 测量
  useEffect(() => {
    const styleId = 'amis-safe-sticky-style'
    if (!document.getElementById(styleId)) {
      const style = document.createElement('style')
      style.id = styleId
      style.innerHTML = `
        /* 用原生 CSS Sticky 替代 JS Affix，完全避免 getBoundingClientRect 调用 */
        .safe-sticky-table thead th {
          position: sticky !important;
          top: 0 !important;
          z-index: 2 !important;
          background: var(--Table-thead-bg, #f6f7f9) !important;
        }
      `
      document.head.appendChild(style)
    }
  }, [])

  // ★ 新增：全局错误终极拦截（捕获阶段），防止 SDK 内部漏网的测量崩溃导致白屏
  useEffect(() => {
    const handleError = (event) => {
      const msg = event.error?.message || event.message || ''
      if (msg.includes('getBoundingClientRect')) {
        event.stopImmediatePropagation()
        event.preventDefault()
        console.warn('[AmISForm] 已拦截 amis SDK 内部 getBoundingClientRect 空指针异常')
        return true
      }
    }

    const handleRejection = (event) => {
      const msg = event.reason?.message || ''
      if (msg.includes('getBoundingClientRect')) {
        event.stopImmediatePropagation()
        event.preventDefault()
        return true
      }
    }

    // 使用 true 在捕获阶段拦截，确保早于任何其他监听器
    window.addEventListener('error', handleError, true)
    window.addEventListener('unhandledrejection', handleRejection, true)

    return () => {
      window.removeEventListener('error', handleError, true)
      window.removeEventListener('unhandledrejection', handleRejection, true)
    }
  }, [])

  const destroyAmis = () => {
    if (amisScopedRef.current) {
      try {
        if (typeof amisScopedRef.current.destroy === 'function') {
          amisScopedRef.current.destroy()
        }
      } catch (e) {}
      amisScopedRef.current = null
    }
    if (containerRef.current) {
      try { containerRef.current.innerHTML = '' } catch (e) {}
    }
  }

  const initAmis = async () => {
    if (!schema || !containerRef.current || !isMountedRef.current) return
    const currentVersion = ++initVersionRef.current

    const waitForAmis = () => {
      return new Promise((resolve) => {
        const check = () => {
          if (window.amis || window.amisRequire) resolve(true)
          else setTimeout(check, 50)
        }
        check()
      })
    }
    await waitForAmis()

    if (currentVersion !== initVersionRef.current) return
    if (!isMountedRef.current || !containerRef.current) return

    let embed = null
    if (window.amis && typeof window.amis.embed === 'function') {
      embed = window.amis.embed
    } else if (window.amisRequire) {
      const mod = window.amisRequire('amis/embed')
      if (mod && typeof mod === 'function') embed = mod
      else if (mod && mod.embed) embed = mod.embed
    }

    if (!embed || typeof embed !== 'function') return
    if (currentVersion !== initVersionRef.current) return

    destroyAmis()
    if (currentVersion !== initVersionRef.current || !containerRef.current) return

    let amisSchema = setFieldsReadOnly(schema, readonly)
    amisSchema = setTableSafeProps(amisSchema)

    await new Promise(resolve => requestAnimationFrame(resolve))
    await new Promise(resolve => requestAnimationFrame(resolve))

    if (currentVersion !== initVersionRef.current || !containerRef.current) return

    try {
      // ★★★ 核心修复：两步渲染法 ★★★
      // 第一步：先传空数据 embed，让表格骨架（thead/refs）安全挂载，不触发100+行的耗时渲染
      amisScopedRef.current = embed(containerRef.current, amisSchema, {
        locale: 'zh-CN',
        theme: 'cxd',
        data: {},  // 传空对象！
        readOnly: readonly,
        onChange: (val) => {
          if (!readonly && onChange) {
            isInternalChangeRef.current = true
            onChange(val)
          }
        }
      })
    } catch (e) {
      console.error('[AmISForm] embed failed:', e)
      return
    }

    // 第二步：等骨架稳定后（300ms），再注入100+行的真实数据
    await new Promise(resolve => setTimeout(resolve, 300))

    if (currentVersion !== initVersionRef.current) return
    if (!isMountedRef.current || !amisScopedRef.current) return

    try {
      if (value && Object.keys(value).length > 0) {
        amisScopedRef.current.updateProps({ data: value || {} })
      }
      prevValueRef.current = JSON.stringify(value || {})
    } catch (e) {
      console.warn('[AmISForm] initial data injection failed:', e)
    }
  }

  useEffect(() => {
    isMountedRef.current = true
    const schemaStr = JSON.stringify(schema || {})
    const readonlyStr = String(readonly)

    if (prevSchemaRef.current === schemaStr && prevReadonlyRef.current === readonlyStr && amisScopedRef.current) {
      return
    }

    prevSchemaRef.current = schemaStr
    prevReadonlyRef.current = readonlyStr
    initAmis()

    return () => {
      isMountedRef.current = false
      initVersionRef.current++
      destroyAmis()
    }
  }, [schema, readonly])

  useEffect(() => {
    if (isInternalChangeRef.current) {
      isInternalChangeRef.current = false
      prevValueRef.current = JSON.stringify(value || {})
      return
    }

    const valueStr = JSON.stringify(value || {})
    if (prevValueRef.current === valueStr) return
    prevValueRef.current = valueStr

    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current)

    debounceTimerRef.current = setTimeout(() => {
      if (!isMountedRef.current || !amisScopedRef.current) return

      requestAnimationFrame(() => {
        if (!isMountedRef.current || !amisScopedRef.current) return
        try {
          amisScopedRef.current.updateProps({ data: value || {} })
        } catch (e) {
          console.warn('[AmISForm] updateProps failed:', e)
        }
      })
    }, 300)

    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current)
    }
  }, [value])

  if (!schema) {
    return (
      <div style={{ width: '100%', minHeight: 100, padding: 20, color: '#86909C' }}>
        暂无表单数据
      </div>
    )
  }

  return (
    <div ref={containerRef} style={{ width: '100%', minHeight: 100 }} />
  )
}

export default AmISForm
