from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "IERP AI Assistant"
    DEBUG: bool = True

    # Database - 使用完整 URL 格式
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/i_analysis_agent"

    # 密钥（用于 Fernet 加密 N8N 密码）
    SECRET_KEY: str = "ierp-ai-assistant-secret-key-change-in-production"

    # Token 传输方式（对齐 Java 项目的 TokenProperties）
    # 读取顺序：JWT_HEADER_NAME header → JWT_COOKIE_NAME cookie → Authorization: Bearer
    JWT_HEADER_NAME: str = "jwt"
    JWT_COOKIE_NAME: str = "jwt"

    # N8N
    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_API_KEY: str = ""
    N8N_DEFAULT_TIMEOUT: int = 120

    # Redis - Celery broker & result backend
    REDIS_URL: str = "redis://localhost:6379/0"

    # AgentScope Java 后端 - OpenAI Chat Completions 兼容端点
    # 启动 Spring Boot 应用后默认监听 8080；内部共享 token 与 application.yml 一致
    AGENTSCOPE_URL: str = "http://localhost:8080"
    AGENTSCOPE_INTERNAL_TOKEN: str = "changeme"
    AGENTSCOPE_MODEL: str = "note-taker"
    AGENTSCOPE_TIMEOUT: int = 120  # 单次 chat 请求超时（秒）；流式按 chunk 计算
    # 注：post-action 端点（/v1/price-band/analyze 等）也复用上面这组配置；
    # 若未来拆微服务可补 AGENTSCOPE_PRICEBAND_URL / _TOKEN / _TIMEOUT。

    # ========== 外部 Token 校验 ==========
    # 调用 token 服务器的 /seqmappro/s/web/auth/token/validate 来验证 JWT，
    # 替代本地验签（我们不具备 JWT 签发密钥）。
    TOKEN_VALIDATION_ENABLED: bool = True
    TOKEN_VALIDATE_URL: str = "https://jssj.xupu3d.com:13008/seqmappro/s/web/auth/token/validate"
    TOKEN_VALIDATE_TIMEOUT: int = 10
    TOKEN_VALIDATE_VERIFY_SSL: bool = False

    # 默认租户（TOKEN_VALIDATION_ENABLED=False 时使用）
    DEFAULT_TENANT_ID: str = "default"
    DEFAULT_USER_ID: str = "default"
    DEFAULT_USER_NAME: str = "默认用户"

    # ========== 文件存储 ==========
    # STORAGE_BACKEND 决定使用哪种存储后端
    # - "local": 写入服务器本地目录，FastAPI StaticFiles 直接对外提供
    # - "oss2":  上传到阿里云 OSS（需配置 OSS_* 字段）
    STORAGE_BACKEND: str = "local"  # local | oss2

    # Local 存储配置
    LOCAL_STORAGE_DIR: str = "./uploads"
    LOCAL_STORAGE_URL_PREFIX: str = "/static/uploads"
    # 单文件最大字节数（防恶意上传占满磁盘）
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB

    # 阿里云 OSS2 配置（仅 STORAGE_BACKEND=oss2 时生效）
    # 启动时若 mode=oss2 但任一关键字段为空，直接抛错
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_ENDPOINT: str = ""              # 如 oss-cn-hangzhou.aliyuncs.com
    OSS_BUCKET: str = ""
    OSS_URL_PREFIX: str = ""            # 如 https://my-bucket.oss-cn-hangzhou.aliyuncs.com
    # bucket 内路径前缀，便于按租户/业务隔离
    # 留空则直接用 file_uuid 作为 key
    OSS_OBJECT_KEY_PREFIX: str = ""     # 如 "tenant-files/"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()