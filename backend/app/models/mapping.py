"""工作流节点映射（v1 DAG 模型）。

设计：
- `node_type` 区分两种本质不同的节点：
    - "n8n"   : 普通 n8n webhook 节点
    - "agent" : AgentScope 同步端点调用节点（v1 也称为 post-action）
- DAG 边：`previous_node_id` 自引用 FK，指向其上游节点（n8n 或 agent）。
- v1 限定单值（线性链）；将来要扩 fan-out 只需把它改成 JSON 数组。
- 删除上游节点走 SET NULL，下游节点保留但 UI 提示"上游缺失"。

注意：底层的 JSON 列（`intent_schema`/`artifact_schema`/`post_action_config`）按
node_type 分布，并非同一行多态——后端 API 在保存时按 node_type 校验必填字段。
"""
from sqlalchemy import Column, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class WorkflowNodeMapping(BaseModel):
    __tablename__ = "workflow_node_mappings"

    route_id = Column(String(36), ForeignKey("workflow_routes.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(100), nullable=False)
    node_name = Column(String(200))
    n8n_workflow_id = Column(String(200))
    intent_schema = Column(JSON, nullable=True)
    artifact_schema = Column(JSON, nullable=True)
    tenant_id = Column(String(36), nullable=False, index=True)

    # ---- 节点类型 ----
    # "n8n"  : 普通 n8n webhook 节点，必填 n8n_workflow_id + intent/artifact schema
    # "agent": AgentScope 同步端点调用节点，必填 post_action_config + previous_node_id
    node_type = Column(String(20), nullable=False, default="n8n", index=True)

    # ---- agent 节点专用字段 ----
    # post_action_config JSON 形状：
    #   {
    #     "enabled": true,
    #     "api_path": "/v1/price-band/analyze",
    #     "method": "POST",
    #     "timeout_sec": 120,
    #     "request_body_template": {
    #       "userId": "${user_id}",
    #       "sessionId": "${session_id}",
    #       "salesData": "${artifact.processedData.salesData}",
    #       "options": {}
    #     }
    #   }
    post_action_config = Column(JSON, nullable=True)

    # ---- DAG 边 ----
    # agent 节点通过 previous_node_id 指向其上游（n8n 或另一个 agent）。
    # v1 限定单值；改 JSON 数组即可支持 fan-out，不需要动其他代码。
    # ON DELETE SET NULL：删除上游节点不会级联删下游（线性链 v1 下游仍有业务价值）。
    previous_node_id = Column(
        String(36),
        ForeignKey("workflow_node_mappings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    route = relationship("WorkflowRoute", back_populates="node_mappings")
    # 自引用关系：当前节点的上游节点（自身 ↔ previous_node_id）
    previous = relationship(
        "WorkflowNodeMapping",
        remote_side="WorkflowNodeMapping.id",
        backref="next_nodes",
    )