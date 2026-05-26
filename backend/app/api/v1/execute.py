from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Dict, Any
import uuid
from app.database import get_db
from app.models.workflow import WorkflowRoute
from app.models.environment import N8NEnvironment
from app.models.mapping import WorkflowNodeMapping
from app.services.n8n_service import get_n8n_service


router = APIRouter()


class ExecuteRequest(BaseModel):
    user_id: str
    inputs: Dict[str, Any]


class ExecuteResponse(BaseModel):
    task_id: str
    status: str
    message: str


@router.post("/{workflow_id}", response_model=ExecuteResponse)
async def execute_workflow(
    workflow_id: str,
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db)
):
    # Get workflow with environment and mapping
    result = await db.execute(
        select(WorkflowRoute)
        .options(selectinload(WorkflowRoute.environment))
        .options(selectinload(WorkflowRoute.node_mappings))
        .where(WorkflowRoute.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    if not workflow.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="工作流已禁用")

    if not workflow.node_mappings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未配置节点映射")

    mapping = workflow.node_mappings[0]
    environment = workflow.environment

    # Create n8n service
    n8n_service = get_n8n_service(environment.base_url, environment.api_key)

    # Generate task id
    task_id = str(uuid.uuid4())

    # Apply input mapping if configured
    final_inputs = request.inputs
    if mapping.input_mapping:
        final_inputs = {k: request.inputs.get(v) for k, v in mapping.input_mapping.items()}

    try:
        result_data = await n8n_service.execute_workflow(
            workflow_id=workflow.n8n_workflow_id,
            node_id=mapping.node_id,
            inputs=final_inputs
        )
        return ExecuteResponse(
            task_id=task_id,
            status="completed",
            message="工作流执行成功"
        )
    except Exception as e:
        return ExecuteResponse(
            task_id=task_id,
            status="failed",
            message=f"工作流执行失败: {str(e)}"
        )


@router.get("/{workflow_id}/status/{task_id}")
async def get_execution_status(
    workflow_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    # TODO: 实现任务状态查询（可使用 Redis 或数据库存储任务状态）
    return {
        "task_id": task_id,
        "status": "completed",
        "message": "任务状态查询功能待实现"
    }


@router.post("/{workflow_id}/preview")
async def preview_workflow(
    workflow_id: str,
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkflowRoute)
        .options(selectinload(WorkflowRoute.node_mappings))
        .where(WorkflowRoute.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    if not workflow.node_mappings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未配置节点映射")

    mapping = workflow.node_mappings[0]

    # Preview the mapped inputs
    preview_inputs = request.inputs
    if mapping.input_mapping:
        preview_inputs = {k: request.inputs.get(v) for k, v in mapping.input_mapping.items()}

    return {
        "workflow_id": workflow_id,
        "node_id": mapping.node_id,
        "mapped_inputs": preview_inputs,
        "message": "预览信息"
    }