from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class N8NEnvironmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    base_url: str = Field(..., max_length=500)
    api_key: Optional[str] = None
    is_active: bool = True
    # 入站字段：username 明文，password 明文（落库前由 endpoint 加密为 password_enc）
    username: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, max_length=500)


class N8NEnvironmentCreate(N8NEnvironmentBase):
    pass


class N8NEnvironmentUpdate(BaseModel):
    """配合 `exclude_unset=True` 区分"未传=不改"和"传 None=置空"：
    - 字段缺失 → 不动 DB
    - 字段为 null → 把 DB 字段置 NULL（清除凭据）
    """
    name: Optional[str] = Field(None, max_length=100)
    base_url: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = None
    is_active: Optional[bool] = None
    username: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, max_length=500)


class N8NEnvironmentResponse(BaseModel):
    """响应模型：username 明文回显（前端要展示），password 永不返回（防泄漏）。"""
    id: str
    name: str
    base_url: str
    api_key: Optional[str] = None
    is_active: bool
    username: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class N8NEnvironmentTestResponse(BaseModel):
    success: bool
    message: str