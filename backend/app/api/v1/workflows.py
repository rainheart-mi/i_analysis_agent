from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import json
from pathlib import Path
from app.database import get_db
from app.models.workflow import WorkflowRoute
from app.schemas.workflow import (
    WorkflowRouteCreate, WorkflowRouteUpdate,
    WorkflowRouteResponse, WorkflowRouteListResponse
)
from app.config import settings
from app.api.deps import get_current_user_tenant
from app.services.tenant_query import scoped_query, scoped_query_by_id, apply_tenant


router = APIRouter()


@router.get("", response_model=WorkflowRouteListResponse)
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    # Count total（带 tenant 过滤）
    count_result = await db.execute(
        select(func.count()).select_from(WorkflowRoute).where(WorkflowRoute.tenant_id == tid)
    )
    total = count_result.scalar()

    # Get items
    result = await db.execute(
        scoped_query(db, WorkflowRoute, tid)
        .options(selectinload(WorkflowRoute.node_mappings))
        .order_by(WorkflowRoute.sort_order, WorkflowRoute.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().all()

    return WorkflowRouteListResponse(items=items, total=total)


@router.post("", response_model=WorkflowRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow: WorkflowRouteCreate,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    data = workflow.model_dump()
    data.pop("tenant_id", None)  # 禁止前端传入
    db_workflow = apply_tenant(WorkflowRoute(**data), tid)
    db.add(db_workflow)
    await db.flush()
    await db.refresh(db_workflow)
    return db_workflow


@router.get("/{workflow_id}", response_model=WorkflowRouteResponse)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    result = await db.execute(
        scoped_query_by_id(db, WorkflowRoute, workflow_id, tid)
        .options(selectinload(WorkflowRoute.node_mappings))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowRouteResponse)
async def update_workflow(
    workflow_id: str,
    workflow_update: WorkflowRouteUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    result = await db.execute(scoped_query_by_id(db, WorkflowRoute, workflow_id, tid))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    update_data = workflow_update.model_dump(exclude_unset=True)
    update_data.pop("tenant_id", None)  # 禁止跨字段篡改
    for key, value in update_data.items():
        setattr(workflow, key, value)

    await db.flush()
    await db.refresh(workflow)
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    result = await db.execute(scoped_query_by_id(db, WorkflowRoute, workflow_id, tid))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    await db.delete(workflow)
    return None


@router.get("/{workflow_id}/intents")
async def get_intent_schema(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    result = await db.execute(
        scoped_query_by_id(db, WorkflowRoute, workflow_id, tid)
        .options(selectinload(WorkflowRoute.node_mappings))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    if not workflow.node_mappings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置节点映射")

    mapping = workflow.node_mappings[0]
    if not mapping.intent_schema_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置意图表单")

    schema_path = Path(settings.SCHEMA_BASE_PATH) / mapping.intent_schema_path
    if not schema_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Schema文件不存在: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    return schema


@router.get("/{workflow_id}/artifacts")
async def get_artifact_schema(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    result = await db.execute(
        scoped_query_by_id(db, WorkflowRoute, workflow_id, tid)
        .options(selectinload(WorkflowRoute.node_mappings))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    if not workflow.node_mappings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置节点映射")

    mapping = workflow.node_mappings[0]
    if not mapping.artifact_schema_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置生成物表单")

    schema_path = Path(settings.SCHEMA_BASE_PATH) / mapping.artifact_schema_path
    if not schema_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Schema文件不存在: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    return schema
