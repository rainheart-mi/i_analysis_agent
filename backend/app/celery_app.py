from celery import Celery

app = Celery('i_analysis_agent')
app.config_from_object('app.celery_config')

# 显式导入任务模块以确保任务注册
from app.tasks import workflow_tasks  # noqa

app.autodiscover_tasks(['app.tasks'])