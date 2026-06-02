# Amis 表单渲染替换实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Vue 3 项目的 DynamicForm.vue 替换为百度 amis 低代码框架，使用 amis JSON 格式存储 Schema

**Architecture:** 新增 AmISForm.vue 组件，使用 amis/embed SDK 渲染表单。重写所有 Schema 文件为 amis 格式。替换现有引用。

**Tech Stack:** amis SDK, Vue 3, JSON Schema → amis JSON

---

## 文件结构

```
frontend/src/views/ai-assistant/
├── DynamicForm.vue        → 废弃（保留备份）
├── AmISForm.vue          → 新增（amis渲染器）

backend/schemas/
├── intent_forms/demo/
│   └── intent_schema.json  → 重写为 amis 格式
└── artifact_forms/demo/
    └── artifact_schema.json → 重写为 amis 格式
```

---

### Task 1: 创建 AmISForm.vue 组件

**Files:**
- Create: `frontend/src/views/ai-assistant/AmISForm.vue`

- [ ] **Step 1: 创建基础 amis 渲染组件**

```vue
<template>
  <div ref="amisRef" class="amis-form-container"></div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import axios from 'axios'

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
const amisRef = ref(null)
let amisInstance = null

onMounted(() => {
  initAmis()
})

const initAmis = async () => {
  const { embed } = await import('amis')
  const { fetchWriter } = await import('@/api/workflow')
  
  amisInstance = embed(amisRef.value, buildAmisSchema(), {
    locale: 'zh-CN',
    data: props.modelValue,
    readOnly: props.readonly,
    props: {
      // amis 环境配置
    }
  })
}

const buildAmisSchema = () => {
  if (!props.schema) return null
  // 直接使用 props.schema 作为 amis JSON
  return {
    ...props.schema,
    // 如果是表单模式且 readonly，添加静态展示模式
    ...(props.readonly && props.schema.type === 'form' 
      ? { mode: 'readonly' } 
      : {})
  }
}

// 监听 schema 变化
watch(() => props.schema, async (schema) => {
  if (schema && amisRef.value) {
    amisInstance?.updateProps(buildAmisSchema())
  }
}, { immediate: true })

// 监听数据变化
watch(() => props.modelValue, (val) => {
  amisInstance?.updateProps({ data: val })
}, { deep: true })
</script>

<style scoped>
.amis-form-container {
  padding: 20px;
}
</style>
```

- [ ] **Step 2: 运行测试验证**

Build frontend: `cd frontend && npm run build`
Expected: 无语法错误，amis SDK 正常加载

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/ai-assistant/AmISForm.vue
git commit -m "feat: add AmISForm.vue amis renderer component"
```

---

### Task 2: 重写 Intent Schema 为 amis 格式

**Files:**
- Modify: `backend/schemas/intent_forms/demo/intent_schema.json`

**原格式 (JSON Schema):**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "category": { "type": "string", "title": "品类" },
    "date_range": { "type": "string", "title": "日期范围" },
    "export_format": { "type": "string", "title": "导出格式", "enum": ["xlsx", "pdf", "csv"] }
  }
}
```

- [ ] **Step 1: 重写为 amis JSON 格式**

```json
{
  "type": "form",
  "mode": "horizontal",
  "wrapWithPanel": false,
  "body": [
    {
      "type": "select",
      "name": "category",
      "label": "品类",
      "placeholder": "选择要分析的品类",
      "options": [
        { "label": "生鲜食品", "value": "fresh" },
        { "label": "烘焙", "value": "baking" },
        { "label": "蔬菜", "value": "vegetable" }
      ],
      "required": true
    },
    {
      "type": "input-date-range",
      "name": "date_range",
      "label": "日期范围",
      "required": true
    },
    {
      "type": "select",
      "name": "export_format",
      "label": "导出格式",
      "options": [
        { "label": "Excel (.xlsx)", "value": "xlsx" },
        { "label": "PDF (.pdf)", "value": "pdf" },
        { "label": "CSV (.csv)", "value": "csv" }
      ],
      "value": "xlsx"
    }
  ]
}
```

- [ ] **Step 2: 提交**

```bash
git add backend/schemas/intent_forms/demo/intent_schema.json
git commit -m "refactor: convert intent_schema.json to amis format"
```

---

### Task 3: 重写 Artifact Schema 为 amis 格式

**Files:**
- Modify: `backend/schemas/artifact_forms/demo/artifact_schema.json`

**原格式 (JSON Schema):**
```json
{
  "properties": {
    "summary_metrics": { "type": "array", "ui:widget": "summary-grid" },
    "sales_report": { "type": "array", "ui:widget": "table" },
    "weekly_trend": { "type": "array", "ui:widget": "table" },
    "insights": { "type": "array", "ui:widget": "insight-box" }
  }
}
```

- [ ] **Step 1: 重写为 amis JSON 格式**

