from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.workflow import WorkflowRoute
from app.schemas.workflow import (
    WorkflowRouteCreate, WorkflowRouteUpdate,
    WorkflowRouteResponse, WorkflowRouteListResponse
)
from app.api.deps import get_current_user_tenant
from app.services.tenant_query import scoped_query, scoped_query_by_id, apply_tenant


router = APIRouter()


@router.get("", response_model=WorkflowRouteListResponse)
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    # Count total（带 tenant 过滤）
    count_result = await db.execute(
        select(func.count()).select_from(WorkflowRoute).where(WorkflowRoute.tenant_id == ctx.tenant_id)
    )
    total = count_result.scalar()

    # Get items
    result = await db.execute(
        scoped_query(db, WorkflowRoute, ctx.tenant_id)
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
    ctx = Depends(get_current_user_tenant),
):
    data = workflow.model_dump()
    data.pop("tenant_id", None)  # 禁止前端传入
    db_workflow = apply_tenant(WorkflowRoute(**data), ctx.tenant_id)
    db.add(db_workflow)
    await db.flush()
    await db.refresh(db_workflow)
    return db_workflow


@router.get("/{workflow_id}", response_model=WorkflowRouteResponse)
async def get_workflow(
    workflow_id: str,
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
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowRouteResponse)
async def update_workflow(
    workflow_id: str,
    workflow_update: WorkflowRouteUpdate,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(scoped_query_by_id(db, WorkflowRoute, workflow_id, ctx.tenant_id))
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
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(scoped_query_by_id(db, WorkflowRoute, workflow_id, ctx.tenant_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    await db.delete(workflow)
    return None


@router.get("/{workflow_id}/intents")
async def get_intent_schema(
    workflow_id: str,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置节点映射")

    # 取 DAG 入口节点（无 previous_node_id），它是 intent_schema 的携带者
    entry = next(
        (m for m in workflow.node_mappings if not m.previous_node_id),
        workflow.node_mappings[0],
    )
    # 未配置意图表单视为"无需任何输入字段"（200 + 空对象），不再 404
    # 原因：支持意图表达为空的工作流（如固定模板、纯数据查询类）
    # AmISForm 对空 schema 有占位；执行链对 intent_data={} 友好
    return entry.intent_schema or {}



@router.get("/{workflow_id}/artifacts")
async def get_artifact_schema(
    workflow_id: str,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置节点映射")

    # 取 DAG 入口节点（无 previous_node_id）
    entry = next(
        (m for m in workflow.node_mappings if not m.previous_node_id),
        workflow.node_mappings[0],
    )
    # 同上：artifacts 也支持"无生成物 schema"，返回 200 + 空对象
    return entry.artifact_schema or {}
