from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TaskCreate(BaseModel):
    workflow_id: str
    name: Optional[str] = None


class TaskResponse(BaseModel):
    id: str
    user_id: str
    workflow_id: str
    name: Optional[str]
    status: str
    current_node_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NodeExecutionCreate(BaseModel):
    node_id: str
    intent_data: Dict[str, Any] = {}


class NodeExecutionResponse(BaseModel):
    id: str
    task_instance_id: str
    node_id: str
    node_name: Optional[str]
    intent_schema_path: Optional[str]
    artifact_schema_path: Optional[str]
    intent_data: Dict[str, Any]
    artifact_data: Optional[Dict[str, Any]]
    intent_schema: Optional[Dict[str, Any]] = None
    artifact_schema: Optional[Dict[str, Any]] = None
    status: str
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class NodeUpdateRequest(BaseModel):
    intent_data: Optional[Dict[str, Any]] = None
    artifact_data: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class TaskDetailResponse(BaseModel):
    task: TaskResponse
    nodes: List[NodeExecutionResponse]
    workflow_title: Optional[str] = None