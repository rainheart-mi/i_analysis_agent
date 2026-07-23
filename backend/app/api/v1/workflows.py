from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
import logging
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.config import settings
from app.database import get_db
from app.models.workflow import WorkflowRoute
from app.schemas.workflow import (
    WorkflowRouteCreate, WorkflowRouteUpdate,
    WorkflowRouteResponse, WorkflowRouteListResponse
)
from app.api.deps import get_current_user_tenant
from app.services.tenant_query import scoped_query, scoped_query_by_id, apply_tenant


logger = logging.getLogger(__name__)
router = APIRouter()


# ========== 通用 AMIS schema source → options 内联 ==========
# 背景：AMIS 6.13.0 的 tree-select / input-tree 用 source 异步加载时，
#       checkbox 视觉不同步（点击事件能触发但 UI 不切换）。
#       解决：服务端在 get_intent_schema 返回前，把 tree 组件的 source 内联成 options，
#       强制走 sync 渲染路径。
# 通用化：只针对 type 是 tree-select / input-tree 的组件处理，其他组件（select/crud 等）source 不动。
# 不限特定 URL——任何 `/api/...` 形式的本地 API 都会自动预取内联。

_RECURSIVE_KEYS = ("body", "columns", "items", "tabs",
                   "header", "footer", "toolbar", "actions")
_TREE_TYPES = ("tree-select", "input-tree")


def _extract_options_from_response(data) -> list | None:
    """从 AMIS 标准响应里提取 options 数组。

    支持的响应结构（按优先级）：
      1. {data: {options: [...]}}
      2. {data: [...]}
      3. {options: [...]}
    """
    if not isinstance(data, dict):
        return None
    inner = data.get("data")
    if isinstance(inner, dict) and isinstance(inner.get("options"), list):
        return inner["options"]
    if isinstance(inner, list):
        return inner
    if isinstance(data.get("options"), list):
        return data["options"]
    return None


async def _resolve_source_data(source: str, base_url: str) -> list | None:
    """对 `/api/...` 这种本地 API 路径，发起 GET 请求，提取 options。

    失败返回 None（不抛错，让 AMIS 走异步加载作为降级）。
    只处理以 `/` 开头的字符串路径；其他形态（变量引用、对象形式、函数形式）返回 None。
    """
    if not isinstance(source, str) or not source.startswith("/"):
        return None  # 变量引用 / 外部 URL / 对象 / 函数，交给 AMIS 处理
    url = base_url.rstrip("/") + source
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            return _extract_options_from_response(resp.json())
    except Exception as e:
        logger.warning("hydrate source %s failed: %s", source, e)
        return None


async def _hydrate_sources(schema: dict, base_url: str) -> dict:
    """递归遍历 schema，把所有 `tree-select` / `input-tree` 组件的
    `source: "/api/..."` 替换为内联 `options`，绕开 AMIS 6.13 checkbox bug。

    只处理：
      - 组件 type 是 `tree-select` 或 `input-tree`
      - source 是字符串且以 `/` 开头（内部 API 路径）
    其他组件、其他形态保持原样。
    """
    if not isinstance(schema, dict):
        return schema

    # ★ 只针对 tree-select / input-tree 这两种有 checkbox bug 的组件
    if schema.get("type") in _TREE_TYPES:
        source = schema.get("source")
        if isinstance(source, str) and source.startswith("/"):
            options = await _resolve_source_data(source, base_url)
            if options is not None:
                new_schema = dict(schema)
                new_schema.pop("source", None)
                new_schema["options"] = options
                schema = new_schema

    for key in _RECURSIVE_KEYS:
        child = schema.get(key)
        if isinstance(child, list):
            schema[key] = [
                await _hydrate_sources(item, base_url)
                for item in child if isinstance(item, dict)
            ]
        elif isinstance(child, dict):
            schema[key] = await _hydrate_sources(child, base_url)

    return schema


@router.get("", response_model=WorkflowRouteListResponse)
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    # Count total（带 tenant 过滤）
    count_result = await db.execute(
        select(func.count()).select_from(WorkflowRoute).where(WorkflowRoute.tenant_id == ctx.tenant_id)
    )
    total = count_result.scalar()

    # Get items
    result = await db.execute(
        scoped_query(db, WorkflowRoute, ctx.tenant_id)
        .options(selectinload(WorkflowRoute.node_mappings))
        .order_by(WorkflowRoute.sort_order, WorkflowRoute.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().all()

    return WorkflowRouteListResponse(items=items, total=total)


@router.post("", response_model=WorkflowRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow: WorkflowRouteCreate,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    data = workflow.model_dump()
    data.pop("tenant_id", None)  # 禁止前端传入
    db_workflow = apply_tenant(WorkflowRoute(**data), ctx.tenant_id)
    db.add(db_workflow)
    await db.flush()
    await db.refresh(db_workflow)
    return db_workflow


@router.get("/{workflow_id}", response_model=WorkflowRouteResponse)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(
        scoped_query_by_id(db, WorkflowRoute, workflow_id, ctx.tenant_id)
        .options(selectinload(WorkflowRoute.node_mappings))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowRouteResponse)
async def update_workflow(
    workflow_id: str,
    workflow_update: WorkflowRouteUpdate,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(scoped_query_by_id(db, WorkflowRoute, workflow_id, ctx.tenant_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    update_data = workflow_update.model_dump(exclude_unset=True)
    update_data.pop("tenant_id", None)  # 禁止跨字段篡改
    for key, value in update_data.items():
        setattr(workflow, key, value)

    await db.flush()
    await db.refresh(workflow)
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(scoped_query_by_id(db, WorkflowRoute, workflow_id, ctx.tenant_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    await db.delete(workflow)
    return None


@router.get("/{workflow_id}/intents")
async def get_intent_schema(
    workflow_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(
        scoped_query_by_id(db, WorkflowRoute, workflow_id, ctx.tenant_id)
        .options(selectinload(WorkflowRoute.node_mappings))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    if not workflow.node_mappings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置节点映射")

    # 取 DAG 入口节点（无 previous_node_id），它是 intent_schema 的携带者
    entry = next(
        (m for m in workflow.node_mappings if not m.previous_node_id),
        workflow.node_mappings[0],
    )
    schema = entry.intent_schema or {}

    # ★ 通用水合：把 tree-select/input-tree 的 `source: "/api/..."` 内联成 `options`，
    #   绕开 AMIS 6.13.0 的 checkbox 视觉不同步 bug（其他组件、其他形态不受影响）
    #   base_url 从请求头自动获取，不写死端口
    base_url = f"{request.url.scheme}://{request.url.netloc}"
    schema = await _hydrate_sources(schema, base_url)

    # 未配置意图表单视为"无需任何输入字段"（200 + 空对象），不再 404
    # 原因：支持意图表达为空的工作流（如固定模板、纯数据查询类）
    # AmISForm 对空 schema 有占位；执行链对 intent_data={} 友好
    return schema



@router.get("/{workflow_id}/artifacts")
async def get_artifact_schema(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    result = await db.execute(
        scoped_query_by_id(db, WorkflowRoute, workflow_id, ctx.tenant_id)
        .options(selectinload(WorkflowRoute.node_mappings))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    if not workflow.node_mappings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未配置节点映射")

    # 取 DAG 入口节点（无 previous_node_id）
    entry = next(
        (m for m in workflow.node_mappings if not m.previous_node_id),
        workflow.node_mappings[0],
    )
    # 同上：artifacts 也支持"无生成物 schema"，返回 200 + 空对象
    return entry.artifact_schema or {}
