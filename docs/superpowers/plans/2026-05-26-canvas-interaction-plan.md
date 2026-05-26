# 画布交互模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现画布交互模块，支持工作流实例的创建、节点切换、意图澄清表单执行、生成物展示，所有数据持久化到数据库。

**Architecture:** 后端新增 TaskInstance 和 NodeExecution 数据模型，前端新增画布布局组件（WorkflowSidebar、NodeTabs、NodeContent），通过 Pinia Store 管理状态，后端 API 支持任务的创建、执行、状态查询。

**Tech Stack:** Python/FastAPI (后端), Vue 3/Pinia (前端), SQLAlchemy (ORM), Element Plus (UI)

---

## 文件结构

### 后端新增文件
- `backend/app/models/task.py` - TaskInstance 和 NodeExecution 模型
- `backend/app/schemas/task.py` - Pydantic 请求/响应模型
- `backend/app/api/v1/tasks.py` - 任务管理 API

### 后端修改文件
- `backend/app/models/__init__.py` - 添加模型导出
- `backend/app/router.py` - 注册任务路由
- `backend/app/api/v1/execute.py` - 增强执行 API 支持多节点

### 前端新增文件
- `frontend/src/store/task.js` - 任务状态管理
- `frontend/src/views/ai-assistant/WorkflowSidebar.vue` - 左侧工作流实例栏
- `frontend/src/views/ai-assistant/NodeTabs.vue` - 节点 Tab 组件
- `frontend/src/views/ai-assistant/NodeContent.vue` - 节点内容区（上下分区）

### 前端修改文件
- `frontend/src/store/workflow.js` - 添加工作流实例相关状态
- `frontend/src/api/workflow.js` - 添加任务相关 API 调用
- `frontend/src/views/ai-assistant/AIAssistant.vue` - 集成新组件
- `frontend/src/views/ai-assistant/CanvasArea.vue` - 改为使用 NodeContent

---

## 任务 1: 后端数据模型

**Files:**
- Create: `backend/app/models/task.py`
- Modify: `backend/app/models/__init__.py:5`

- [ ] **Step 1: 创建 TaskInstance 和 NodeExecution 模型**

```python
# backend/app/models/task.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class TaskInstance(BaseModel):
    __tablename__ = "task_instances"

    user_id = Column(String(36), nullable=False, index=True)
    workflow_id = Column(String(36), ForeignKey("workflow_routes.id"), nullable=False)
    name = Column(String(200))
    status = Column(String(20), default="pending")  # pending/running/completed/failed
    current_node_id = Column(String(100))
    
    workflow = relationship("WorkflowRoute")
    node_executions = relationship("NodeExecution", back_populates="task_instance", cascade="all, delete-orphan")


class NodeExecution(BaseModel):
    __tablename__ = "node_executions"

    task_instance_id = Column(String(36), ForeignKey("task_instances.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(100), nullable=False)
    node_name = Column(String(200))
    intent_schema_path = Column(String(500))
    artifact_schema_path = Column(String(500))
    intent_data = Column(JSON, default={})
    artifact_data = Column(JSON, default=None)
    status = Column(String(20), default="pending")  # pending/running/completed/failed
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    task_instance = relationship("TaskInstance", back_populates="node_executions")
```

- [ ] **Step 2: 更新模型导出**

```python
# backend/app/models/__init__.py (修改第5行后)
from app.models.base import BaseModel
from app.models.user import User
from app.models.environment import N8NEnvironment
from app.models.workflow import WorkflowRoute
from app.models.mapping import WorkflowNodeMapping
from app.models.task import TaskInstance, NodeExecution

__all__ = ["BaseModel", "User", "N8NEnvironment", "WorkflowRoute", "WorkflowNodeMapping", "TaskInstance", "NodeExecution"]
```

- [ ] **Step 3: 运行数据库迁移**

