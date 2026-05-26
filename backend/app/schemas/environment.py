from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class N8NEnvironmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    base_url: str = Field(..., max_length=500)
    api_key: Optional[str] = None
    is_active: bool = True


class N8NEnvironmentCreate(N8NEnvironmentBase):
    pass


class N8NEnvironmentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    base_url: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = None
    is_active: Optional[bool] = None


class N8NEnvironmentResponse(N8NEnvironmentBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class N8NEnvironmentTestResponse(BaseModel):
    success: bool
    message: str