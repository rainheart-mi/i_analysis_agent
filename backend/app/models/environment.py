from sqlalchemy import Column, String, Boolean
from app.models.base import BaseModel


class N8NEnvironment(BaseModel):
    __tablename__ = "n8n_environments"

    name = Column(String(100), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(255))
    is_active = Column(Boolean, default=True)
    tenant_id = Column(String(36), nullable=False, index=True)

    # Basic Auth 凭据（用于 N8N webhook 触发节点的"Generic Auth > Basic Auth"）
    # 都 nullable：保留"只 api_key 不要 basic auth"的场景
    # password_enc 是 Fernet 加密后的密文（用 settings.SECRET_KEY 派生 key）
    username = Column(String(255), nullable=True)
    password_enc = Column(String(500), nullable=True)
