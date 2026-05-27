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

    # Mock Mode - 当为 True 时，worker 不调用真实的 n8n API
    MOCKER_MODE: bool = False

    # Schema Files - 相对于 backend 目录
    SCHEMA_BASE_PATH: str = "."

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()