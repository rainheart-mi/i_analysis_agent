"""
异步工作流执行服务
负责调用 N8N 接口并处理执行结果
"""
import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings


async def execute_node_background(task_id: str, node_id: str):
    """
    后台执行节点（在新的 db session 中执行）
    """
    # 延迟导入以避免循环依赖
    from app.database import async_session_maker
    from app.models.task import TaskInstance, NodeExecution
    from app.models.mapping import WorkflowNodeMapping

    async with async_session_maker() as db:
        # 获取任务和节点信息
        result = await db.execute(
            select(TaskInstance)
            .options(selectinload(TaskInstance.node_executions))
            .where(TaskInstance.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return

        node = next((n for n in task.node_executions if n.node_id == node_id), None)
        if not node:
            return

        # 获取 N8N webhook ID
        n8n_workflow_id = await _get_n8n_workflow_id(db, task.workflow_id, node_id)

        # 调用 N8N
        try:
            result_data = await _call_n8n(n8n_workflow_id, node.intent_data)
            await _mark_node_completed(db, node, task, result_data)
        except Exception as e:
            await _mark_node_failed(db, node, task, str(e))


async def _get_n8n_workflow_id(db, workflow_id: str, node_id: str) -> Optional[str]:
    """获取节点对应的 N8N webhook ID"""
    result = await db.execute(
        select(WorkflowNodeMapping)
        .where(
            WorkflowNodeMapping.route_id == workflow_id,
            WorkflowNodeMapping.node_id == node_id
        )
    )
    mapping = result.scalar_one_or_none()
    return mapping.n8n_workflow_id if mapping else None


async def _call_n8n(webhook_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """调用 N8N webhook"""
    if not webhook_id:
        raise Exception("N8N workflow ID not configured")

    url = f"{settings.N8N_BASE_URL}/webhook/{webhook_id}"

    async with httpx.AsyncClient(timeout=settings.N8N_DEFAULT_TIMEOUT) as client:
        try:
            response = await client.post(url, json=inputs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"N8N API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"N8N call failed: {str(e)}")


async def _mark_node_completed(db, node, task, result_data: Dict[str, Any]):
    """标记节点为已完成"""
    node.artifact_data = result_data
    node.status = "completed"
    node.completed_at = datetime.utcnow()

    await db.commit()

    # 检查是否所有节点都已完成
    all_completed = all(n.status == "completed" for n in task.node_executions)
    if all_completed:
        task.status = "completed"
        await db.commit()
    else:
        # 激活下一个 pending 节点
        await _activate_next_node(db, task, node)


async def _mark_node_failed(db, node, task, error_message: str):
    """标记节点为失败"""
    node.status = "failed"
    node.error_message = error_message
    node.completed_at = datetime.utcnow()

    task.status = "failed"
    await db.commit()


async def _activate_next_node(db, task, current_node):
    """激活下一个节点"""
    pending_nodes = [n for n in task.node_executions if n.status == "pending"]
    if not pending_nodes:
        return

    next_node = pending_nodes[0]
    task.current_node_id = next_node.node_id
    task.status = "running"
    await db.commit()


# 旧的 asyncio 实现已废弃，改用 Celery
# def start_background_execution(task_id: str, node_id: str):
#     """
#     启动后台执行任务
#     在 FastAPI 的 request 之外独立运行
#     """
#     task = asyncio.create_task(execute_node_background(task_id, node_id))
#     return task