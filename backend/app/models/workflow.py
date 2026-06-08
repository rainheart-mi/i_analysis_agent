from sqlalchemy import Column, String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class WorkflowRoute(BaseModel):
    __tablename__ = "workflow_routes"

    environment_id = Column(String(36), ForeignKey("n8n_environments.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    n8n_workflow_id = Column(String(100))
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    tenant_id = Column(String(36), nullable=False, index=True)

    environment = relationship("N8NEnvironment")
    node_mappings = relationship("WorkflowNodeMapping", back_populates="route", cascade="all, delete-orphan")
