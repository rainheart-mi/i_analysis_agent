"""post_action_template.resolve_template 单测。

覆盖：
- 三种根路径：user_id / session_id / artifact.<点路径>
- 嵌套 dict / list 中占位符递归
- 路径不存在 → TemplateError(missing_field:...)
- 非字符串值原样保留
- KNOWN_POST_ACTIONS 白名单
"""
import pytest

from app.services.post_action_template import (
    KNOWN_POST_ACTIONS,
    TemplateError,
    get_known_api_paths,
    resolve_template,
)


CTX = {
    "user_id": "alice",
    "session_id": "sess-001",
    "artifact": {
        "processedData": {
            "salesData": [
                {"skuId": "S001", "price": 9.9, "soldQty": 100},
                {"skuId": "S002", "price": 19.9, "soldQty": 50},
            ],
            "summary": "ok",
        },
        "rawOutput": "raw text",
    },
}


def test_resolve_user_id_root():
    assert resolve_template("${user_id}", CTX) == "alice"


def test_resolve_session_id_root():
    assert resolve_template("${session_id}", CTX) == "sess-001"


def test_resolve_artifact_deep_path():
    out = resolve_template("${artifact.processedData.salesData}", CTX)
    assert isinstance(out, list)
    assert out[0]["skuId"] == "S001"


def test_resolve_nested_dict_template():
    template = {
        "userId": "${user_id}",
        "sessionId": "${session_id}",
        "salesData": "${artifact.processedData.salesData}",
        "options": {"topK": 5, "label": "literal"},
    }
    out = resolve_template(template, CTX)
    assert out == {
        "userId": "alice",
        "sessionId": "sess-001",
        "salesData": CTX["artifact"]["processedData"]["salesData"],
        "options": {"topK": 5, "label": "literal"},
    }


def test_resolve_inside_list_keeps_placeholder_semantics():
    template = ["${user_id}", "literal", 42]
    assert resolve_template(template, CTX) == ["alice", "literal", 42]


def test_missing_field_raises_template_error():
    with pytest.raises(TemplateError) as ei:
        resolve_template("${artifact.processedData.salesDataMissing}", CTX)
    assert "missing_field:artifact.processedData.salesDataMissing" in str(ei.value)


def test_missing_user_id_raises():
    with pytest.raises(TemplateError):
        resolve_template("${unknown}", CTX)


def test_non_string_value_passthrough():
    assert resolve_template(123, CTX) == 123
    assert resolve_template(True, CTX) is True
    assert resolve_template(None, CTX) is None


def test_partial_placeholder_not_treated_as_substitution():
    # 缺右花括号时按字面量保留
    assert resolve_template("${user_id", CTX) == "${user_id"
    # 缺左花括号时按字面量保留
    assert resolve_template("user_id}", CTX) == "user_id}"


def test_known_post_actions_contains_price_band():
    paths = {entry["api_path"] for entry in KNOWN_POST_ACTIONS.values()}
    assert "/v1/price-band/analyze" in paths
    assert "POST" in {entry["method"] for entry in KNOWN_POST_ACTIONS.values()}


def test_get_known_api_paths_matches_registry():
    paths = get_known_api_paths()
    assert paths == {entry["api_path"] for entry in KNOWN_POST_ACTIONS.values()}


# ---- 增强 hint：错误信息携带"卡住那一层"的父路径 + 可用 keys ----


def test_missing_artifact_subkey_includes_parent_and_keys():
    """二层路径拼写错（如大小写）时，hint 显示父路径 + 该层 keys，
    用户能直接看到自己想要的 key 长什么样。"""
    with pytest.raises(TemplateError) as ei:
        resolve_template("${artifact.processedData.salesDataX}", CTX)
    msg = str(ei.value)
    assert "missing_field:artifact.processedData.salesDataX" in msg
    assert "at 'artifact.processedData'" in msg
    # sorted keys: salesData, summary
    assert "available: salesData, summary" in msg


def test_missing_artifact_top_includes_artifact_keys():
    """artifact 顶层 key 写错时，hint 显示 artifact 这一层的 keys。"""
    with pytest.raises(TemplateError) as ei:
        resolve_template("${artifact.bogus}", CTX)
    msg = str(ei.value)
    assert "at 'artifact'" in msg
    # sorted keys: processedData, rawOutput
    assert "available: processedData, rawOutput" in msg


def test_missing_root_placeholder_includes_root_keys():
    """非 artifact/user_id/session_id 的根 key 写错时，hint 显示 <root> 层的 keys。"""
    with pytest.raises(TemplateError) as ei:
        resolve_template("${unknown}", CTX)
    msg = str(ei.value)
    assert "at '<root>'" in msg
    # sorted keys: artifact, session_id, user_id
    assert "available: artifact, session_id, user_id" in msg


def test_template_error_carries_structured_fields():
    """除字符串 hint 外，TemplateError 实例也带 failed_path / parent_path / available_keys。"""
    with pytest.raises(TemplateError) as ei:
        resolve_template("${artifact.bogus}", CTX)
    err = ei.value
    assert err.failed_path == "artifact.bogus"
    assert err.parent_path == "artifact"
    assert "processedData" in err.available_keys
    assert "rawOutput" in err.available_keys
