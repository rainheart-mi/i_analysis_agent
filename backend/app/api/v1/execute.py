from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
from typing import Dict, Any
import uuid
from app.database import get_db
from app.models.workflow import WorkflowRoute
from app.models.environment import N8NEnvironment
from app.models.mapping import WorkflowNodeMapping
from app.services.n8n_service import get_n8n_service
from app.api.deps import get_current_user_tenant
from app.services.crypto import decrypt_password
from app.services.tenant_query import scoped_query_by_id


router = APIRouter()


class ExecuteRequest(BaseModel):
    user_id: str = ""  # 兼容旧字段；后端忽略实际值，从 token 解析
    inputs: Dict[str, Any]


class ExecuteResponse(BaseModel):
    task_id: str
    status: str
    message: str


@router.post("/{workflow_id}", response_model=ExecuteResponse)
async def execute_workflow(
    workflow_id: str,
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    # 1. workflow 必须属于当前 tenant
    result = await db.execute(
        scoped_query_by_id(db, WorkflowRoute, workflow_id, ctx.tenant_id)
        .options(selectinload(WorkflowRoute.environment))
        .options(selectinload(WorkflowRoute.node_mappings))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    if not workflow.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="工作流已禁用")

    if not workflow.node_mappings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未配置节点映射")

    # 2. 二次校验 environment 与 mapping 都在当前 tenant 内
    environment = workflow.environment
    if not environment or environment.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="环境不存在")

    mapping = workflow.node_mappings[0]
    if mapping.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点映射不存在")

    # Create n8n service（含 Basic Auth 凭据：username 明文 + password 从 password_enc 解密）
    basic_password = (
        decrypt_password(environment.password_enc)
        if environment.password_enc
        else None
    )
    n8n_service = get_n8n_service(
        environment.base_url,
        environment.api_key,
        "production",
        environment.username,
        basic_password,
    )

    # Generate task id
    task_id = str(uuid.uuid4())

    try:
        result_data = await n8n_service.execute_workflow(
            workflow_id=workflow.n8n_workflow_id,
            node_id=mapping.node_id,
            inputs=request.inputs
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
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
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
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(
        scoped_query_by_id(db, WorkflowRoute, workflow_id, ctx.tenant_id)
        .options(selectinload(WorkflowRoute.node_mappings))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    if not workflow.node_mappings:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未配置节点映射")

    mapping = workflow.node_mappings[0]
    if mapping.tenant_id != ctx.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点映射不存在")

    return {
        "workflow_id": workflow_id,
        "node_id": mapping.node_id,
        "inputs": request.inputs,
        "message": "预览信息"
    }