```json
{
  "type": "service",
  "body": [
    {
      "type": "grid",
      "columns": [
        {
          "body": [
            {
              "type": "static",
              "tpl": "<span class='metric-value' style='color:#667eea'>${summary_metrics|raw|pickBy:item.value}</span>",
              "label": "分析品类数"
            }
          ]
        },
        {
          "body": [
            {
              "type": "static",
              "tpl": "<span class='metric-value' style='color:#10B981'>${sales_rate|pickBy:item.value|default:0}%</span>",
              "label": "销售达成"
            }
          ]
        }
      ]
    },
    {
      "type": "table",
      "name": "sales_report",
      "label": "表1：大类销售额/毛利额预算达成情况",
      "columns": [
        { "label": "排名", "name": "rank", "width": 60 },
        { "label": "大类", "name": "category" },
        { "label": "销售实际", "name": "sales_actual", "type": "number" },
        { "label": "销售预算", "name": "sales_budget", "type": "number" },
        { "label": "销售达成率", "name": "sales_rate", "type": "number" },
        { "label": "毛利实际", "name": "profit_actual", "type": "number" },
        { "label": "毛利预算", "name": "profit_budget", "type": "number" },
        { "label": "毛利达成率", "name": "profit_rate", "type": "number" }
      ]
    },
    {
      "type": "table",
      "name": "weekly_trend",
      "label": "表2：大类周环比趋势",
      "columns": [
        { "label": "大类", "name": "category" },
        { "label": "周期", "name": "period" },
        { "label": "周销售额", "name": "sales", "type": "number" },
        { "label": "环比", "name": "trend" }
      ]
    },
    {
      "type": "plain",
      "label": "关键洞察",
      "body": [
        {
          "type": "list",
          "name": "insights",
          "items": [
            { "type": "tpl", "tpl": "${insight}" }
          ]
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: 提交**

```bash
git add backend/schemas/artifact_forms/demo/artifact_schema.json
git commit -m "refactor: convert artifact_schema.json to amis format"
```

---

### Task 4: 替换 NodeContent.vue 引用

**Files:**
- Modify: `frontend/src/views/ai-assistant/NodeContent.vue:14-18`

- [ ] **Step 1: 替换 DynamicForm 为 AmISForm**

修改 import:
```javascript
// 旧
import DynamicForm from './DynamicForm.vue'

// 新
import AmISForm from './AmISForm.vue'
```

修改使用处:
```vue
<!-- 旧 -->
<dynamic-form
  ref="intentFormRef"
  :schema="intentSchema"
  v-model="intentFormData"
  :readonly="isNodeExecuted"
/>

<!-- 新 -->
<am-i-s-form
  ref="intentFormRef"
  :schema="intentSchema"
  v-model="intentFormData"
  :readonly="isNodeExecuted"
/>
```

同样替换 artifact 部分:
```vue
<!-- 旧 -->
<dynamic-form
  :schema="artifactSchema"
  :model-value="artifactFormData"
  readonly
/>

<!-- 新 -->
<am-i-s-form
  :schema="artifactSchema"
  :model-value="artifactFormData"
  readonly
/>
```

- [ ] **Step 2: 运行测试验证**

```bash
cd frontend && npm run build
```
Expected: 无编译错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/ai-assistant/NodeContent.vue
git commit -m "refactor: replace DynamicForm with AmISForm in NodeContent"
```

---

### Task 5: 替换 IntentFormPreview.vue 引用

**Files:**
- Modify: `frontend/src/views/ai-assistant/IntentFormPreview.vue:41`

- [ ] **Step 1: 替换 DynamicForm 为 AmISForm**

修改 import 和使用处（参照 Task 4）

- [ ] **Step 2: 提交**

```bash
git add frontend/src/views/ai-assistant/IntentFormPreview.vue
git commit -m "refactor: replace DynamicForm with AmISForm in IntentFormPreview"
```

---

### Task 6: 删除或归档原 DynamicForm.vue

**Files:**
- Archive: `frontend/src/views/ai-assistant/DynamicForm.vue` → `frontend/src/views/ai-assistant/DynamicForm.vue.bak`

- [ ] **Step 1: 移动文件**

```bash
mv frontend/src/views/ai-assistant/DynamicForm.vue frontend/src/views/ai-assistant/DynamicForm.vue.bak
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/views/ai-assistant/DynamicForm.vue.bak
git rm frontend/src/views/ai-assistant/DynamicForm.vue
git commit -m "refactor: archive original DynamicForm.vue"
```

---

## 自查清单

- [ ] 所有 Schema 文件已转换为 amis 格式
- [ ] AmISForm.vue 正确渲染 intent 表单
- [ ] AmISForm.vue 正确渲染 artifact 展示
- [ ] readonly 模式正常生效
- [ ] NodeContent.vue 和 IntentFormPreview.vue 引用已替换
- [ ] 前后端联调测试通过