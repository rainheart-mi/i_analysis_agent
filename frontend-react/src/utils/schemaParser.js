/**
 * JSON Schema 解析工具
 * 将 JSON Schema 转换为 Ant Design 表单配置
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
      return { component: 'range-picker', props: { ...options } }
    case 'date-picker':
      return { component: 'date-picker', props: { ...options } }
    case 'select':
      return { component: 'select', props: { ...options } }
    case 'switch':
      return { component: 'switch' }
    case 'radio':
      return { component: 'radio-group', props: { ...options } }
    case 'checkbox':
      return { component: 'checkbox-group', props: { ...options } }
    case 'input-number':
      return { component: 'input-number', props: { ...options } }
    case 'color-picker':
      return { component: 'color-picker', props: { ...options } }
    case 'slider':
      return { component: 'slider', props: { ...options } }
    case 'upload':
      return { component: 'upload', props: { ...options } }
    default:
      if (prop.type === 'array' && prop.items?.enum) {
        return { component: 'select', props: { mode: 'multiple', ...options } }
      }
      if (prop.format === 'date-range') {
        return { component: 'range-picker', props: { ...options } }
      }
      if (prop.format === 'date') {
        return { component: 'date-picker', props: { ...options } }
      }
      if (prop.type === 'boolean') {
        return { component: 'switch' }
      }
      if (prop.type === 'number' || prop.type === 'integer') {
        return { component: 'input-number', props: { ...options } }
      }
      if (prop.enum) {
        return { component: 'select', props: { ...options } }
      }
      if (prop.format === 'textarea') {
        return { component: 'textarea', props: { ...options } }
      }
      return { component: 'input', props: { ...options } }
  }
}

export function formatCurrency(value) {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY'
  }).format(value)
}

export function getRateColor(rate) {
  if (rate >= 100) return '#52C41A'
  if (rate >= 80) return '#FAAD14'
  return '#FF4D4F'
}

export function formatTrend(value) {
  if (!value) return '-'
  if (value > 0) return `↑${Math.abs(value).toFixed(1)}%`
  if (value < 0) return `↓${Math.abs(value).toFixed(1)}%`
  return '-'
}