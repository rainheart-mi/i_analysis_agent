"""Post-action 请求体模板解析与端点注册表。

设计要点：
1. `KNOWN_POST_ACTIONS` 维护允许被调用的 AgentScope 端点白名单。
   mapping.post_action_config.api_path 必须在该白名单内才允许下发 HTTP 请求，
   防止配置方任意指向外部 URL（鉴权/超时/审计无法集中管控）。
2. `resolve_template` 支持 `${user_id}` / `${session_id}` / `${artifact.<点路径>}`
   占位符，递归解析 dict / list 节点；路径不存在抛 `TemplateError`，
   调用方映射为 post_action 失败。
"""
from __future__ import annotations

from typing import Any, Dict


# 允许被 mapping.post_action_config 引用的 AgentScope 端点。
# 未来追加新端点时同步在此登记；mapping 配置的 api_path 必须命中其中之一。
KNOWN_POST_ACTIONS: Dict[str, Dict[str, Any]] = {
    "price_band": {
        "api_path": "/v1/price-band/analyze",
        "method": "POST",
        "default_timeout_sec": 120,
    },
    # 后续示例：
    # "anomaly_detection": {"api_path": "/v1/anomaly/detect", "method": "POST", "default_timeout_sec": 60},
}


class TemplateError(Exception):
    """模板占位符解析失败（如路径不存在）。

    可选携带 failure context（失败发生的父路径 + 该层可用 keys），便于错误信息
    直接提示用户修正 `${...}` 的拼写错误，而不必再去 DB 查 artifact_data。
    """

    def __init__(
        self,
        message: str,
        *,
        failed_path: str | None = None,
        parent_path: str | None = None,
        available_keys: list[str] | None = None,
    ):
        super().__init__(message)
        self.failed_path = failed_path
        self.parent_path = parent_path
        self.available_keys = available_keys or []


def resolve_template(template: Any, ctx: Dict[str, Any]) -> Any:
    """递归把模板中的 `${...}` 占位符替换为 ctx 里的实际值。

    支持的三种根路径：
    - `${user_id}`              任务所属用户 ID
    - `${session_id}`           AgentScope 会话 ID（默认与 n8n 父节点同 ID）
    - `${artifact.<dot.path>}`  父 n8n 节点的 artifact_data 内字段

    非字符串值原样保留；路径不存在抛 `TemplateError(missing_field:...)`，
    错误信息附带"卡住那一层"的可用 keys 提示。
    """
    def walk(node: Any) -> Any:
        if isinstance(node, str) and node.startswith("${") and node.endswith("}"):
            raw_path = node[2:-1]
            segments = raw_path.split(".")
            cur: Any = ctx
            traversed: list[str] = []
            for seg in segments:
                if isinstance(cur, dict) and seg in cur:
                    cur = cur[seg]
                    traversed.append(seg)
                else:
                    parent_path = ".".join(traversed) if traversed else "<root>"
                    available = sorted(cur.keys()) if isinstance(cur, dict) else []
                    hint = (
                        f" (at '{parent_path}' available: {', '.join(available)})"
                        if available
                        else f" (at '{parent_path}' no dict keys available)"
                    )
                    raise TemplateError(
                        f"missing_field:{raw_path}{hint}",
                        failed_path=raw_path,
                        parent_path=parent_path,
                        available_keys=available,
                    )
            return cur
        if isinstance(node, str):
            return node
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(template)


def get_known_api_paths() -> set[str]:
    """返回注册表里所有允许的 api_path，供 mapping 校验用。"""
    return {entry["api_path"] for entry in KNOWN_POST_ACTIONS.values()}
