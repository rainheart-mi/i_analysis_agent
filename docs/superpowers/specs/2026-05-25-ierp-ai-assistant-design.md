# IERP AI Assistant 工作流配置系统设计文档

**日期**: 2026-05-25
**版本**: 1.0
**状态**: 待用户评审

---

## 1. 项目概述

### 1.1 项目背景

基于 IERP_Orchestrator 架构图，构建一个企业级 AI 助手系统，核心功能是通过可视化配置将 N8N 工作流与 AI 对话界面连接起来，实现"对话驱动式"的 ERP 操作体验。

### 1.2 核心功能

1. **工作流路由配置**：管理 AI 助手可调用的工作流入口（标题、描述）
2. **工作流节点映射配置**：建立工作流路由与 N8N 内部节点的映射关系
3. **意图澄清表单配置**：通过 JSON Schema 定义工作流执行前的用户交互表单
4. **生成物表单草稿配置**：通过 JSON Schema 定义工作流执行后的结果展示表单
5. **N8N 环境配置**：支持多套 N8N 环境（开发、测试、生产）
6. **AI 对话界面**：三栏式布局，右侧对话面板 + 中央画布区域

### 1.3 技术栈

| 层级 | 技术选型 |
|------|----------|
| 后端 | Python 3.11+ / FastAPI |
| 前端 | Vue 3 + Element Plus |
| 数据库 | MySQL / PostgreSQL |
| 文件存储 | JSON Schema 文件（文件系统） |
| 工作流引擎 | N8N（通过 REST API 调用） |
| 认证 | JWT Token |

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Vue 3 Frontend                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  侧边菜单栏  │  │  中央画布   │  │    AI 对话面板      │  │
│  │            │  │ (动态表单)  │  │  (工作流选择+对话)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                           │ HTTP/REST
┌──────────────────────────▼────────────────────────────────┐
│                    FastAPI Backend                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ 工作流配置API │  │  执行引擎   │  │    认证模块      │  │
│  │ (CRUD)       │  │ (调用N8N)   │  │   (JWT)         │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│           │                              │                 │
│  ┌────────▼────────┐        ┌────────────▼─────────────┐   │
│  │   MySQL DB      │        │    JSON Schema Files    │   │
│  │  (配置元数据)   │        │   (表单模板存储)         │   │
│  └─────────────────┘        └─────────────────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼────────────────────────────────┐
│                      N8N Server                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Workflow 1  │  Workflow 2  │  ...      │    │
│  └─────────────────────────────────────────────────────┘    │
│  Webhook: POST /webhook/workflow-execute                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块职责

| 模块 | 职责 |
|------|------|
| `workflow_routes` | 管理工作流入口列表，供 AI 对话面板展示 |
| `workflow_node_mappings` | 存储工作流路由与 N8N Node ID 的映射 |
| `intent_forms` | 管理意图澄清表单的 JSON Schema 文件路径 |
| `artifact_forms` | 管理生成物表单的 JSON Schema 文件路径 |
| `n8n_environments` | 管理 N8N 环境配置（URL、认证信息） |
| `ai_executor` | 接收用户意图 → 选择工作流 → 调用 N8N → 返回结果 |

---

## 3. 数据库设计

### 3.1 ER 图

```
┌─────────────────────┐     ┌─────────────────────┐
│  n8n_environments   │     │    workflow_routes   │
├─────────────────────┤     ├─────────────────────┤
│ id (PK)             │     │ id (PK)             │
│ name                │◄────│ environment_id (FK) │
│ base_url            │     │ title               │
│ api_key             │     │ description         │
│ is_active           │     │ is_active           │
│ created_at          │     │ created_at          │
└─────────────────────┘     │ updated_at          │
                            └─────────┬───────────┘
                                      │
                          ┌──────────▼───────────┐
                          │workflow_node_mappings│
                          ├──────────────────────┤
                          │ id (PK)              │
                          │ route_id (FK)        │────┐
                          │ node_id              │    │
                          │ intent_schema_path   │    │
                          │ artifact_schema_path│    │
                          │ config (JSON)       │    │
                          │ created_at          │    │
                          └─────────────────────┘    │
                                                    │
                          ┌─────────────────────┐    │
                          │  JSON Schema Files   │◄───┘
                          ├─────────────────────┤
                          │ intent_forms/       │
                          │   {route_id}/       │
                          │     intent_schema.json
                          │ artifact_forms/     │
                          │   {route_id}/       │
                          │     artifact_schema.json
                          └─────────────────────┘
```

### 3.2 表结构 SQL

