from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from app.database import get_db
from app.models.mapping import WorkflowNodeMapping
from app.models.workflow import WorkflowRoute
from app.schemas.mapping import (
    WorkflowNodeMappingCreate, WorkflowNodeMappingUpdate,
    WorkflowNodeMappingResponse, WorkflowNodeMappingListResponse
)


router = APIRouter()


@router.get("/workflow/{route_id}", response_model=WorkflowNodeMappingListResponse)
async def list_mappings_by_route(
    route_id: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkflowNodeMapping)
        .where(WorkflowNodeMapping.route_id == route_id)
        .order_by(WorkflowNodeMapping.created_at)
    )
    items = result.scalars().all()
    return WorkflowNodeMappingListResponse(items=list(items), total=len(items))


@router.post("/workflow/{route_id}", response_model=WorkflowNodeMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_mapping(
    route_id: str,
    mapping: WorkflowNodeMappingCreate,
    db: AsyncSession = Depends(get_db)
):
    # Verify route exists
    route_result = await db.execute(select(WorkflowRoute).where(WorkflowRoute.id == route_id))
    if not route_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    db_mapping = WorkflowNodeMapping(**mapping.model_dump())
    db.add(db_mapping)
    await db.flush()
    await db.refresh(db_mapping)
    return db_mapping


@router.put("/{mapping_id}", response_model=WorkflowNodeMappingResponse)
async def update_mapping(
    mapping_id: str,
    mapping_update: WorkflowNodeMappingUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WorkflowNodeMapping).where(WorkflowNodeMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="映射不存在")

    update_data = mapping_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(mapping, key, value)

    await db.flush()
    await db.refresh(mapping)
    return mapping


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(mapping_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WorkflowNodeMapping).where(WorkflowNodeMapping.id == mapping_id)
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="映射不存在")

    await db.delete(mapping)
    return None