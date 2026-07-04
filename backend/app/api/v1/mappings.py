from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.database import get_db
from app.models.mapping import WorkflowNodeMapping
from app.models.workflow import WorkflowRoute
from app.schemas.mapping import (
    WorkflowNodeMappingCreate, WorkflowNodeMappingUpdate,
    WorkflowNodeMappingResponse, WorkflowNodeMappingListResponse
)
from app.api.deps import get_current_user_tenant
from app.services.tenant_query import scoped_query, scoped_query_by_id, apply_tenant


router = APIRouter()


# ---- Cycle 检测（agent 节点配 previous_node_id 时校验无环） ----

async def _check_no_cycle(
    db: AsyncSession,
    tid: str,
    *,
    self_id: str | None,
    previous_node_id: str,
    route_id: str,
) -> None:
    """从 previous_node_id 沿 previous_node_id 链向上 walk；若回到 self_id 则视为环。

    同时校验 previous_node_id 属于同一 route_id（跨 route 视为非法边）。
    """
    visited: set[str] = set()
    cursor: str | None = previous_node_id
    while cursor and cursor not in visited:
        if self_id and cursor == self_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="previous_node_id 形成环（不能指向自身）",
            )
        visited.add(cursor)

        prev_row = await db.execute(
            scoped_query_by_id(db, WorkflowNodeMapping, cursor, tid)
        )
        prev_mapping = prev_row.scalar_one_or_none()
        if not prev_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"上游节点 {cursor} 不存在或不属于当前租户",
            )
        if prev_mapping.route_id != route_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="previous_node_id 必须属于同一工作流（route_id）",
            )
        cursor = prev_mapping.previous_node_id


# ---- 节点类型相关必填校验 ----

def _validate_node_type_fields(data: dict, *, partial: bool = False) -> None:
    """按 node_type 校验必填字段。

    - n8n  : n8n_workflow_id 必填非空
    - agent: post_action_config 必填非空 + previous_node_id 必填

    `partial=True` 用于 update：缺字段不报错（视为不更新），但已有字段类型不合法仍报错。
    """
    node_type = data.get("node_type") or "n8n"
    if node_type not in ("n8n", "agent"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"node_type 必须是 n8n 或 agent，当前: {node_type}",
        )

    if node_type == "n8n":
        n8n_id = data.get("n8n_workflow_id")
        if not partial and not (isinstance(n8n_id, str) and n8n_id.strip()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="node_type='n8n' 必须配置 n8n_workflow_id",
            )
    elif node_type == "agent":
        pac = data.get("post_action_config")
        prev = data.get("previous_node_id")
        if not partial:
            if not isinstance(pac, dict) or not pac:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="node_type='agent' 必须配置 post_action_config",
                )
            if not (isinstance(prev, str) and prev.strip()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="node_type='agent' 必须配置 previous_node_id",
                )


@router.get("/workflow/{route_id}", response_model=WorkflowNodeMappingListResponse)
async def list_mappings_by_route(
    route_id: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(
        scoped_query(db, WorkflowNodeMapping, ctx.tenant_id)
        .where(WorkflowNodeMapping.route_id == route_id)
        .order_by(WorkflowNodeMapping.created_at)
    )
    items = result.scalars().all()
    return WorkflowNodeMappingListResponse(items=list(items), total=len(items))


@router.post("/workflow/{route_id}", response_model=WorkflowNodeMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_mapping(
    route_id: str,
    mapping: WorkflowNodeMappingCreate,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    # Verify route 存在且属于当前 tenant
    route_result = await db.execute(scoped_query_by_id(db, WorkflowRoute, route_id, ctx.tenant_id))
    if not route_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    data = mapping.model_dump()
    data["route_id"] = route_id
    data.pop("tenant_id", None)

    # 按 node_type 校验必填字段
    _validate_node_type_fields(data, partial=False)

    # agent 节点：previous_node_id cycle 检测 + 同 route 校验
    if data.get("node_type") == "agent":
        await _check_no_cycle(
            db, ctx.tenant_id,
            self_id=None,
            previous_node_id=data["previous_node_id"],
            route_id=route_id,
        )

    db_mapping = apply_tenant(WorkflowNodeMapping(**data), ctx.tenant_id)
    db.add(db_mapping)
    await db.flush()
    await db.refresh(db_mapping)
    return db_mapping


@router.put("/{mapping_id}", response_model=WorkflowNodeMappingResponse)
async def update_mapping(
    mapping_id: str,
    mapping_update: WorkflowNodeMappingUpdate,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(scoped_query_by_id(db, WorkflowNodeMapping, mapping_id, ctx.tenant_id))
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="映射不存在")

    update_data = mapping_update.model_dump(exclude_unset=True)
    update_data.pop("tenant_id", None)

    # 合并：未传的字段保持原值，校验用"最终态"
    merged = {**{c.name: getattr(mapping, c.name) for c in mapping.__table__.columns}, **update_data}
    # 移除非数据字段（id / created_at / updated_at / route 关系）
    for non_data in ("id", "created_at", "updated_at", "route"):
        merged.pop(non_data, None)

    _validate_node_type_fields(merged, partial=True)

    # agent 节点：previous_node_id 改了就要重新 cycle 检测
    new_node_type = merged.get("node_type") or "n8n"
    new_prev = merged.get("previous_node_id")
    if new_node_type == "agent":
        if not new_prev:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="node_type='agent' 必须配置 previous_node_id",
            )
        await _check_no_cycle(
            db, ctx.tenant_id,
            self_id=mapping.id,
            previous_node_id=new_prev,
            route_id=mapping.route_id,
        )

    for key, value in update_data.items():
        setattr(mapping, key, value)

    await db.flush()
    await db.refresh(mapping)
    return mapping


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    mapping_id: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(scoped_query_by_id(db, WorkflowNodeMapping, mapping_id, ctx.tenant_id))
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="映射不存在")

    # 下游 agent 节点的 previous_node_id 通过 ON DELETE SET NULL 自动置空（不级联删）。
    await db.delete(mapping)
    return None