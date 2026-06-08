"""
在线迁移脚本：为现有业务表添加 tenant_id 字段
（不 drop 数据，安全升级）

⚠️ 与 init_db.py 的区别：
  - init_db.py: drop 全部表重建（破坏性，仅开发/测试）
  - 本脚本: ALTER TABLE ADD COLUMN（保留数据，生产可用）

使用方法:
    python scripts/migrate_add_tenant_id.py

迁移完成后，需要：
    1. 重启 uvicorn 和 Celery worker
    2. 验证：所有现有业务记录的 tenant_id 均为 'default'
"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine


DEFAULT_TENANT_ID = "default"
DEFAULT_TENANT_NAME = "默认租户"
DEFAULT_TENANT_CODE = "default"


# 业务表 → tenant_id 列定义
TABLES_TO_ALTER = [
    "users",
    "n8n_environments",
    "workflow_routes",
    "workflow_node_mappings",
    "task_instances",
    "node_executions",
]


async def main():
    print("=" * 50)
    print("在线迁移：添加 tenant_id 字段（保留数据）")
    print("=" * 50)

    async with engine.begin() as conn:
        # 1. 创建 tenants 表（如果不存在）
        print("\n[1/4] 创建 tenants 表...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tenants (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(50) UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
            )
        """))
        print("  ✓ tenants 表就绪")

        # 2. 插入默认租户（如果不存在）
        print("\n[2/4] 创建默认租户...")
        await conn.execute(text("""
            INSERT INTO tenants (id, name, code, is_active)
            VALUES (:tid, :tname, :tcode, true)
            ON CONFLICT (id) DO NOTHING
        """), {
            "tid": DEFAULT_TENANT_ID,
            "tname": DEFAULT_TENANT_NAME,
            "tcode": DEFAULT_TENANT_CODE,
        })
        print(f"  ✓ 默认租户 {DEFAULT_TENANT_ID} 就绪")

        # 3. 给每张业务表添加 tenant_id 列
        print("\n[3/4] 添加 tenant_id 字段到业务表...")
        for table in TABLES_TO_ALTER:
            # 检查列是否已存在
            check = await conn.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :t AND column_name = 'tenant_id'
            """), {"t": table})
            if check.scalar():
                print(f"  - {table}: tenant_id 已存在，跳过")
                continue

            # users 表加 FK；其他表加普通列
            if table == "users":
                await conn.execute(text(f"""
                    ALTER TABLE {table}
                    ADD COLUMN tenant_id VARCHAR(36) NOT NULL
                    DEFAULT '{DEFAULT_TENANT_ID}'
                """))
                await conn.execute(text(f"""
                    ALTER TABLE {table}
                    ADD CONSTRAINT fk_{table}_tenant
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
                """))
            else:
                await conn.execute(text(f"""
                    ALTER TABLE {table}
                    ADD COLUMN tenant_id VARCHAR(36) NOT NULL
                    DEFAULT '{DEFAULT_TENANT_ID}'
                """))

            # 添加索引
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS ix_{table}_tenant_id
                ON {table} (tenant_id)
            """))
            print(f"  ✓ {table}: tenant_id 已添加")

        # 4. 把 users 表已有 admin 用户关联到 default 租户
        print("\n[4/4] 验证数据...")
        r = await conn.execute(text("SELECT COUNT(*) FROM users WHERE tenant_id = :tid"),
                              {"tid": DEFAULT_TENANT_ID})
        user_count = r.scalar()
        print(f"  ✓ users 表中 {user_count} 个用户已归属 default 租户")

        for table in TABLES_TO_ALTER:
            r = await conn.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id = :tid"),
                {"tid": DEFAULT_TENANT_ID}
            )
            count = r.scalar()
            print(f"  ✓ {table}: {count} 条记录归属 default 租户")

    print("\n" + "=" * 50)
    print("迁移完成!")
    print("=" * 50)
    print("\n下一步:")
    print("1. 重启 uvicorn: pkill -f 'uvicorn.*8090' && nohup uvicorn app.main:app --host 0.0.0.0 --port 8090 &")
    print("2. 重启 Celery worker")
    print("3. 登录测试: 现有 admin/admin123 仍可用（归属 default 租户）")
    print(f"4. JWT token 中将自动包含 tenant_id='{DEFAULT_TENANT_ID}'")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