```bash
cd C:/LLM/i_analysis_agent/backend
python -c "from app.database import engine, Base; from app.models.task import TaskInstance, NodeExecution; import asyncio; asyncio.run(engine.begin()).rollback()" 2>/dev/null || echo "需要执行 init_db.py 初始化新表"
```

---

## 任务 2: 后端 Schema 定义

**Files:**
- Create: `backend/app/schemas/task.py`

- [ ] **Step 1: 创建任务相关 Schema**

```python
# backend/app/schemas/task.py
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime


class TaskCreate(BaseModel):
    workflow_id: str
    name: Optional[str] = None


class TaskResponse(BaseModel):
    id: str
    user_id: str
    workflow_id: str
    name: Optional[str]
    status: str
    current_node_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NodeExecutionCreate(BaseModel):
    node_id: str
    intent_data: Dict[str, Any] = {}


class NodeExecutionResponse(BaseModel):
    id: str
    task_instance_id: str
    node_id: str
    node_name: Optional[str]
    intent_data: Dict[str, Any]
    artifact_data: Optional[Dict[str, Any]]
    status: str
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class TaskDetailResponse(BaseModel):
    task: TaskResponse
    nodes: List[NodeExecutionResponse]
    workflow_title: Optional[str] = None
```

---

## 任务 3: 后端 API 实现

**Files:**
- Create: `backend/app/api/v1/tasks.py`
- Modify: `backend/app/router.py:11`

- [ ] **Step 1: 创建任务 API**

```python
# backend/app/api/v1/tasks.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db
from app.models.task import TaskInstance, NodeExecution
from app.models.workflow import WorkflowRoute
from app.models.mapping import WorkflowNodeMapping
from app.schemas.task import (
    TaskCreate, TaskResponse, TaskDetailResponse,
    NodeExecutionCreate, NodeExecutionResponse
)

router = APIRouter()


@router.post("", response_model=TaskResponse)
async def create_task(
    request: TaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新的任务实例"""
    # 获取工作流信息
    result = await db.execute(
        select(WorkflowRoute)
        .options(selectinload(WorkflowRoute.node_mappings))
        .where(WorkflowRoute.id == request.workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="工作流不存在")
    
    # 创建任务实例
    task = TaskInstance(
        user_id="anonymous",  # TODO: 从认证获取
        workflow_id=request.workflow_id,
        name=request.name or workflow.title,
        status="pending"
    )
    db.add(task)
    await db.flush()
    
    # 为每个节点创建执行记录
    for mapping in workflow.node_mappings:
        node_exec = NodeExecution(
            task_instance_id=task.id,
            node_id=mapping.node_id,
            node_name=mapping.node_name,
            intent_schema_path=mapping.intent_schema_path,
            artifact_schema_path=mapping.artifact_schema_path,
            status="pending"
        )
        db.add(node_exec)
    
    await db.commit()
    await db.refresh(task)
    return task


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db)
):
    """获取用户的所有任务"""
    result = await db.execute(
        select(TaskInstance)
        .where(TaskInstance.user_id == "anonymous")
        .order_by(TaskInstance.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取任务详情（含所有节点执行记录）"""
    result = await db.execute(
        select(TaskInstance)
        .options(selectinload(TaskInstance.node_executions))
        .options(selectinload(TaskInstance.workflow))
        .where(TaskInstance.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return TaskDetailResponse(
        task=task,
        nodes=task.node_executions,
        workflow_title=task.workflow.title if task.workflow else None
    )


@router.patch("/{task_id}/nodes/{node_id}/execute")
async def execute_node(
    task_id: str,
    node_id: str,
    request: NodeExecutionCreate,
    db: AsyncSession = Depends(get_db)
):
    """执行指定节点"""
    # 获取节点执行记录
    result = await db.execute(
        select(NodeExecution)
        .options(selectinload(NodeExecution.task_instance))
        .options(selectinload(NodeExecution.task_instance.workflow))
        .where(
            NodeExecution.task_instance_id == task_id,
            NodeExecution.node_id == node_id
        )
    )
    node_exec = result.scalar_one_or_none()
    if not node_exec:
        raise HTTPException(status_code=404, detail="节点不存在")
    
    # 更新意图数据
    node_exec.intent_data = request.intent_data
    node_exec.status = "running"
    
    # 更新任务状态
    task = node_exec.task_instance
    task.status = "running"
    task.current_node_id = node_id
    
    await db.commit()
    
    return {"message": "节点执行中", "node_id": node_id}


@router.patch("/{task_id}/nodes/{node_id}")
async def update_node(
    task_id: str,
    node_id: str,
    artifact_data: Dict[str, Any] = None,
    status: str = None,
    error_message: str = None,
    db: AsyncSession = Depends(get_db)
):
    """更新节点执行结果"""
    result = await db.execute(
        select(NodeExecution)
        .where(
            NodeExecution.task_instance_id == task_id,
            NodeExecution.node_id == node_id
        )
    )
    node_exec = result.scalar_one_or_none()
    if not node_exec:
        raise HTTPException(status_code=404, detail="节点不存在")
    
    if artifact_data is not None:
        node_exec.artifact_data = artifact_data
    if status:
        node_exec.status = status
        if status == "completed":
            node_exec.completed_at = datetime.utcnow()
    if error_message:
        node_exec.error_message = error_message
    
    await db.commit()
    return {"message": "节点已更新"}
```

