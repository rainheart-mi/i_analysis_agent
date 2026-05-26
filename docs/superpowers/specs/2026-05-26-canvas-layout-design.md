# 画布交互设计规格书

> **设计日期:** 2026-05-26
> **状态:** 已确认

## 1. 概述

### 1.1 目标
设计 IERP_Orchestrator 的画布交互模块，支持多工作流实例并行管理，每个实例内多个节点可切换查看，意图澄清与生成物分上下区展示，所有数据持久化到数据库。

### 1.2 核心特性
- 工作流实例瀑布式垂直堆叠（左侧边栏）
- 每个工作流实例包含多个节点子 Tab（水平滚动）
- 节点内意图澄清（输入）和生成物（输出）上下分区展示
- 执行后表单只读，操作按钮隐藏
- 任务数据持久化到数据库

---

## 2. 页面布局

### 2.1 整体布局
```
┌─────────────────────────────────────────────────────────┐
│                    顶部 Header                         │
├──────────────┬────────────────────────────────────────┤
│              │           Node Sub-Tabs                  │
│  工作流实例   │  [节点1] [节点2] [节点3]               │
│  (垂直堆叠)   ├────────────────────────────────────────┤
│              │                                         │
│  ┌────────┐ │           Canvas Content                │
│  │品类运营│ │  ┌─────────────────────────────────┐   │
│  │分析    │ │  │  意图澄清 (上)                   │   │
│  └────────┘ │  │  - 表单只读                     │   │
│  ┌────────┐ │  │  - 隐藏操作按钮                 │   │
│  │门店销售│ │  └─────────────────────────────────┘   │
│  │分析    │ │  ┌─────────────────────────────────┐   │
│  └────────┘ │  │  生成物展示 (下)                 │   │
│              │  │  - 汇总指标                     │   │
│              │  │  - 数据表格                     │   │
│              │  │  - 洞察提示                     │   │
│              │  └─────────────────────────────────┘   │
└──────────────┴────────────────────────────────────────┘
```

### 2.2 左侧工作流实例栏
- **布局**: 垂直排列，自上向下展开
- **工作流卡片**:
  - 图标 + 名称
  - 节点进度指示器（圆点 + 连接线）
  - 状态标签（执行中/已完成）
  - 时间戳
- **折叠**: 点击工作流卡片可折叠/展开节点列表
- **新建**: 顶部"+ 新建"按钮

### 2.3 节点子 Tab
- **布局**: 水平排列，超出宽度可滚动
- **Tab 内容**:
  - 状态指示点（已完成/进行中/待处理）
  - 节点名称
- **切换**: 点击 Tab 切换节点内容

### 2.4 Canvas 内容区
- **意图澄清区（输入）**:
  - 顶部标题 + 状态标签
  - 表单内容（卡片式）
  - 执行后：表单只读，背景变灰，隐藏操作按钮
  
- **分隔线**:
  - 渐变线条 + "数据输出" 徽章
  
- **生成物区（输出）**:
  - 汇总指标网格（4列）
  - 数据表格（支持达成率色块、趋势箭头）
  - 洞察提示框
  - 底部操作栏

---

## 3. 数据模型

### 3.1 任务实例 (TaskInstance)
```python
class TaskInstance(BaseModel):
    __tablename__ = "task_instances"
    
    id: str                    # UUID
    user_id: str                # 用户ID
    workflow_id: str            # 工作流ID (外键)
    status: str                 # pending/running/completed/failed
    current_node_id: str        # 当前节点ID
    created_at: datetime
    updated_at: datetime
```

### 3.2 节点执行记录 (NodeExecution)
```python
class NodeExecution(BaseModel):
    __tablename__ = "node_executions"
    
    id: str                    # UUID
    task_instance_id: str       # 任务实例ID (外键)
    node_id: str                # 节点ID
    node_name: str              # 节点名称
    intent_data: JSON           # 意图澄清输入数据
    artifact_data: JSON          # 生成物输出数据
    status: str                 # pending/running/completed/failed
    started_at: datetime
    completed_at: datetime
```

