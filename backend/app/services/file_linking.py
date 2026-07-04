"""
文件 ↔ 工作流实例 关联服务。

工作流执行 endpoint 在保存 intent_data 后调 link_files_in_intent_data()：
递归扫描 intent_data 里的所有字符串值，匹配 UploadedFile.object_key / public_url，
自动创建 FileAttachment 行，绑定到 task_instance_id / node_execution_id。

设计取舍：
- 服务端自动扫描 → 前端零改动
- best-effort 匹配 → 匹配不到不报错（兼容历史数据 / 上传后被删的孤儿文件）
- 用 SQL `IN` 一次性查回所有命中的 UploadedFile，避免 N+1
"""
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UploadedFile, FileAttachment

logger = logging.getLogger(__name__)


def _extract_strings(node: Any) -> List[str]:
    """DFS 递归收集 dict/list 里所有 string 叶子节点值

    跳过 None / 非字符串（数字、布尔、对象等）
    """
    out: List[str] = []
    if isinstance(node, dict):
        for v in node.values():
            out.extend(_extract_strings(v))
    elif isinstance(node, list):
        for v in node:
            out.extend(_extract_strings(v))
    elif isinstance(node, str):
        out.append(node)
    return out


def _find_field_for_value(intent_data: Any, target: str) -> Optional[str]:
    """DFS 反查：在 intent_data 里找值 == target 的最近一层 key 名（点路径）

    返回 'a.b.c' 这种路径；找不到返回 None
    """
    def _walk(node: Any, path: str) -> Optional[str]:
        if isinstance(node, dict):
            for k, v in node.items():
                p = f"{path}.{k}" if path else k
                if isinstance(v, str) and v == target:
                    return p
                r = _walk(v, p)
                if r:
                    return r
        elif isinstance(node, list):
            for i, v in enumerate(node):
                p = f"{path}[{i}]"
                if isinstance(v, str) and v == target:
                    return p
                r = _walk(v, p)
                if r:
                    return r
        return None
    return _walk(intent_data, "")


async def link_files_in_intent_data(
    db: AsyncSession,
    tenant_id: str,
    intent_data: Optional[Dict[str, Any]],
    *,
    task_instance_id: Optional[str] = None,
    node_execution_id: Optional[str] = None,
) -> List[FileAttachment]:
    """扫描 intent_data，找到所有引用的 UploadedFile 并创建关联

    Returns:
        新建的 FileAttachment 列表（已 add 到 session，未 commit；调用方负责 commit）
    """
    if not intent_data:
        return []

    # 1. 收集所有 string 值（去重）
    candidates: Set[str] = set(_extract_strings(intent_data))
    if not candidates:
        return []

    # 2. 一次性查回所有匹配的 UploadedFile
    #    注意：URL 形如 "/static/uploads/2026/06/abc.xlsx"，DB 存的是 object_key="2026/06/abc.xlsx"
    #    public_url = "/static/uploads/2026/06/abc.xlsx" 是 amis 写入表单的实际值
    #    所以匹配 public_url（amis 用这个）和 object_key（双重保险）
    result = await db.execute(
        select(UploadedFile).where(
            UploadedFile.tenant_id == tenant_id,
            or_(
                UploadedFile.public_url.in_(candidates),
                UploadedFile.object_key.in_(candidates),
            ),
        )
    )
    matched_files = result.scalars().all()
    if not matched_files:
        logger.debug(f"[file_linking] no matched files for tenant={tenant_id}")
        return []

    # 3. 为每个匹配的文件创建 FileAttachment（按 file_id + node_execution_id 去重）
    #    用 dict 模拟 set: key = (file_id, node_execution_id)
    existing_result = await db.execute(
        select(FileAttachment.file_id, FileAttachment.node_execution_id).where(
            FileAttachment.tenant_id == tenant_id,
            FileAttachment.file_id.in_([f.id for f in matched_files]),
        )
    )
    existing_pairs: Set[Tuple[str, Optional[str]]] = {
        (fid, nid) for fid, nid in existing_result.all()
    }

    created: List[FileAttachment] = []
    for f in matched_files:
        # 反查 field_name：先按 public_url 查，再按 object_key 查
        field_name = _find_field_for_value(intent_data, f.public_url)
        if not field_name and f.object_key != f.public_url:
            field_name = _find_field_for_value(intent_data, f.object_key)

        key = (f.id, node_execution_id)
        if key in existing_pairs:
            # 已经关联过（同 file + 同 node_execution），跳过避免重复
            continue

        att = FileAttachment(
            file_id=f.id,
            tenant_id=tenant_id,
            task_instance_id=task_instance_id,
            node_execution_id=node_execution_id,
            field_name=field_name,
        )
        db.add(att)
        created.append(att)
        existing_pairs.add(key)  # 防止同一 intent_data 引用同一 file 多次

    if created:
        logger.info(
            f"[file_linking] tenant={tenant_id} task={task_instance_id} "
            f"node={node_execution_id} linked {len(created)} files"
        )
    return created
