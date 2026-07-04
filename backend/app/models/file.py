"""
文件相关数据模型：UploadedFile / FileAttachment

- UploadedFile：所有已上传文件的元数据（一次上传一行；多租户隔离）
- FileAttachment：文件 ↔ 工作流实例的关联（一次执行涉及多个文件，N:N）
"""
from sqlalchemy import Column, String, BigInteger, ForeignKey, Index, text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class UploadedFile(BaseModel):
    """已上传文件元数据

    设计要点：
    - id (PK) 来自 BaseModel 的 UUID；file_uuid 是面向外部的公网 ID（与 id 区分便于将来轮换）
    - storage_backend 冗余 'local' | 'oss2'，避免 JOIN / 字符串解析判断后端
    - object_key 是存储内唯一 key；local 下为相对路径，oss2 下为 bucket 相对路径（不含 prefix）
    - public_url 冗余存储，避免每次访问都拼装
    - oss_bucket / oss_object_key 仅 oss2 模式下填充
    """
    __tablename__ = "uploaded_files"

    file_uuid = Column(String(36), unique=True, nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)

    original_filename = Column(String(500), nullable=False)
    content_type = Column(String(200), nullable=True)
    size_bytes = Column(BigInteger, nullable=False)

    storage_backend = Column(String(20), nullable=False)   # 'local' | 'oss2'
    object_key = Column(String(500), nullable=False)
    local_path = Column(String(500), nullable=True)
    public_url = Column(String(1000), nullable=False)
    oss_bucket = Column(String(200), nullable=True)
    oss_object_key = Column(String(500), nullable=True)


class FileAttachment(BaseModel):
    """文件 ↔ 工作流实例 / 节点执行的关联

    - 一个 file 可被多个 execution 引用（共享）
    - 一个 execution 可引用多个 file（一个表单里多个 input-file 字段）
    - field_name 记录文件来自 intent_data 的哪个字段，便于溯源
    """
    __tablename__ = "file_attachments"

    file_id = Column(
        String(36),
        ForeignKey("uploaded_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_instance_id = Column(
        String(36),
        ForeignKey("task_instances.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    node_execution_id = Column(
        String(36),
        ForeignKey("node_executions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    tenant_id = Column(String(36), nullable=False, index=True)
    field_name = Column(String(200), nullable=True)  # 来自 intent_data 的字段名

    # 同一文件在同一 node_execution 下不应该重复关联
    __table_args__ = (
        Index(
            "ix_file_attachments_unique",
            "file_id", "node_execution_id",
            unique=True,
            postgresql_where=text("node_execution_id IS NOT NULL"),
        ),
    )
