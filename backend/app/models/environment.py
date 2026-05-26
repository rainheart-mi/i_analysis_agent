from sqlalchemy import Column, String, Boolean
from app.models.base import BaseModel


class N8NEnvironment(BaseModel):
    __tablename__ = "n8n_environments"

    name = Column(String(100), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(255))
    is_active = Column(Boolean, default=True)