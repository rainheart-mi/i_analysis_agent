from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "IERP AI Assistant"
    DEBUG: bool = True
    ENV: str = "development"

    # Database - 使用完整 URL 格式
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/i_analysis_agent"

    # JWT
    SECRET_KEY: str = "ierp-ai-assistant-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # N8N
    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_API_KEY: str = ""
    N8N_DEFAULT_TIMEOUT: int = 120

    # Mock Mode - mocker: 不调用n8n | test: 调用test webhook | production: 调用production webhook
    # mocker: 不调用真实 n8n API，等待界面 mock 完成
    # test: 调用 n8n test webhook (工作流未发布时)
    # production: 调用 n8n production webhook (工作流已发布)
    MOCKER_MODE: str = "mocker"  # mocker / test / production

    # Redis - Celery broker & result backend
    REDIS_URL: str = "redis://localhost:6379/0"

    # Schema Files - 相对于 backend 目录
    SCHEMA_BASE_PATH: str = "."

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()