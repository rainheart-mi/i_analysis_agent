"""鉴权依赖项 - 多租户上下文注入

业务端点通过 Depends(get_current_user_tenant) 自动获得 (user, tenant_id)，
所有数据库操作必须以 tenant_id 隔离。

Token 读取顺序（对齐 Java 项目 TokenManager.getTokenFromRequest）：
  1. settings.JWT_HEADER_NAME 指定的 header（默认 `jwt`）
  2. settings.JWT_COOKIE_NAME 指定的 cookie（默认 `jwt`）
  3. `Authorization: Bearer <token>`（兼容旧前端）
"""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_token


def _extract_token(request: Request) -> str | None:
    """从请求中按优先级提取 JWT token。"""
    # 1. 优先：自定义 header（如 `jwt: xxx`）—— 对齐 Java 项目
    header_name = settings.JWT_HEADER_NAME
    if header_name:
        token = request.headers.get(header_name)
        if token:
            return token.strip()

    # 2. 次选：同名 cookie —— 对齐 Java 项目
    cookie_name = settings.JWT_COOKIE_NAME
    if cookie_name:
        token = request.cookies.get(cookie_name)
        if token:
            return token.strip()

    # 3. 兜底：Authorization: Bearer —— 兼容旧前端
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    return None


async def get_current_user_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> tuple[User, str]:
    """从 JWT 解析出当前用户与所属租户 ID。

    Returns:
        (user, tenant_id) 元组。调用方解构：`user, tid = ctx`
    """
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tid = payload.get("tenant_id")
    if not tid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌缺少 tenant_id",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌缺少 sub",
        )

    # 双重校验：sub 与 tenant_id 必须一致（防 token 篡改/跨租户 token 复用）
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tid)
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用",
        )

    return user, tid
