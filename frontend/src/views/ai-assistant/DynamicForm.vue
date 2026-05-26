<template>
  <div class="dynamic-form">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules || {}"
      label-position="top"
      class="form-content"
    >
      <template v-for="item in formItems" :key="item.prop">
        <!-- 表格组件 -->
        <template v-if="item.component === 'table'">
          <div class="form-section">
            <div class="section-header">
              <h3 class="section-title">{{ item.config.title }}</h3>
            </div>
            <el-table
              :data="formData[item.prop] || mockTableData"
              border
              stripe
              class="data-table"
            >
              <el-table-column
                v-for="(col, colKey) in getTableColumns(item.config)"
                :key="colKey"
                :prop="colKey"
                :label="col.title"
                :width="col.width"
              >
                <template #default="{ row }">
                  <span
                    class="cell-value"
                    :style="{ color: getCellColor(col, row[colKey]) }"
                  >
                    {{ formatCellValue(col, row[colKey]) }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>

        <!-- 汇总网格组件 -->
        <template v-else-if="item.component === 'summary-grid'">
          <div class="summary-grid">
            <el-card
              v-for="(metric, idx) in formData[item.prop] || mockSummaryData"
              :key="idx"
              class="summary-card"
            >
              <div class="metric-value" :style="{ color: getMetricColor(metric.color) }">
                {{ metric.value }}
              </div>
              <div class="metric-label">{{ metric.label }}</div>
            </el-card>
          </div>
        </template>

        <!-- 洞察框组件 -->
        <template v-else-if="item.component === 'insight-box'">
          <div class="insights">
            <div
              v-for="(insight, idx) in formData[item.prop] || mockInsights"
              :key="idx"
              class="insight-item"
            >
              <el-icon class="insight-icon"><InfoFilled /></el-icon>
              <span>{{ insight }}</span>
            </div>
          </div>
        </template>

        <!-- 标准表单项 -->
        <template v-else>
          <el-form-item :label="item.label" :prop="item.prop" :required="item.required">
            <el-input
              v-if="item.component === 'el-input'"
              v-model="formData[item.prop]"
              v-bind="item.props"
              :disabled="props.readonly"
              class="form-input"
            />
            <el-select
              v-else-if="item.component === 'el-select'"
              v-model="formData[item.prop]"
              v-bind="item.props"
              :disabled="props.readonly"
              class="form-select"
            >
              <el-option
                v-for="opt in getEnumOptions(item)"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <el-switch
              v-else-if="item.component === 'el-switch'"
              v-model="formData[item.prop]"
              :disabled="props.readonly"
            />
            <el-date-picker
              v-else-if="item.component === 'el-date-picker'"
              v-model="formData[item.prop]"
              v-bind="item.props"
              :disabled="props.readonly"
              class="form-date-picker"
            />
            <el-input-number
              v-else-if="item.component === 'el-input-number'"
              v-model="formData[item.prop]"
              v-bind="item.props"
              :disabled="props.readonly"
            />
          </el-form-item>
        </template>
      </template>
    </el-form>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { parseSchema, formatCurrency, getRateColor, formatTrend } from '@/utils/schemaParser'
import { InfoFilled } from '@element-plus/icons-vue'

const props = defineProps({
  schema: {
    type: Object,
    default: null
  },
  modelValue: {
    type: Object,
    default: () => ({})
  },
  readonly: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const formRef = ref(null)
const formData = ref({})
const formRules = ref({})

// Mock data for preview
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

watch(
  () => props.modelValue,
  (val) => {
    // Only update if the value is different to avoid circular updates
    if (JSON.stringify(val) !== JSON.stringify(formData.value)) {
      formData.value = { ...val }
    }
  },
  { immediate: true, deep: true }
)

watch(
  formData,
  (val) => {
    if (JSON.stringify(val) !== JSON.stringify(props.modelValue)) {
      emit('update:modelValue', val)
    }
  },
  { deep: true }
)

const formItems = ref([])

watch(
  () => props.schema,
  (schema) => {
    if (schema) {
      const parsed = parseSchema(schema)
      formItems.value = parsed
      const defaults = {}
      parsed.forEach(item => {
        if (item.config?.default !== undefined) {
          defaults[item.prop] = item.config.default
        }
      })
      // Only set formData if it's empty to avoid overwriting user input
      if (Object.keys(formData.value).length === 0) {
        formData.value = defaults
      }
    }
  },
  { immediate: true }
)

const getEnumOptions = (item) => {
  if (!item.config?.items?.enum) return []
  return item.config.items.enum.map(val => ({
    value: val,
    label: val
  }))
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
    blue: '#667eea',
    green: '#10B981',
    yellow: '#F59E0B',
    red: '#EF4444'
  }
  return colorMap[color] || '#667eea'
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

.dynamic-form {
  padding: 0;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

.form-section {
  margin-bottom: 20px;
  background: #fff;
  border-radius: 16px;
  border: 1px solid rgba(0, 0, 0, 0.04);
  overflow: hidden;
  transition: all 0.2s;
}

.form-section:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.section-header {
  margin-bottom: 0;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.04) 0%, rgba(118, 75, 162, 0.04) 100%);
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.section-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title::before {
  content: '';
  width: 4px;
  height: 16px;
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
  border-radius: 2px;
}

.data-table {
  border-radius: 0;
  overflow: hidden;
}

:deep(.data-table .el-table__header th) {
  background: #f8f9fb !important;
  color: #64748b;
  font-weight: 600;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 12px 16px !important;
}

:deep(.data-table .el-table__body td) {
  padding: 14px 16px !important;
  font-size: 0.9rem;
}

:deep(.data-table .el-table__row:hover td) {
  background: rgba(102, 126, 234, 0.04) !important;
}

.cell-value {
  font-weight: 500;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.summary-card {
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.04);
  text-align: center;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  background: #fff;
}

.summary-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  border-color: rgba(102, 126, 234, 0.2);
}

:deep(.summary-card .el-card__body) {
  padding: 24px 20px;
}

.metric-value {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
}

.metric-label {
  font-size: 0.8rem;
  color: #94a3b8;
  margin-top: 8px;
}

.insights {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.06) 0%, rgba(118, 75, 162, 0.06) 100%);
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 20px;
  border: 1px dashed rgba(102, 126, 234, 0.2);
}

