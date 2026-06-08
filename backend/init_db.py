"""
数据库初始化脚本
用于创建所有表和初始化数据

⚠️ 危险：此脚本会 drop 全部表并重建，仅适用于开发/测试环境
生产环境应使用 alembic 迁移或编写专用迁移脚本

使用方法:
    python init_db.py
"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 目录到 path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.database import engine, Base, AsyncSessionLocal
from app.models import (
    User, N8NEnvironment, WorkflowRoute, WorkflowNodeMapping, Tenant
)
from app.services.auth_service import get_password_hash


# 默认租户 ID（与部署配置保持一致）
DEFAULT_TENANT_ID = "default"
DEFAULT_TENANT_NAME = "默认租户"
DEFAULT_TENANT_CODE = "default"


async def create_tables():
    """重建所有表（drop + create）"""
    print("正在 drop 旧表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("正在创建新表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("表创建完成!")


async def create_default_tenant(session):
    """创建默认租户（如果不存在）"""
    result = await session.execute(
        text("SELECT id FROM tenants WHERE id = :tid"),
        {"tid": DEFAULT_TENANT_ID}
    )
    if result.scalar_one_or_none():
        print(f"默认租户 {DEFAULT_TENANT_ID} 已存在，跳过")
        return
    tenant = Tenant(
        id=DEFAULT_TENANT_ID,
        name=DEFAULT_TENANT_NAME,
        code=DEFAULT_TENANT_CODE,
        is_active=True,
    )
    session.add(tenant)
    await session.flush()
    print(f"默认租户 {DEFAULT_TENANT_ID} 创建完成!")


async def create_test_user():
    """创建测试用户（绑定到默认租户）"""
    print("正在创建测试用户...")
    async with AsyncSessionLocal() as session:
        await create_default_tenant(session)
        result = await session.execute(
            text("SELECT id FROM users WHERE username = 'admin'")
        )
        existing = result.scalar_one_or_none()

        if existing:
            print("测试用户已存在，跳过创建")
            return

        admin_user = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            email="admin@example.com",
            is_active=True,
            tenant_id=DEFAULT_TENANT_ID,
        )
        session.add(admin_user)
        await session.commit()
        print("测试用户创建完成!")
        print("  用户名: admin")
        print("  密码: admin123")
        print(f"  租户: {DEFAULT_TENANT_ID}")


async def create_test_data():
    """创建测试数据（所有记录绑定到默认租户）"""
    print("正在创建测试数据...")
    async with AsyncSessionLocal() as session:
        # 检查是否已存在测试环境
        result = await session.execute(
            text("SELECT id FROM n8n_environments WHERE tenant_id = :tid LIMIT 1"),
            {"tid": DEFAULT_TENANT_ID}
        )
        existing = result.scalar_one_or_none()

        if existing:
            print("测试数据已存在，跳过创建")
            return

        # 创建测试 N8N 环境
        env = N8NEnvironment(
            name="本地开发环境",
            base_url="http://localhost:5678",
            api_key="",
            is_active=True,
            tenant_id=DEFAULT_TENANT_ID,
        )
        session.add(env)
        await session.flush()

        # 创建示例工作流
        workflow = WorkflowRoute(
            environment_id=env.id,
            title="品类运营分析",
            description="分析指定品类的销售数据，生成运营报告",
            n8n_workflow_id="demo-category-analysis",
            is_active=True,
            sort_order=1,
            tenant_id=DEFAULT_TENANT_ID,
        )
        session.add(workflow)
        await session.flush()

        # 创建节点映射（tenant_id 继承自 workflow）
        mapping = WorkflowNodeMapping(
            route_id=workflow.id,
            node_id="category-analysis-node",
            node_name="品类分析节点",
            intent_schema_path="schemas/intent_forms/demo/intent_schema.json",
            artifact_schema_path="schemas/artifact_forms/demo/artifact_schema.json",
            n8n_workflow_id="demo-category-analysis",
            tenant_id=DEFAULT_TENANT_ID,
        )
        session.add(mapping)

        # 创建陈列复盘报告工作流
        display_review_workflow = WorkflowRoute(
            environment_id=env.id,
            title="陈列复盘报告",
            description="对比业务周期与复盘周期的陈列效果，生成复盘报告",
            n8n_workflow_id="display-review-workflow",
            is_active=True,
            sort_order=2,
            tenant_id=DEFAULT_TENANT_ID,
        )
        session.add(display_review_workflow)
        await session.flush()

        # 创建陈列复盘节点的映射
        display_review_mapping = WorkflowNodeMapping(
            route_id=display_review_workflow.id,
            node_id="display-review-node",
            node_name="陈列复盘节点",
            intent_schema_path="schemas/intent_forms/demo/display_review_intent_schema.json",
            artifact_schema_path="schemas/artifact_forms/demo/display_review_artifact_schema.json",
            n8n_workflow_id="display-review-workflow",
            tenant_id=DEFAULT_TENANT_ID,
        )
        session.add(display_review_mapping)

        await session.commit()
        print("测试数据创建完成!")


async def main():
    print("=" * 50)
    print("IERP AI Assistant 数据库初始化（多租户版）")
    print("=" * 50)
    print("⚠️  警告：将 drop 全部表并重建")

    try:
        await create_tables()
        await create_test_user()
        await create_test_data()

        print("=" * 50)
        print("数据库初始化完成!")
        print("=" * 50)
        print("\n快速开始:")
        print("1. 启动后端: uvicorn app.main:app --reload")
        print("2. 启动 Celery worker: python -m celery -A app.celery_app worker --loglevel=info --pool=solo")
        print("3. 登录后台: http://localhost:8000/docs")
        print("   用户名: admin")
        print("   密码: admin123")
        print(f"   租户: {DEFAULT_TENANT_ID}")

    except Exception as e:
        print(f"初始化失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
