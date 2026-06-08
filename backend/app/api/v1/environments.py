from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models.environment import N8NEnvironment
from app.schemas.environment import (
    N8NEnvironmentCreate, N8NEnvironmentUpdate,
    N8NEnvironmentResponse, N8NEnvironmentTestResponse
)
from app.api.deps import get_current_user_tenant
from app.services.tenant_query import scoped_query, scoped_query_by_id, apply_tenant


router = APIRouter()


@router.get("", response_model=List[N8NEnvironmentResponse])
async def list_environments(
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    result = await db.execute(
        scoped_query(db, N8NEnvironment, tid)
        .order_by(N8NEnvironment.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=N8NEnvironmentResponse, status_code=status.HTTP_201_CREATED)
async def create_environment(
    env: N8NEnvironmentCreate,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    db_env = apply_tenant(N8NEnvironment(**env.model_dump()), tid)
    db.add(db_env)
    await db.flush()
    await db.refresh(db_env)
    return db_env


@router.get("/{env_id}", response_model=N8NEnvironmentResponse)
async def get_environment(
    env_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    result = await db.execute(scoped_query_by_id(db, N8NEnvironment, env_id, tid))
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="环境不存在")
    return env


@router.put("/{env_id}", response_model=N8NEnvironmentResponse)
async def update_environment(
    env_id: str,
    env_update: N8NEnvironmentUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    result = await db.execute(scoped_query_by_id(db, N8NEnvironment, env_id, tid))
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="环境不存在")

    update_data = env_update.model_dump(exclude_unset=True)
    # 禁止跨字段篡改 tenant_id
    update_data.pop("tenant_id", None)
    for key, value in update_data.items():
        setattr(env, key, value)

    await db.flush()
    await db.refresh(env)
    return env


@router.delete("/{env_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment(
    env_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    result = await db.execute(scoped_query_by_id(db, N8NEnvironment, env_id, tid))
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="环境不存在")

    await db.delete(env)
    return None


@router.post("/{env_id}/test", response_model=N8NEnvironmentTestResponse)
async def test_environment(
    env_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    _, tid = ctx
    result = await db.execute(scoped_query_by_id(db, N8NEnvironment, env_id, tid))
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="环境不存在")

    # TODO: 实现实际的 N8N 连接测试
    return N8NEnvironmentTestResponse(success=True, message="连接成功")