### 3.3 关系
```
TaskInstance (1) ─────< NodeExecution (N)
                              │
                              ├── intent_data (意图澄清输入)
                              └── artifact_data (生成物输出)
```

---

## 4. UI 组件

### 4.1 工作流实例卡片
| 状态 | 样式 |
|------|------|
| 默认 | 白色背景，圆角边框 |
| 活跃 | 渐变紫色背景，边框高亮 |
| 折叠 | 仅显示标题，隐藏节点进度 |

### 4.2 节点进度指示器
| 状态 | 样式 |
|------|------|
| 已完成 | 绿色实心圆 + 绿色连接线 |
| 进行中 | 紫色脉冲圆 + 渐变连接线 |
| 待处理 | 灰色空心圆 |

### 4.3 表单状态
| 状态 | 样式 |
|------|------|
| 编辑中 | 白色背景，输入框正常 |
| 只读 | 灰色背景，输入值变灰，不可编辑 |
| 隐藏按钮 | 操作按钮 `display: none` |

### 4.4 生成物样式
| 组件 | 样式 |
|------|------|
| 汇总指标 | 4列网格卡片，悬停上浮 |
| 达成率 | 绿色(≥100%)/黄色(80-100%)/红色(<80%) |
| 趋势箭头 | 绿色↑/红色↓ |
| 洞察框 | 虚线边框 + 渐变背景 |

---

## 5. 前端页面结构

```
AIAssistant.vue
├── AppLayout.vue
│   ├── Sidebar.vue
│   └── Header.vue
└── CanvasArea.vue
    ├── WorkflowSidebar.vue      # 左侧工作流实例列表
    ├── NodeTabs.vue             # 节点 Tab 切换
    └── NodeContent.vue
        ├── IntentForm.vue       # 意图澄清表单
        │   └── DynamicForm.vue  # 动态表单渲染
        └── ArtifactView.vue     # 生成物展示
            ├── MetricsGrid.vue  # 汇总指标
            ├── DataTable.vue    # 数据表格
            └── InsightsBox.vue  # 洞察提示
```

---

## 6. 后端 API

### 6.1 任务管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/tasks` | 创建任务实例 |
| GET | `/api/v1/tasks` | 获取用户所有任务 |
| GET | `/api/v1/tasks/{id}` | 获取任务详情 |
| PATCH | `/api/v1/tasks/{id}` | 更新任务状态 |

### 6.2 节点执行
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/tasks/{task_id}/nodes/{node_id}/execute` | 执行节点 |
| GET | `/api/v1/tasks/{task_id}/nodes/{node_id}` | 获取节点数据 |
| PATCH | `/api/v1/tasks/{task_id}/nodes/{node_id}` | 更新节点数据 |

### 6.3 Schema 加载
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/workflows/{id}/schema` | 获取工作流完整 Schema（含所有节点） |

---

## 7. 执行流程

### 7.1 新建工作流实例
1. 用户点击"+ 新建工作流"
2. 弹出工作流选择器
3. 选择后创建 TaskInstance
4. 加载工作流的节点列表
5. 默认选中第一个节点

### 7.2 执行节点
1. 用户在意图澄清表单填写数据
2. 点击"执行工作流"
3. 表单变为只读，显示执行状态
4. 调用后端 API 执行 N8N 工作流
5. 获取结果后更新 NodeExecution
6. 切换到生成物展示

### 7.3 节点切换
1. 点击节点 Tab
2. 加载该节点的 intent_data 和 artifact_data
3. 如有 artifact_data 显示生成物
4. 如仅有 intent_data 显示意图澄清表单

---

## 8. 数据持久化

### 8.1 保存时机
- **意图澄清**: 用户输入时自动保存（防丢失）
- **执行结果**: N8N 回调或轮询获取后保存
- **状态变更**: 立即保存

### 8.2 离线支持
- 前端 localStorage 缓存草稿
- 页面刷新后从后端恢复数据
- 网络恢复后同步离线数据

---

## 9. 参考文件

- 设计草稿: `.superpowers/brainstorm/1950-1779732698/content/layout-v5.html`
- 当前数据模型: `backend/app/models/`
- 当前 Schema 解析: `frontend/src/utils/schemaParser.js`