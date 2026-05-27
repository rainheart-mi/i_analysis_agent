"""
数据库初始化脚本
用于创建所有表和初始化数据

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
from app.models import User, N8NEnvironment, WorkflowRoute, WorkflowNodeMapping
from app.services.auth_service import get_password_hash


async def create_tables():
    """创建所有表"""
    print("正在创建表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("表创建完成!")


async def create_test_user():
    """创建测试用户"""
    print("正在创建测试用户...")
    async with AsyncSessionLocal() as session:
        # 检查是否已存在
        result = await session.execute(
            text("SELECT id FROM users WHERE username = 'admin'")
        )
        existing = result.scalar_one_or_none()

        if existing:
            print("测试用户已存在，跳过创建")
            return

        # 创建默认管理员用户 (密码: admin123)
        admin_user = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            email="admin@example.com",
            is_active=True
        )
        session.add(admin_user)
        await session.commit()
        print("测试用户创建完成!")
        print("  用户名: admin")
        print("  密码: admin123")


async def create_test_data():
    """创建测试数据"""
    print("正在创建测试数据...")
    async with AsyncSessionLocal() as session:
        # 检查是否已存在测试环境
        result = await session.execute(
            text("SELECT id FROM n8n_environments LIMIT 1")
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
            is_active=True
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
            sort_order=1
        )
        session.add(workflow)
        await session.flush()

        # 创建节点映射
        mapping = WorkflowNodeMapping(
            route_id=workflow.id,
            node_id="category-analysis-node",
            node_name="品类分析节点",
            intent_schema_path="schemas/intent_forms/demo/intent_schema.json",
            artifact_schema_path="schemas/artifact_forms/demo/artifact_schema.json",
            input_mapping={"date_range": "date_range", "category": "category"},
            output_mapping={"report": "report", "chart": "chart"}
        )
        session.add(mapping)

        # 创建陈列复盘报告工作流
        display_review_workflow = WorkflowRoute(
            environment_id=env.id,
            title="陈列复盘报告",
            description="对比业务周期与复盘周期的陈列效果，生成复盘报告",
            n8n_workflow_id="display-review-workflow",
            is_active=True,
            sort_order=2
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
            input_mapping={"business_period": "business_period", "review_period": "review_period"},
            output_mapping=None
        )
        session.add(display_review_mapping)

        await session.commit()
        print("测试数据创建完成!")


async def main():
    print("=" * 50)
    print("IERP AI Assistant 数据库初始化")
    print("=" * 50)

    try:
        await create_tables()
        await create_test_user()
        await create_test_data()

        print("=" * 50)
        print("数据库初始化完成!")
        print("=" * 50)
        print("\n快速开始:")
        print("1. 启动后端: uvicorn app.main:app --reload")
        print("2. 登录后台: http://localhost:8000/docs")
        print("   用户名: admin")
        print("   密码: admin123")

    except Exception as e:
        print(f"初始化失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())