.insight-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  font-size: 0.85rem;
  color: #64748b;
}

.insight-item:not(:last-child) {
  border-bottom: 1px solid rgba(102, 126, 234, 0.08);
}

.insight-icon {
  color: #667eea;
  font-size: 14px;
}

/* Form item styling - Card layout */
:deep(.el-form-item) {
  margin-bottom: 16px;
  padding: 16px 20px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.04);
  transition: all 0.2s;
}

:deep(.el-form-item:hover) {
  border-color: rgba(102, 126, 234, 0.15);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03);
}

:deep(.el-form-item__label) {
  font-size: 0.85rem;
  font-weight: 600;
  color: #1a1a2e;
  padding-bottom: 0;
}

:deep(.el-form-item__error) {
  font-size: 0.75rem;
  padding-top: 4px;
}

.form-input :deep(.el-input__wrapper),
.form-select :deep(.el-input__wrapper),
.form-date-picker :deep(.el-input__wrapper) {
  border-radius: 10px !important;
  border: 1px solid rgba(0, 0, 0, 0.08) !important;
  box-shadow: none !important;
  padding: 2px 12px !important;
}

.form-input :deep(.el-input__wrapper:hover),
.form-select :deep(.el-input__wrapper:hover),
.form-date-picker :deep(.el-input__wrapper:hover) {
  border-color: rgba(102, 126, 234, 0.5) !important;
}

.form-input :deep(.el-input__wrapper.is-focus),
.form-select :deep(.el-input__wrapper.is-focus),
.form-date-picker :deep(.el-input__wrapper.is-focus) {
  border-color: #667eea !important;
}

.form-input :deep(.el-input.is-disabled .el-input__wrapper),
.form-select :deep(.el-select.is-disabled .el-input__wrapper),
.form-date-picker :deep(.el-date-editor.is-disabled .el-input__wrapper) {
  background: #f5f5f5 !important;
  border-color: #e8e8e8 !important;
  opacity: 0.8;
}
</style>