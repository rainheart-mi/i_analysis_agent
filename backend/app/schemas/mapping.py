from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class WorkflowNodeMappingBase(BaseModel):
    route_id: str
    node_id: str = Field(..., min_length=1)
    node_name: Optional[str] = None
    intent_schema_path: Optional[str] = None
    artifact_schema_path: Optional[str] = None
    input_mapping: Optional[Dict[str, Any]] = None
    output_mapping: Optional[Dict[str, Any]] = None


class WorkflowNodeMappingCreate(WorkflowNodeMappingBase):
    pass


class WorkflowNodeMappingUpdate(BaseModel):
    route_id: Optional[str] = None
    node_id: Optional[str] = None
    node_name: Optional[str] = None
    intent_schema_path: Optional[str] = None
    artifact_schema_path: Optional[str] = None
    input_mapping: Optional[Dict[str, Any]] = None
    output_mapping: Optional[Dict[str, Any]] = None


class WorkflowNodeMappingResponse(WorkflowNodeMappingBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowNodeMappingListResponse(BaseModel):
    items: List[WorkflowNodeMappingResponse]
    total: int