from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
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


@router.get("/workflow/{route_id}", response_model=WorkflowNodeMappingListResponse)
async def list_mappings_by_route(
    route_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    result = await db.execute(
        scoped_query(db, WorkflowNodeMapping, tid)
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
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    # Verify route 存在且属于当前 tenant
    route_result = await db.execute(scoped_query_by_id(db, WorkflowRoute, route_id, tid))
    if not route_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    data = mapping.model_dump()
    data["route_id"] = route_id
    data.pop("tenant_id", None)
    db_mapping = apply_tenant(WorkflowNodeMapping(**data), tid)
    db.add(db_mapping)
    await db.flush()
    await db.refresh(db_mapping)
    return db_mapping


@router.put("/{mapping_id}", response_model=WorkflowNodeMappingResponse)
async def update_mapping(
    mapping_id: str,
    mapping_update: WorkflowNodeMappingUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    result = await db.execute(scoped_query_by_id(db, WorkflowNodeMapping, mapping_id, tid))
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="映射不存在")

    update_data = mapping_update.model_dump(exclude_unset=True)
    update_data.pop("tenant_id", None)
    for key, value in update_data.items():
        setattr(mapping, key, value)

    await db.flush()
    await db.refresh(mapping)
    return mapping


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    mapping_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    result = await db.execute(scoped_query_by_id(db, WorkflowNodeMapping, mapping_id, tid))
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="映射不存在")

    await db.delete(mapping)
    return None
