from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class WorkflowNodeMapping(BaseModel):
    __tablename__ = "workflow_node_mappings"

    route_id = Column(String(36), ForeignKey("workflow_routes.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(100), nullable=False)
    node_name = Column(String(200))
    intent_schema_path = Column(String(500))
    artifact_schema_path = Column(String(500))
    n8n_workflow_id = Column(String(200))  # N8N webhook ID for this node
    tenant_id = Column(String(36), nullable=False, index=True)

    route = relationship("WorkflowRoute", back_populates="node_mappings")