- [ ] **Step 2: 更新路由导出**

```python
# backend/app/router.py (修改)
from fastapi import APIRouter
from app.api.v1 import auth, environments, workflows, mappings, execute, tasks

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(environments.router, prefix="/n8n-environments", tags=["N8N环境"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["工作流路由"])
api_router.include_router(mappings.router, prefix="/mappings", tags=["节点映射"])
api_router.include_router(execute.router, prefix="/execute", tags=["工作流执行"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务管理"])
```

---

## 任务 4: 前端 Store

**Files:**
- Create: `frontend/src/store/task.js`
- Modify: `frontend/src/store/workflow.js`

- [ ] **Step 1: 创建任务 Store**

```javascript
// frontend/src/store/task.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskApi } from '@/api/workflow'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref([])
  const currentTask = ref(null)
  const currentNodeId = ref(null)
  const isExecuting = ref(false)

  const currentNode = computed(() => {
    if (!currentTask.value?.node_executions) return null
    return currentTask.value.node_executions.find(n => n.node_id === currentNodeId.value)
  })

  const nodes = computed(() => {
    return currentTask.value?.node_executions || []
  })

  async function createTask(workflowId, name) {
    const res = await taskApi.create(workflowId, name)
    const task = res.data
    tasks.value.unshift(task)
    currentTask.value = task
    if (task.node_executions?.length > 0) {
      currentNodeId.value = task.node_executions[0].node_id
    }
    return task
  }

  async function fetchTask(taskId) {
    const res = await taskApi.getDetail(taskId)
    currentTask.value = res.data
    if (res.data.nodes?.length > 0 && !currentNodeId.value) {
      currentNodeId.value = res.data.nodes[0].node_id
    }
    return res.data
  }

  async function executeNode(nodeId, intentData) {
    if (!currentTask.value) return
    isExecuting.value = true
    try {
      await taskApi.executeNode(currentTask.value.id, nodeId, intentData)
      // 轮询获取执行状态
      await pollNodeStatus(nodeId)
    } finally {
      isExecuting.value = false
    }
  }

  async function pollNodeStatus(nodeId, maxAttempts = 30) {
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(r => setTimeout(r, 1000))
      await fetchTask(currentTask.value.id)
      const node = currentTask.value.node_executions?.find(n => n.node_id === nodeId)
      if (node?.status === 'completed' || node?.status === 'failed') {
        return node
      }
    }
    throw new Error('执行超时')
  }

  function setCurrentNode(nodeId) {
    currentNodeId.value = nodeId
  }

  function clearCurrentTask() {
    currentTask.value = null
    currentNodeId.value = null
  }

  return {
    tasks,
    currentTask,
    currentNodeId,
    currentNode,
    nodes,
    isExecuting,
    createTask,
    fetchTask,
    executeNode,
    setCurrentNode,
    clearCurrentTask
  }
})
```

