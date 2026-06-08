from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, TokenRefreshRequest, UserResponse
from app.services.auth_service import (
    verify_password, create_access_token,
    create_refresh_token, decode_token, get_password_hash
)
from app.api.deps import get_current_user_tenant


router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    access_token = create_access_token(data={
        "sub": user.id,
        "username": user.username,
        "tenant_id": user.tenant_id,
    })
    refresh_token = create_refresh_token(data={
        "sub": user.id,
        "tenant_id": user.tenant_id,
    })

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌")

    tid = payload.get("tenant_id")
    if not tid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新令牌缺少 tenant_id")

    result = await db.execute(
        select(User).where(User.id == payload["sub"], User.tenant_id == tid)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")

    access_token = create_access_token(data={
        "sub": user.id,
        "username": user.username,
        "tenant_id": user.tenant_id,
    })
    new_refresh_token = create_refresh_token(data={
        "sub": user.id,
        "tenant_id": user.tenant_id,
    })

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    ctx: tuple = Depends(get_current_user_tenant),
):
    """返回当前登录用户信息（包含 tenant_id）"""
    user, _ = ctx
    return user
