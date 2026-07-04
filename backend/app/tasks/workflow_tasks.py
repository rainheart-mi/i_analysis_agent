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
    """Celery Task: 执行 n8n 节点

    完成后若 mapping 配置了 post_action（auto/both 模式），
    派发 `execute_post_action_node` 让子节点独立跑，不阻塞 workflow 推进。
    """
    print(f"[execute_n8n_node] Task started: task_id={task_id}, node_id={node_id}")
    from app.database import async_session_maker
    from app.models.task import TaskInstance, NodeExecution
    from app.models.workflow import WorkflowRoute
    from app.models.mapping import WorkflowNodeMapping
    from app.services.n8n_service import get_n8n_service
    from app.config import settings

    async def _execute():
        async with async_session_maker() as db:
            result = await db.execute(
                select(TaskInstance)
                .options(selectinload(TaskInstance.node_executions))
                .options(
                    selectinload(TaskInstance.workflow)
                    .selectinload(WorkflowRoute.environment)
                )
                .options(
                    selectinload(TaskInstance.workflow)
                    .selectinload(WorkflowRoute.node_mappings)
                )
                .where(TaskInstance.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return {"error": "Task not found"}

            # 多租户：节点必须属于当前任务的租户
            node = next((n for n in task.node_executions
                         if n.node_id == node_id and n.tenant_id == task.tenant_id), None)
            if not node:
                return {"error": "Node not found"}

            # 找到当前 mapping（用于读 post_action_config 与校验 n8n_workflow_id）
            mapping = next(
                (m for m in task.workflow.node_mappings if m.id == node.mapping_id),
                None,
            )
            if not mapping:
                return {"error": f"Mapping {node.mapping_id} not found"}

            # 获取环境配置
            environment = task.workflow.environment

            node.status = "running"
            node.started_at = datetime.utcnow()
            task.status = "running"
            task.current_node_id = node_id
            await db.commit()

            try:
                # Basic Auth 凭据：username 明文，password 需从 password_enc 解密
                # 延迟导入：避免在文件顶层引入 settings 时循环依赖
                from app.services.crypto import decrypt_password
                basic_password = (
                    decrypt_password(environment.password_enc)
                    if environment.password_enc
                    else None
                )
                n8n_service = get_n8n_service(
                    environment.base_url,
                    environment.api_key,
                    environment.username,
                    basic_password,
                )
                # 多租户校验：environment 必须属于当前任务的租户
                if environment.tenant_id != task.tenant_id:
                    return {"status": "failed", "error": "environment tenant mismatch"}
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

                # 触发下游 agent 节点（按 DAG 边推进；按需自动派发 pending 状态的 agent）
                _dispatch_next_node(task, mapping)

                all_completed = all(
                    n.status in ("completed", "failed") for n in task.node_executions
                )
                if all_completed:
                    # 仅当没有任何 failed 节点时才标 task 完成
                    has_failed = any(n.status == "failed" for n in task.node_executions)
                    task.status = "failed" if has_failed else "completed"
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


def _dispatch_next_node(task, completed_mapping) -> None:
    """DAG 边推进：找 completed_mapping 的下游（previous_node_id == completed_mapping.id），
    若下游 NodeExecution 仍是 pending 则派发它。

    支持任意 node_type：
    - n8n  下游 → execute_n8n_node.delay（用户后续在 UI 点"执行"才真正派发，此函数不直接派 n8n）
    - agent 下游 → ★ 改为不自动派发（让前端流式接管，见下方注释）

    当前用法：n8n 完成后立刻派发 agent 下游；n8n → n8n 仍由前端"执行工作流"按钮触发。

    ★ 为何 agent 下游不再自动派发 Celery？
      agent 节点是流式 SSE 代理（POST /v1/price-band/analyze/stream），需要 FastAPI 进程的
      StreamingResponse 把帧推给浏览器。Celery worker 进程没有浏览器侧的 HTTP response，
      即使内部 fetch SSE 也只能消费到本地（写 DB / 入内存），无法推到浏览器。
      因此 agent 下游改为：前端 polling 检测到 n8n 完成 → 自动调 trigger_post_action?stream=true。
      Celery 任务 execute_post_action_node 保留作为兜底（无浏览器 / 前端失败时可手动调）。
    """
    if not completed_mapping:
        return
    next_mappings = [
        m for m in task.workflow.node_mappings
        if m.previous_node_id == completed_mapping.id
    ]
    for next_m in next_mappings:
        next_node = next(
            (n for n in task.node_executions if n.mapping_id == next_m.id),
            None,
        )
        if not next_node or next_node.status != "pending":
            continue
        if next_m.node_type == "agent":
            # ★ agent 下游不再自动派发；前端 polling 会检测并触发流式 SSE。
            #   Celery 任务 execute_post_action_node 保留供手动兜底。
            print(
                f"[dispatch_next_node] agent downstream pending: task_id={task.id} "
                f"node_id={next_node.node_id} (waiting for frontend SSE)",
            )
        else:
            # n8n 下游：保留 UI 触发语义，不在 worker 里直接派发
            print(
                f"[dispatch_next_node] n8n downstream pending: task_id={task.id} "
                f"node_id={next_node.node_id} (waiting for UI)",
            )


@app.task(bind=True, name='execute_post_action_node')
def execute_post_action_node(self, task_id: str, node_id: str, mapping_id: str):
    """Celery Task: 执行 post-action 节点

    - 调 AgentScope 同步端点（/v1/price-band/analyze 等）
    - 响应写入 `node.artifact_data`
    - 失败写 `node.error_message` + status="failed"，不阻断 task 推进
    """
    print(f"[execute_post_action_node] Task started: task_id={task_id}, node_id={node_id}")
    from app.database import async_session_maker
    from app.models.task import TaskInstance, NodeExecution
    from app.models.workflow import WorkflowRoute
    from app.services import agentscope_proxy

    async def _run():
        async with async_session_maker() as db:
            result = await db.execute(
                select(TaskInstance)
                .options(selectinload(TaskInstance.node_executions))
                .options(
                    selectinload(TaskInstance.workflow)
                    .selectinload(WorkflowRoute.node_mappings)
                )
                .where(TaskInstance.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return {"error": "Task not found"}

            node = next(
                (n for n in task.node_executions
                 if n.node_id == node_id and n.tenant_id == task.tenant_id),
                None,
            )
            if not node:
                return {"error": "Node not found"}

            # 找 agent mapping 自己
            agent_mapping = next(
                (m for m in task.workflow.node_mappings
                 if m.id == mapping_id and m.node_type == "agent"),
                None,
            )
            if not agent_mapping or not agent_mapping.previous_node_id:
                return {"error": "agent mapping or previous_node_id missing"}

            # 通过 previous_node_id 找上游 NodeExecution（提供 artifact 上下文）
            parent_node = next(
                (n for n in task.node_executions
                 if n.mapping_id == agent_mapping.previous_node_id),
                None,
            )
            if not parent_node:
                return {"error": "upstream node not found"}

            # 上游节点必须是 completed（防止上游还没跑完就被触发）
            if parent_node.status != "completed":
                node.status = "failed"
                node.error_message = f"上游节点未完成（status={parent_node.status}），跳过 agent 节点"
                node.completed_at = datetime.utcnow()
                await db.commit()
                return {"status": "skipped", "reason": "upstream_not_completed"}

            node.status = "running"
            node.started_at = datetime.utcnow()
            await db.commit()

            try:
                data = await agentscope_proxy.call_post_action(
                    agent_mapping=agent_mapping,
                    parent_node=parent_node,
                    task=task,
                )
                node.artifact_data = data
                node.status = "completed"
                node.completed_at = datetime.utcnow()
                print(
                    f"[execute_post_action_node] completed: task_id={task_id} "
                    f"node_id={node_id} keys={list(data.keys()) if isinstance(data, dict) else type(data).__name__}",
                )
            except agentscope_proxy.PostActionError as e:
                node.status = "failed"
                node.error_message = str(e)
                node.completed_at = datetime.utcnow()
                print(
                    f"[execute_post_action_node] PostActionError: task_id={task_id} "
                    f"node_id={node_id} error={e}",
                )
            except Exception as e:
                node.status = "failed"
                node.error_message = f"{e.__class__.__name__}:{e}"
                node.completed_at = datetime.utcnow()
                print(
                    f"[execute_post_action_node] unexpected error: task_id={task_id} "
                    f"node_id={node_id} error={e}",
                )

            # 维护 task 整体状态 + 推进下游（DAG 边）
            # 先 commit 当前节点状态，再 dispatch 下游（dispatch 内部需要最新 commit）
            all_done = all(
                n.status in ("completed", "failed") for n in task.node_executions
            )
            if all_done:
                has_failed = any(n.status == "failed" for n in task.node_executions)
                task.status = "failed" if has_failed else "completed"
            else:
                pending_nodes = [n for n in task.node_executions if n.status == "pending"]
                if pending_nodes:
                    task.current_node_id = pending_nodes[0].node_id
            await db.commit()

            # DAG 边推进：找 agent 自己的下游；若有 agent 下游则链式派发
            # （agent → n8n 仍由前端触发；agent → agent 自动派发）
            _dispatch_next_node(task, agent_mapping)

            return {"status": node.status}

    loop = _get_task_loop()
    return loop.run_until_complete(_run())