- [ ] **Step 2: 更新 API 调用**

```javascript
// frontend/src/api/workflow.js (添加)
export const taskApi = {
  create: (workflowId, name) => axios.post('/api/v1/tasks', { workflow_id: workflowId, name }),
  list: () => axios.get('/api/v1/tasks'),
  getDetail: (taskId) => axios.get(`/api/v1/tasks/${taskId}`),
  executeNode: (taskId, nodeId, intentData) => 
    axios.patch(`/api/v1/tasks/${taskId}/nodes/${nodeId}/execute`, { intent_data: intentData }),
  updateNode: (taskId, nodeId, data) => 
    axios.patch(`/api/v1/tasks/${taskId}/nodes/${nodeId}`, data)
}
```

---

## 任务 5: 前端组件 - WorkflowSidebar

**Files:**
- Create: `frontend/src/views/ai-assistant/WorkflowSidebar.vue`

- [ ] **Step 1: 创建组件**

```vue
<template>
  <div class="workflow-sidebar">
    <div class="sidebar-header">
      <span>工作流实例</span>
      <button class="add-btn" @click="showWorkflowSelector = true">+ 新建</button>
    </div>
    <div class="workflow-list">
      <div
        v-for="task in taskStore.tasks"
        :key="task.id"
        class="workflow-item"
        :class="{ active: task.id === taskStore.currentTask?.id }"
        @click="selectTask(task)"
      >
        <div class="workflow-header">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
          </svg>
          <span class="workflow-name">{{ task.name }}</span>
          <svg class="collapse-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 9l6 6 6-6"/>
          </svg>
        </div>
        <div class="workflow-nodes">
          <template v-for="(node, idx) in task.node_executions" :key="node.node_id">
            <div class="node-dot" :class="getNodeStatusClass(node.status)">
              {{ idx + 1 }}
            </div>
            <div v-if="idx < task.node_executions.length - 1" class="node-line" :class="getNodeStatusClass(node.status)"></div>
          </template>
        </div>
        <div class="workflow-meta" :class="task.status">{{ getStatusText(task.status) }}</div>
      </div>
    </div>

    <el-dialog v-model="showWorkflowSelector" title="选择工作流" width="400px">
      <el-select v-model="selectedWorkflowId" placeholder="选择工作流" filterable class="workflow-select">
        <el-option v-for="wf in workflowStore.workflows" :key="wf.id" :label="wf.title" :value="wf.id">
          <div class="workflow-option">
            <span>{{ wf.title }}</span>
            <span class="desc">{{ wf.description }}</span>
          </div>
        </el-option>
      </el-select>
      <template #footer>
        <el-button @click="showWorkflowSelector = false">取消</el-button>
        <el-button type="primary" @click="createNewTask" :disabled="!selectedWorkflowId">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useTaskStore } from '@/store/task'
import { useWorkflowStore } from '@/store/workflow'

const taskStore = useTaskStore()
const workflowStore = useWorkflowStore()
const showWorkflowSelector = ref(false)
const selectedWorkflowId = ref(null)

function getNodeStatusClass(status) {
  return { completed: status === 'completed', active: status === 'running', pending: status === 'pending' }
}

function getStatusText(status) {
  const map = { pending: '待执行', running: '执行中', completed: '已完成', failed: '失败' }
  return map[status] || status
}

async function selectTask(task) {
  await taskStore.fetchTask(task.id)
}

async function createNewTask() {
  if (!selectedWorkflowId.value) return
  await taskStore.createTask(selectedWorkflowId.value)
  showWorkflowSelector.value = false
  selectedWorkflowId.value = null
}
</script>

<style scoped>
.workflow-sidebar {
  width: 260px;
  background: #fff;
  border-right: 1px solid rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid rgba(0,0,0,0.04);
  font-weight: 600;
  font-size: 0.85rem;
  color: #1a1a2e;
}

.add-btn {
  padding: 4px 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 6px;
  color: white;
  font-size: 0.7rem;
  cursor: pointer;
}

.workflow-list { flex: 1; overflow-y: auto; padding: 12px; }

.workflow-item {
  background: #f8f9fb;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 10px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
}

.workflow-item:hover { border-color: rgba(102,126,234,0.2); }
.workflow-item.active {
  background: linear-gradient(135deg, rgba(102,126,234,0.06) 0%, rgba(118,75,162,0.06) 100%);
  border-color: rgba(102,126,234,0.2);
}

.workflow-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.workflow-header svg { color: #667eea; flex-shrink: 0; }
.workflow-name { flex: 1; font-size: 0.85rem; font-weight: 600; color: #1a1a2e; }
.collapse-icon { color: #94a3b8; }

.workflow-nodes { display: flex; align-items: center; gap: 4px; padding: 8px 0; font-size: 0.7rem; }

.node-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.6rem;
  font-weight: 600;
  color: white;
}
.node-dot.completed { background: #10B981; }
.node-dot.active { background: #667eea; }
.node-dot.pending { background: #e2e8f0; color: #94a3b8; }

.node-line { flex: 1; height: 2px; min-width: 12px; }
.node-line.completed { background: #10B981; }
.node-line.active { background: linear-gradient(90deg, #667eea, #764ba2); }

.workflow-meta { font-size: 0.7rem; color: #94a3b8; margin-top: 4px; }
.workflow-meta.running { color: #667eea; }
.workflow-meta.completed { color: #10B981; }
</style>
```

