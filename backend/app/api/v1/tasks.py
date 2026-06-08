from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Any, Dict, Optional
import uuid
import json
from datetime import datetime
from pathlib import Path

from app.database import get_db
from app.models.task import TaskInstance, NodeExecution
from app.models.workflow import WorkflowRoute
from app.schemas.task import (
    TaskCreate, TaskResponse, TaskDetailResponse,
    NodeExecutionResponse, NodeUpdateRequest
)
from app.config import settings
from app.api.deps import get_current_user_tenant
from app.services.tenant_query import scoped_query, scoped_query_by_id, apply_tenant


router = APIRouter()


def load_schema_file(schema_path: str) -> Optional[Dict[str, Any]]:
    """Load schema content from file path"""
    if not schema_path:
        return None
    try:
        base_path = Path(settings.SCHEMA_BASE_PATH).resolve()
        full_path = (base_path / schema_path).resolve()
        if full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def build_node_response(node_exec: NodeExecution) -> NodeExecutionResponse:
    """Build NodeExecutionResponse with schema content loaded from files"""
    intent_schema = None
    artifact_schema = None

    if node_exec.intent_schema_path:
        intent_schema = load_schema_file(node_exec.intent_schema_path)
    if node_exec.artifact_schema_path:
        artifact_schema = load_schema_file(node_exec.artifact_schema_path)

    return NodeExecutionResponse(
        id=node_exec.id,
        task_instance_id=node_exec.task_instance_id,
        node_id=node_exec.node_id,
        node_name=node_exec.node_name,
        intent_schema_path=node_exec.intent_schema_path,
        artifact_schema_path=node_exec.artifact_schema_path,
        intent_data=node_exec.intent_data or {},
        artifact_data=node_exec.artifact_data,
        intent_schema=intent_schema,
        artifact_schema=artifact_schema,
        status=node_exec.status,
        error_message=node_exec.error_message,
        started_at=node_exec.started_at,
        completed_at=node_exec.completed_at
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    """Create a task for the given workflow_id，归属到当前 user+tenant"""
    user, tid = ctx
    result = await db.execute(
        scoped_query_by_id(db, WorkflowRoute, task_data.workflow_id, tid)
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
        user_id=user.id,
        workflow_id=task_data.workflow_id,
        name=task_data.name or f"Task-{task_id[:8]}",
        status="pending"
    ), tid)
    db.add(task)

    for mapping in workflow.node_mappings:
        node_exec = apply_tenant(NodeExecution(
            id=str(uuid.uuid4()),
            task_instance_id=task_id,
            node_id=mapping.node_id,
            node_name=mapping.node_name,
            intent_schema_path=mapping.intent_schema_path,
            artifact_schema_path=mapping.artifact_schema_path,
            n8n_workflow_id=mapping.n8n_workflow_id,
            intent_data={},
            status="pending"
        ), tid)
        db.add(node_exec)

    await db.flush()
    await db.refresh(task)
    return task


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    """Return all tasks for the current user in the current tenant"""
    user, tid = ctx
    result = await db.execute(
        scoped_query(db, TaskInstance, tid)
        .where(TaskInstance.user_id == user.id)
        .order_by(TaskInstance.created_at.desc())
    )
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task_detail(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    """Return task with all node executions（按 user_id 隔离）"""
    user, tid = ctx
    result = await db.execute(
        scoped_query_by_id(db, TaskInstance, task_id, tid)
        .where(TaskInstance.user_id == user.id)
        .options(selectinload(TaskInstance.node_executions))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    workflow_result = await db.execute(
        scoped_query_by_id(db, WorkflowRoute, task.workflow_id, tid)
    )
    workflow_title = workflow_result.scalar_one_or_none() and \
                     (await db.execute(select(WorkflowRoute.title).where(WorkflowRoute.id == task.workflow_id))).scalar_one_or_none()

    nodes_with_schema = [build_node_response(n) for n in task.node_executions]

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
    ctx: tuple = Depends(get_current_user_tenant),
):
    """异步执行节点"""
    user, tid = ctx
    result = await db.execute(
        scoped_query_by_id(db, TaskInstance, task_id, tid)
        .where(TaskInstance.user_id == user.id)
        .options(selectinload(TaskInstance.node_executions))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node_exec = None
    for node in task.node_executions:
        if node.node_id == node_id and node.tenant_id == tid:
            node_exec = node
            break

    if not node_exec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点执行记录不存在")

    if node_exec.status not in ("pending", "failed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="节点状态不允许执行")

    if update_data.intent_data is not None:
        node_exec.intent_data = update_data.intent_data

    node_exec.status = "pending"
    task.status = "running"
    task.current_node_id = node_id

    if task.node_executions and node_exec == task.node_executions[0]:
        if update_data.intent_data:
            first_value = list(update_data.intent_data.values())[0]
            if first_value:
                workflow_result = await db.execute(
                    scoped_query_by_id(db, WorkflowRoute, task.workflow_id, tid)
                )
                workflow_row = workflow_result.scalar_one_or_none()
                workflow_title = workflow_row.title if workflow_row else "任务"
                task.name = f"{workflow_title}-{first_value}"

    await db.commit()

    from app.tasks.workflow_tasks import execute_n8n_node
    execute_n8n_node.delay(task_id, node_id, node_exec.n8n_workflow_id, node_exec.intent_data)
    print(f"[execute_node] Task dispatched: task_id={task_id}, node_id={node_id}, tenant_id={tid}")

    return {"message": "节点开始执行", "task_id": task_id, "node_id": node_id, "status": "pending"}


@router.patch("/{task_id}/nodes/{node_id}", status_code=status.HTTP_200_OK)
async def update_node(
    task_id: str,
    node_id: str,
    update_data: NodeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    """Update artifact_data, status, error_message, completed_at"""
    user, tid = ctx
    result = await db.execute(
        scoped_query_by_id(db, TaskInstance, task_id, tid)
        .where(TaskInstance.user_id == user.id)
        .options(selectinload(TaskInstance.node_executions))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node_exec = None
    for node in task.node_executions:
        if node.node_id == node_id and node.tenant_id == tid:
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
    ctx: tuple = Depends(get_current_user_tenant),
):
    """Mock 完成节点执行"""
    user, tid = ctx
    result = await db.execute(
        scoped_query_by_id(db, TaskInstance, task_id, tid)
        .where(TaskInstance.user_id == user.id)
        .options(selectinload(TaskInstance.node_executions))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node_exec = None
    for node in task.node_executions:
        if node.node_id == node_id and node.tenant_id == tid:
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
    ctx: tuple = Depends(get_current_user_tenant),
):
    """获取节点执行状态"""
    user, tid = ctx
    result = await db.execute(
        scoped_query_by_id(db, TaskInstance, task_id, tid)
        .where(TaskInstance.user_id == user.id)
        .options(selectinload(TaskInstance.node_executions))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node = next((n for n in task.node_executions if n.node_id == node_id and n.tenant_id == tid), None)
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
        "completed_at": node.completed_at.isoformat() if node.completed_at else None
    }


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: tuple = Depends(get_current_user_tenant),
):
    """Delete a single task and its node executions"""
    user, tid = ctx
    result = await db.execute(
        scoped_query_by_id(db, TaskInstance, task_id, tid)
        .where(TaskInstance.user_id == user.id)
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
    ctx: tuple = Depends(get_current_user_tenant),
):
    """Batch delete tasks and their node executions"""
    user, tid = ctx
    if not task_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请提供要删除的任务ID列表")

    result = await db.execute(
        scoped_query(db, TaskInstance, tid)
        .where(TaskInstance.user_id == user.id, TaskInstance.id.in_(task_ids))
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
