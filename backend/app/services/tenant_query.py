"""多租户数据隔离工具

所有业务端点必须通过本模块的辅助函数执行数据库操作，
确保 tenant_id 过滤被强制应用。
"""
from sqlalchemy import select
from typing import Type, TypeVar
from app.models.base import BaseModel

T = TypeVar("T", bound=BaseModel)


def scoped_query(db, model: Type[T], tenant_id: str):
    """返回一个强制带 tenant_id 过滤的 select 查询。

    Usage:
        result = await db.execute(
            scoped_query(db, WorkflowRoute, tid)
            .options(selectinload(WorkflowRoute.node_mappings))
            .order_by(...)
        )
    """
    return select(model).where(model.tenant_id == tenant_id)


def scoped_query_by_id(db, model: Type[T], obj_id: str, tenant_id: str):
    """返回带 (id, tenant_id) 双重过滤的 select 查询，找不到统一 404（防 ID 枚举）。"""
    return select(model).where(model.id == obj_id, model.tenant_id == tenant_id)


def apply_tenant(obj: T, tenant_id: str) -> T:
    """为新建对象注入 tenant_id。链式调用：
        db_obj = apply_tenant(WorkflowRoute(**data), tid)
    """
    obj.tenant_id = tenant_id
    return obj
