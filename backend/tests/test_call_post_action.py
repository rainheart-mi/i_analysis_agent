"""call_post_action 单测，用 respx mock httpx 拦截 AgentScope 调用。

覆盖：
- 200 成功 → 返回 dict
- 200 但响应体含 error 字段 → PostActionError
- 400 / 401 / 500 / 503 → PostActionError(upstream_xxx)
- ConnectError → PostActionError(agentscope_unavailable)
- TimeoutException → PostActionError(agentscope_timeout)
- api_path 不在白名单 → PostActionError(unknown_api_path:...)
- enabled=false → PostActionError(post_action_not_enabled)
- request_body_template 缺失 → PostActionError(missing_request_body_template)
"""
import pytest
import respx
import httpx

from app.config import settings
from app.services import agentscope_proxy
from app.services.agentscope_proxy import PostActionError


def _make_mapping(api_path="/v1/price-band/analyze", enabled=True, template=None, timeout=120):
    """构造一个最小可用的 WorkflowNodeMapping 替身（不连 DB）。"""
    class _M:
        pass
    m = _M()
    m.post_action_config = {
        "enabled": enabled,
        "api_path": api_path,
        "method": "POST",
        "timeout_sec": timeout,
        "request_body_template": template or {
            "userId": "${user_id}",
            "sessionId": "${session_id}",
            "salesData": "${artifact.processedData.salesData}",
        },
    }
    return m


def _make_node(artifact=None, node_id="node-001"):
    class _N:
        pass
    n = _N()
    n.id = node_id
    n.artifact_data = artifact
    return n


def _make_task(user_id="alice"):
    class _T:
        pass
    t = _T()
    t.id = "task-001"
    t.user_id = user_id
    return t


def _sales_artifact():
    return {
        "processedData": {
            "salesData": [{"skuId": "S001", "price": 9.9, "soldQty": 100}],
        }
    }


@pytest.mark.asyncio
@respx.mock
async def test_call_post_action_200_returns_dict():
    body = _sales_artifact()
    respx.post(f"{settings.AGENTSCOPE_URL}/v1/price-band/analyze").mock(
        return_value=httpx.Response(
            200,
            json={
                "status": 200,
                "userId": "alice",
                "sessionId": "node-001",
                "dataPath": "datasets/input-alice-session-1.json",
                "sha256": "abc",
                "rowCount": 1,
                "model": "minimaxi:MiniMax-M3",
                "finalMessage": "ok",
            },
        )
    )
    out = await agentscope_proxy.call_post_action(
        agent_mapping=_make_mapping(),
        parent_node=_make_node(body),
        task=_make_task(),
    )
    assert out["status"] == 200
    assert out["finalMessage"] == "ok"


@pytest.mark.asyncio
async def test_call_post_action_rejects_disabled():
    with pytest.raises(PostActionError) as ei:
        await agentscope_proxy.call_post_action(
            agent_mapping=_make_mapping(enabled=False),
            parent_node=_make_node(_sales_artifact()),
            task=_make_task(),
        )
    assert "post_action_not_enabled" in str(ei.value)


@pytest.mark.asyncio
async def test_call_post_action_rejects_unknown_api_path():
    with pytest.raises(PostActionError) as ei:
        await agentscope_proxy.call_post_action(
            agent_mapping=_make_mapping(api_path="/v1/evil/exfiltrate"),
            parent_node=_make_node(_sales_artifact()),
            task=_make_task(),
        )
    assert "unknown_api_path" in str(ei.value)


@pytest.mark.asyncio
async def test_call_post_action_rejects_missing_template():
    mapping = _make_mapping()
    mapping.post_action_config["request_body_template"] = None
    with pytest.raises(PostActionError) as ei:
        await agentscope_proxy.call_post_action(
            agent_mapping=mapping,
            parent_node=_make_node(_sales_artifact()),
            task=_make_task(),
        )
    assert "missing_request_body_template" in str(ei.value)


@pytest.mark.asyncio
async def test_call_post_action_template_missing_field_raises():
    # artifact 没有 salesData → 模板解析失败
    with pytest.raises(PostActionError) as ei:
        await agentscope_proxy.call_post_action(
            agent_mapping=_make_mapping(),
            parent_node=_make_node({"processedData": {}}),
            task=_make_task(),
        )
    assert "template_error" in str(ei.value)
    assert "salesData" in str(ei.value)


@pytest.mark.asyncio
@respx.mock
async def test_call_post_action_400_raises():
    respx.post(f"{settings.AGENTSCOPE_URL}/v1/price-band/analyze").mock(
        return_value=httpx.Response(400, json={"status": 400, "error": "bad salesData"})
    )
    with pytest.raises(PostActionError) as ei:
        await agentscope_proxy.call_post_action(
            agent_mapping=_make_mapping(),
            parent_node=_make_node(_sales_artifact()),
            task=_make_task(),
        )
    assert "upstream_400" in str(ei.value)


@pytest.mark.asyncio
@respx.mock
async def test_call_post_action_401_raises():
    respx.post(f"{settings.AGENTSCOPE_URL}/v1/price-band/analyze").mock(
        return_value=httpx.Response(401, text="invalid token")
    )
    with pytest.raises(PostActionError) as ei:
        await agentscope_proxy.call_post_action(
            agent_mapping=_make_mapping(),
            parent_node=_make_node(_sales_artifact()),
            task=_make_task(),
        )
    assert "upstream_401" in str(ei.value)


