from sqlalchemy import Column, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class TaskInstance(BaseModel):
    __tablename__ = "task_instances"

    user_id = Column(String(36), nullable=False, index=True)
    workflow_id = Column(String(36), ForeignKey("workflow_routes.id"), nullable=False)
    name = Column(String(200))
    status = Column(String(20), default="pending")  # pending/running/completed/failed
    current_node_id = Column(String(100))
    tenant_id = Column(String(36), nullable=False, index=True)

    # 组织 & 员工信息（从 JWT claims oi/ot/ei/en 注入）
    org_id = Column(String(36), nullable=True, index=True)
    org_type = Column(String(20), nullable=True)
    emp_id = Column(String(36), nullable=True)
    emp_name = Column(String(100), nullable=True)

    workflow = relationship("WorkflowRoute")
    node_executions = relationship("NodeExecution", back_populates="task_instance", cascade="all, delete-orphan")


class NodeExecution(BaseModel):
    __tablename__ = "node_executions"

    task_instance_id = Column(String(36), ForeignKey("task_instances.id", ondelete="CASCADE"), nullable=False)
    mapping_id = Column(String(36), ForeignKey("workflow_node_mappings.id", ondelete="CASCADE"), nullable=False, index=True)
    node_id = Column(String(100), nullable=False)
    node_name = Column(String(200))
    intent_schema = Column(JSON, nullable=True)
    artifact_schema = Column(JSON, nullable=True)
    n8n_workflow_id = Column(String(200))  # N8N webhook ID for this node
    intent_data = Column(JSON, default={})
    artifact_data = Column(JSON, default=None)
    status = Column(String(20), default="pending")  # pending/running/completed/failed
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    tenant_id = Column(String(36), nullable=False, index=True)

    # 组织 & 员工信息（从 JWT claims oi/ot/ei/en 注入）
    org_id = Column(String(36), nullable=True, index=True)
    org_type = Column(String(20), nullable=True)
    emp_id = Column(String(36), nullable=True)
    emp_name = Column(String(100), nullable=True)

    task_instance = relationship("TaskInstance", back_populates="node_executions")
    mapping = relationship("WorkflowNodeMapping")