```sql
-- N8N 环境配置表
CREATE TABLE n8n_environments (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL COMMENT '环境名称，如：生产环境',
    base_url VARCHAR(500) NOT NULL COMMENT 'N8N 服务地址',
    api_key VARCHAR(255) COMMENT 'N8N API Key',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 工作流路由表（工作流入口）
CREATE TABLE workflow_routes (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    environment_id VARCHAR(36) NOT NULL COMMENT '关联的N8N环境',
    title VARCHAR(200) NOT NULL COMMENT '工作流标题',
    description TEXT COMMENT '工作流描述',
    n8n_workflow_id VARCHAR(100) COMMENT 'N8N Workflow ID',
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (environment_id) REFERENCES n8n_environments(id)
);

-- 工作流节点映射表
CREATE TABLE workflow_node_mappings (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    route_id VARCHAR(36) NOT NULL COMMENT '关联的工作流路由',
    node_id VARCHAR(100) NOT NULL COMMENT 'N8N 节点ID',
    node_name VARCHAR(200) COMMENT '节点名称',
    intent_schema_path VARCHAR(500) COMMENT '意图澄清表单 JSON Schema 文件路径',
    artifact_schema_path VARCHAR(500) COMMENT '生成物表单 JSON Schema 文件路径',
    input_mapping JSON COMMENT '输入字段映射配置',
    output_mapping JSON COMMENT '输出字段映射配置',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (route_id) REFERENCES workflow_routes(id) ON DELETE CASCADE
);

-- 用户表（简化版）
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 操作审计日志表
CREATE TABLE operation_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(36),
    route_id VARCHAR(36),
    action VARCHAR(50) COMMENT 'execute, configure, etc.',
    request_payload JSON,
    response_payload JSON,
    status VARCHAR(20) COMMENT 'success, failed',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## 4. API 设计

### 4.1 认证 API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/auth/login` | 用户登录，返回 JWT Token |
| POST | `/api/v1/auth/refresh` | 刷新 Token |
| GET | `/api/v1/auth/me` | 获取当前用户信息 |

### 4.2 N8N 环境 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/n8n-environments` | 获取所有环境 |
| POST | `/api/v1/n8n-environments` | 创建环境 |
| GET | `/api/v1/n8n-environments/{id}` | 获取单个环境 |
| PUT | `/api/v1/n8n-environments/{id}` | 更新环境 |
| DELETE | `/api/v1/n8n-environments/{id}` | 删除环境 |
| POST | `/api/v1/n8n-environments/{id}/test` | 测试连接 |

### 4.3 工作流路由 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/workflows` | 获取所有工作流路由 |
| POST | `/api/v1/workflows` | 创建工作流路由 |
| GET | `/api/v1/workflows/{id}` | 获取单个工作流路由 |
| PUT | `/api/v1/workflows/{id}` | 更新工作流路由 |
| DELETE | `/api/v1/workflows/{id}` | 删除工作流路由 |
| GET | `/api/v1/workflows/{id}/intents` | 获取意图澄清表单 Schema |
| GET | `/api/v1/workflows/{id}/artifacts` | 获取生成物表单 Schema |

### 4.4 工作流节点映射 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/workflows/{route_id}/mappings` | 获取节点映射列表 |
| POST | `/api/v1/workflows/{route_id}/mappings` | 创建节点映射 |
| PUT | `/api/v1/mappings/{id}` | 更新节点映射 |
| DELETE | `/api/v1/mappings/{id}` | 删除节点映射 |

### 4.5 执行 API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/execute/{route_id}` | 执行工作流 |
| GET | `/api/v1/execute/{route_id}/status/{task_id}` | 查询执行状态 |
| POST | `/api/v1/execute/{route_id}/preview` | 预览工作流输入 |

### 4.6 请求/响应示例

**POST `/api/v1/execute/{route_id}`**

Request:
```json
{
  "user_id": "user-123",
  "inputs": {
    "product_name": "iPhone 15",
    "date_range": "2024-01-01 to 2024-12-31"
  }
}
```

Response:
```json
{
  "task_id": "task-456",
  "status": "pending",
  "message": "工作流已提交执行"
}
```

---

## 5. JSON Schema 表单设计

### 5.1 意图澄清表单 Schema 示例

文件路径: `schemas/intent_forms/{route_id}/intent_schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "product_name": {
      "type": "string",
      "title": "商品名称",
      "description": "请输入要查询的商品名称"
    },
    "date_range": {
      "type": "string",
      "title": "日期范围",
      "format": "date-range",
      "ui:widget": "date-range-picker"
    },
    "export_format": {
      "type": "string",
      "title": "导出格式",
      "enum": ["xlsx", "pdf", "csv"],
      "default": "xlsx"
    }
  },
  "required": ["product_name"]
}
```

### 5.2 生成物表单 Schema 示例