@pytest.mark.asyncio
@respx.mock
async def test_call_post_action_503_raises():
    respx.post(f"{settings.AGENTSCOPE_URL}/v1/price-band/analyze").mock(
        return_value=httpx.Response(503, json={"status": 503, "error": "feature disabled"})
    )
    with pytest.raises(PostActionError) as ei:
        await agentscope_proxy.call_post_action(
            agent_mapping=_make_mapping(),
            parent_node=_make_node(_sales_artifact()),
            task=_make_task(),
        )
    assert "upstream_503" in str(ei.value)


@pytest.mark.asyncio
@respx.mock
async def test_call_post_action_500_raises():
    respx.post(f"{settings.AGENTSCOPE_URL}/v1/price-band/analyze").mock(
        return_value=httpx.Response(500, text="boom")
    )
    with pytest.raises(PostActionError) as ei:
        await agentscope_proxy.call_post_action(
            agent_mapping=_make_mapping(),
            parent_node=_make_node(_sales_artifact()),
            task=_make_task(),
        )
    assert "upstream_500" in str(ei.value)


@pytest.mark.asyncio
@respx.mock
async def test_call_post_action_200_with_error_field_raises():
    """200 但上游 Java 端在 body 里塞 error 字段时也要视为失败。"""
    respx.post(f"{settings.AGENTSCOPE_URL}/v1/price-band/analyze").mock(
        return_value=httpx.Response(200, json={"error": "agent build failed"})
    )
    with pytest.raises(PostActionError) as ei:
        await agentscope_proxy.call_post_action(
            agent_mapping=_make_mapping(),
            parent_node=_make_node(_sales_artifact()),
            task=_make_task(),
        )
    assert "upstream_error" in str(ei.value)


@pytest.mark.asyncio
@respx.mock
async def test_call_post_action_connect_error_raises():
    respx.post(f"{settings.AGENTSCOPE_URL}/v1/price-band/analyze").mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    with pytest.raises(PostActionError) as ei:
        await agentscope_proxy.call_post_action(
            agent_mapping=_make_mapping(),
            parent_node=_make_node(_sales_artifact()),
            task=_make_task(),
        )
    assert "agentscope_unavailable" in str(ei.value)


@pytest.mark.asyncio
@respx.mock
async def test_call_post_action_timeout_raises():
    respx.post(f"{settings.AGENTSCOPE_URL}/v1/price-band/analyze").mock(
        side_effect=httpx.TimeoutException("read timeout")
    )
    with pytest.raises(PostActionError) as ei:
        await agentscope_proxy.call_post_action(
            agent_mapping=_make_mapping(),
            parent_node=_make_node(_sales_artifact()),
            task=_make_task(),
        )
    assert "agentscope_timeout" in str(ei.value)


@pytest.mark.asyncio
@respx.mock
async def test_call_post_action_timeout_includes_class_name_and_timeout_value():
    """httpx.TimeoutException.__str__ 默认空字符串，错误信息必须拼上
    class 名 + 配置的 timeout 数值（默认 settings.AGENTSCOPE_TIMEOUT=120），
    否则用户看到的错误就是 'agentscope_timeout:' 一片空白。"""
    respx.post(f"{settings.AGENTSCOPE_URL}/v1/price-band/analyze").mock(
        side_effect=httpx.ReadTimeout("read")
    )
    with pytest.raises(PostActionError) as ei:
        await agentscope_proxy.call_post_action(
            agent_mapping=_make_mapping(),  # 默认 timeout=120
            parent_node=_make_node(_sales_artifact()),
            task=_make_task(),
        )
    msg = str(ei.value)
    assert "agentscope_timeout" in msg
    assert "ReadTimeout" in msg
    assert "timeout=120s" in msg


@pytest.mark.asyncio
@respx.mock
async def test_call_post_action_sends_correct_headers():
    """验证 X-Internal-Token / X-Session-Id / X-User-Id 都正确带上。"""
    route = respx.post(f"{settings.AGENTSCOPE_URL}/v1/price-band/analyze").mock(
        return_value=httpx.Response(200, json={"status": 200, "ok": True})
    )
    await agentscope_proxy.call_post_action(
        agent_mapping=_make_mapping(),
        parent_node=_make_node(_sales_artifact(), node_id="n-exec-42"),
        task=_make_task(user_id="bob"),
    )
    sent = route.calls.last.request
    assert sent.headers["X-Internal-Token"] == settings.AGENTSCOPE_INTERNAL_TOKEN
    assert sent.headers["X-Session-Id"] == "n-exec-42"
    assert sent.headers["X-User-Id"] == "bob"
    body = sent.content.decode()
    assert '"userId":"bob"' in body
    assert '"sessionId":"n-exec-42"' in body


@pytest.mark.asyncio
@respx.mock
async def test_call_post_action_reads_config_from_agent_mapping():
    """DAG 模型：agent 节点自己带 post_action_config，call_post_action 不回查父。

    验证传入 agent_mapping 含配置即可工作；不需要任何"父"对象。
    """
    respx.post(f"{settings.AGENTSCOPE_URL}/v1/price-band/analyze").mock(
        return_value=httpx.Response(200, json={"status": 200, "ok": True})
    )
    # 不传 parent_node 也能调（实际生产里 parent_node 由 caller 通过 previous_node_id 反查后传入）
    out = await agentscope_proxy.call_post_action(
        agent_mapping=_make_mapping(),
        parent_node=_make_node(_sales_artifact()),
        task=_make_task(),
    )
    assert out["status"] == 200
