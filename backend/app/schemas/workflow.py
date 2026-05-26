from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class WorkflowRouteBase(BaseModel):
    environment_id: str
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    n8n_workflow_id: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0


class WorkflowRouteCreate(WorkflowRouteBase):
    pass


class WorkflowRouteUpdate(BaseModel):
    environment_id: Optional[str] = None
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    n8n_workflow_id: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class WorkflowRouteResponse(WorkflowRouteBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowRouteListResponse(BaseModel):
    items: List[WorkflowRouteResponse]
    total: int