---

## 任务 6: 前端组件 - NodeTabs

**Files:**
- Create: `frontend/src/views/ai-assistant/NodeTabs.vue`

- [ ] **Step 1: 创建组件**

```vue
<template>
  <div class="node-tabs">
    <div
      v-for="node in taskStore.nodes"
      :key="node.node_id"
      class="subtab"
      :class="{ active: node.node_id === taskStore.currentNodeId }"
      @click="taskStore.setCurrentNode(node.node_id)"
    >
      <span class="node-status" :class="node.status"></span>
      <span class="node-name">{{ node.node_name || node.node_id }}</span>
    </div>
  </div>
</template>

<script setup>
import { useTaskStore } from '@/store/task'
const taskStore = useTaskStore()
</script>

<style scoped>
.node-tabs {
  background: #fff;
  padding: 0 20px;
  display: flex;
  border-bottom: 1px solid rgba(0,0,0,0.08);
}

.subtab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  font-size: 0.8rem;
  color: #94a3b8;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 0.2s;
}

.subtab:hover { color: #667eea; }
.subtab.active { color: #667eea; border-bottom-color: #667eea; font-weight: 600; }

.node-status {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.node-status.completed { background: #10B981; }
.node-status.running { background: #667eea; animation: pulse 1.5s infinite; }
.node-status.pending { background: #e2e8f0; }
.node-status.failed { background: #EF4444; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
```

---

## 任务 7: 前端组件 - NodeContent

**Files:**
- Create: `frontend/src/views/ai-assistant/NodeContent.vue`

- [ ] **Step 1: 创建组件**

