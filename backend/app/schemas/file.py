"""
文件相关 Pydantic schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class UploadedFileResponse(BaseModel):
    """文件元数据（对外暴露）"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_uuid: str
    tenant_id: str
    user_id: str
    original_filename: str
    content_type: Optional[str] = None
    size_bytes: int
    storage_backend: str
    object_key: str
    public_url: str
    oss_bucket: Optional[str] = None
    oss_object_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AmisUploadData(BaseModel):
    """amis input-file 响应 data 字段

    amis 要求响应形如 { "status": 0, "msg": "ok", "data": { "value": "...", ... } }
    value 是写入表单字段的字符串（公网 URL）
    """
    value: str = Field(..., description="写入表单字段的字符串（公网 URL）")
    file_id: str = Field(..., description="上传文件的 file_uuid")
    name: str = Field(..., description="原始文件名")
    size: int = Field(..., description="字节数")
    url: str = Field(..., description="同 value，保留字段兼容")


class AmisUploadResponse(BaseModel):
    """amis input-file receiver 完整响应"""
    status: int = 0
    msg: str = "ok"
    data: AmisUploadData


class FileAttachmentResponse(BaseModel):
    """文件关联响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_id: str
    task_instance_id: Optional[str] = None
    node_execution_id: Optional[str] = None
    tenant_id: str
    field_name: Optional[str] = None
    created_at: datetime
