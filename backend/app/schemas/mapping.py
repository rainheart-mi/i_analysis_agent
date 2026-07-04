from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class WorkflowNodeMappingBase(BaseModel):
    route_id: str
    node_id: str = Field(..., min_length=1)
    node_name: Optional[str] = None
    intent_schema: Optional[Dict[str, Any]] = None
    artifact_schema: Optional[Dict[str, Any]] = None
    # 允许存量 NULL（历史数据未补），但创建/更新时空字符串会被 min_length=1 拒绝
    n8n_workflow_id: Optional[str] = Field(None, min_length=1, max_length=200)
    # ---- DAG 字段 ----
    # node_type: "n8n" | "agent"
    # previous_node_id: agent 节点指向其上游 mapping.id（自引用 FK，SET NULL）
    # post_action_config: agent 节点必填；n8n 节点为 null
    node_type: Optional[str] = Field("n8n", description="n8n | agent")
    previous_node_id: Optional[str] = Field(None, description="DAG 边：指向同 route 下上游 mapping.id")
    post_action_config: Optional[Dict[str, Any]] = Field(
        None,
        description="agent 节点必填；按 node_type 校验",
    )


class WorkflowNodeMappingCreate(WorkflowNodeMappingBase):
    # route_id 由 URL 路径参数 `/mappings/workflow/{route_id}` 提供，payload 不传
    route_id: Optional[str] = None
    # n8n_workflow_id 改为 optional：DAG 模型下只有 node_type='n8n' 才必填；
    # 必填校验交给 _validate_node_type_fields（已在 api/v1/mappings.py 实现），
    # 这样 agent 节点提交时不会被 Pydantic 提前 422。
    n8n_workflow_id: Optional[str] = Field(None, min_length=1, max_length=200)


class WorkflowNodeMappingUpdate(BaseModel):
    route_id: Optional[str] = None
    node_id: Optional[str] = None
    node_name: Optional[str] = None
    intent_schema: Optional[Dict[str, Any]] = None
    artifact_schema: Optional[Dict[str, Any]] = None
    # 同 Create：optional；按 node_type 校验由 _validate_node_type_fields(partial=True) 负责
    n8n_workflow_id: Optional[str] = Field(None, min_length=1, max_length=200)
    node_type: Optional[str] = None
    previous_node_id: Optional[str] = None
    post_action_config: Optional[Dict[str, Any]] = None


class WorkflowNodeMappingResponse(WorkflowNodeMappingBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowNodeMappingListResponse(BaseModel):
    items: List[WorkflowNodeMappingResponse]
    total: int