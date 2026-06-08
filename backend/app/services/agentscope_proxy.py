"""AgentScope Java 后端代理服务。

职责：
1. 校验 node_execution_id 存在且属于当前 tenant。
2. 从 NodeExecution.artifact_data 抽取工作流执行结果，构造 system message 注入上下文。
3. 用 httpx.AsyncClient 流式转发到 Java 端 /v1/chat/completions，
   把上游的 SSE 行原样回传给前端，零格式转换。
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.task import NodeExecution
from app.services.tenant_query import scoped_query_by_id
from app.schemas.chat import ChatMessage

logger = logging.getLogger(__name__)


class NodeExecutionNotFound(Exception):
    """节点不存在或不属于当前 tenant。"""


def _extract_workflow_context(artifact_data: dict | None) -> str:
    """从 artifact_data.processedData 抽取关键字段，构造注入提示词。

    优先使用 aiResponse.rawOutput（N8N 产出的 AI 文本），否则退到 fields 整体序列化。
    """
    if not artifact_data:
        return "（该节点未产出 artifact_data）"

    processed = artifact_data.get("processedData") or artifact_data
    if not isinstance(processed, dict):
        return f"（artifact_data 格式异常：{type(processed).__name__}）"

    # 1) 优先取 aiResponse.rawOutput
    ai_response = processed.get("aiResponse")
    if isinstance(ai_response, dict):
        raw = ai_response.get("rawOutput")
        if isinstance(raw, str) and raw.strip():
            return raw

    # 2) 其次 fields
    fields = processed.get("fields")
    if isinstance(fields, dict) and fields:
        try:
            return json.dumps(fields, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return str(fields)

    # 3) 兜底：整个 processed 的 JSON
    try:
        return json.dumps(processed, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(processed)


def build_chat_messages(
    node_execution: NodeExecution,
    user_messages: list[ChatMessage],
) -> list[dict]:
    """构造发给 AgentScope 的 OpenAI 风格 messages 列表。

    - 在 user 消息之前插入一条 system 消息，带上工作流执行结果作为上下文
    - 保留前端传来的 user 消息原序
    """
    context = _extract_workflow_context(node_execution.artifact_data)
    system_msg = {
        "role": "system",
        "content": (
            "你是一个数据分析助手。下面是当前工作流节点的执行结果，"
            "请基于该结果回答用户后续的提问。\n\n"
            f"工作流执行结果：\n{context}"
        ),
    }
    return [system_msg] + [m.model_dump() for m in user_messages]


async def load_node_execution(db: AsyncSession, node_execution_id: str, tenant_id: str) -> NodeExecution:
    """带 tenant 隔离地加载 NodeExecution。找不到抛 NodeExecutionNotFound。"""
    result = await db.execute(
        scoped_query_by_id(db, NodeExecution, node_execution_id, tenant_id)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise NodeExecutionNotFound(f"NodeExecution {node_execution_id} not found")
    return node


async def stream_chat_completion(
    node_execution: NodeExecution,
    user_id: str,
    user_messages: list[ChatMessage],
) -> AsyncIterator[bytes]:
    """流式调用 AgentScope Java 后端，把上游 SSE 行原样回传。

    失败时 yield 一条 JSON 错误事件，前端可识别降级。
    """
    messages = build_chat_messages(node_execution, user_messages)
    payload = {
        "model": settings.AGENTSCOPE_MODEL,
        "messages": messages,
        "stream": True,
    }
    headers = {
        "Content-Type": "application/json",
        "X-Internal-Token": settings.AGENTSCOPE_INTERNAL_TOKEN,
        "X-Session-Id": node_execution.id,
        "X-User-Id": user_id,
    }
    url = f"{settings.AGENTSCOPE_URL.rstrip('/')}/v1/chat/completions"

    logger.info("proxy stream -> %s sessionId=%s userId=%s msgs=%d", url, node_execution.id, user_id, len(messages))

    try:
        async with httpx.AsyncClient(timeout=settings.AGENTSCOPE_TIMEOUT) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    logger.error("agentscope upstream %d: %s", resp.status_code, body[:200])
                    err = json.dumps({
                        "error": "agentscope_upstream_error",
                        "status": resp.status_code,
                    }, ensure_ascii=False)
                    yield f"data: {err}\n\n".encode("utf-8")
                    return

                async for chunk in resp.aiter_bytes():
                    if chunk:
                        yield chunk
    except httpx.ConnectError as e:
        logger.error("agentscope connect error: %s", e)
        err = json.dumps({"error": "agentscope_unavailable"}, ensure_ascii=False)
        yield f"data: {err}\n\n".encode("utf-8")
    except httpx.TimeoutException as e:
        logger.error("agentscope timeout: %s", e)
        err = json.dumps({"error": "agentscope_timeout"}, ensure_ascii=False)
        yield f"data: {err}\n\n".encode("utf-8")
    except Exception as e:
        logger.exception("agentscope unexpected error: %s", e)
        err = json.dumps({"error": "agentscope_internal_error"}, ensure_ascii=False)
        yield f"data: {err}\n\n".encode("utf-8")


async def fetch_session_history(
    user_id: str,
    node: NodeExecution,
) -> tuple[list[dict], str | None]:
    """从 AgentScope 拉取指定 (userId, sessionId) 的消息历史。

    Returns (messages, source)：
    - messages: AgentScope 返回的 messages 列表（可能含 system/tool 角色，由调用方决定是否过滤）
    - source: AgentScope 响应里的 source 字段，便于诊断（"session:agent_state" / "agent-context" / None）

    失败时不抛异常，返回 ([], 错误信息)，让上游以空历史 + 错误日志降级展示。
    """
    from urllib.parse import quote
    url = (
        f"{settings.AGENTSCOPE_URL.rstrip('/')}"
        f"/v1/sessions/{node.id}/messages"
        f"?userId={quote(user_id, safe='')}"
    )
    headers = {"X-Internal-Token": settings.AGENTSCOPE_INTERNAL_TOKEN}
    try:
        async with httpx.AsyncClient(timeout=settings.AGENTSCOPE_TIMEOUT) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                body = await resp.aread()
                logger.error("agentscope history %d: %s", resp.status_code, body[:200])
                return [], f"upstream_{resp.status_code}"
            data = resp.json()
            if isinstance(data, dict) and data.get("error"):
                logger.warning("agentscope history error: %s", data.get("error"))
                return [], str(data.get("error"))
            messages = data.get("messages") or []
            return messages, data.get("source")
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.error("agentscope history fetch failed: %s", e)
        return [], e.__class__.__name__
    except Exception as e:
        logger.exception("agentscope history unexpected error: %s", e)
        return [], f"{e.__class__.__name__}: {e}"


async def check_agentscope_health() -> tuple[bool, str | None]:
    """探活：调 Java 端 GET /actuator/health（无需 token）。"""
    url = f"{settings.AGENTSCOPE_URL.rstrip('/')}/actuator/health"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return True, None
            return False, f"status {resp.status_code}"
    except Exception as e:
        return False, str(e)
