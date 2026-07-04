"""AgentScope Java 后端代理服务。

职责：
1. 校验 node_execution_id 存在且属于当前 tenant。
2. 从 NodeExecution.artifact_data 抽取工作流执行结果，构造 system message 注入上下文。
3. 用 httpx.AsyncClient 流式转发到 Java 端 /v1/chat/completions，
   把上游的 SSE 行原样回传给前端，零格式转换。
4. (post-action) 调 AgentScope 其他端点（当前白名单：/v1/price-band/analyze），
   把上一节点 artifact_data 注入请求体；同步阻塞，结果落 NodeExecution.artifact_data。
"""
from __future__ import annotations

import json
import time
import logging
from typing import AsyncIterator, Awaitable, Callable

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.task import NodeExecution, TaskInstance
from app.models.mapping import WorkflowNodeMapping
from app.services.tenant_query import scoped_query_by_id
from app.schemas.chat import ChatMessage

logger = logging.getLogger(__name__)


class NodeExecutionNotFound(Exception):
    """节点不存在或不属于当前 tenant。"""


class PostActionError(Exception):
    """Post-action 调用失败：模板错误、API 不在白名单、上游非 200、网络/超时等。

    Celery 任务接住后写入 `node.error_message` 并标 `status="failed"`。
    """


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


# ========== Post-action（节点完成后调 AgentScope 同步端点） ==========