文件路径: `schemas/artifact_forms/{route_id}/artifact_schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "sales_report": {
      "type": "object",
      "title": "销售报告",
      "properties": {
        "total_revenue": {
          "type": "number",
          "title": "总收入"
        },
        "order_count": {
          "type": "integer",
          "title": "订单数量"
        },
        "top_products": {
          "type": "array",
          "title": "热销商品",
          "items": {
            "type": "object",
            "properties": {
              "name": { "type": "string" },
              "count": { "type": "integer" }
            }
          }
        }
      }
    },
    "chart_url": {
      "type": "string",
      "format": "uri",
      "title": "图表链接"
    }
  }
}
```

### 5.4 生成物表格 Schema 扩展示例

文件路径: `schemas/artifact_forms/{route_id}/artifact_schema.json`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "summary_metrics": {
      "type": "array",
      "title": "汇总指标",
      "ui:widget": "summary-grid",
      "items": {
        "type": "object",
        "properties": {
          "label": { "type": "string", "title": "指标名称" },
          "value": { "type": "string", "title": "指标值" },
          "color": { "type": "string", "enum": ["blue", "green", "yellow", "red"], "title": "颜色" }
        }
      }
    },
    "sales_report": {
      "type": "array",
      "title": "表1：大类销售额/毛利额预算达成情况",
      "ui:widget": "table",
      "items": {
        "type": "object",
        "properties": {
          "rank": { "type": "integer", "title": "排名" },
          "category": { "type": "string", "title": "大类", "ui:widget": "link" },
          "sales_actual": { "type": "number", "title": "销售实际", "ui:widget": "currency" },
          "sales_budget": { "type": "number", "title": "销售预算", "ui:widget": "currency" },
          "sales_rate": { "type": "number", "title": "销售达成率", "ui:widget": "rate-color" },
          "profit_actual": { "type": "number", "title": "毛利实际", "ui:widget": "currency" },
          "profit_budget": { "type": "number", "title": "毛利预算", "ui:widget": "currency" },
          "profit_rate": { "type": "number", "title": "毛利达成率", "ui:widget": "rate-color" }
        }
      }
    },
    "weekly_trend": {
      "type": "array",
      "title": "表2：大类周环比趋势",
      "ui:widget": "table",
      "ui:options": {
        "spanMethod": "rowspan"
      },
      "items": {
        "type": "object",
        "properties": {
          "category": { "type": "string", "title": "大类", "ui:widget": "row-header" },
          "period": { "type": "string", "title": "周期", "enum": ["本周", "上周"] },
          "sales": { "type": "number", "title": "周销售额" },
          "trend": { "type": "string", "title": "环比", "ui:widget": "trend-arrow" }
        }
      }
    },
    "insights": {
      "type": "array",
      "title": "关键洞察",
      "ui:widget": "insight-box",
      "items": {
        "type": "string"
      }
    }
  }
}
```

### 5.5 ui:widget 完整类型映射

| ui:widget | Element Plus 组件 | 说明 |
|-----------|-------------------|------|
| `input` | ElInput | 单行文本输入 |
| `textarea` | ElInput type="textarea" | 多行文本 |
| `date-picker` | ElDatePicker | 日期选择 |
| `date-range-picker` | ElDatePicker type="daterange" | 日期范围 |
| `time-picker` | ElTimePicker | 时间选择 |
| `select` | ElSelect | 下拉选择 |
| `radio` | ElRadioGroup | 单选组 |
| `checkbox` | ElCheckboxGroup | 多选组 |
| `switch` | ElSwitch | 开关 |
| `slider` | ElSlider | 滑块 |
| `input-number` | ElInputNumber | 数字输入 |
| `color-picker` | ElColorPicker | 颜色选择 |
| `cascader` | ElCascader | 级联选择 |
| `transfer` | ElTransfer | 穿梭框 |
| `upload` | ElUpload | 文件上传 |
| `image-upload` | ElUpload accept="image/*" | 图片上传 |
| `table` | ElTable | 数据表格（支持行合并、颜色映射、趋势箭头） |
| `summary-grid` | ElCard + Grid | 汇总指标卡片网格 |
| `insight-box` | ElAlert | 洞察提示框 |
| `link` | `<a>` | 可点击链接（自定义列模板） |
| `rate-color` | 自定义 | 达成率颜色映射（绿>100%，黄80-100%，红<80%） |
| `trend-arrow` | 自定义 | 趋势箭头（↑绿↓红） |
| `currency` | 自定义 | 货币格式化（¥符号、千分位） |
| `row-header` | 自定义 | 行合并表头样式 |

---

## 6. 前端架构

### 6.1 页面结构

```
src/
├── views/
│   ├── dashboard/           # 中控仪表盘
│   ├── workflow-config/     # 工作流配置管理
│   │   ├── EnvironmentList.vue    # N8N环境列表
│   │   ├── WorkflowRoutes.vue     # 工作流路由列表
│   │   ├── NodeMappings.vue       # 节点映射配置
│   │   └── SchemaEditor.vue       # JSON Schema 编辑器
│   └── ai-assistant/        # AI 助手主界面
│       ├── AIAssistant.vue        # 主组件（三栏布局）
│       ├── ChatPanel.vue          # 右侧对话面板
│       ├── WorkflowSelector.vue   # 工作流选择器
│       ├── ChatMessage.vue        # 消息气泡
│       ├── CanvasArea.vue         # 中央画布区域
│       ├── DynamicForm.vue       # 动态表单渲染器
│       └── FormPreview.vue       # 生成物表单预览
├── components/
│   ├── layout/              # 布局组件
│   └── common/              # 通用组件
├── store/                   # Pinia 状态管理
│   ├── user.js
│   ├── workflow.js
│   └── chat.js
├── api/                     # API 请求模块
│   ├── auth.js
│   ├── workflow.js
│   └── n8n.js
└── router/
    └── index.js
