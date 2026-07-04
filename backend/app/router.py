from fastapi import APIRouter
from app.api.v1 import environments, workflows, mappings, execute, tasks, config, chat, files


api_router = APIRouter()

api_router.include_router(environments.router, prefix="/n8n-environments", tags=["N8N环境"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["工作流路由"])
api_router.include_router(mappings.router, prefix="/mappings", tags=["节点映射"])
api_router.include_router(execute.router, prefix="/execute", tags=["工作流执行"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务管理"])
api_router.include_router(config.router, prefix="/config", tags=["应用配置"])
api_router.include_router(chat.router, prefix="/chat", tags=["AI智能体对话"])
api_router.include_router(files.router, prefix="/files", tags=["文件存储"])