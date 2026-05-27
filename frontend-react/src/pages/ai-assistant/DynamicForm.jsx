import { useState, useEffect, useRef } from 'react'
import { Table, Card, Typography, Input, Select, Switch, DatePicker, InputNumber, Tag } from 'antd'
import { InfoCircleOutlined } from '@ant-design/icons'
import { parseSchema, formatCurrency, getRateColor, formatTrend } from '@/utils/schemaParser'

const { Text } = Typography

const mockTableData = [
  { rank: 1, category: '3R熟食', sales_actual: 21660, sales_budget: 23349, sales_rate: 92.8, profit_actual: 3810, profit_budget: 3035, profit_rate: 125.5 },
  { rank: 2, category: '烘焙', sales_actual: 48348, sales_budget: 61366, sales_rate: 78.8, profit_actual: 7821, profit_budget: 14430, profit_rate: 54.2 },
  { rank: 3, category: '蔬菜', sales_actual: 204489, sales_budget: 270754, sales_rate: 75.5, profit_actual: 41376, profit_budget: 54151, profit_rate: 76.4 }
]

const mockSummaryData = [
  { label: '分析品类数', value: '15', color: 'blue' },
  { label: '销售达成100%', value: '0', color: 'green' },
  { label: '达成率均值', value: '57.2%', color: 'yellow' },
  { label: '待提升品类', value: '15', color: 'red' }
]

const mockInsights = [
  '点击大类名称可下钻到商品明细分析',
  '销售达成率100%以上为绿色，80-100%为黄色，80%以下为红色',
  '周环比：上升箭头绿色，下降箭头红色'
]

