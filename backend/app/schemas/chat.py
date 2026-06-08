"""AI 聊天面板请求/响应模型（OpenAI 兼容子集）。"""
from pydantic import BaseModel, Field
from typing import Literal


class ChatMessage(BaseModel):
    """OpenAI 风格单条消息。"""
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatStreamRequest(BaseModel):
    """前端 ChatPanel 调用的请求体。"""
    node_execution_id: str = Field(..., description="工作流节点执行 ID，作为 AgentScope sessionId")
    messages: list[ChatMessage] = Field(..., min_length=1, description="聊天历史，含最新 user 消息")
    stream: bool = Field(default=True, description="是否走 SSE 流式")


class ChatHealthResponse(BaseModel):
    """检查 AgentScope Java 后端是否可达。"""
    ok: bool
    agentscope_url: str
    detail: str | None = None
