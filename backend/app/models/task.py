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

    workflow = relationship("WorkflowRoute")
    node_executions = relationship("NodeExecution", back_populates="task_instance", cascade="all, delete-orphan")


class NodeExecution(BaseModel):
    __tablename__ = "node_executions"

    task_instance_id = Column(String(36), ForeignKey("task_instances.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(100), nullable=False)
    node_name = Column(String(200))
    intent_schema_path = Column(String(500))
    artifact_schema_path = Column(String(500))
    intent_data = Column(JSON, default={})
    artifact_data = Column(JSON, default=None)
    status = Column(String(20), default="pending")  # pending/running/completed/failed
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    task_instance = relationship("TaskInstance", back_populates="node_executions")