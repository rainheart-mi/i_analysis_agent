from pathlib import Path
import logging
import os
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.router import api_router

# 配置日志级别（默认 INFO；可用 LOG_LEVEL 环境变量覆盖，例如 LOG_LEVEL=DEBUG）
# 生产环境保持 INFO；临时排查 trigger_post_action 等问题时
# 用 LOG_LEVEL=DEBUG uvicorn app.main:app --reload 启动可看到完整 trace。
_log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)
_log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_log_datefmt = "%Y-%m-%d %H:%M:%S"

# ★ 日志持久化（默认开启，可设 LOG_TO_FILE=false 关掉）
# - 路径：backend/logs/app.log（与 backend/app/ 同级；不在 git 追踪范围）
# - 轮转：RotatingFileHandler 10MB × 5 备份（总 ~50MB 上限，长期跑不撑盘）
# - 编码：utf-8（保留中文 + emoji）
# - 启动横幅会打印当前生效路径，便于 grep
_log_to_file = os.getenv("LOG_TO_FILE", "true").lower() not in ("false", "0", "no", "off")
_log_dir = Path(__file__).resolve().parent.parent / "logs"
_log_file_path: Path | None = None
if _log_to_file:
    _log_dir.mkdir(parents=True, exist_ok=True)
    _log_file_path = _log_dir / "app.log"

logging.basicConfig(
    level=_log_level,
    format=_log_format,
    datefmt=_log_datefmt,
)

# ★ 挂 RotatingFileHandler 到 root logger，让所有 app.* logger（app.api.v1.tasks 等）
#   自动继承。basicConfig 只能配一次，所以 FileHandler 在 basicConfig 之后手动 add。
if _log_file_path is not None:
    _file_handler = RotatingFileHandler(
        filename=_log_file_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
        delay=True,  # 第一次 write 时才 open，uvicorn 启动异常也不会留空文件
    )
    _file_handler.setLevel(_log_level)
    _file_handler.setFormatter(logging.Formatter(_log_format, _log_datefmt))
    logging.getLogger().addHandler(_file_handler)


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 仅当 storage backend 为 local 时挂载静态目录（OSS 模式由客户端直接访问 OSS URL）
if (settings.STORAGE_BACKEND or "local").lower() == "local":
    _upload_dir = Path(settings.LOCAL_STORAGE_DIR).resolve()
    _upload_dir.mkdir(parents=True, exist_ok=True)
    _mount_path = settings.LOCAL_STORAGE_URL_PREFIX.rstrip("/")
    app.mount(_mount_path, StaticFiles(directory=str(_upload_dir)), name="uploads")
    print(f"[Startup] Local file storage mounted at {_mount_path} -> {_upload_dir}")

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    """启动时输出提示信息"""
    print("[Startup] IERP AI Assistant backend started.")
    print(f"[Startup] Storage backend: {settings.STORAGE_BACKEND}")
    if _log_level == logging.DEBUG:
        print(f"[Startup] LOG_LEVEL={_log_level_name} (debug=ON)")
    else:
        print(f"[Startup] LOG_LEVEL={_log_level_name}")
    if _log_file_path is not None:
        print(f"[Startup] Log file: {_log_file_path} (RotatingFileHandler 10MB×5)")
    else:
        print("[Startup] Log file: disabled (LOG_TO_FILE=false)")
    print("To run workflow tasks, start Celery worker in another terminal:")
    print("  python -m celery -A app.celery_app worker --loglevel=info --pool=solo")


@app.get("/health")
async def health_check():
    return {"status": "ok"}