```

### 6.2 三栏布局实现

```
┌────────────────────────────────────────────────────────────────┐
│                      Header (Logo + 用户信息)                   │
├────────────┬─────────────────────────────────┬───────────────┤
│            │                                 │               │
│  侧边菜单栏  │        中央画布区域              │  AI 对话面板   │
│  (240px)   │     (动态表单/结果展示)           │   (360px)    │
│            │                                 │               │
│  - 中控仪表盘 │  ┌─────────────────────┐       │ ┌───────────┐ │
│  - 工作流配置 │  │   动态渲染的表单     │       │ │工作流选择 │ │
│  - AI助手    │  │   或生成物预览       │       │ │           │ │
│              │  └─────────────────────┘       │ │ 对话历史  │ │
│              │                                 │ │           │ │
│              │                                 │ │ 输入框    │ │
│              │                                 │ └───────────┘ │
└────────────┴─────────────────────────────────┴───────────────┘
```

### 6.3 动态表单渲染流程

```
1. 用户在 ChatPanel 选择工作流
   ↓
2. 前端调用 GET /api/v1/workflows/{id}/intents 获取意图 Schema
   ↓
3. DynamicForm 组件解析 Schema，渲染表单
   ↓
4. 用户填写表单并提交
   ↓
5. 前端调用 POST /api/v1/execute/{route_id} 执行工作流
   ↓
6. 获取 Artifact Schema，渲染生成物表单
```

### 6.4 关键组件说明

| 组件 | 职责 |
|------|------|
| `DynamicForm.vue` | 核心组件，根据 JSON Schema 动态渲染表单项 |
| `WorkflowSelector.vue` | 下拉选择工作流，显示已配置的工作流列表 |
| `ChatMessage.vue` | 消息气泡组件，支持文本、表单卡片、结果卡片 |
| `CanvasArea.vue` | 画布容器，渲染意图表单或生成物预览 |

---

## 7. 安全设计

### 7.1 认证流程

1. 用户登录 → 后端验证 → 返回 JWT Access Token + Refresh Token
2. Access Token 有效期：30 分钟
3. Refresh Token 有效期：7 天
4. 所有 API 请求需携带 `Authorization: Bearer <token>`

### 7.2 N8N API Key 安全

- N8N API Key 加密存储（AES-256）
- 支持配置刷新，不泄露明文
- 日志中脱敏处理

### 7.3 输入校验

- 所有用户输入使用 Pydantic 进行校验
- SQL 注入防护（使用 ORM）
- XSS 防护（CORS 配置）

---

## 8. 目录结构

### 8.1 后端目录结构

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── workflows.py
│   │       ├── mappings.py
│   │       ├── environments.py
│   │       └── execute.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── workflow.py
│   │   └── environment.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── workflow.py
│   │   └── environment.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── n8n_service.py
│   │   └── workflow_service.py
│   ├── main.py
│   └── router.py
├── schemas/                    # JSON Schema 文件存储
│   ├── intent_forms/
│   └── artifact_forms/
├── tests/
├── requirements.txt
└── README.md
```

### 8.2 前端目录结构

```
frontend/
├── public/
├── src/
│   ├── api/
│   ├── assets/
│   ├── components/
│   ├── composables/
│   ├── router/
│   ├── store/
│   ├── utils/
│   ├── views/
│   ├── App.vue
│   └── main.js
├── .env
├── index.html
├── package.json
└── vite.config.js
```

---

## 9. 部署架构

### 9.1 容器化部署（推荐）

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/ierp
      - N8N_BASE_URL=http://n8n:5678
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data

  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
```

---

## 10. TODO

- [ ] 用户确认设计后，编写详细实现计划
- [ ] 确定数据库具体类型（MySQL/PostgreSQL）
- [ ] 确认 N8N 环境配置详情
- [ ] 确定是否需要 SSRF 防护方案

---

**下一步**: 请评审此设计文档，如有调整意见请告知。确认后我将使用 `writing-plans` 技能生成详细实现计划。