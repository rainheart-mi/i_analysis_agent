import { useRef, useEffect, useImperativeHandle, forwardRef } from 'react'

/**
 * amis 6.x 钩子：每次请求前 mutate 配置。
 *
 * 本项目已配置 TOKEN_VALIDATION_ENABLED=false，后端不读 jwt header，
 * 这里不再注入 token（与 axios 拦截器 src/api/index.js 对齐）。
 *
 * ★ 关键：amis 6.x 的 embed(element, schema, props, envOptions) 签名中，
 *   requestAdaptor 必须放在 **第 4 个参数（envOptions）**，而不是 props。
 *   SDK 内部 O = __assign({...defaults}, envOptions) 构 env，props 不参与。
 *   SDK 源码 sdk.js:2741 的 k 函数读 r.requestAdaptor（r = envOptions）。
 */
const requestAdaptor = (api) => {
  // 临时诊断日志：确认 requestAdaptor 真的被调用，并打印注入前的 headers
  console.log('[AmISForm] requestAdaptor invoked', {
    url: api?.url,
    method: api?.method,
    inHeaders: api?.headers,
    tokenLen: token.length,
  })
  if (!token) return api
  return {
    ...api,
    headers: { ...(api.headers || {}), jwt: token },
  }
}

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

const AmISForm = forwardRef(function AmISForm({ schema, value, onChange, readonly }, ref) {
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

  // ★ pending schema：setSchema 调 initAmis 时用此变量传递 schema，
//   避免 initAmis 从 props 读 schema（流式渲染时 props.schema 为 null）
  const pendingSchemaRef = useRef(null)

  const initAmis = async (schemaOverride) => {
    const s = schemaOverride || schema
    if (!s || !containerRef.current || !isMountedRef.current) return
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

    let amisSchema = setFieldsReadOnly(s, readonly)
    amisSchema = setTableSafeProps(amisSchema)

    await new Promise(resolve => requestAnimationFrame(resolve))
    await new Promise(resolve => requestAnimationFrame(resolve))

    if (currentVersion !== initVersionRef.current || !containerRef.current) return

    try {
      // ★★★ 核心修复：两步渲染法 ★★★
      // 第一步：先传空数据 embed，让表格骨架（thead/refs）安全挂载，不触发100+行的耗时渲染
      const initialData = (value && Object.keys(value).length > 0) ? value : {}
      amisScopedRef.current = embed(containerRef.current, amisSchema, {
        locale: 'zh-CN',
        theme: 'cxd',
        data: initialData,
        readOnly: readonly,
        onChange: (val) => {
          if (!readonly && onChange) {
            isInternalChangeRef.current = true
            onChange(val)
          }
        }
      }, {
        // ★ 第 4 个参数 = env options：必须放这里才能被 amis 注入到 O.fetcher
        requestAdaptor,
      })
    } catch (e) {
      console.error('[AmISForm] embed failed:', e)
      return
    }

    // 第二步：等骨架稳定后（300ms），再注入100+行的真实数据
    // ★ 对 page 类型 schema（agent 自带 data 字段）跳过等待 —— 模板变量在 embed 时已就位，无需再 update
    const hasInitialData = value && Object.keys(value).length > 0
    if (!hasInitialData) {
      await new Promise(resolve => setTimeout(resolve, 300))
    }

    if (currentVersion !== initVersionRef.current) return
    if (!isMountedRef.current || !amisScopedRef.current) return

    try {
      if (hasInitialData) {
        // 幂等：与 embed 时传入的 data 相同，updateProps 不触发额外重渲染
        amisScopedRef.current.updateProps({ data: value || {} })
      }
      prevValueRef.current = JSON.stringify(value || {})
    } catch (e) {
      console.warn('[AmISForm] initial data injection failed:', e)
    }
  }

  // ★ 暴露 imperative API 给外部（如 SSE 流 Hook）做增量更新
  // 必须在 initAmis 定义之后，因为 setData/setSchema/reload 都要调用它
  useImperativeHandle(ref, () => ({
    /**
     * 增量更新 page.data。优先用 amis 6.x 原生 setData，
     * 降级用 updateProps({ data })。
     *
     * ★ 调用后必须同步 prevValueRef，否则 useEffect(value) 的 300ms debounce
     *   会再调一次 updateProps，导致双触发。
     */
    setData(patch) {
      const inst = amisScopedRef.current
      if (!inst) return false
      try {
        const baseData = inst.props?.data || {}
        if (typeof inst.setData === 'function') {
          inst.setData(patch)
        } else {
          // 降级：用 updateProps 合并现有 data
          inst.updateProps({ data: { ...baseData, ...patch } })
        }
        // 同步 prevValueRef 防 useEffect(value) 双触发
        prevValueRef.current = JSON.stringify({ ...baseData, ...patch })
        return true
      } catch (e) {
        console.warn('[AmISForm] setData failed:', e)
        return false
      }
    },

    /**
     * 整体替换 schema。强制 destroy + re-embed。
     * 仅在 artifact 事件触发完整 schema 切换时调用。
     *
     * ★ setSchema 是 async 操作（initAmis 内部有 2 个 RAF + 300ms 等待），
     *   与同一帧的 setData 可能竞态。调用方需自行处理顺序。
     */
    setSchema(newSchema) {
      // 流式渲染时 useAgentStream 传入的是数组 [schema1, schema2, ...]，
      // 需转换为 amis 能识别的单 schema 对象：
      //   - 1 个 schema → 直接使用
      //   - 多个 schema → 包装为 tabs 容器
      let schemaToUse = newSchema
      if (Array.isArray(newSchema)) {
        if (newSchema.length === 1) {
          schemaToUse = newSchema[0]
        } else {
          schemaToUse = {
            type: 'tabs',
            tabsMode: 'chrome',
            className: 'artifact-tabs',
            contentClassName: 'artifact-tabs-content',
            tabs: newSchema.map((s, i) => ({
              title: s.title || `报告 ${i + 1}`,
              body: s.type ? s : (s.body || s),
            })),
          }
        }
      }
      prevSchemaRef.current = null  // 强制 initAmis 跳过 prevSchemaRef 短路
      prevReadonlyRef.current = null
      pendingSchemaRef.current = schemaToUse
      initAmis(schemaToUse)
    },

    /** 强制重新嵌入（极少用） */
    reload() {
      initAmis()
    },
  }), [])

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

  return (
    <div ref={containerRef} style={{ width: '100%', minHeight: 100, overflowX: 'auto' }} />
  )
})

export default AmISForm
