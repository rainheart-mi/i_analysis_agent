"""AI 聊天面板 API。

- POST /api/v1/chat/stream  → SSE 流式代理到 AgentScope Java
- GET  /api/v1/chat/history → 拉取历史会话（代理到 AgentScope SessionController）
- GET  /api/v1/chat/sessions → 列出当前用户的所有 session（侧边栏历史入口）
- GET  /api/v1/chat/health  → 探活 AgentScope 后端
"""
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_tenant
from app.config import settings
from app.database import get_db
from app.schemas.chat import ChatHealthResponse, ChatStreamRequest
from app.services import agentscope_proxy
from app.services.agentscope_proxy import NodeExecutionNotFound

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatHistoryItem(BaseModel):
    """单条历史消息（OpenAI 风格）。"""
    role: str
    content: str
    name: Optional[str] = None
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    """历史会话响应。source 字段是后端诊断标签，不透传给前端。"""
    node_execution_id: str
    messages: list[ChatHistoryItem]
    error: Optional[str] = None


@router.post("/stream")
async def chat_stream(
    body: ChatStreamRequest,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """前端 ChatPanel 调用的流式端点。

    流程：
    1. 校验 node_execution_id 属于当前 tenant
    2. 从 artifact_data 注入 system context
    3. 转发到 AgentScope Java，透传 SSE
    """
    try:
        node = await agentscope_proxy.load_node_execution(db, body.node_execution_id, ctx.tenant_id)
    except NodeExecutionNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"节点执行记录 {body.node_execution_id} 不存在或无权访问",
        )

    if node.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"节点状态为 {node.status}，需等待执行完成",
        )

    generator = agentscope_proxy.stream_chat_completion(node, ctx.user_id, body.messages)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲，保证流式
        },
    )


@router.get("/history", response_model=ChatHistoryResponse)
async def chat_history(
    node_execution_id: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """拉取指定节点执行的历史 AI 对话。

    数据源是 AgentScope 服务端（按 X-Session-Id = node_execution.id 落库）。
    本接口只做 tenant 隔离 + 代理，不在本服务持久化。
    """
    try:
        node = await agentscope_proxy.load_node_execution(db, node_execution_id, ctx.tenant_id)
    except NodeExecutionNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"节点执行记录 {node_execution_id} 不存在或无权访问",
        )

    if node.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"节点状态为 {node.status}，需等待执行完成",
        )

    messages, source_or_error = await agentscope_proxy.fetch_session_history(ctx.user_id, node)
    # fetch_session_history 在失败时把错误信息放在第二个返回值（不是真正的 source）
    # AgentScope SessionController.loadMessages 合法 source 值：
    #   "agent-factory-cache"        — 进程内 AgentFactory 缓存命中
    #   "session:agent_state"        — Redis 持久化命中（冷启动后回退）
    #   "agent-context"              — 上述两条都没命中（无历史或 Redis 未启用）的默认兜底
    # 除以上三种以外的非空字符串才算错误（如 upstream_5xx / ConnectError / 异常类名）
    KNOWN_SOURCES = ("agent-factory-cache", "session:agent_state", "agent-context")
    is_source = source_or_error in KNOWN_SOURCES
    if is_source:
        return ChatHistoryResponse(
            node_execution_id=node.id,
            messages=[ChatHistoryItem(**m) for m in messages],
        )
    return ChatHistoryResponse(
        node_execution_id=node.id,
        messages=[],
        error=source_or_error,
    )


@router.get("/sessions")
async def chat_sessions(
    ctx = Depends(get_current_user_tenant),
):
    """列出当前用户的所有 AgentScope session（侧边栏历史入口）。

    代理到 AgentScope GET /v1/sessions?userId={user.id}，透传响应；
    上游不可达 / 鉴权失败时降级返空 + error 标记。
    """
    url = f"{settings.AGENTSCOPE_URL.rstrip('/')}/v1/sessions"
    headers = {"X-Internal-Token": settings.AGENTSCOPE_INTERNAL_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=settings.AGENTSCOPE_TIMEOUT) as client:
            resp = await client.get(url, params={"userId": ctx.user_id}, headers=headers)
            if resp.status_code != 200:
                body = await resp.aread()
                logger.error("agentscope list sessions %d: %s", resp.status_code, body[:200])
                return {
                    "userId": ctx.user_id,
                    "count": 0,
                    "sessions": [],
                    "error": f"upstream_{resp.status_code}",
                }
            return resp.json()
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.error("agentscope list sessions fetch failed: %s", e)
        return {
            "userId": ctx.user_id,
            "count": 0,
            "sessions": [],
            "error": e.__class__.__name__,
        }
    except Exception as e:
        logger.exception("agentscope list sessions unexpected error: %s", e)
        return {
            "userId": ctx.user_id,
            "count": 0,
            "sessions": [],
            "error": f"{e.__class__.__name__}: {e}",
        }


@router.get("/health", response_model=ChatHealthResponse)
async def chat_health():
    """探活 AgentScope Java 后端。"""
    from app.config import settings

    ok, detail = await agentscope_proxy.check_agentscope_health()
    return ChatHealthResponse(ok=ok, agentscope_url=settings.AGENTSCOPE_URL, detail=detail)
