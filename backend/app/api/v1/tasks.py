from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import asyncio
from typing import List, AsyncIterator
import uuid
import json
import logging
from datetime import datetime

from app.config import settings
from app.database import get_db, AsyncSessionLocal
from app.models.task import TaskInstance, NodeExecution
from app.models.workflow import WorkflowRoute
from app.schemas.task import (
    TaskCreate, TaskResponse, TaskDetailResponse,
    NodeExecutionResponse, NodeUpdateRequest, NodeArtifactRequest
)
from app.api.deps import get_current_user_tenant
from app.services.agentscope_proxy import stream_price_band_analyze
from app.services.tenant_query import scoped_query, scoped_query_by_id, apply_tenant
from app.services.file_linking import link_files_in_intent_data


router = APIRouter()

logger = logging.getLogger(__name__)


def build_node_response(
    node_exec: NodeExecution,
    mapping_to_node_exec_id: dict[str, str] | None = None,
) -> NodeExecutionResponse:
    """Build NodeExecutionResponse, directly exposing schema JSON columns.

    解析 mapping.previous_node_id（自引用 DAG 边），识别 agent 节点并把
    上游 node_execution_id 暴露给前端。
    `mapping_to_node_exec_id` 由调用方预计算（同一 task 内 mapping_id → node_execution_id），
    避免 N+1 查询。
    """
    mapping = node_exec.mapping
    mapping_id = mapping.id if mapping else None
    node_type = mapping.node_type if mapping else "n8n"
    parent_node_execution_id: str | None = None
    if mapping and mapping.previous_node_id and mapping_to_node_exec_id:
        parent_node_execution_id = mapping_to_node_exec_id.get(mapping.previous_node_id)
    return NodeExecutionResponse(
        id=node_exec.id,
        task_instance_id=node_exec.task_instance_id,
        node_id=node_exec.node_id,
        node_name=node_exec.node_name,
        intent_data=node_exec.intent_data or {},
        artifact_data=node_exec.artifact_data,
        intent_schema=node_exec.intent_schema,
        artifact_schema=node_exec.artifact_schema,
        status=node_exec.status,
        error_message=node_exec.error_message,
        started_at=node_exec.started_at,
        completed_at=node_exec.completed_at,
        mapping_id=mapping_id,
        node_type=node_type,
        parent_node_execution_id=parent_node_execution_id,
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """Create a task for the given workflow_id，归属到当前 user+tenant"""
    result = await db.execute(
        scoped_query_by_id(db, WorkflowRoute, task_data.workflow_id, ctx.tenant_id)
        .options(selectinload(WorkflowRoute.node_mappings))
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    if not workflow.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="工作流已禁用")

    task_id = str(uuid.uuid4())
    task = apply_tenant(TaskInstance(
        id=task_id,
        user_id=ctx.user_id,
        workflow_id=task_data.workflow_id,
        name=task_data.name or f"Task-{task_id[:8]}",
        status="pending",
        org_id=ctx.org_id,
        org_type=ctx.org_type,
        emp_id=ctx.emp_id,
        emp_name=ctx.emp_name,
    ), ctx.tenant_id)
    db.add(task)

    # ---- 拓扑遍历建 NodeExecution ----
    # v1 线性链下退化为按 previous 链顺序处理；算法为将来 fan-out 留口子
    # （把 previous_node_id 改 JSON 数组时这一段不用动）。
    mappings = list(workflow.node_mappings)
    mapping_ids = {m.id for m in mappings}
    in_degree: dict[str, int] = {m.id: 0 for m in mappings}
    children_map: dict[str, list] = {}
    for m in mappings:
        if m.previous_node_id and m.previous_node_id in mapping_ids:
            children_map.setdefault(m.previous_node_id, []).append(m)
            in_degree[m.id] = in_degree.get(m.id, 0) + 1

    # Kahn BFS — 初始队列按 node_type 排序：n8n 优先于 agent
    queue = sorted(
        [m for m in mappings if in_degree[m.id] == 0],
        key=lambda m: (0 if m.node_type == "n8n" else 1),
    )
    ordered: list = []
    while queue:
        m = queue.pop(0)
        ordered.append(m)
        for child in children_map.get(m.id, []):
            in_degree[child.id] -= 1
            if in_degree[child.id] == 0:
                queue.append(child)

    for mapping in ordered:
        node_exec = apply_tenant(NodeExecution(
            id=str(uuid.uuid4()),
            task_instance_id=task_id,
            mapping_id=mapping.id,
            node_id=mapping.node_id,
            node_name=mapping.node_name,
            intent_schema=mapping.intent_schema,
            artifact_schema=mapping.artifact_schema,
            n8n_workflow_id=mapping.n8n_workflow_id,
            intent_data={},
            status="pending"
        ), ctx.tenant_id)
        db.add(node_exec)

    await db.flush()
    await db.refresh(task)
    return task


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """Return all tasks for the current user in the current tenant"""
    result = await db.execute(
        scoped_query(db, TaskInstance, ctx.tenant_id)
        .where(TaskInstance.user_id == ctx.user_id)
        .order_by(TaskInstance.created_at.desc())
    )
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task_detail(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """Return task with all node executions（按 user_id 隔离）"""
    result = await db.execute(
        scoped_query_by_id(db, TaskInstance, task_id, ctx.tenant_id)
        .where(TaskInstance.user_id == ctx.user_id)
        .options(
            selectinload(TaskInstance.node_executions).selectinload(NodeExecution.mapping)
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    workflow_result = await db.execute(
        scoped_query_by_id(db, WorkflowRoute, task.workflow_id, ctx.tenant_id)
    )
    workflow_title = workflow_result.scalar_one_or_none() and \
                     (await db.execute(select(WorkflowRoute.title).where(WorkflowRoute.id == task.workflow_id))).scalar_one_or_none()

    mapping_to_node_exec_id = {n.mapping_id: n.id for n in task.node_executions}
    nodes_with_schema = [build_node_response(n, mapping_to_node_exec_id) for n in task.node_executions]

    return TaskDetailResponse(
        task=task,
        nodes=nodes_with_schema,
        workflow_title=workflow_title
    )


@router.patch("/{task_id}/nodes/{node_id}/execute", status_code=status.HTTP_200_OK)
async def execute_node(
    task_id: str,
    node_id: str,
    update_data: NodeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """异步执行节点"""
    result = await db.execute(
        scoped_query_by_id(db, TaskInstance, task_id, ctx.tenant_id)
        .where(TaskInstance.user_id == ctx.user_id)
        .options(selectinload(TaskInstance.node_executions))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node_exec = None
    for node in task.node_executions:
        if node.node_id == node_id and node.tenant_id == ctx.tenant_id:
            node_exec = node
            break

    if not node_exec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点执行记录不存在")

    if node_exec.status not in ("pending", "failed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="节点状态不允许执行")

    if update_data.intent_data is not None:
        node_exec.intent_data = update_data.intent_data

    # 关联 intent_data 里引用的上传文件到本次执行（best-effort，匹配不到不报错）
    await link_files_in_intent_data(
        db,
        tenant_id=ctx.tenant_id,
        intent_data=update_data.intent_data,
        task_instance_id=task_id,
        node_execution_id=node_exec.id,
    )

    # fail-fast: 节点未配置 n8n webhook 时直接拒绝,避免拼出 /webhook/None 触发 n8n 404
    if not node_exec.n8n_workflow_id:
        node_exec.status = "failed"
        node_exec.error_message = "该节点未配置 n8n webhook,请在管理后台编辑 workflow node mapping 填写 n8n_workflow_id"
        node_exec.completed_at = datetime.utcnow()
        task.status = "failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该节点未配置 n8n webhook,请联系管理员补全 mapping 配置",
        )

    node_exec.status = "pending"
    task.status = "running"
    task.current_node_id = node_id

    if task.node_executions and node_exec == task.node_executions[0]:
        if update_data.intent_data:
            first_value = list(update_data.intent_data.values())[0]
            if first_value:
                workflow_result = await db.execute(
                    scoped_query_by_id(db, WorkflowRoute, task.workflow_id, ctx.tenant_id)
                )
                workflow_row = workflow_result.scalar_one_or_none()
                workflow_title = workflow_row.title if workflow_row else "任务"
                task.name = f"{workflow_title}-{first_value}"

    await db.commit()

    from app.tasks.workflow_tasks import execute_n8n_node
    execute_n8n_node.delay(task_id, node_id, node_exec.n8n_workflow_id, node_exec.intent_data)
    print(f"[execute_node] Task dispatched: task_id={task_id}, node_id={node_id}, tenant_id={ctx.tenant_id}")

    return {"message": "节点开始执行", "task_id": task_id, "node_id": node_id, "status": "pending"}


@router.patch("/{task_id}/nodes/{node_id}", status_code=status.HTTP_200_OK)
async def update_node(
    task_id: str,
    node_id: str,
    update_data: NodeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """Update artifact_data, status, error_message, completed_at"""
    result = await db.execute(
        scoped_query_by_id(db, TaskInstance, task_id, ctx.tenant_id)
        .where(TaskInstance.user_id == ctx.user_id)
        .options(selectinload(TaskInstance.node_executions))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node_exec = None
    for node in task.node_executions:
        if node.node_id == node_id and node.tenant_id == ctx.tenant_id:
            node_exec = node
            break

    if not node_exec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点执行记录不存在")

    if update_data.artifact_data is not None:
        node_exec.artifact_data = update_data.artifact_data
    if update_data.status is not None:
        node_exec.status = update_data.status
    if update_data.error_message is not None:
        node_exec.error_message = update_data.error_message
    if update_data.completed_at is not None:
        node_exec.completed_at = update_data.completed_at

    all_completed = all(n.status == "completed" for n in task.node_executions)
    if all_completed:
        task.status = "completed"

    return {"message": "节点更新成功", "node_id": node_id}


@router.post("/{task_id}/nodes/{node_id}/mock-complete", status_code=status.HTTP_200_OK)
async def mock_complete_node(
    task_id: str,
    node_id: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """Mock 完成节点执行"""
    result = await db.execute(
        scoped_query_by_id(db, TaskInstance, task_id, ctx.tenant_id)
        .where(TaskInstance.user_id == ctx.user_id)
        .options(selectinload(TaskInstance.node_executions))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node_exec = None
    for node in task.node_executions:
        if node.node_id == node_id and node.tenant_id == ctx.tenant_id:
            node_exec = node
            break

    if not node_exec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点执行记录不存在")

    # Mock artifact data - must match display_review_artifact_schema.json structure
    mock_artifact_data = {
        "processedData": {
            "summary": {
                "periodA": {"startDate": "2026-04-01", "endDate": "2026-04-16"},
                "periodB": {"startDate": "2026-04-15", "endDate": "2026-05-01"},
                "totalSalesA": 135231.96,
                "totalSalesB": 143811.48,
                "totalItemsInA": 1333,
                "totalItemsInB": 1363,
                "totalShelvesInA": 115,
                "totalShelvesInB": 116,
                "overallGrowthRate": "6.34%"
            },
            "keyMetrics": [
                {"指标名称": "商品 SKU 数", "本期": 1363, "上期": 1333, "变化率": "+2.3%"},
                {"指标名称": "货架数", "本期": 116, "上期": 115, "变化率": "+0.9%"},
                {"指标名称": "平均坪效", "本期": "2,850", "上期": "2,680", "变化率": "+6.3%"}
            ],
            "categorySalesGrowth": [
                {"大类": "水果", "期初销售额": 26782.99, "期末销售额": 35055.34, "销售额增长率": "+30.89%"},
                {"大类": "冷冻品", "期初销售额": 5534.20, "期末销售额": 6852.21, "销售额增长率": "+23.82%"},
                {"大类": "肉禽蛋", "期初销售额": 42523.04, "期末销售额": 48405.16, "销售额增长率": "+13.83%"},
                {"大类": "蔬菜", "期初销售额": 42507.95, "期末销售额": 48189.87, "销售额增长率": "+13.37%"},
                {"大类": "烘焙", "期初销售额": 10796.44, "期末销售额": 11914.31, "销售额增长率": "+10.35%"},
                {"大类": "粮油调味", "期初销售额": 21224.13, "期末销售额": 23288.68, "销售额增长率": "+9.73%"},
                {"大类": "烟酒饮料", "期初销售额": 19299.66, "期末销售额": 20660.39, "销售额增长率": "+7.05%"},
                {"大类": "休闲食品", "期初销售额": 5021.52, "期末销售额": 5337.79, "销售额增长率": "+6.30%"},
                {"大类": "水产", "期初销售额": 18256.85, "期末销售额": 19196.62, "销售额增长率": "+5.15%"},
                {"大类": "冷藏日配", "期初销售额": 28652.56, "期末销售额": 30065.74, "销售额增长率": "+4.93%"},
                {"大类": "家清个护", "期初销售额": 3912.86, "期末销售额": 4084.39, "销售额增长率": "+4.38%"},
                {"大类": "生活百货", "期初销售额": 791.33, "期末销售额": 780.84, "销售额增长率": "-1.33%"},
                {"大类": "收银区", "期初销售额": 28.95, "期末销售额": 26.92, "销售额增长率": "-7.01%"},
                {"大类": "3R熟食", "期初销售额": 6543.57, "期末销售额": 5110.93, "销售额增长率": "-21.89%"},
                {"大类": "婴保宠物", "期初销售额": 42.90, "期末销售额": 19.90, "销售额增长率": "-53.61%"}
            ],
            "newAndLost": {
                "newItems": [{"商品编码": "10000013"}, {"商品编码": "10000031"}],
                "lostItems": [{"商品编码": "10000097"}, {"商品编码": "10000179"}],
                "newShelves": ["M-SC07B-S002", "M-HB02A-S002"],
                "lostShelves": ["M-SG05B-S001"]
            },
            "newItemsDetail": [
                {"商品编码": "10000013", "商品名称": "有机苹果", "品类": "水果", "货架": "M-SC07B-S002"},
                {"商品编码": "10000031", "商品名称": "进口车厘子", "品类": "水果", "货架": "M-HB02A-S002"}
            ],
            "lostItemsDetail": [
                {"商品编码": "10000097", "商品名称": "过期酸奶", "品类": "冷藏日配", "货架": "M-LD09B-S004"},
                {"商品编码": "10000179", "商品名称": "临期面包", "品类": "烘焙", "货架": "M-BP10A-S003"}
            ],
            "newShelvesDetail": [
                {"货架ID": "M-SC07B-S002", "货架位置": "A区-03", "面积": "12㎡"},
                {"货架ID": "M-HB02A-S002", "货架位置": "C区-01", "面积": "8㎡"}
            ],
            "lostShelvesDetail": [
                {"货架ID": "M-SG05B-S001", "货架位置": "B区-05", "面积": "6㎡"}
            ],
            "shelfSaturationChanges": [
                {"货架ID": "M-SC07B-S002", "期初商品数": 0, "期末商品数": 1, "期初销售额": 0, "期末销售额": 13.8, "销售额变化率": None},
                {"货架ID": "M-HB02A-S002", "期初商品数": 0, "期末商品数": 1, "期初销售额": 0, "期末销售额": 13.9, "销售额变化率": None}
            ],
            "shelfEfficiencyChart": {
                "labels": ["M-SC07B-S003", "M-BP13A-S001", "M-HB02A-S001", "M-LS001", "M-BP15B-G001"],
                "efficiency": [880, 296, 54, 73, 46],
                "trend": [387, 255, 200, 120, 109]
            },
            "aiResponse": {
                "rawOutput": "### 品类管理复盘报告（2026.04.01–2026.05.01）\n\n#### 一、整体表现：稳健增长，结构分化显著\n- **销售达成**：总销售额从 ¥135,231.96 → ¥143,811.48，**整体增长 +6.34%**。\n- **货架与商品规模**：货架数+1（115→116），商品数+30（1333→1363），净增30款。\n\n#### 二、大类表现分析：水果/冷冻领跑，熟食/婴保严重失速\n- **水果** +30.89%、**冷冻品** +23.82% 领跑\n- **3R熟食** -21.89%、**婴保宠物** -53.61% 严重失速\n\n#### 三、下一步动作清单\n1. 24h内：核查M-SG05B-S001下架原因\n2. 72h内：对TOP5失能货架开展现场动线/补货/价签三重稽查\n3. 本周内：输出《水果/冷冻品陈列SOP》",
                "suggestions": [
                    "优化水果品类库存周转",
                    "提升烘焙品类商品品质",
                    "加强蔬菜品类促销力度",
                    "关注低效货架坪效提升"
                ]
            }
        }
    }

    node_exec.artifact_data = mock_artifact_data
    node_exec.status = "completed"
    node_exec.completed_at = datetime.utcnow()

    all_completed = all(n.status == "completed" for n in task.node_executions)
    if all_completed:
        task.status = "completed"
    else:
        pending_nodes = [n for n in task.node_executions if n.status == "pending"]
        if pending_nodes:
            next_node = pending_nodes[0]
            task.current_node_id = next_node.node_id
            task.status = "running"

    await db.commit()

    return {
        "message": "节点执行完成",
        "node_id": node_id,
        "status": "completed",
        "next_node_id": task.current_node_id if not all_completed else None,
        "task_status": task.status
    }


@router.get("/{task_id}/nodes/{node_id}/status", status_code=status.HTTP_200_OK)
async def get_node_status(
    task_id: str,
    node_id: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """获取节点执行状态"""
    result = await db.execute(
        scoped_query_by_id(db, TaskInstance, task_id, ctx.tenant_id)
        .where(TaskInstance.user_id == ctx.user_id)
        .options(
            selectinload(TaskInstance.node_executions)
            .selectinload(NodeExecution.mapping)
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node = next((n for n in task.node_executions if n.node_id == node_id and n.tenant_id == ctx.tenant_id), None)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点不存在")

    return {
        "node_id": node.node_id,
        "node_name": node.node_name,
        "status": node.status,
        "intent_data": node.intent_data,
        "artifact_data": node.artifact_data,
        "error_message": node.error_message,
        "started_at": node.started_at.isoformat() if node.started_at else None,
        "completed_at": node.completed_at.isoformat() if node.completed_at else None,
        "mapping_id": node.mapping_id,
        "node_type": (node.mapping.node_type if node.mapping else "n8n"),
    }


@router.post("/{task_id}/nodes/{node_id}/post-action/trigger")
async def trigger_post_action(
    task_id: str,
    node_id: str,
    stream: bool = Query(
        False,
        description="true 时同步流式 SSE 响应（不走 Celery），用于前端实时渲染价格带分析进度",
    ),
    direct_stream: bool = Query(
        False,
        description="true 时 stream 模式返回 Java SSE 端点元数据，前端直连 Java，不再经 proxy 转发 SSE",
    ),
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """手动触发 post-action 节点（trigger_mode='manual'/'both' 时由前端按钮调用）。

    校验：
    1. 任务存在且归属当前 user+tenant
    2. 节点存在，归属当前 tenant
    3. 节点 mapping.node_type == "post_action" 且有 parent_mapping_id
    4. 父 n8n 节点 status == "completed"（否则 400）
    5. 当前节点 status ∈ {pending, failed}（避免重入）
    """
    # ★ DEBUG trace：入口处先记一组关键上下文，便于全链路 grep
    logger.info(
        "[trigger_post_action] ENTRY task_id=%s node_id=%s tenant_id=%s user_id=%s stream=%s",
        task_id, node_id, ctx.tenant_id, ctx.user_id, stream,
    )
    result = await db.execute(
        scoped_query_by_id(db, TaskInstance, task_id, ctx.tenant_id)
        .where(TaskInstance.user_id == ctx.user_id)
        .options(
            selectinload(TaskInstance.node_executions).selectinload(NodeExecution.mapping)
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        logger.warning("[trigger_post_action] task not found task_id=%s", task_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node_exec = next(
        (n for n in task.node_executions
         if n.node_id == node_id and n.tenant_id == ctx.tenant_id),
        None,
    )
    if not node_exec:
        logger.warning(
            "[trigger_post_action] node not found task_id=%s node_id=%s",
            task_id, node_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点执行记录不存在")

    mapping = node_exec.mapping
    logger.debug(
        "[trigger_post_action] loaded: node_id=%s status=%s node_type=%s "
        "mapping_id=%s has_previous=%s post_action_enabled=%s",
        node_exec.node_id, node_exec.status,
        mapping.node_type if mapping else None,
        mapping.id if mapping else None,
        bool(mapping and mapping.previous_node_id),
        bool((mapping.post_action_config or {}).get("enabled")) if mapping else False,
    )
    if not mapping or mapping.node_type != "agent" or not mapping.previous_node_id:
        logger.warning(
            "[trigger_post_action] not an agent node: task_id=%s node_id=%s mapping=%s",
            task_id, node_id,
            {"node_type": mapping.node_type if mapping else None,
             "has_previous": bool(mapping and mapping.previous_node_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该节点不是 agent 节点（缺少 previous_node_id）",
        )

    parent_node = next(
        (n for n in task.node_executions if n.mapping_id == mapping.previous_node_id),
        None,
    )
    if not parent_node or parent_node.status != "completed":
        logger.warning(
            "[trigger_post_action] parent not ready: task_id=%s node_id=%s parent=%s",
            task_id, node_id,
            {"found": bool(parent_node),
             "status": parent_node.status if parent_node else None},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上游节点未完成，无法触发 agent 节点",
        )

    if node_exec.status == "completed":
        # completed 是终态：前端轮询有 2s 延迟时按钮可能仍可见，给一个明确 409
        # 让前端能区分"已成功完成"和"暂未就绪"两类 4xx
        logger.info(
            "[trigger_post_action] skip: already completed task_id=%s node_id=%s",
            task_id, node_id,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="节点已完成，无需重新触发；如需重跑请新建任务",
        )
    if node_exec.status not in ("pending", "failed"):
        logger.warning(
            "[trigger_post_action] invalid state: task_id=%s node_id=%s status=%s",
            task_id, node_id, node_exec.status,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"节点状态为 {node_exec.status}，不允许重复触发",
        )

    logger.debug(
        "[trigger_post_action] parent ready: parent_node_id=%s artifact_keys=%s",
        parent_node.node_id,
        list((parent_node.artifact_data or {}).keys()) if parent_node.artifact_data else [],
    )

    # ★ 行级锁 + 原子化状态检查：防止并发请求处理同一节点。
    #   select_for_update 锁住行 → 重验状态 → commit 时释放锁。
    #   第二个请求在 select_for_update 处等待，获锁后发现 status 已变 → 409 拒绝。
    locked_ne_result = await db.execute(
        select(NodeExecution)
        .where(NodeExecution.id == node_exec.id)
        .with_for_update()
    )
    locked_ne = locked_ne_result.scalar_one_or_none()
    if not locked_ne or locked_ne.status not in ("pending", "failed"):
        logger.warning(
            "[trigger_post_action] concurrent request detected: task_id=%s node_id=%s status=%s",
            task_id, node_id, locked_ne.status if locked_ne else "gone",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="节点状态已变更，请刷新后重试",
        )

    # 重置 status 为 pending，便于 worker 重新执行
    node_exec.status = "pending"
    node_exec.error_message = None
    node_exec.completed_at = None
    await db.commit()
    logger.debug(
        "[trigger_post_action] reset status=pending: task_id=%s node_id=%s",
        task_id, node_id,
    )

    if stream:
        # ---- 流式模式：直接代理 AgentScope SSE 到前端（不走 Celery）----
        # 走 request_body_template 模板渲染（与同步 call_post_action 路径一致）：
        #   mapping.post_action_config.request_body_template 里的 ${user_id}/${session_id}/
        #   ${artifact.processedData.salesData} 等占位符要被替换为实际值。
        #   流式分支之前漏了这一步，导致 AgentScope 收到原始 payload（无 salesData 等字段）→ 400。
        from app.services.post_action_template import resolve_template, TemplateError

        logger.info(
            "[trigger_post_action:stream] entering stream branch task_id=%s node_id=%s "
            "node_exec_id=%s mapping_id=%s",
            task_id, node_id, node_exec.id, mapping.id,
        )
        cfg = mapping.post_action_config or {}
        body_template = cfg.get("request_body_template")
        logger.debug(
            "[trigger_post_action:stream] post_action_config: has_template=%s "
            "api_path=%s method=%s timeout_sec=%s",
            isinstance(body_template, dict),
            cfg.get("api_path"),
            cfg.get("method"),
            cfg.get("timeout_sec"),
        )
        if isinstance(body_template, dict):
            artifact = parent_node.artifact_data or {}
            if not isinstance(artifact, dict):
                artifact = {}
            render_ctx = {
                "user_id": ctx.user_id,
                "session_id": parent_node.id,
                "artifact": artifact,
            }
            logger.debug(
                "[trigger_post_action:stream] render_ctx: user_id=%s session_id=%s "
                "artifact_keys=%s",
                render_ctx["user_id"], render_ctx["session_id"],
                list(artifact.keys()),
            )
            try:
                payload = resolve_template(body_template, render_ctx)
                logger.debug(
                    "[trigger_post_action:stream] template rendered OK: payload=%s",
                    payload,
                )
            except TemplateError as e:
                logger.error(
                    "[trigger_post_action:stream] template render FAILED task_id=%s "
                    "node_id=%s err=%s",
                    task_id, node_id, e,
                )
                # 模板渲染失败 → 立即 yield error 帧并 return
                err = json.dumps({
                    "error": "template_error",
                    "detail": str(e),
                }, ensure_ascii=False)

                async def _err_gen() -> AsyncIterator[bytes]:
                    yield f"data: {err}\n\n".encode("utf-8")

                return StreamingResponse(
                    _err_gen(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "X-Accel-Buffering": "no",
                        "Connection": "keep-alive",
                    },
                )
        else:
            # 无模板配置：fallback 到原始 payload（向后兼容老 mapping）
            payload = {
                "task_id": task_id,
                "node_id": node_id,
                "intent_data": node_exec.intent_data or {},
                "parent_artifact": parent_node.artifact_data or {},
            }
            logger.warning(
                "[trigger_post_action:stream] no request_body_template, using fallback "
                "payload (legacy path) task_id=%s node_id=%s",
                task_id, node_id,
            )

        # ★ 内存累积器：stage / schema-fragment / midcat 事件仅更新此 dict，
        # 不触发 DB commit；final / fatal-error 时一次性 commit 完整数据。
        accumulated: dict = dict(node_exec.artifact_data or {})
        # ★ 后台 DB 写入函数（不阻塞 SSE 转发）
        #   使用独立 session（AsyncSessionLocal），不复用依赖注入的 db——
        #   get_db 的 session 在 StreamingResponse 响应体生成器结束后会被关闭，
        #   而 _commit_final 作为 asyncio.create_task 后台运行，可能在 session 关闭后才执行；
        #   闭包里的 node_exec/task 在独立 session 中是 detached 实例，直接改字段不会持久化。
        #   因此只传标量 id，在独立 session 内重新 get/attach 再改字段。
        async def _commit_final(node_exec_id, task_id, accumulated, artifact_schema):
            try:
                async with AsyncSessionLocal() as session:
                    ne = await session.get(NodeExecution, node_exec_id)
                    if ne is None:
                        logger.warning("[trigger_post_action:on_event] FINAL node_exec not found id=%s", node_exec_id)
                        return
                    ne.artifact_data = dict(accumulated)
                    if artifact_schema is not None:
                        ne.artifact_schema = artifact_schema
                    ne.status = "completed"
                    ne.completed_at = datetime.utcnow()
                    # 重新加载 task + node_executions 判断是否全部完成
                    t_result = await session.execute(
                        select(TaskInstance)
                        .options(selectinload(TaskInstance.node_executions))
                        .where(TaskInstance.id == task_id)
                    )
                    task_obj = t_result.scalar_one_or_none()
                    if task_obj is not None:
                        all_done = all(n.status == "completed" for n in task_obj.node_executions)
                        task_obj.status = "completed" if all_done else "running"
                    await session.commit()
                    logger.info("[trigger_post_action:on_event] FINAL committed: task_id=%s node_id=%s artifact_keys=%s",
                        task_id, node_exec_id, list(accumulated.keys()))
            except Exception:
                logger.exception("[trigger_post_action:on_event] final commit failed")

        async def _commit_failed(node_exec_id, task_id, accumulated, message):
            try:
                async with AsyncSessionLocal() as session:
                    ne = await session.get(NodeExecution, node_exec_id)
                    if ne is None:
                        logger.warning("[trigger_post_action:on_event] FATAL node_exec not found id=%s", node_exec_id)
                        return
                    ne.artifact_data = dict(accumulated)
                    ne.status = "failed"
                    ne.error_message = message or "agentscope_error"
                    ne.completed_at = datetime.utcnow()
                    await session.commit()
                    logger.error("[trigger_post_action:on_event] FATAL committed: task_id=%s node_id=%s err=%s",
                        task_id, node_exec_id, message)
            except Exception:
                logger.exception("[trigger_post_action:on_event] failed commit failed")
        logger.debug(
            "[trigger_post_action:stream] accumulator initialized: keys=%s",
            list(accumulated.keys()),
        )
        # ★ 所有 DB 写入改为后台任务（asyncio.create_task），不阻塞 SSE 转发
        # ★ 注意：start 事件不写 DB——status=pending 在 trigger_post_action 入口已设置
        #   final 时才更新为 completed，error 时才更新为 failed

        async def on_event(ev: dict) -> None:
            """流式事件回调：仅记录日志，不阻塞 SSE 转发。

            所有 DB 写入改为后台任务（asyncio.create_task），
            确保 yield chunk 不被 on_event 阻塞。
            """
            nonlocal accumulated
            ev_type = ev.get("type")
            logger.debug(
                "[trigger_post_action:on_event] ev=%s task_id=%s node_id=%s",
                ev_type, task_id, node_id,
            )
            try:
                if ev_type == "start":
                    # ★ 仅更新内存，不写 DB
                    #   status=pending 在 trigger_post_action 入口已设置
                    #   前端通过 SSE start 事件就知道"节点在跑"
                    accumulated["_stream_state"] = "streaming"
                    accumulated["progress"] = 0
                    accumulated["started_at"] = datetime.utcnow().isoformat()
                elif ev_type == "intermediate":
                    # ★ 中间生成物（AMIS schema + data）—— 仅日志，不写 DB
                    component_id = ev.get("componentId", "")
                    logger.debug(
                        "[trigger_post_action:on_event] intermediate componentId=%s "
                        "has_schema=%s has_data=%s",
                        component_id,
                        ev.get("schema") is not None,
                        ev.get("data") is not None,
                    )
                elif ev_type == "final":
                    # ★ 仅更新内存，DB 写入交给后台任务
                    accumulated["progress"] = 100
                    # ★ 先标记 completed，再 commit DB——防止 commit 失败导致 proxy 不注入 artifact_snapshot
                    accumulated["_stream_state"] = "completed"

                    # ★ 通用规范下 final.data 是完整 artifact 快照
                    final_data = ev.get("data") or {}
                    artifact_schema = None
                    if final_data:
                        # artifact_schemas 已经是完整的 AMIS pages，直接用作 artifact_schema
                        if "artifact_schemas" in final_data:
                            artifact_schema = final_data["artifact_schemas"]
                        # 合并其他字段到 accumulated（保留 llmSuccess/llmFailed/elapsedMs 等）
                        for k, v in final_data.items():
                            if k != "artifact_schemas":
                                accumulated[k] = v

                    asyncio.create_task(
                        _commit_final(node_exec.id, task_id, accumulated, artifact_schema)
                    )
                elif ev_type == "error" and ev.get("fatal"):
                    # ★ fatal error：DB 写入交给后台任务
                    accumulated["_stream_state"] = "failed"
                    accumulated["error"] = ev.get("message")
                    asyncio.create_task(
                        _commit_failed(node_exec.id, task_id, accumulated, ev.get("message"))
                    )
                # ping 已被 stream_price_band_analyze 内部过滤，不到 on_event
                # 非 fatal error 忽略：流继续推进，最终以 final 事件为准
            except Exception:
                logger.exception(
                    "[trigger_post_action:on_event] write failed for event=%s "
                    "task_id=%s node_id=%s",
                    ev_type, task_id, node_id,
                )

        # ★ wrapper generator：透传 AgentScope 框架
        # ★ 通用规范下：final 事件已携带完整 artifact 快照，无需再注入 artifact_snapshot
        async def _stream_plus_snapshot():
            chunk_idx = 0
            import time as _time
            t_start = _time.time()
            logger.info("[trigger_post_action:_stream_plus_snapshot] entering wrapper")
            stream = stream_price_band_analyze(
                payload=payload,
                user_id=ctx.user_id,
                session_id=node_exec.id,
                on_event=on_event,
            )
            async for chunk in stream:
                chunk_idx += 1
                elapsed_ms = int((_time.time() - t_start) * 1000)
                logger.info(
                    "[trigger_post_action:_stream_plus_snapshot] wrapper chunk #%d elapsed=%dms size=%d",
                    chunk_idx, elapsed_ms, len(chunk))
                yield chunk
                # ★ 关键修复：让出事件循环，强制 FastAPI 立即 flush
                await asyncio.sleep(0)
                logger.info(
                    "[trigger_post_action:_stream_plus_snapshot] wrapper chunk #%d yielded",
                    chunk_idx)
            logger.info(
                "[trigger_post_action:_stream_plus_snapshot] stream ended, total chunks=%d total_elapsed=%dms",
                chunk_idx, int((_time.time() - t_start) * 1000))

        if direct_stream:
            # ★ 直接流模式：返回 Java 后端 SSE 端点元数据，前端直连 Java 拉 SSE 流
            #   不再经 proxy 转发 SSE，避免代理侧 SSE 帧缓冲/生命周期问题。
            #   前端收到 final 事件后，调 POST /{task_id}/nodes/{node_id}/artifact 落库。
            logger.info(
                "[trigger_post_action:stream] direct_stream mode: returning metadata "
                "session_id=%s user_id=%s",
                node_exec.id, ctx.user_id,
            )
            # 恢复任务状态 polling（direct_stream 模式下代理不代理 SSE，需前端自己管理）
            # streaming_node_id 标记由前端在 start 时设置
            return {
                "ok": True,
                "message": "stream_ready",
                "direct_stream": True,
                "task_id": task_id,
                "node_id": node_id,
                "node_exec_id": node_exec.id,
                "mapping_id": mapping.id,
                "stream_url": "/v1/price-band/analyze/stream",
                "internal_token": settings.AGENTSCOPE_INTERNAL_TOKEN,
                "body": payload,  # 前端直连 Java SSE 时需要 POST 的 body
            }

        logger.info(
            "[trigger_post_action:stream] returning StreamingResponse: "
            "session_id=%s user_id=%s",
            node_exec.id, ctx.user_id,
        )
        return StreamingResponse(
            _stream_plus_snapshot(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # 禁 nginx 缓冲
                "Connection": "keep-alive",
            },
        )

    # ---- 异步模式（默认，向后兼容 Celery worker）----
    from app.tasks.workflow_tasks import execute_post_action_node
    execute_post_action_node.delay(task_id, node_id, mapping.id)
    logger.info(
        "[trigger_post_action] dispatched (celery): task_id=%s node_id=%s mapping_id=%s",
        task_id, node_id, mapping.id,
    )
    return {
        "message": "post-action 已派发",
        "task_id": task_id,
        "node_id": node_id,
        "status": "pending",
    }


@router.post("/{task_id}/nodes/{node_id}/artifact", status_code=status.HTTP_200_OK)
async def set_node_artifact(
    task_id: str,
    node_id: str,
    body: NodeArtifactRequest,
    ctx = Depends(get_current_user_tenant),
):
    """SSE 直连模式下，前端收到 final 事件后回调此端点，落库 artifact 数据。

    使用独立 session（AsyncSessionLocal）而非 Depends(get_db)，
    避免 StreamingResponse 式的 session 生命周期冲突——此端点是短请求，不涉及流式输出。
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TaskInstance)
            .where(TaskInstance.id == task_id, TaskInstance.tenant_id == ctx.tenant_id, TaskInstance.user_id == ctx.user_id)
            .options(selectinload(TaskInstance.node_executions))
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

        node_exec = next(
            (n for n in task.node_executions if n.node_id == node_id),
            None,
        )
        if not node_exec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点执行记录不存在")

        # 写入 artifact 数据
        if body.artifact_data is not None:
            node_exec.artifact_data = body.artifact_data
        if body.artifact_schema is not None:
            node_exec.artifact_schema = body.artifact_schema
        if body.error_message:
            node_exec.status = "failed"
            node_exec.error_message = body.error_message
        else:
            node_exec.status = "completed"
        node_exec.completed_at = datetime.utcnow()

        # 更新任务状态
        all_done = all(n.status == "completed" for n in task.node_executions)
        task.status = "completed" if all_done else "running"

        await session.commit()
        logger.info(
            "[set_node_artifact] committed: task_id=%s node_id=%s status=%s task_status=%s",
            task_id, node_id, node_exec.status, task.status,
        )
        return {"ok": True}


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """Delete a single task and its node executions"""
    result = await db.execute(
        scoped_query_by_id(db, TaskInstance, task_id, ctx.tenant_id)
        .where(TaskInstance.user_id == ctx.user_id)
        .options(selectinload(TaskInstance.node_executions))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    for node in task.node_executions:
        await db.delete(node)
    await db.delete(task)
    await db.commit()

    return {"message": "任务已删除", "task_id": task_id}


@router.delete("", status_code=status.HTTP_200_OK)
async def delete_tasks(
    task_ids: List[str],
    db: AsyncSession = Depends(get_db),
    ctx = Depends(get_current_user_tenant),
):
    """Batch delete tasks and their node executions"""
    if not task_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请提供要删除的任务ID列表")

    result = await db.execute(
        scoped_query(db, TaskInstance, ctx.tenant_id)
        .where(TaskInstance.user_id == ctx.user_id, TaskInstance.id.in_(task_ids))
        .options(selectinload(TaskInstance.node_executions))
    )
    tasks = result.scalars().all()

    if not tasks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到要删除的任务")

    deleted_count = 0
    for task in tasks:
        for node in task.node_executions:
            await db.delete(node)
        await db.delete(task)
        deleted_count += 1

    await db.commit()

    return {"message": f"已删除 {deleted_count} 个任务", "deleted_count": deleted_count}
