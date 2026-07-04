"""鉴权依赖项 — 多租户/组织/员工上下文注入

业务端点通过 Depends(get_current_user_tenant) 获得 AuthContext，
JWT 由外部 token 服务器的 /web/auth/token/validate API 完成校验并返回用户/租户/组织信息。

Token 读取顺序（对齐 Java 项目 TokenManager.getTokenFromRequest）：
  1. settings.JWT_HEADER_NAME 指定的 header（默认 `jwt`）
  2. settings.JWT_COOKIE_NAME 指定的 cookie（默认 `jwt`）
  3. `Authorization: Bearer <token>`（兼容旧前端）
"""
import logging
from dataclasses import dataclass
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.token_validation import (
    TokenValidationError,
    decode_jwt_payload,
    validate_token_external,
)


logger = logging.getLogger(__name__)


@dataclass
class AuthContext:
    """认证上下文，主要信息由外部 token 校验 API 提供。

    字段来源：
      tenant_id / user_id / user_name / org_id     — 来自 validate API 响应
      org_type / emp_id / emp_name                 — 来自 JWT payload（ot/ei/en claims）
    """
    tenant_id: str | None = None
    user_id: str | None = None
    user_name: str | None = None
    org_id: str | None = None
    org_type: str | None = None
    emp_id: str | None = None
    emp_name: str | None = None


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


def _icn_to_str(raw: int | str | None) -> str | None:
    """将 validate API 返回的 ICN.id（Java long → 我们存 string）统一转 str。"""
    if raw is None:
        return None
    return str(raw)


async def get_current_user_tenant(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """校验 JWT 并构建认证上下文。

    流程：
      1. 从请求中提取 JWT
      2. 调用外部 token 服务器 /token/validate API 验证
      3. 根据 API 响应（tenant / user / organization）构建 AuthContext
      4. 额外从 JWT payload 提取 ot/ei/en 等 claims
    """
    path = request.url.path

    # 1. Token validation 关闭：完全跳过 token 校验，直接用 default user
    #    部署文档：.env 配 TOKEN_VALIDATION_ENABLED=false + DEFAULT_TENANT_ID + DEFAULT_USER_ID
    #    即"无 token 直连"模式，前端不需要携带 jwt
    if not settings.TOKEN_VALIDATION_ENABLED:
        ctx = AuthContext(
            tenant_id=settings.DEFAULT_TENANT_ID,
            user_id=settings.DEFAULT_USER_ID,
            user_name=settings.DEFAULT_USER_NAME,
        )
        request.state.auth_context = ctx
        logger.info(
            "[auth] token validation disabled, using default: path=%s tenant=%s user=%s",
            path, ctx.tenant_id, ctx.user_id,
        )
        return ctx

    # 2. Token validation 开启：要求 token，调外部 API 验证
    token = _extract_token(request)
    logger.warning("[auth] path=%s has_token=%s token_len=%s token_preview=%s...%s",
                   path, bool(token),
                   len(token) if token else 0,
                   token[:50] if token else "",
                   token[-20:] if token else "")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 调用外部 API 验证
    try:
        result = await validate_token_external(token)
    except TokenValidationError as e:
        logger.error("[auth] token 服务器异常: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )

    if not result["valid"]:
        logger.warning("[auth] token 校验失败: %s", result.get("message"))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result["message"],
        )

    data = result["data"]

    # ---- 从 validate API 响应提取核心字段 ----
    tenant_info = data.get("tenant") or {}
    user_info = data.get("user") or {}
    org_info = data.get("organization") or {}

    # ---- 额外从 JWT payload 提取 ot/ei/en ----
    jwt_payload = decode_jwt_payload(token)

    ctx = AuthContext(
        tenant_id=_icn_to_str(tenant_info.get("id")),
        user_id=_icn_to_str(user_info.get("id")),
        user_name=user_info.get("name"),
        org_id=_icn_to_str(org_info.get("id")),
        org_type=str(jwt_payload.get("ot")) if jwt_payload.get("ot") else None,
        emp_id=str(jwt_payload.get("ei")) if jwt_payload.get("ei") else None,
        emp_name=str(jwt_payload.get("en")) if jwt_payload.get("en") else None,
    )

    # 跳过本地租户校验：tenant_id 来自外部 token 服务器的可信响应，
    # 多租户数据隔离由 scoped_query(scoped_query_by_id) 在业务查询中强制应用。

    logger.info("[auth] AuthContext 构建完成: tenant=%s user=%s org=%s",
             ctx.tenant_id, ctx.user_id, ctx.org_id)

    # 存入 request.state 供 services 层使用
    request.state.auth_context = ctx

    return ctx