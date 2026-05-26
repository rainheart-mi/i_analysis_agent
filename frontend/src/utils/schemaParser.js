/**
 * JSON Schema 解析工具
 * 将 JSON Schema 转换为 Element Plus 表单配置
 */

export function parseSchema(schema) {
  if (!schema || !schema.properties) {
    return []
  }

  return Object.entries(schema.properties).map(([key, prop]) => ({
    prop: key,
    label: prop.title || key,
    ...parseProperty(key, prop, schema)
  }))
}

function parseProperty(key, prop, schema) {
  const base = {
    required: schema.required?.includes(key) || false
  }

  // Handle ui:widget
  const widget = prop['ui:widget']
  const options = prop['ui:options'] || {}

  switch (widget) {
    case 'table':
      return { component: 'table', config: { ...prop, ...options } }
    case 'summary-grid':
      return { component: 'summary-grid', config: { ...prop, ...options } }
    case 'insight-box':
      return { component: 'insight-box', config: { ...prop, ...options } }
    case 'date-range-picker':
      return { component: 'el-date-picker', props: { type: 'daterange', ...options } }
    case 'date-picker':
      return { component: 'el-date-picker', props: { type: 'date', ...options } }
    case 'select':
      return { component: 'el-select', props: { ...options } }
    case 'switch':
      return { component: 'el-switch' }
    case 'radio':
      return { component: 'el-radio-group', props: { ...options } }
    case 'checkbox':
      return { component: 'el-checkbox-group', props: { ...options } }
    case 'input-number':
      return { component: 'el-input-number', props: { ...options } }
    case 'color-picker':
      return { component: 'el-color-picker', props: { ...options } }
    case 'slider':
      return { component: 'el-slider', props: { ...options } }
    case 'upload':
      return { component: 'el-upload', props: { ...options } }
    default:
      // Auto-detect based on type and format
      if (prop.type === 'array' && prop.items?.enum) {
        return { component: 'el-select', props: { multiple: true, ...options } }
      }
      if (prop.format === 'date-range') {
        return { component: 'el-date-picker', props: { type: 'daterange', ...options } }
      }
      if (prop.format === 'date') {
        return { component: 'el-date-picker', props: { type: 'date', ...options } }
      }
      if (prop.type === 'boolean') {
        return { component: 'el-switch' }
      }
      if (prop.type === 'number' || prop.type === 'integer') {
        return { component: 'el-input-number', props: { ...options } }
      }
      if (prop.enum) {
        return { component: 'el-select', props: { ...options } }
      }
      if (prop.format === 'textarea') {
        return { component: 'el-input', props: { type: 'textarea', ...options } }
      }
      return { component: 'el-input', props: { ...options } }
  }
}

/**
 * 格式化货币显示
 */
export function formatCurrency(value) {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY'
  }).format(value)
}

/**
 * 格式化达成率颜色
 */
export function getRateColor(rate) {
  if (rate >= 100) return '#10B981'
  if (rate >= 80) return '#F59E0B'
  return '#EF4444'
}

/**
 * 格式化趋势箭头
 */
export function formatTrend(value) {
  if (!value) return ''
  if (value > 0) return `↑${Math.abs(value).toFixed(1)}%`
  if (value < 0) return `↓${Math.abs(value).toFixed(1)}%`
  return '-'
}