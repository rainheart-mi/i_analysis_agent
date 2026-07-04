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
from app.services.crypto import encrypt_password, decrypt_password
from app.services.n8n_service import get_n8n_service
from app.services.tenant_query import scoped_query, scoped_query_by_id, apply_tenant


router = APIRouter()


@router.get("", response_model=List[N8NEnvironmentResponse])
async def list_environments(
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(
        scoped_query(db, N8NEnvironment, ctx.tenant_id)
        .order_by(N8NEnvironment.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=N8NEnvironmentResponse, status_code=status.HTTP_201_CREATED)
async def create_environment(
    env: N8NEnvironmentCreate,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    payload = env.model_dump()
    # 入站 password 明文 → 落库前加密为 password_enc；
    # ORM 没有 password 字段，所以要从 payload 弹出，避免 setattr 失败
    plain_password = payload.pop("password", None)
    payload["password_enc"] = encrypt_password(plain_password) if plain_password else None
    db_env = apply_tenant(N8NEnvironment(**payload), ctx.tenant_id)
    db.add(db_env)
    await db.flush()
    await db.refresh(db_env)
    return db_env


@router.get("/{env_id}", response_model=N8NEnvironmentResponse)
async def get_environment(
    env_id: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(scoped_query_by_id(db, N8NEnvironment, env_id, ctx.tenant_id))
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="环境不存在")
    return env


@router.put("/{env_id}", response_model=N8NEnvironmentResponse)
async def update_environment(
    env_id: str,
    env_update: N8NEnvironmentUpdate,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(scoped_query_by_id(db, N8NEnvironment, env_id, ctx.tenant_id))
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="环境不存在")

    update_data = env_update.model_dump(exclude_unset=True)
    # 禁止跨字段篡改 tenant_id
    update_data.pop("tenant_id", None)

    # password 字段特殊处理：明文 → password_enc
    # 配合 exclude_unset：未传=不动；传 None 或空串=置空（清除凭据）
    if "password" in update_data:
        plain_password = update_data.pop("password")
        if plain_password:
            update_data["password_enc"] = encrypt_password(plain_password)
        else:
            update_data["password_enc"] = None

    for key, value in update_data.items():
        setattr(env, key, value)

    await db.flush()
    await db.refresh(env)
    return env


@router.delete("/{env_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment(
    env_id: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(scoped_query_by_id(db, N8NEnvironment, env_id, ctx.tenant_id))
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="环境不存在")

    await db.delete(env)
    return None


@router.post("/{env_id}/test", response_model=N8NEnvironmentTestResponse)
async def test_environment(
    env_id: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(scoped_query_by_id(db, N8NEnvironment, env_id, ctx.tenant_id))
    env = result.scalar_one_or_none()
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="环境不存在")

    # 用 N8NService.test_connection 真实测一次 GET /rest
    # 带上 Basic Auth 凭据（如果配置了），避免因认证不通过误判
    basic_password = (
        decrypt_password(env.password_enc) if env.password_enc else None
    )
    n8n = get_n8n_service(
        env.base_url,
        env.api_key,
        "production",
        env.username,
        basic_password,
    )
    success, message = await n8n.test_connection()
    return N8NEnvironmentTestResponse(success=success, message=message)