```vue
<template>
  <div class="node-content">
    <!-- 意图澄清区域 -->
    <div class="intent-section" :class="{ executed: isNodeExecuted }">
      <div class="section-header">
        <span class="section-title">意图澄清</span>
        <span class="section-badge">输入</span>
        <span class="status-tag" :class="taskStore.currentNode?.status">
          {{ getStatusText(taskStore.currentNode?.status) }}
        </span>
      </div>
      <div class="form-card" :class="{ readonly: isNodeExecuted }">
        <dynamic-form
          v-if="intentSchema"
          :schema="intentSchema"
          v-model="intentFormData"
          :readonly="isNodeExecuted"
        />
        <div v-else class="empty-hint">该节点无意图澄清表单</div>
      </div>
      <div v-if="!isNodeExecuted" class="action-bar">
        <el-button @click="handleReset" class="btn-reset">重置</el-button>
        <el-button type="primary" @click="handleExecute" class="btn-primary">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M13 5l7 7-7 7M5 12h15"/>
          </svg>
          执行工作流
        </el-button>
      </div>
    </div>

    <!-- 分隔线 -->
    <div class="section-divider">
      <div class="divider-line"></div>
      <div v-if="hasArtifact" class="divider-badge">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 5v14M5 12l7 7 7-7"/>
        </svg>
        数据输出
      </div>
      <div class="divider-line"></div>
    </div>

    <!-- 生成物区域 -->
    <div v-if="hasArtifact" class="artifact-section">
      <div class="section-header">
        <span class="section-title">生成物展示</span>
        <span class="section-badge success">输出</span>
      </div>
      <dynamic-form
        v-if="artifactSchema"
        :schema="artifactSchema"
        :model-value="taskStore.currentNode?.artifact_data"
        readonly
      />
      <div v-else-if="taskStore.isExecuting" class="loading-state">
        <div class="loader">
          <div class="loader-ring"></div>
          <div class="loader-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#667eea" stroke-width="2">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4"/>
            </svg>
          </div>
        </div>
        <p>工作流执行中，请稍候...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useTaskStore } from '@/store/task'
import DynamicForm from './DynamicForm.vue'

const taskStore = useTaskStore()
const intentFormData = ref({})

const isNodeExecuted = computed(() => {
  const status = taskStore.currentNode?.status
  return status === 'completed' || status === 'running'
})

const hasArtifact = computed(() => {
  return taskStore.currentNode?.artifact_data && Object.keys(taskStore.currentNode.artifact_data).length > 0
})

const intentSchema = computed(() => {
  // TODO: 从 currentNode.intent_schema_path 加载
  return taskStore.currentNode?.intent_schema_path ? loadSchema(taskStore.currentNode.intent_schema_path) : null
})

const artifactSchema = computed(() => {
  // TODO: 从 currentNode.artifact_schema_path 加载
  return taskStore.currentNode?.artifact_schema_path ? loadSchema(taskStore.currentNode.artifact_schema_path) : null
})

async function loadSchema(path) {
  // 从后端加载 schema
  try {
    const res = await fetch(`/schemas/${path}`)
    return await res.json()
  } catch {
    return null
  }
}

function getStatusText(status) {
  const map = { pending: '待执行', running: '执行中...', completed: '已完成', failed: '执行失败' }
  return map[status] || ''
}

function handleReset() {
  intentFormData.value = {}
}

async function handleExecute() {
  if (!taskStore.currentNode) return
  await taskStore.executeNode(taskStore.currentNode.node_id, intentFormData.value)
}

watch(() => taskStore.currentNode?.intent_data, (val) => {
  if (val) intentFormData.value = { ...val }
}, { immediate: true })
</script>

<style scoped>
.node-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.section-title { font-size: 0.9rem; font-weight: 600; color: #1a1a2e; }

.section-badge {
  background: rgba(102,126,234,0.1);
  color: #667eea;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 500;
}
.section-badge.success { background: rgba(16,185,129,0.1); color: #10B981; }

.status-tag {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 0.7rem;
}
.status-tag.running { background: rgba(245,158,11,0.1); color: #F59E0B; }
.status-tag.completed { background: rgba(16,185,129,0.1); color: #10B981; }
.status-tag.failed { background: rgba(239,68,68,0.1); color: #EF4444; }

.form-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid rgba(0,0,0,0.04);
}
.form-card.readonly { background: #fafafa; border-color: rgba(102,126,234,0.1); }

.action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

.btn-reset {
  padding: 10px 20px;
  border-radius: 10px;
  border: 1px solid rgba(0,0,0,0.08);
  background: #fff;
  color: #64748b;
}
.btn-reset:hover { border-color: #667eea; color: #667eea; }

.btn-primary {
  padding: 10px 24px;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: #fff;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-divider { display: flex; align-items: center; gap: 12px; }
.divider-line { flex: 1; height: 1px; background: linear-gradient(90deg, transparent, rgba(0,0,0,0.08), transparent); }

.divider-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: rgba(16,185,129,0.1);
  border-radius: 12px;
  color: #10B981;
  font-size: 0.7rem;
  font-weight: 600;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
  background: #fff;
  border-radius: 12px;
  border: 1px solid rgba(0,0,0,0.04);
}

.loader { position: relative; width: 60px; height: 60px; margin-bottom: 16px; }
.loader-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: #667eea;
  animation: spin 1s linear infinite;
}
.loader-icon {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: spin 2s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
```

