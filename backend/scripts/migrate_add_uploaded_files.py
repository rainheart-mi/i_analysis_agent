"""
在线迁移脚本：创建 uploaded_files / file_attachments 表 + 关联索引。

⚠️ 与 init_db.py 的区别：
  - init_db.py: drop 全部表重建（破坏性，仅开发/测试）
  - 本脚本: CREATE TABLE IF NOT EXISTS（保留数据，生产可用）

使用方法:
    python scripts/migrate_add_uploaded_files.py

完成后需重启 uvicorn 让 ORM 看到新表。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine


async def main():
    print("=" * 50)
    print("在线迁移：创建 uploaded_files / file_attachments 表")
    print("=" * 50)

    async with engine.begin() as conn:
        # 1. uploaded_files
        print("\n[1/4] 创建 uploaded_files 表...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id VARCHAR(36) PRIMARY KEY,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
                file_uuid VARCHAR(36) UNIQUE NOT NULL,
                tenant_id VARCHAR(36) NOT NULL,
                user_id VARCHAR(36) NOT NULL,
                original_filename VARCHAR(500) NOT NULL,
                content_type VARCHAR(200),
                size_bytes BIGINT NOT NULL,
                storage_backend VARCHAR(20) NOT NULL,
                object_key VARCHAR(500) NOT NULL,
                local_path VARCHAR(500),
                public_url VARCHAR(1000) NOT NULL,
                oss_bucket VARCHAR(200),
                oss_object_key VARCHAR(500)
            )
        """))
        print("  [OK] uploaded_files 表就绪")

        # 2. uploaded_files 索引
        print("\n[2/4] 创建 uploaded_files 索引...")
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS ix_uploaded_files_file_uuid ON uploaded_files (file_uuid)",
            "CREATE INDEX IF NOT EXISTS ix_uploaded_files_tenant_id ON uploaded_files (tenant_id)",
            "CREATE INDEX IF NOT EXISTS ix_uploaded_files_user_id ON uploaded_files (user_id)",
        ]:
            await conn.execute(text(idx_sql))
        print("  [OK] uploaded_files 索引就绪")

        # 3. file_attachments
        print("\n[3/4] 创建 file_attachments 表...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS file_attachments (
                id VARCHAR(36) PRIMARY KEY,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
                file_id VARCHAR(36) NOT NULL REFERENCES uploaded_files(id) ON DELETE CASCADE,
                task_instance_id VARCHAR(36) REFERENCES task_instances(id) ON DELETE CASCADE,
                node_execution_id VARCHAR(36) REFERENCES node_executions(id) ON DELETE CASCADE,
                tenant_id VARCHAR(36) NOT NULL,
                field_name VARCHAR(200)
            )
        """))
        print("  [OK] file_attachments 表就绪")

        # 4. file_attachments 索引
        print("\n[4/4] 创建 file_attachments 索引...")
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS ix_file_attachments_file_id ON file_attachments (file_id)",
            "CREATE INDEX IF NOT EXISTS ix_file_attachments_task_instance_id ON file_attachments (task_instance_id)",
            "CREATE INDEX IF NOT EXISTS ix_file_attachments_node_execution_id ON file_attachments (node_execution_id)",
            "CREATE INDEX IF NOT EXISTS ix_file_attachments_tenant_id ON file_attachments (tenant_id)",
            # 唯一索引（同一 file + 同一 node_execution 不重复）
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_file_attachments_unique "
            "ON file_attachments (file_id, node_execution_id) "
            "WHERE node_execution_id IS NOT NULL",
        ]:
            await conn.execute(text(idx_sql))
        print("  [OK] file_attachments 索引就绪")

        # 验证
        print("\n[验证] 表结构...")
        r = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_name IN ('uploaded_files', 'file_attachments')
            ORDER BY table_name
        """))
        for row in r.all():
            print(f"  [OK] {row[0]} 已存在")

    print("\n" + "=" * 50)
    print("迁移完成!")
    print("=" * 50)
    print("\n下一步:")
    print("1. 重启 uvicorn 让 ORM 看到新表")
    print("2. 上传文件: curl -X POST .../api/v1/files/upload -F 'file=@test.xlsx'")
    print("3. 验证元数据: curl .../api/v1/files/<file_uuid>/metadata")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