async def call_post_action(
    agent_mapping: WorkflowNodeMapping,
    parent_node: NodeExecution,
    task: TaskInstance,
) -> dict:
    """同步阻塞调 AgentScope post-action 端点，返回响应 dict。

    - 配置从 `agent_mapping.post_action_config` 自己读取（DAG 模型下 agent 节点自带配置）
    - 把 `parent_node.artifact_data` 当 `artifact` 上下文注入
    - 调 `AGENTSCOPE_URL + api_path`，复用 X-Internal-Token / X-Session-Id / X-User-Id
    - `api_path` 必须在 `KNOWN_POST_ACTIONS` 白名单内
    - 失败抛 `PostActionError`（由 Celery 任务接住写 `node.error_message`）
    """
    from app.services.post_action_template import (
        KNOWN_POST_ACTIONS, resolve_template, TemplateError,
    )

    cfg = agent_mapping.post_action_config or {}
    if not cfg.get("enabled"):
        raise PostActionError("post_action_not_enabled")

    api_path = cfg.get("api_path")
    method = (cfg.get("method") or "POST").upper()
    timeout = cfg.get("timeout_sec") or settings.AGENTSCOPE_TIMEOUT

    if not api_path:
        raise PostActionError("missing_api_path")
    allowed = {entry["api_path"] for entry in KNOWN_POST_ACTIONS.values()}
    if api_path not in allowed:
        raise PostActionError(f"unknown_api_path:{api_path}")

    body_template = cfg.get("request_body_template")
    if not isinstance(body_template, dict):
        raise PostActionError("missing_request_body_template")

    # user_id / session_id / artifact 三种根路径
    artifact = parent_node.artifact_data or {}
    if not isinstance(artifact, dict):
        # n8n 节点完成时一定写入 dict；若非 dict（历史脏数据）当空 dict
        artifact = {}
    ctx = {
        "user_id": task.user_id,
        "session_id": parent_node.id,  # 与 chat 一致：session = 父 n8n node_execution.id
        "artifact": artifact,
    }
    try:
        body = resolve_template(body_template, ctx)
    except TemplateError as e:
        raise PostActionError(f"template_error:{e}") from e

    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Internal-Token": settings.AGENTSCOPE_INTERNAL_TOKEN,
        "X-Session-Id": parent_node.id,
        "X-User-Id": task.user_id,
    }
    url = f"{settings.AGENTSCOPE_URL.rstrip('/')}{api_path}"

    logger.info(
        "post-action -> %s sessionId=%s userId=%s method=%s",
        url, parent_node.id, task.user_id, method,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(method, url, json=body, headers=headers)
    except httpx.ConnectError as e:
        raise PostActionError(
            f"agentscope_unavailable:{e.__class__.__name__}:{e}"
        ) from e
    except httpx.TimeoutException as e:
        # httpx.TimeoutException.__str__ 默认空字符串，附加 class 名 + 配置的 timeout
        raise PostActionError(
            f"agentscope_timeout:{e.__class__.__name__} (timeout={timeout}s)"
        ) from e
    except Exception as e:
        raise PostActionError(
            f"agentscope_internal_error:{e.__class__.__name__}:{e}"
        ) from e

    if resp.status_code != 200:
        body_preview = (resp.text or "")[:200]
        logger.error(
            "post-action upstream %d: %s", resp.status_code, body_preview,
        )
        raise PostActionError(f"upstream_{resp.status_code}:{body_preview}")

    try:
        data = resp.json()
    except Exception as e:
        raise PostActionError(f"upstream_invalid_json:{e}") from e

    if isinstance(data, dict) and data.get("error"):
        raise PostActionError(f"upstream_error:{data['error']}")

    if not isinstance(data, dict):
        raise PostActionError(f"upstream_unexpected_payload:{type(data).__name__}")

    return data


# ========== Streaming post-action（价格带分析 SSE） ==========

async def stream_price_band_analyze(
    payload: dict,
    user_id: str,
    session_id: str,
    on_event: Callable[[dict], Awaitable[None]] | None = None,
) -> AsyncIterator[bytes]:
    """代理 AgentScope `/v1/price-band/analyze/stream` 的 SSE 流。

    设计要点：
    - 透传 SSE 帧到前端（零格式转换），由前端按 amis setData 语义解析。
    - on_event 回调用于增量写 DB artifact_data（中间态 + 最终态）。
      仅对非 ping 事件触发；ping 是 keepalive，库内无需落库。
    - 错误三段式 try/except 与 stream_chat_completion 一致：
      ConnectError → agentscope_unavailable
      TimeoutException → agentscope_timeout
      其他 → agentscope_internal_error
    - 流式必须 timeout=None：上游可能持续 1~5min，
      前端有 30s 无 ping abort + 5min 总 timeout 兜底。
    """
    headers = {
        "Content-Type": "application/json",
        "X-Internal-Token": settings.AGENTSCOPE_INTERNAL_TOKEN,
        "X-User-Id": user_id,
        "X-Session-Id": session_id,
        "Accept": "text/event-stream",
    }
    url = f"{settings.AGENTSCOPE_URL.rstrip('/')}/v1/price-band/analyze/stream"

    logger.info(
        "stream_price_band -> %s sessionId=%s userId=%s",
        url, session_id, user_id,
    )

    # ★ 自动把 userId / sessionId 注入到 payload body
    #   AgentScope 上游要求这两个字段在 body（不是 headers）：
    #     {"type":"error","code":"BAD_REQUEST","message":"userId and sessionId are required"}
    #   headers 仍保留 X-User-Id / X-Session-Id 用于其他端点（如 chat history）
    #   调用方无需关心此细节，传入 payload 即可
    enriched_payload = {
        **payload,
        "userId": user_id,
        "sessionId": session_id,
    }

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", url, json=enriched_payload, headers=headers) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    logger.error(
                        "agentscope stream upstream %d: %s",
                        resp.status_code, body[:200],
                    )
                    err = json.dumps({
                        "error": "agentscope_upstream_error",
                        "status": resp.status_code,
                        "detail": body.decode("utf-8", errors="replace")[:500],
                    }, ensure_ascii=False)
                    yield f"data: {err}\n\n".encode("utf-8")
                    return

                buffer = b""
                chunk_count = 0
                last_log_time = time.time()
                import time as _time_inner
                t_start_inner = _time_inner.time()
                logger.info("[stream_price_band] entering aiter_bytes loop")
                async for chunk in resp.aiter_bytes():
                    if not chunk:
                        continue
                    chunk_count += 1
                    elapsed_ms = int((_time_inner.time() - t_start_inner) * 1000)
                    # 0) 诊断日志：每个 chunk 都记录（前 50 个），之后每 5 秒打一次汇总
                    now = time.time()
                    if chunk_count <= 50 or now - last_log_time > 5:
                        preview = chunk[:200].decode("utf-8", errors="replace").replace("\n", "\\n")
                        logger.info(
                            "stream_price_band chunk #%d elapsed=%dms size=%d preview=%s",
                            chunk_count, elapsed_ms, len(chunk), preview,
                        )
                        last_log_time = now
                    # 1) 透传给前端（不做任何格式转换）
                    yield chunk
                    logger.info("stream_price_band chunk #%d yielded", chunk_count)
                    # 2) 行级解析，零拷贝友好（标准 SSE 以 \n\n 切帧）
                    buffer += chunk
                    while b"\n\n" in buffer:
                        frame, buffer = buffer.split(b"\n\n", 1)
                        for line in frame.split(b"\n"):
                            if not line.startswith(b"data: "):
                                continue
                            try:
                                ev = json.loads(line[6:].decode("utf-8"))
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                continue
                            if on_event is None:
                                continue
                            if ev.get("type") == "ping":
                                # ping 是 keepalive，库内无需落库
                                continue
                            logger.info(
                                "stream_price_band on_event type=%s req=%s",
                                ev.get("type"), ev.get("requestId"))
                            await on_event(ev)
                logger.info("stream_price_band total chunks received: %d", chunk_count)
    except httpx.ConnectError as e:
        logger.error("agentscope stream connect error: %s", e)
        err = json.dumps({"error": "agentscope_unavailable"}, ensure_ascii=False)
        yield f"data: {err}\n\n".encode("utf-8")
    except httpx.TimeoutException as e:
        logger.error("agentscope stream timeout: %s", e)
        err = json.dumps({"error": "agentscope_timeout"}, ensure_ascii=False)
        yield f"data: {err}\n\n".encode("utf-8")
    except Exception as e:
        logger.exception("agentscope stream unexpected error: %s", e)
        err = json.dumps({
            "error": "agentscope_internal_error",
            "detail": str(e)[:200],
        }, ensure_ascii=False)
        yield f"data: {err}\n\n".encode("utf-8")

