from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator


class NodeArtifactRequest(BaseModel):
    """SSE final/fatal error 事件后前端回调代理，落库 artifact 数据。

    正常流程：final 事件后带 artifact_data + artifact_schema，status=completed。
    失败流程：fatal error 后带 error_message，status=failed。
    """
    artifact_data: Optional[Any] = None
    artifact_schema: Optional[Any] = None
    error_message: Optional[str] = None


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
    org_id: Optional[str] = None
    org_type: Optional[str] = None
    emp_id: Optional[str] = None
    emp_name: Optional[str] = None
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
    intent_data: Optional[Any] = {}
    artifact_data: Optional[Any] = None
    intent_schema: Optional[Dict[str, Any]] = {}
    artifact_schema: Optional[Any] = {}
    status: str
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    mapping_id: Optional[str] = None
    node_type: Optional[str] = None
    parent_node_execution_id: Optional[str] = None
    org_id: Optional[str] = None
    org_type: Optional[str] = None
    emp_id: Optional[str] = None
    emp_name: Optional[str] = None

    @field_validator('intent_schema', 'artifact_schema', mode='before')
    @classmethod
    def null_to_empty_dict(cls, v):
        return {} if v is None else v

    class Config:
        from_attributes = True


class NodeUpdateRequest(BaseModel):
    intent_data: Optional[Dict[str, Any]] = None
    artifact_data: Optional[Any] = None
    status: Optional[str] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class TaskDetailResponse(BaseModel):
    task: TaskResponse
    nodes: List[NodeExecutionResponse]
    workflow_title: Optional[str] = None