"""WorkflowNodeMapping DAG 校验单测。

覆盖：
- _validate_node_type_fields: 节点类型必填字段
- _check_no_cycle: cycle 检测 + 跨 route 校验

注：本测试不连真实 DB；async 部分用 AsyncMock 替代 db.execute 路径。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from app.api.v1.mappings import _validate_node_type_fields, _check_no_cycle


# ============ _validate_node_type_fields ============

def test_validate_n8n_requires_n8n_workflow_id():
    with pytest.raises(HTTPException) as ei:
        _validate_node_type_fields({"node_type": "n8n"})
    assert "n8n_workflow_id" in str(ei.value.detail)


def test_validate_n8n_rejects_empty_n8n_workflow_id():
    with pytest.raises(HTTPException) as ei:
        _validate_node_type_fields({"node_type": "n8n", "n8n_workflow_id": "  "})
    assert "n8n_workflow_id" in str(ei.value.detail)


def test_validate_n8n_passes_when_n8n_workflow_id_set():
    _validate_node_type_fields({"node_type": "n8n", "n8n_workflow_id": "demo-hook"})
    # partial=True 时缺字段不报错
    _validate_node_type_fields({"node_type": "n8n"}, partial=True)


def test_validate_agent_requires_post_action_config():
    with pytest.raises(HTTPException) as ei:
        _validate_node_type_fields({
            "node_type": "agent",
            "previous_node_id": "upstream-id",
        })
    assert "post_action_config" in str(ei.value.detail)


def test_validate_agent_rejects_empty_post_action_config():
    with pytest.raises(HTTPException) as ei:
        _validate_node_type_fields({
            "node_type": "agent",
            "previous_node_id": "upstream-id",
            "post_action_config": {},
        })
    assert "post_action_config" in str(ei.value.detail)


def test_validate_agent_rejects_non_dict_post_action_config():
    with pytest.raises(HTTPException) as ei:
        _validate_node_type_fields({
            "node_type": "agent",
            "previous_node_id": "upstream-id",
            "post_action_config": "enabled",
        })
    assert "post_action_config" in str(ei.value.detail)


def test_validate_agent_requires_previous_node_id():
    with pytest.raises(HTTPException) as ei:
        _validate_node_type_fields({
            "node_type": "agent",
            "post_action_config": {"enabled": True, "api_path": "/v1/x"},
        })
    assert "previous_node_id" in str(ei.value.detail)


def test_validate_agent_passes_when_all_required_set():
    _validate_node_type_fields({
        "node_type": "agent",
        "previous_node_id": "upstream-id",
        "post_action_config": {"enabled": True, "api_path": "/v1/x"},
    })


def test_validate_rejects_unknown_node_type():
    with pytest.raises(HTTPException) as ei:
        _validate_node_type_fields({"node_type": "evil"})
    assert "n8n" in str(ei.value.detail) and "agent" in str(ei.value.detail)


def test_validate_defaults_node_type_to_n8n():
    # 不传 node_type → 走 n8n 分支
    with pytest.raises(HTTPException) as ei:
        _validate_node_type_fields({})
    assert "n8n_workflow_id" in str(ei.value.detail)


# ============ _check_no_cycle ============

def _make_db_with_chain(route_id, chain):
    """构造 mock db：`chain` 是 [(mapping_id, previous_node_id), ...] 的有向链。

    db.execute(...).scalar_one_or_none() 按 mapping_id 返回 mock mapping 对象。
    """
    chain_map = {mid: (mid, prev) for mid, prev in chain}

    async def fake_execute(_stmt):
        # 真实代码从 stmt 取不到东西；用闭包参数传 mapping_id
        # 这里需要 hack：在 _check_no_cycle 里通过 scoped_query_by_id 查询，
        # 我们用线程局部 / MagicMock 对象来模拟返回值。
        raise NotImplementedError("not used; see _patch_db_execute below")

    db = MagicMock()
    db.execute = AsyncMock(side_effect=fake_execute)
    return db, chain_map


class _FakeResult:
    def __init__(self, mapping):
        self._mapping = mapping

    def scalar_one_or_none(self):
        return self._mapping


def _make_mapping_obj(mid, prev, route_id):
    m = MagicMock()
    m.id = mid
    m.previous_node_id = prev
    m.route_id = route_id
    return m


@pytest.mark.asyncio
async def test_check_no_cycle_self_reference_rejected():
    """previous_node_id == self.id → 400（自环）。"""
    chain = [("m1", "m1")]  # m1.previous = m1
    db, chain_map = _make_db_with_chain("route-1", chain)

    async def execute(_stmt):
        return _FakeResult(_make_mapping_obj("m1", "m1", "route-1"))

    db.execute.side_effect = execute
    with pytest.raises(HTTPException) as ei:
        await _check_no_cycle(
            db, "tid-1",
            self_id="m1",
            previous_node_id="m1",
            route_id="route-1",
        )
    assert "环" in str(ei.value.detail) or "自身" in str(ei.value.detail)


@pytest.mark.asyncio
async def test_check_no_cycle_three_node_cycle_rejected():
    """A → B → A 视为环。"""
    # A.previous = B, B.previous = A；查询 B 时发现 B.previous = A == self_id → 400
    async def execute(_stmt):
        return _FakeResult(_make_mapping_obj("B", "A", "route-1"))

    db = MagicMock()
    db.execute = AsyncMock(side_effect=execute)
    with pytest.raises(HTTPException):
        await _check_no_cycle(
            db, "tid-1",
            self_id="A",
            previous_node_id="B",
            route_id="route-1",
        )


@pytest.mark.asyncio
async def test_check_no_cycle_linear_chain_passes():
    """A → B → C 不应报错。"""
    # 查询 B 时：B.previous = C；再查 C：C.previous = None → 退出
    async def execute(_stmt):
        # 第一次：返回 B（previous = C）；第二次：返回 C（previous = None）
        execute.calls = getattr(execute, "calls", 0) + 1
        if execute.calls == 1:
            return _FakeResult(_make_mapping_obj("B", "C", "route-1"))
        return _FakeResult(_make_mapping_obj("C", None, "route-1"))

    db = MagicMock()
    db.execute = AsyncMock(side_effect=execute)
    # 不应抛异常
    await _check_no_cycle(
        db, "tid-1",
        self_id="A",
        previous_node_id="B",
        route_id="route-1",
    )


@pytest.mark.asyncio
async def test_check_no_cycle_rejects_upstream_missing():
    """上游 mapping 在 DB 找不到（其他 tenant 的 mapping / 已删除）→ 400。"""
    async def execute(_stmt):
        return _FakeResult(None)

    db = MagicMock()
    db.execute = AsyncMock(side_effect=execute)
    with pytest.raises(HTTPException) as ei:
        await _check_no_cycle(
            db, "tid-1",
            self_id="A",
            previous_node_id="ghost",
            route_id="route-1",
        )
    assert "上游节点" in str(ei.value.detail) or "不属于" in str(ei.value.detail)


@pytest.mark.asyncio
async def test_check_no_cycle_rejects_cross_route():
    """previous_node_id 跨 route → 400。"""
    async def execute(_stmt):
        return _FakeResult(_make_mapping_obj("B", None, "route-2"))  # 上游在不同 route

    db = MagicMock()
    db.execute = AsyncMock(side_effect=execute)
    with pytest.raises(HTTPException) as ei:
        await _check_no_cycle(
            db, "tid-1",
            self_id="A",
            previous_node_id="B",
            route_id="route-1",
        )
    assert "同一工作流" in str(ei.value.detail) or "route_id" in str(ei.value.detail)