"""
外部 Token 校验服务

调用 token 服务器的 /seqmappro/s/web/auth/token/validate API 来验证 JWT，
替代本地验签（后端不具备 JWT 签发密钥）。
"""
import json
import base64
import logging
from typing import Any

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


class TokenValidationError(Exception):
    """token 服务器不可达或返回异常时抛出"""
    pass


def decode_jwt_payload(token: str) -> dict[str, Any]:
    """解码 JWT payload（不解验签名）。

    仅用于获取 claims 中 validate API 未返回的额外字段（如 ot/ei/en）。
    调用前必须先经过外部 validate API 验证.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        padding = 4 - len(parts[1]) % 4
        if padding != 4:
            parts[1] += "=" * padding
        payload_bytes = base64.urlsafe_b64decode(parts[1])
        return json.loads(payload_bytes)
    except Exception as e:
        logger.warning("JWT payload 解码失败: %s", e)
        return {}


async def validate_token_external(token: str) -> dict:
    """调用外部 token 校验 API 验证 JWT。

    Returns:
        {"valid": True, "data": {...}}          — 验证通过，data 为 BTokenValidateResult
        {"valid": False, "message": "..."}      — 验证失败
        raises TokenValidationError              — 网络/服务器异常
    """
    url = settings.TOKEN_VALIDATE_URL
    token_preview = f"{token[:30]}...{token[-10:]}" if len(token) > 40 else token
    logger.info("[token_validate] 开始调用: url=%s token_len=%s token=%s",
                url, len(token), token_preview)

    async with httpx.AsyncClient(
            timeout=settings.TOKEN_VALIDATE_TIMEOUT,
            verify=settings.TOKEN_VALIDATE_VERIFY_SSL,
    ) as client:
        try:
            resp = await client.get(url, headers={"jwt": token})
            logger.info(
                "[token_validate] HTTP %s | body_preview=%s",
                resp.status_code, resp.text[:300],
            )
        except httpx.ConnectError as e:
            logger.error("[token_validate] 连接失败: %s", e, exc_info=True)
            raise TokenValidationError(f"Token 服务器不可达: {e}") from e
        except httpx.TimeoutException as e:
            logger.error("[token_validate] 超时: %s", e, exc_info=True)
            raise TokenValidationError(f"Token 服务器超时: {e}") from e
        except Exception as e:
            logger.error("[token_validate] 未知异常: %s", e, exc_info=True)
            raise TokenValidationError(f"Token 服务器请求异常: {e}") from e

        if resp.status_code != 200:
            logger.warning(
                "[token_validate] 非 200 状态码: %s body=%s",
                resp.status_code, resp.text[:500],
            )
            raise TokenValidationError(
                f"Token 服务器返回异常状态码: {resp.status_code}"
            )

        try:
            body = resp.json()
        except Exception as e:
            logger.error("[token_validate] 响应 JSON 解析失败: %s body=%s", e, resp.text[:500], exc_info=True)
            raise TokenValidationError(f"Token 服务器响应非 JSON: {e}") from e

        if not body.get("success"):
            msg = body.get("message", "Token 校验失败")
            logger.warning("[token_validate] 校验失败: %s", msg)
            return {
                "valid": False,
                "message": msg,
            }

        logger.info("[token_validate] 校验成功: tenant=%s user=%s",
                     body.get("data", {}).get("tenant", {}).get("id"),
                     body.get("data", {}).get("user", {}).get("id"))
        return {"valid": True, "data": body["data"]}