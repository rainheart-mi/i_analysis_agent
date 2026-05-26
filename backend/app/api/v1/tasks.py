from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Any, Dict, Optional
import uuid
import json
from datetime import datetime
from pathlib import Path

from app.database import get_db
from app.models.task import TaskInstance, NodeExecution
from app.models.workflow import WorkflowRoute
from app.schemas.task import (
    TaskCreate, TaskResponse, TaskDetailResponse,
    NodeExecutionResponse, NodeUpdateRequest
)
from app.config import settings


router = APIRouter()


def load_schema_file(schema_path: str) -> Optional[Dict[str, Any]]:
    """Load schema content from file path"""
    if not schema_path:
        return None
    try:
        base_path = Path(settings.SCHEMA_BASE_PATH).resolve()
        full_path = (base_path / schema_path).resolve()
        if full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def build_node_response(node_exec: NodeExecution) -> NodeExecutionResponse:
    """Build NodeExecutionResponse with schema content loaded from files"""
    intent_schema = None
    artifact_schema = None

    if node_exec.intent_schema_path:
        intent_schema = load_schema_file(node_exec.intent_schema_path)
    if node_exec.artifact_schema_path:
        artifact_schema = load_schema_file(node_exec.artifact_schema_path)

    return NodeExecutionResponse(
        id=node_exec.id,
        task_instance_id=node_exec.task_instance_id,
        node_id=node_exec.node_id,
        node_name=node_exec.node_name,
        intent_schema_path=node_exec.intent_schema_path,
        artifact_schema_path=node_exec.artifact_schema_path,
        intent_data=node_exec.intent_data or {},
        artifact_data=node_exec.artifact_data,
        intent_schema=intent_schema,
        artifact_schema=artifact_schema,
        status=node_exec.status,
        error_message=node_exec.error_message,
        started_at=node_exec.started_at,
        completed_at=node_exec.completed_at
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a task for the given workflow_id"""
    result = await db.execute(
        select(WorkflowRoute)
        .options(selectinload(WorkflowRoute.node_mappings))
        .where(WorkflowRoute.id == task_data.workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    if not workflow.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="工作流已禁用")

    task_id = str(uuid.uuid4())
    task = TaskInstance(
        id=task_id,
        user_id="anonymous",
        workflow_id=task_data.workflow_id,
        name=task_data.name or f"Task-{task_id[:8]}",
        status="pending"
    )
    db.add(task)

    for mapping in workflow.node_mappings:
        node_exec = NodeExecution(
            id=str(uuid.uuid4()),
            task_instance_id=task_id,
            node_id=mapping.node_id,
            node_name=mapping.node_name,
            intent_schema_path=mapping.intent_schema_path,
            artifact_schema_path=mapping.artifact_schema_path,
            intent_data={},
            status="pending"
        )
        db.add(node_exec)

    await db.flush()
    await db.refresh(task)
    return task


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db)
):
    """Return all tasks for the current user (user_id = "anonymous")"""
    result = await db.execute(
        select(TaskInstance)
        .where(TaskInstance.user_id == "anonymous")
        .order_by(TaskInstance.created_at.desc())
    )
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task_detail(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Return task with all node executions, include workflow_title and schema content"""
    result = await db.execute(
        select(TaskInstance)
        .options(selectinload(TaskInstance.node_executions))
        .where(TaskInstance.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    workflow_result = await db.execute(
        select(WorkflowRoute.title)
        .where(WorkflowRoute.id == task.workflow_id)
    )
    workflow_title = workflow_result.scalar_one_or_none()

    nodes_with_schema = [build_node_response(n) for n in task.node_executions]

    return TaskDetailResponse(
        task=task,
        nodes=nodes_with_schema,
        workflow_title=workflow_title
    )


@router.patch("/{task_id}/nodes/{node_id}/execute", status_code=status.HTTP_200_OK)
async def execute_node(
    task_id: str,
    node_id: str,
    update_data: NodeUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update node's intent_data and status to 'running', update task status and current_node_id"""
    result = await db.execute(
        select(TaskInstance)
        .options(selectinload(TaskInstance.node_executions))
        .where(TaskInstance.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node_exec = None
    for node in task.node_executions:
        if node.node_id == node_id:
            node_exec = node
            break

    if not node_exec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点执行记录不存在")

    # Update intent_data if provided
    if update_data.intent_data is not None:
        node_exec.intent_data = update_data.intent_data

    node_exec.status = "running"
    node_exec.started_at = datetime.utcnow()

    task.status = "running"
    task.current_node_id = node_id

    return {"message": "节点开始执行", "node_id": node_id, "status": "running"}


@router.patch("/{task_id}/nodes/{node_id}", status_code=status.HTTP_200_OK)
async def update_node(
    task_id: str,
    node_id: str,
    update_data: NodeUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update artifact_data, status, error_message, completed_at"""
    result = await db.execute(
        select(TaskInstance)
        .options(selectinload(TaskInstance.node_executions))
        .where(TaskInstance.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node_exec = None
    for node in task.node_executions:
        if node.node_id == node_id:
            node_exec = node
            break

    if not node_exec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点执行记录不存在")

    if update_data.artifact_data is not None:
        node_exec.artifact_data = update_data.artifact_data
    if update_data.status is not None:
        node_exec.status = update_data.status
    if update_data.error_message is not None:
        node_exec.error_message = update_data.error_message
    if update_data.completed_at is not None:
        node_exec.completed_at = update_data.completed_at

    all_completed = all(n.status == "completed" for n in task.node_executions)
    if all_completed:
        task.status = "completed"

    return {"message": "节点更新成功", "node_id": node_id}


@router.post("/{task_id}/nodes/{node_id}/mock-complete", status_code=status.HTTP_200_OK)
async def mock_complete_node(
    task_id: str,
    node_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Mock complete a node execution with sample artifact data"""
    result = await db.execute(
        select(TaskInstance)
        .options(selectinload(TaskInstance.node_executions))
        .where(TaskInstance.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node_exec = None
    for node in task.node_executions:
        if node.node_id == node_id:
            node_exec = node
            break

    if not node_exec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点执行记录不存在")

    # Mock artifact data
    mock_artifact_data = {
        "summary_metrics": [
            {"label": "分析品类数", "value": "15", "color": "blue"},
            {"label": "销售达成100%", "value": "0", "color": "green"},
            {"label": "达成率均值", "value": "57.2%", "color": "yellow"},
            {"label": "待提升品类", "value": "15", "color": "red"}
        ],
        "sales_report": [
            {"rank": 1, "category": "3R熟食", "sales_actual": 21660, "sales_budget": 23349, "sales_rate": 92.8, "profit_actual": 3810, "profit_budget": 3035, "profit_rate": 125.5},
            {"rank": 2, "category": "烘焙", "sales_actual": 48348, "sales_budget": 61366, "sales_rate": 78.8, "profit_actual": 7821, "profit_budget": 14430, "profit_rate": 54.2},
            {"rank": 3, "category": "蔬菜", "sales_actual": 204489, "sales_budget": 270754, "sales_rate": 75.5, "profit_actual": 41376, "profit_budget": 54151, "profit_rate": 76.4}
        ],
        "weekly_trend": [
            {"category": "3R熟食", "period": "本周", "sales": 10830, "trend": "+5.2%"},
            {"category": "3R熟食", "period": "上周", "sales": 10290, "trend": "-2.1%"},
            {"category": "烘焙", "period": "本周", "sales": 24174, "trend": "+12.8%"},
            {"category": "烘焙", "period": "上周", "sales": 21440, "trend": "+8.5%"}
        ],
        "insights": [
            "3R熟食品类销售达成率最高，达92.8%",
            "烘焙品类毛利达成率偏低，需关注成本控制",
            "蔬菜品类周环比上升12.8%，表现良好"
        ]
    }

    node_exec.artifact_data = mock_artifact_data
    node_exec.status = "completed"
    node_exec.completed_at = datetime.utcnow()

    task.status = "completed"

    return {"message": "节点执行完成", "node_id": node_id, "status": "completed"}