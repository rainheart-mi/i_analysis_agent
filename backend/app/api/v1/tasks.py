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
    db: AsyncSession = Depends(get_db)
):
    """Create a task for the given workflow_id"""
    result = await db.execute(
        select(WorkflowRoute)
        .options(selectinload(WorkflowRoute.node_mappings))
        .where(WorkflowRoute.id == task_data.workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")

    if not workflow.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="工作流已禁用")

    task_id = str(uuid.uuid4())
    task = TaskInstance(
        id=task_id,
        user_id="anonymous",
        workflow_id=task_data.workflow_id,
        name=task_data.name or f"Task-{task_id[:8]}",
        status="pending"
    )
    db.add(task)

    for mapping in workflow.node_mappings:
        node_exec = NodeExecution(
            id=str(uuid.uuid4()),
            task_instance_id=task_id,
            node_id=mapping.node_id,
            node_name=mapping.node_name,
            intent_schema_path=mapping.intent_schema_path,
            artifact_schema_path=mapping.artifact_schema_path,
            n8n_workflow_id=mapping.n8n_workflow_id,
            intent_data={},
            status="pending"
        )
        db.add(node_exec)

    await db.flush()
    await db.refresh(task)
    return task


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db)
):
    """Return all tasks for the current user (user_id = "anonymous")"""
    result = await db.execute(
        select(TaskInstance)
        .where(TaskInstance.user_id == "anonymous")
        .order_by(TaskInstance.created_at.desc())
    )
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task_detail(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Return task with all node executions, include workflow_title and schema content"""
    result = await db.execute(
        select(TaskInstance)
        .options(selectinload(TaskInstance.node_executions))
        .where(TaskInstance.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    workflow_result = await db.execute(
        select(WorkflowRoute.title)
        .where(WorkflowRoute.id == task.workflow_id)
    )
    workflow_title = workflow_result.scalar_one_or_none()

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
    db: AsyncSession = Depends(get_db)
):
    """
    异步执行节点 - Celery 方式
    1. 更新节点状态为 pending
    2. 立即返回
    3. Celery Worker 异步调用 n8n 并处理结果
    """
    result = await db.execute(
        select(TaskInstance)
        .options(selectinload(TaskInstance.node_executions))
        .where(TaskInstance.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node_exec = None
    for node in task.node_executions:
        if node.node_id == node_id:
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

    # 如果是第一个节点，用 intent_data 的关键值更新任务名称
    if task.node_executions and node_exec == task.node_executions[0]:
        # 取 intent_data 的第一个值作为任务名称后缀
        if update_data.intent_data:
            first_value = list(update_data.intent_data.values())[0]
            if first_value:
                # 获取工作流标题
                workflow_result = await db.execute(
                    select(WorkflowRoute.title)
                    .where(WorkflowRoute.id == task.workflow_id)
                )
                workflow_title = workflow_result.scalar_one_or_none() or "任务"
                task.name = f"{workflow_title}-{first_value}"

    await db.commit()

    # 发送 Celery 任务
    from app.tasks.workflow_tasks import execute_n8n_node
    execute_n8n_node.delay(task_id, node_id, node_exec.n8n_workflow_id, node_exec.intent_data)
    print(f"[execute_node] Task dispatched: task_id={task_id}, node_id={node_id}")

    return {"message": "节点开始执行", "task_id": task_id, "node_id": node_id, "status": "pending"}


@router.patch("/{task_id}/nodes/{node_id}", status_code=status.HTTP_200_OK)
async def update_node(
    task_id: str,
    node_id: str,
    update_data: NodeUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update artifact_data, status, error_message, completed_at"""
    result = await db.execute(
        select(TaskInstance)
        .options(selectinload(TaskInstance.node_executions))
        .where(TaskInstance.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node_exec = None
    for node in task.node_executions:
        if node.node_id == node_id:
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
    db: AsyncSession = Depends(get_db)
):
    """
    Mock 完成节点执行
    - 标记当前节点为 completed
    - 如果还有下一个 pending 节点，激活它
    - 如果所有节点都完成，才标记工作流为 completed
    """
    result = await db.execute(
        select(TaskInstance)
        .options(selectinload(TaskInstance.node_executions))
        .where(TaskInstance.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node_exec = None
    for node in task.node_executions:
        if node.node_id == node_id:
            node_exec = node
            break

    if not node_exec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点执行记录不存在")

    # Mock artifact data - must match display_review_artifact_schema.json structure
    mock_artifact_data = {
        "processedData": {
            "summary": {
                "periodA": {
                    "startDate": "2026-04-01",
                    "endDate": "2026-04-16"
                },
                "periodB": {
                    "startDate": "2026-04-15",
                    "endDate": "2026-05-01"
                },
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
                "newItems": [
                {"商品编码": "10000013"},{"商品编码": "10000031"},{"商品编码": "10000077"},{"商品编码": "10000079"},{"商品编码": "10000113"},{"商品编码": "10000241"},{"商品编码": "10000327"},{"商品编码": "10000434"},{"商品编码": "10000466"},{"商品编码": "10000499"},{"商品编码": "10000538"},{"商品编码": "10000565"},{"商品编码": "10000568"},{"商品编码": "10000574"},{"商品编码": "10000578"},{"商品编码": "11000138"},{"商品编码": "11000218"},{"商品编码": "11000269"},{"商品编码": "11000280"},{"商品编码": "11000281"},{"商品编码": "11000282"},{"商品编码": "11000283"},{"商品编码": "11000284"},{"商品编码": "11000285"},{"商品编码": "11000286"},{"商品编码": "11000288"},{"商品编码": "11000289"},{"商品编码": "11000291"},{"商品编码": "11000292"},{"商品编码": "12000114"},{"商品编码": "12000234"},{"商品编码": "13000179"},{"商品编码": "13000244"},{"商品编码": "13000246"},{"商品编码": "13000249"},{"商品编码": "14000051"},{"商品编码": "14000055"},{"商品编码": "14000056"},{"商品编码": "14000091"},{"商品编码": "14000133"},{"商品编码": "14000141"},{"商品编码": "14000142"},{"商品编码": "15000116"},{"商品编码": "15000118"},{"商品编码": "16000041"},{"商品编码": "16000098"},{"商品编码": "16000158"},{"商品编码": "16000243"},{"商品编码": "21000001"},{"商品编码": "21000009"},{"商品编码": "21000041"},{"商品编码": "21000091"},{"商品编码": "21000117"},{"商品编码": "21000133"},{"商品编码": "21000135"},{"商品编码": "21000145"},{"商品编码": "21000175"},{"商品编码": "21000220"},{"商品编码": "21000244"},{"商品编码": "21000253"},{"商品编码": "21000370"},{"商品编码": "21000382"},{"商品编码": "21000441"},{"商品编码": "21000459"},{"商品编码": "21000466"},{"商品编码": "21000515"},{"商品编码": "21000519"},{"商品编码": "21000529"},{"商品编码": "22000029"},{"商品编码": "22000033"},{"商品编码": "22000037"},{"商品编码": "22000067"},{"商品编码": "22000076"},{"商品编码": "22000108"},{"商品编码": "22000192"},{"商品编码": "22000288"},{"商品编码": "22000328"},{"商品编码": "22000334"},{"商品编码": "22000545"},{"商品编码": "22000571"},{"商品编码": "22000589"},{"商品编码": "22000613"},{"商品编码": "22000625"},{"商品编码": "22000639"},{"商品编码": "22000645"},{"商品编码": "22000657"},{"商品编码": "22000671"},{"商品编码": "22000756"},{"商品编码": "22000807"},{"商品编码": "22000873"},{"商品编码": "22000884"},{"商品编码": "22000886"},{"商品编码": "22000888"},{"商品编码": "22000890"},{"商品编码": "22000892"},{"商品编码": "22000894"},{"商品编码": "22000896"},{"商品编码": "22000898"},{"商品编码": "22000902"},{"商品编码": "22000906"},{"商品编码": "22000922"},{"商品编码": "22000924"},{"商品编码": "22000928"},{"商品编码": "22000930"},{"商品编码": "22000936"},{"商品编码": "22000940"},{"商品编码": "22000944"},{"商品编码": "22000946"},{"商品编码": "23000005"},{"商品编码": "23000041"},{"商品编码": "23000093"},{"商品编码": "23000134"},{"商品编码": "23000159"},{"商品编码": "23000246"},{"商品编码": "23000256"},{"商品编码": "23000292"},{"商品编码": "23000308"},{"商品编码": "23000343"},{"商品编码": "23000354"},{"商品编码": "23000362"},{"商品编码": "23000368"},{"商品编码": "23000383"},{"商品编码": "23000387"},{"商品编码": "23000405"},{"商品编码": "23000433"},{"商品编码": "23000464"},{"商品编码": "23000495"},{"商品编码": "23000513"},{"商品编码": "23000534"},{"商品编码": "23000538"},{"商品编码": "23000557"},{"商品编码": "23000561"},{"商品编码": "23000563"},{"商品编码": "23000565"},{"商品编码": "23000567"},{"商品编码": "23000569"},{"商品编码": "23000573"},{"商品编码": "23000575"},{"商品编码": "23000577"},{"商品编码": "23000579"},{"商品编码": "23000581"},{"商品编码": "23000592"},{"商品编码": "23000594"},{"商品编码": "23000596"},{"商品编码": "23000598"},{"商品编码": "23000600"},{"商品编码": "23000602"},{"商品编码": "23000604"},{"商品编码": "23000610"},{"商品编码": "24000019"},{"商品编码": "24000057"},{"商品编码": "24000155"},{"商品编码": "24000157"},{"商品编码": "24000235"},{"商品编码": "24000263"},{"商品编码": "24000343"},{"商品编码": "24000359"},{"商品编码": "24000363"},{"商品编码": "24000458"},{"商品编码": "24000503"},{"商品编码": "24000549"},{"商品编码": "24000571"},{"商品编码": "24000621"},{"商品编码": "24000694"},{"商品编码": "24000716"},{"商品编码": "24000720"},{"商品编码": "24000727"},{"商品编码": "24000789"},{"商品编码": "25000007"},{"商品编码": "25000061"},{"商品编码": "25000123"},{"商品编码": "25000199"},{"商品编码": "25000261"},{"商品编码": "25000289"},{"商品编码": "25000293"},{"商品编码": "25000301"},{"商品编码": "25000303"},{"商品编码": "25000342"},{"商品编码": "25000349"},{"商品编码": "25000353"},{"商品编码": "25000355"},{"商品编码": "26000013"},{"商品编码": "26000039"},{"商品编码": "26000076"},{"商品编码": "26000078"},{"商品编码": "27000020"},{"商品编码": "28010103"},{"商品编码": "98000150"}
            ],
            "lostItems": [
                {"商品编码": "10000097"},{"商品编码": "10000179"},{"商品编码": "10000185"},{"商品编码": "10000199"},{"商品编码": "10000267"},{"商品编码": "10000310"},{"商品编码": "10000346"},{"商品编码": "10000448"},{"商品编码": "10000485"},{"商品编码": "10000488"},{"商品编码": "10000496"},{"商品编码": "10000506"},{"商品编码": "10000514"},{"商品编码": "10000517"},{"商品编码": "10000560"},{"商品编码": "10000567"},{"商品编码": "11000093"},{"商品编码": "11000145"},{"商品编码": "11000207"},{"商品编码": "11000255"},{"商品编码": "11000260"},{"商品编码": "11000263"},{"商品编码": "11000264"},{"商品编码": "11000270"},{"商品编码": "11000275"},{"商品编码": "12000119"},{"商品编码": "12000134"},{"商品编码": "12000159"},{"商品编码": "12000161"},{"商品编码": "12000164"},{"商品编码": "12000172"},{"商品编码": "12000215"},{"商品编码": "13000009"},{"商品编码": "13000150"},{"商品编码": "13000235"},{"商品编码": "13000247"},{"商品编码": "13000250"},{"商品编码": "13000255"},{"商品编码": "14000089"},{"商品编码": "14000112"},{"商品编码": "14000134"},{"商品编码": "15000107"},{"商品编码": "15000108"},{"商品编码": "15000109"},{"商品编码": "15000112"},{"商品编码": "15000114"},{"商品编码": "16000018"},{"商品编码": "16000060"},{"商品编码": "16000061"},{"商品编码": "16000162"},{"商品编码": "16000181"},{"商品编码": "16000222"},{"商品编码": "16000235"},{"商品编码": "21000007"},{"商品编码": "21000013"},{"商品编码": "21000019"},{"商品编码": "21000021"},{"商品编码": "21000029"},{"商品编码": "21000059"},{"商品编码": "21000089"},{"商品编码": "21000093"},{"商品编码": "21000105"},{"商品编码": "21000125"},{"商品编码": "21000163"},{"商品编码": "21000191"},{"商品编码": "21000197"},{"商品编码": "21000234"},{"商品编码": "21000247"},{"商品编码": "21000330"},{"商品编码": "21000344"},{"商品编码": "21000362"},{"商品编码": "21000366"},{"商品编码": "21000399"},{"商品编码": "21000412"},{"商品编码": "21000416"},{"商品编码": "21000418"},{"商品编码": "22000003"},{"商品编码": "22000013"},{"商品编码": "22000073"},{"商品编码": "22000080"},{"商品编码": "22000178"},{"商品编码": "22000196"},{"商品编码": "22000198"},{"商品编码": "22000228"},{"商品编码": "22000252"},{"商品编码": "22000336"},{"商品编码": "22000338"},{"商品编码": "22000414"},{"商品编码": "22000430"},{"商品编码": "22000432"},{"商品编码": "22000469"},{"商品编码": "22000504"},{"商品编码": "22000535"},{"商品编码": "22000611"},{"商品编码": "22000629"},{"商品编码": "22000653"},{"商品编码": "22000691"},{"商品编码": "22000695"},{"商品编码": "22000769"},{"商品编码": "22000773"},{"商品编码": "22000805"},{"商品编码": "22000831"},{"商品编码": "22000878"},{"商品编码": "22000880"},{"商品编码": "23000007"},{"商品编码": "23000021"},{"商品编码": "23000025"},{"商品编码": "23000037"},{"商品编码": "23000091"},{"商品编码": "23000142"},{"商品编码": "23000200"},{"商品编码": "23000248"},{"商品编码": "23000294"},{"商品编码": "23000307"},{"商品编码": "23000309"},{"商品编码": "23000315"},{"商品编码": "23000366"},{"商品编码": "23000491"},{"商品编码": "23000493"},{"商品编码": "23000499"},{"商品编码": "23000516"},{"商品编码": "23000522"},{"商品编码": "23000540"},{"商品编码": "23000547"},{"商品编码": "24000133"},{"商品编码": "24000169"},{"商品编码": "24000177"},{"商品编码": "24000231"},{"商品编码": "24000369"},{"商品编码": "24000373"},{"商品编码": "24000407"},{"商品编码": "24000408"},{"商品编码": "24000412"},{"商品编码": "24000497"},{"商品编码": "24000505"},{"商品编码": "24000507"},{"商品编码": "24000509"},{"商品编码": "24000511"},{"商品编码": "24000587"},{"商品编码": "24000589"},{"商品编码": "24000631"},{"商品编码": "24000764"},{"商品编码": "25000021"},{"商品编码": "25000059"},{"商品编码": "25000069"},{"商品编码": "25000095"},{"商品编码": "25000109"},{"商品编码": "25000147"},{"商品编码": "25000151"},{"商品编码": "25000225"},{"商品编码": "25000297"},{"商品编码": "25000321"},{"商品编码": "25000324"},{"商品编码": "25000351"},{"商品编码": "26000048"},{"商品编码": "26000073"},{"商品编码": "27000016"},{"商品编码": "98000712"}
            ],
                "newShelves": ["M-SC07B-S002", "M-HB02A-S002"],
                "lostShelves": ["M-SG05B-S001"]
            },
            "newItemsDetail": [
                {"商品编码": "10000013", "商品名称": "有机苹果", "品类": "水果", "货架": "M-SC07B-S002"},
                {"商品编码": "10000031", "商品名称": "进口车厘子", "品类": "水果", "货架": "M-HB02A-S002"},
                {"商品编码": "10000077", "商品名称": "新鲜草莓", "品类": "水果", "货架": "M-SC07B-S003"},
                {"商品编码": "10000079", "商品名称": "进口蓝莓", "品类": "水果", "货架": "M-BP13A-S001"},
                {"商品编码": "10000113", "商品名称": "有机香蕉", "品类": "水果", "货架": "M-HB02A-S001"},
                {"商品编码": "10000241", "商品名称": "新鲜榴莲", "品类": "水果", "货架": "M-LS001"}
            ],
            "lostItemsDetail": [
                {"商品编码": "10000097", "商品名称": "过期酸奶", "品类": "冷藏日配", "货架": "M-LD09B-S004"},
                {"商品编码": "10000179", "商品名称": "临期面包", "品类": "烘焙", "货架": "M-BP10A-S003"},
                {"商品编码": "10000185", "商品名称": "破损零食", "品类": "休闲食品", "货架": "M-LC01A-W001"}
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
                {"货架ID": "M-HB02A-S002", "期初商品数": 0, "期末商品数": 1, "期初销售额": 0, "期末销售额": 13.9, "销售额变化率": None},
                {"货架ID": "M-SC07B-S003", "期初商品数": 2, "期末商品数": 2, "期初销售额": 361.24, "期末销售额": 1760.56, "销售额变化率": "387.37%"},
                {"货架ID": "M-BP13A-S001", "期初商品数": 1, "期末商品数": 3, "期初销售额": 250, "期末销售额": 887.60, "销售额变化率": "255.04%"},
                {"货架ID": "M-HB02A-S001", "期初商品数": 1, "期末商品数": 1, "期初销售额": 17.99, "期末销售额": 53.98, "销售额变化率": "200.06%"},
                {"货架ID": "M-LS001", "期初商品数": 3, "期末商品数": 6, "期初销售额": 198.75, "期末销售额": 437.4, "销售额变化率": "120.08%"},
                {"货架ID": "M-BP15B-G001", "期初商品数": 2, "期末商品数": 2, "期初销售额": 43.6, "期末销售额": 91.2, "销售额变化率": "109.17%"},
                {"货架ID": "M-LC01A-S010", "期初商品数": 1, "期末商品数": 1, "期初销售额": 13.86, "期末销售额": 27.66, "销售额变化率": "99.57%"},
                {"货架ID": "M-LD09B-S005", "期初商品数": 6, "期末商品数": 6, "期初销售额": 312.44, "期末销售额": 600.59, "销售额变化率": "92.23%"},
                {"货架ID": "M-BP10A-S001", "期初商品数": 6, "期末商品数": 6, "期初销售额": 2433.30, "期末销售额": 4329.34, "销售额变化率": "77.92%"},
                {"货架ID": "M-LD08B-S001", "期初商品数": 1, "期末商品数": 2, "期初销售额": 47.8, "期末销售额": 84.70, "销售额变化率": "77.20%"},
                {"货架ID": "M-BP14A-S001", "期初商品数": 6, "期末商品数": 4, "期初销售额": 243.5, "期末销售额": 418.65, "销售额变化率": "71.93%"},
                {"货架ID": "M-LD09B-W002", "期初商品数": 2, "期末商品数": 2, "期初销售额": 436.67, "期末销售额": 750.28, "销售额变化率": "71.82%"},
                {"货架ID": "M-LD09B-W001", "期初商品数": 4, "期末商品数": 4, "期初销售额": 992.3, "期末销售额": 1654.95, "销售额变化率": "66.78%"},
                {"货架ID": "M-SC06B-S003", "期初商品数": 2, "期末商品数": 2, "期初销售额": 1005.16, "期末销售额": 1619.23, "销售额变化率": "61.09%"},
                {"货架ID": "M-BP10B-S001", "期初商品数": 18, "期末商品数": 19, "期初销售额": 501.20, "期末销售额": 785.09, "销售额变化率": "56.64%"},
                {"货架ID": "M-BP12B-S002", "期初商品数": 5, "期末商品数": 5, "期初销售额": 399.93, "期末销售额": 625.05, "销售额变化率": "56.29%"},
                {"货架ID": "M-LD09B-S006", "期初商品数": 3, "期末商品数": 5, "期初销售额": 88.08, "期末销售额": 130.80, "销售额变化率": "48.50%"},
                {"货架ID": "M-BP14B-S001", "期初商品数": 8, "期末商品数": 7, "期初销售额": 611.74, "期末销售额": 887.74, "销售额变化率": "45.12%"},
                {"货架ID": "M-BP12B-S001", "期初商品数": 6, "期末商品数": 5, "期初销售额": 207.40, "期末销售额": 296.09, "销售额变化率": "42.76%"},
                {"货架ID": "M-LD09B-S001", "期初商品数": 4, "期末商品数": 3, "期初销售额": 98.94, "期末销售额": 136.28, "销售额变化率": "37.74%"},
                {"货架ID": "M-BP12A-S002", "期初商品数": 10, "期末商品数": 10, "期初销售额": 711.09, "期末销售额": 952.97, "销售额变化率": "34.02%"},
                {"货架ID": "M-BP10A-S004", "期初商品数": 12, "期末商品数": 11, "期初销售额": 579.62, "期末销售额": 767.36, "销售额变化率": "32.39%"},
                {"货架ID": "M-BP11A-S004", "期初商品数": 16, "期末商品数": 19, "期初销售额": 1727.46, "期末销售额": 2239.12, "销售额变化率": "29.62%"},
                {"货架ID": "M-LC01A-S009", "期初商品数": 6, "期末商品数": 6, "期初销售额": 2189.13, "期末销售额": 2775.29, "销售额变化率": "26.78%"},
                {"货架ID": "M-BP17B-S001", "期初商品数": 12, "期末商品数": 13, "期初销售额": 800.49, "期末销售额": 1011.44, "销售额变化率": "26.35%"},
                {"货架ID": "M-BP15B-S001", "期初商品数": 10, "期末商品数": 10, "期初销售额": 551.18, "期末销售额": 693.97, "销售额变化率": "25.91%"},
                {"货架ID": "M-BP16B-G001", "期初商品数": 5, "期末商品数": 5, "期初销售额": 241.89, "期末销售额": 299.4, "销售额变化率": "23.78%"},
                {"货架ID": "M-BP02B-S004", "期初商品数": 15, "期末商品数": 11, "期初销售额": 613.43, "期末销售额": 756.90, "销售额变化率": "23.39%"}
            ],
            "shelfEfficiencyChart": {
                "labels": ["M-SC07B-S003", "M-BP13A-S001", "M-HB02A-S001", "M-LS001", "M-BP15B-G001"],
                "efficiency": [880, 296, 54, 73, 46],
                "trend": [387, 255, 200, 120, 109]
            },
            "aiResponse": {
                "rawOutput": "### 品类管理复盘报告（2026.04.01–2026.05.01）\n\n#### 一、整体表现：稳健增长，结构分化显著\n- **销售达成**：总销售额从 ¥135,231.96 → ¥143,811.48，**整体增长 +6.34%**，优于行业同期均值（约+4.2%）。\n- **货架与商品规模**：货架数+1（115→116），商品数+30（1333→1363），**上架188款、下架158款，净增30款**，体现主动汰换与品类优化。\n\n#### 二、大类表现分析：水果/冷冻领跑，熟食/婴保严重失速\n| 大类 | 销售额增长率 | 关键洞察 |\n|------|-------------|----------|\n| **水果** | **+30.89%** | 增长贡献最大（占总增量38%），属高周转、高毛利核心品类 |\n| **冷冻品** | **+23.82%** | 增长稳定，与夏季备货节奏吻合 |\n| **3R熟食** | **-21.89%** | 最大负向拖累项，需紧急复盘 |\n| **婴保宠物** | **-53.61%** | 断崖下跌，判断为整组货架撤柜或品类战略收缩 |\n\n#### 三、货架效能诊断\n- TOP5高增长货架：M-SC07B-S003 (+387.37%)、M-BP13A-S001 (+255.04%)、M-HB02A-S001 (+200.06%)\n- 失能货架预警：M-SG05B-S001 已下架需核查原因\n\n#### 四、下一步动作清单\n1. 24h内：核查M-SG05B-S001下架原因\n2. 72h内：对TOP5失能货架开展现场动线/补货/价签三重稽查\n3. 本周内：输出《水果/冷冻品陈列SOP》",
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

    # 检查是否所有节点都已完成
    all_completed = all(n.status == "completed" for n in task.node_executions)
    if all_completed:
        task.status = "completed"
    else:
        # 激活下一个 pending 节点
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
    db: AsyncSession = Depends(get_db)
):
    """获取节点执行状态"""
    result = await db.execute(
        select(TaskInstance)
        .options(selectinload(TaskInstance.node_executions))
        .where(TaskInstance.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    node = next((n for n in task.node_executions if n.node_id == node_id), None)
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
    db: AsyncSession = Depends(get_db)
):
    """Delete a single task and its node executions"""
    result = await db.execute(
        select(TaskInstance)
        .options(selectinload(TaskInstance.node_executions))
        .where(TaskInstance.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    # Delete node executions first
    for node in task.node_executions:
        await db.delete(node)

    await db.delete(task)
    await db.commit()

    return {"message": "任务已删除", "task_id": task_id}


@router.delete("", status_code=status.HTTP_200_OK)
async def delete_tasks(
    task_ids: List[str],
    db: AsyncSession = Depends(get_db)
):
    """Batch delete tasks and their node executions"""
    if not task_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请提供要删除的任务ID列表")

    result = await db.execute(
        select(TaskInstance)
        .options(selectinload(TaskInstance.node_executions))
        .where(TaskInstance.id.in_(task_ids))
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