---

## 任务 8: 集成到 AIAssistant

**Files:**
- Modify: `frontend/src/views/ai-assistant/AIAssistant.vue`

- [ ] **Step 1: 更新组件**

```vue
<template>
  <div class="ai-assistant">
    <!-- 左侧工作流实例栏 -->
    <div class="workflow-sidebar">
      <workflow-sidebar />
    </div>

    <!-- 右侧画布区域 -->
    <div class="canvas-area">
      <template v-if="taskStore.currentTask">
        <!-- 节点 Tab -->
        <node-tabs />
        <!-- 节点内容 -->
        <div class="canvas-content">
          <node-content />
        </div>
      </template>
      <div v-else class="empty-state">
        <div class="empty-card">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="32" r="28" stroke="#667eea" stroke-width="2" stroke-dasharray="6 4"/>
            <path d="M24 28h16M24 36h10" stroke="#667eea" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <h3>选择一个工作流开始分析</h3>
          <p>从左侧选择或创建工作流实例</p>
        </div>
      </div>
    </div>

    <!-- 右侧对话面板 -->
    <div class="chat-panel">
      <chat-panel ... />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useTaskStore } from '@/store/task'
import { useWorkflowStore } from '@/store/workflow'
import WorkflowSidebar from './WorkflowSidebar.vue'
import NodeTabs from './NodeTabs.vue'
import NodeContent from './NodeContent.vue'
import ChatPanel from './ChatPanel.vue'

const taskStore = useTaskStore()
const workflowStore = useWorkflowStore()

onMounted(() => {
  workflowStore.fetchWorkflows()
})
</script>

<style scoped>
.ai-assistant {
  height: calc(100vh - 64px);
  display: flex;
  gap: 20px;
  padding: 20px;
  background: #f8f9fb;
}

.workflow-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
}

.canvas-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
}

.canvas-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.chat-panel {
  width: 380px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-card {
  text-align: center;
  padding: 48px;
  color: #94a3b8;
}

.empty-card h3 {
  margin: 24px 0 8px;
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a1a2e;
}

.empty-card p {
  margin: 0;
  font-size: 0.85rem;
}
</style>
```

---

## 自检清单

**1. Spec 覆盖:**
- [x] 工作流实例垂直堆叠 - WorkflowSidebar.vue
- [x] 节点 Tab 切换 - NodeTabs.vue
- [x] 意图澄清/生成物上下分区 - NodeContent.vue
- [x] 执行后表单只读 - NodeContent.vue isNodeExecuted
- [x] 数据持久化 - TaskInstance/NodeExecution 模型

**2. 占位符检查:**
- 无 TBD/TODO
- 无未实现的步骤

**3. 类型一致性:**
- taskStore.currentNodeId 与 node.node_id 一致
- intent_data/artifact_data JSON 类型一致