function DynamicForm({ schema, modelValue, readonly = false, onChange }) {
  const [formData, setFormData] = useState({})
  const formItems = parseSchema(schema || {})

  useEffect(() => {
    if (modelValue && typeof modelValue === 'object') {
      setFormData(modelValue)
    }
  }, [modelValue])

  const handleChange = (prop, value) => {
    const newData = { ...formData, [prop]: value }
    setFormData(newData)
    onChange?.(newData)
  }

  const getEnumOptions = (item) => {
    if (!item.config?.items?.enum) return []
    return item.config.items.enum.map(val => ({ value: val, label: val }))
  }

  const getTableColumns = (config) => {
    if (!config.items?.properties) return {}
    return config.items.properties
  }

  const getCellColor = (col, value) => {
    if (col['ui:widget'] === 'rate-color') {
      return getRateColor(value)
    }
    return null
  }

  const formatCellValue = (col, value) => {
    if (col['ui:widget'] === 'currency') {
      return formatCurrency(value)
    }
    if (col['ui:widget'] === 'trend-arrow') {
      return formatTrend(value)
    }
    if (col['ui:widget'] === 'rate-color') {
      return `${value}%`
    }
    return value
  }

  const getMetricColor = (color) => {
    const colorMap = {
      blue: '#5C7CFF',
      green: '#52C41A',
      yellow: '#FAAD14',
      red: '#FF4D4F'
    }
    return colorMap[color] || '#5C7CFF'
  }

  const renderFormItem = (item) => {
    const value = formData[item.prop]

    switch (item.component) {
      case 'table':
        const tableData = formData[item.prop] || mockTableData
        const columns = getTableColumns(item.config) || {}

        return (
          <Card
            key={item.prop}
            size="small"
            style={{ marginBottom: 20, borderRadius: 12, border: '1px solid #E5E6EB' }}
            title={
              <span style={{ fontWeight: 600, fontSize: '14px' }}>{item.config.title}</span>
            }
          >
            <Table
              dataSource={tableData}
              columns={Object.entries(columns).map(([colKey, col]) => ({
                title: col.title,
                dataIndex: colKey,
                key: colKey,
                width: col.width,
                render: (val) => (
                  <span style={{ color: getCellColor(col, val), fontWeight: 500 }}>
                    {formatCellValue(col, val)}
                  </span>
                )
              }))}
              pagination={false}
              rowKey="rank"
              size="small"
            />
          </Card>
        )

      case 'summary-grid':
        const metrics = formData[item.prop] || mockSummaryData
        return (
          <div key={item.prop} style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
            {metrics.map((metric, idx) => (
              <Card key={idx} style={{ borderRadius: 12, textAlign: 'center', border: '1px solid #E5E6EB' }} bodyStyle={{ padding: 24 }}>
                <div style={{ fontSize: '2rem', fontWeight: 700, color: getMetricColor(metric.color), lineHeight: 1.2 }}>
                  {metric.value}
                </div>
                <div style={{ fontSize: '13px', color: '#86909C', marginTop: 8 }}>{metric.label}</div>
              </Card>
            ))}
          </div>
        )

      case 'insight-box':
        const insights = formData[item.prop] || mockInsights
        return (
          <Card
            key={item.prop}
            size="small"
            style={{
              marginBottom: 20,
              borderRadius: 12,
              background: '#F0F1FF',
              border: '1px dashed #7B91FF'
            }}
            bodyStyle={{ padding: 12 }}
          >
            {insights.map((insight, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0' }}>
                <InfoCircleOutlined style={{ color: '#5C7CFF', fontSize: 14 }} />
                <Text style={{ color: '#4E5969', fontSize: '14px' }}>{insight}</Text>
              </div>
            ))}
          </Card>
        )

      case 'input':
        return (
          <Card key={item.prop} style={{ marginBottom: 16, borderRadius: 12, border: '1px solid #E5E6EB' }} bodyStyle={{ padding: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 500, color: '#1D2129' }}>{item.label}</div>
            <Input
              value={value || ''}
              onChange={(e) => handleChange(item.prop, e.target.value)}
              disabled={readonly}
              placeholder={item.config?.placeholder || ''}
              style={{ borderRadius: 8 }}
            />
          </Card>
        )

      case 'textarea':
        return (
          <Card key={item.prop} style={{ marginBottom: 16, borderRadius: 12, border: '1px solid #E5E6EB' }} bodyStyle={{ padding: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 500, color: '#1D2129' }}>{item.label}</div>
            <Input.TextArea
              value={value || ''}
              onChange={(e) => handleChange(item.prop, e.target.value)}
              disabled={readonly}
              placeholder={item.config?.placeholder || ''}
              rows={3}
              style={{ borderRadius: 8 }}
            />
          </Card>
        )

      case 'select':
        return (
          <Card key={item.prop} style={{ marginBottom: 16, borderRadius: 12, border: '1px solid #E5E6EB' }} bodyStyle={{ padding: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 500, color: '#1D2129' }}>{item.label}</div>
            <Select
              value={value}
              onChange={(val) => handleChange(item.prop, val)}
              disabled={readonly}
              options={getEnumOptions(item)}
              placeholder={item.config?.placeholder || '请选择'}
              style={{ width: '100%', borderRadius: 8 }}
            />
          </Card>
        )

      case 'switch':
        return (
          <Card key={item.prop} style={{ marginBottom: 16, borderRadius: 12, border: '1px solid #E5E6EB' }} bodyStyle={{ padding: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontWeight: 500, color: '#1D2129' }}>{item.label}</span>
              <Switch
                checked={value}
                onChange={(checked) => handleChange(item.prop, checked)}
                disabled={readonly}
              />
            </div>
          </Card>
        )

      case 'input-number':
        return (
          <Card key={item.prop} style={{ marginBottom: 16, borderRadius: 12, border: '1px solid #E5E6EB' }} bodyStyle={{ padding: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 500, color: '#1D2129' }}>{item.label}</div>
            <InputNumber
              value={value}
              onChange={(val) => handleChange(item.prop, val)}
              disabled={readonly}
              style={{ width: '100%', borderRadius: 8 }}
              {...item.props}
            />
          </Card>
        )

      case 'date-picker':
        return (
          <Card key={item.prop} style={{ marginBottom: 16, borderRadius: 12, border: '1px solid #E5E6EB' }} bodyStyle={{ padding: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 500, color: '#1D2129' }}>{item.label}</div>
            <DatePicker
              value={value}
              onChange={(date) => handleChange(item.prop, date)}
              disabled={readonly}
              style={{ width: '100%', borderRadius: 8 }}
              {...item.props}
            />
          </Card>
        )

      case 'range-picker':
        return (
          <Card key={item.prop} style={{ marginBottom: 16, borderRadius: 12, border: '1px solid #E5E6EB' }} bodyStyle={{ padding: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 500, color: '#1D2129' }}>{item.label}</div>
            <DatePicker.RangePicker
              value={value}
              onChange={(dates) => handleChange(item.prop, dates)}
              disabled={readonly}
              style={{ width: '100%', borderRadius: 8 }}
              {...item.props}
            />
          </Card>
        )

      default:
        return (
          <Card key={item.prop} style={{ marginBottom: 16, borderRadius: 12, border: '1px solid #E5E6EB' }} bodyStyle={{ padding: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 500, color: '#1D2129' }}>{item.label}</div>
            <Input
              value={value || ''}
              onChange={(e) => handleChange(item.prop, e.target.value)}
              disabled={readonly}
              style={{ borderRadius: 8 }}
            />
          </Card>
        )
    }
  }

  return (
    <div style={{ fontFamily: "'Geist', -apple-system, sans-serif" }}>
      {formItems.map(item => renderFormItem(item))}
    </div>
  )
}

export default DynamicForm