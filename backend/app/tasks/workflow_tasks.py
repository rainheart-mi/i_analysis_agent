from app.celery_app import app
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import json


def safe_serializer(obj):
    """安全序列化 datetime 等对象"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


@app.task(bind=True, name='execute_n8n_node')
def execute_n8n_node(self, task_id: str, node_id: str, n8n_workflow_id: str, intent_data: dict):
    """Celery Task: 执行 n8n 节点"""
    print(f"[execute_n8n_node] Task started: task_id={task_id}, node_id={node_id}")
    import asyncio
    from app.database import async_session_maker
    from app.models.task import TaskInstance, NodeExecution
    from app.services.n8n_service import get_n8n_service
    from app.config import settings

    async def _execute():
        async with async_session_maker() as db:
            result = await db.execute(
                select(TaskInstance)
                .options(selectinload(TaskInstance.node_executions))
                .where(TaskInstance.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return {"error": "Task not found"}

            node = next((n for n in task.node_executions if n.node_id == node_id), None)
            if not node:
                return {"error": "Node not found"}

            node.status = "running"
            node.started_at = datetime.utcnow()
            task.status = "running"
            task.current_node_id = node_id
            await db.commit()

            try:
                # Mocker 模式：不调用真实 n8n API，等待界面 mock 完成
                if settings.MOCKER_MODE:
                    print(f"[execute_n8n_node] Mocker mode - skipping n8n call for task_id={task_id}")
                    return {"status": "waiting_mock"}

                n8n_service = get_n8n_service(settings.N8N_BASE_URL, settings.N8N_API_KEY)
                result_data = await n8n_service.execute_workflow(n8n_workflow_id, node_id, intent_data)

                node.artifact_data = result_data
                node.status = "completed"
                node.completed_at = datetime.utcnow()
                await db.commit()

                all_completed = all(n.status == "completed" for n in task.node_executions)
                if all_completed:
                    task.status = "completed"
                else:
                    pending_nodes = [n for n in task.node_executions if n.status == "pending"]
                    if pending_nodes:
                        task.current_node_id = pending_nodes[0].node_id
                await db.commit()

                return {"status": "completed"}

            except Exception as e:
                node.status = "failed"
                node.error_message = str(e)
                node.completed_at = datetime.utcnow()
                task.status = "failed"
                await db.commit()
                print(f"[execute_n8n_node] Task failed: task_id={task_id}, node_id={node_id}, error={str(e)}")
                return {"status": "failed", "error": str(e)}

    result = asyncio.run(_execute())
    print(f"[execute_n8n_node] Task completed: task_id={task_id}, node_id={node_id}, result={result}")
    return result