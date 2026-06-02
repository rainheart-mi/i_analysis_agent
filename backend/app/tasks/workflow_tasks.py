from app.celery_app import app
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import json
import asyncio


# 模块级事件循环（解决 Windows 上 asyncio 问题）
_task_loop = None


def _get_task_loop():
    global _task_loop
    if _task_loop is None or _task_loop.is_closed():
        _task_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_task_loop)
    return _task_loop


def safe_serializer(obj):
    """安全序列化 datetime 等对象"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


@app.task(bind=True, name='execute_n8n_node')
def execute_n8n_node(self, task_id: str, node_id: str, n8n_workflow_id: str, intent_data: dict):
    """Celery Task: 执行 n8n 节点"""
    print(f"[execute_n8n_node] Task started: task_id={task_id}, node_id={node_id}")
    from app.database import async_session_maker
    from app.models.task import TaskInstance, NodeExecution
    from app.models.workflow import WorkflowRoute
    from app.services.n8n_service import get_n8n_service
    from app.config import settings

    async def _execute():
        async with async_session_maker() as db:
            result = await db.execute(
                select(TaskInstance)
                .options(selectinload(TaskInstance.node_executions))
                .options(selectinload(TaskInstance.workflow).selectinload(WorkflowRoute.environment))
                .where(TaskInstance.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return {"error": "Task not found"}

            node = next((n for n in task.node_executions if n.node_id == node_id), None)
            if not node:
                return {"error": "Node not found"}

            # 获取环境配置
            environment = task.workflow.environment

            node.status = "running"
            node.started_at = datetime.utcnow()
            task.status = "running"
            task.current_node_id = node_id
            await db.commit()

            try:
                # Mocker 模式：不调用真实 n8n API，等待界面 mock 完成
                if settings.MOCKER_MODE == "mocker":
                    print(f"[execute_n8n_node] Mocker mode - skipping n8n call for task_id={task_id}")
                    return {"status": "waiting_mock"}

                n8n_service = get_n8n_service(
                    environment.base_url,
                    environment.api_key,
                    settings.MOCKER_MODE
                )
                result_data = await n8n_service.execute_workflow(n8n_workflow_id, node_id, intent_data)
                print(f"[execute_n8n_node] N8N response: {result_data}")

                # 标准化数据格式：确保数据被包装在 processedData 下
                # n8n 可能返回：
                #   1. [{processedData: {...}}] - 数组包processedData
                #   2. {processedData: {...}} - 直接对象包processedData
                #   3. {summary: ..., categorySalesGrowth: ...} - 扁平数据（需要包装）
                raw_data = result_data
                if isinstance(result_data, list) and len(result_data) > 0:
                    raw_data = result_data[0]

                processed_data = raw_data.get('processedData', raw_data)

                # 如果 processedData 中缺少 summary 等顶层字段，说明返回的是扁平数据
                # 直接将整个 raw_data 作为 processedData 处理
                if 'summary' not in processed_data and 'summary' in raw_data:
                    processed_data = raw_data

                # 修复：把 n8n 返回的 aiResponse 等顶层字段合并到 processedData 内
                # 与 mock 数据结构（processedData.aiResponse.rawOutput）对齐
                for key, value in raw_data.items():
                    if key == 'processedData':
                        continue
                    if key not in processed_data:
                        processed_data[key] = value

                node.artifact_data = {"processedData": processed_data}
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

    loop = _get_task_loop()
    result = loop.run_until_complete(_execute())
    print(f"[execute_n8n_node] Task completed: task_id={task_id}, node_id={node_id}, result={result}")
    return result