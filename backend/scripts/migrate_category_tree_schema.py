"""
在线迁移脚本：用新版的 category tree input schema 替换数据库里 WorkflowRoute 入口节点
映射的 intent_schema 字段。

适用场景：
  - 旧 schema 引用 /api/v1/categories/digit-config（已删除），浏览器控制台报 404
  - 新 schema 是单字段 input-tree，提交后让后端/n8n 按位数拆分
  - 新 schema 加了性能参数（initiallyOpen: false, unfoldedLevel: 2）

用法：
    # 默认更新所有 workflow 的入口节点映射
    python scripts/migrate_category_tree_schema.py

    # 只更新某个 workflow
    python scripts/migrate_category_tree_schema.py --workflow-id <uuid>

    # 只更新某租户的 workflow
    python scripts/migrate_category_tree_schema.py --tenant-id <tenant_uuid>

⚠️ 写库前会打印预览 + 询问 y/n 确认。
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.mapping import WorkflowNodeMapping


# 新 schema（与 backend/schemas/intent_forms/demo/category_tree_input_schema.json 保持一致）
# 关键：后端 /tree 必须返回 {status,msg,data:{options:[...]}} 格式，否则 AMIS 找不到 options
# 使用 deferApi 懒加载：一级节点由 /tree 返回，子节点通过 /defer 按需拉取
NEW_INTENT_SCHEMA = {
    "type": "page",
    "title": "查询参数输入",
    "body": [
        {
            "type": "form",
            "mode": "horizontal",
            "wrapWithPanel": False,
            "body": [
                {
                    "type": "input-text",
                    "name": "period",
                    "label": "月份",
                    "placeholder": "多个月份用英文逗号分隔，例：202604,202605",
                    "description": "支持多值英文逗号分隔格式",
                },
                {
                    "type": "input-tree",
                    "name": "category",
                    "label": "分类编码",
                    "source": "/api/v1/categories/tree",
                    "multiple": True,
                    "searchable": True,
                    "deferApi": "/api/v1/categories/defer",
                    "unfoldedLevel": 2,
                },
            ],
            "actions": [
                {"type": "submit", "label": "执行查询"}
            ],
        }
    ],
}


async def main(workflow_id: str | None, tenant_id: str | None):
    print("=" * 60)
    print("Migration: 替换 WorkflowRoute 入口节点映射的 intent_schema")
    print("=" * 60)
    print(f"\n新 schema 预览（前 200 字符）:")
    print(json.dumps(NEW_INTENT_SCHEMA, ensure_ascii=False)[:200] + "...")

    async with AsyncSessionLocal() as session:
        # 入口节点：previous_node_id IS NULL 的映射
        stmt = select(WorkflowNodeMapping).where(
            WorkflowNodeMapping.previous_node_id.is_(None)
        )
        if workflow_id:
            stmt = stmt.where(WorkflowNodeMapping.route_id == workflow_id)
        if tenant_id:
            stmt = stmt.where(WorkflowNodeMapping.tenant_id == tenant_id)

        result = await session.execute(stmt)
        entries = result.scalars().all()

        if not entries:
            print("\n⚠️  没有匹配条件的工作流，跳过")
            return

        print(f"\n将更新 {len(entries)} 个入口节点映射:")
        for e in entries:
            print(f"  - route_id={e.route_id} node_id={e.node_id} node_name={e.node_name!r}")

        confirm = input("\n确认执行？(y/N): ").strip().lower()
        if confirm != "y":
            print("已取消")
            return

        # 备份旧 schema 到 logs 目录
        backup_dir = Path(__file__).parent.parent / "logs"
        backup_dir.mkdir(exist_ok=True)
        backup_file = backup_dir / "intent_schema_backup.jsonl"
        with open(backup_file, "a", encoding="utf-8") as f:
            for e in entries:
                f.write(json.dumps({
                    "route_id": e.route_id,
                    "node_id": e.node_id,
                    "old_schema": e.intent_schema,
                }, ensure_ascii=False) + "\n")
        print(f"  旧 schema 已备份到: {backup_file}")

        # 写入新 schema
        for e in entries:
            e.intent_schema = NEW_INTENT_SCHEMA

        await session.commit()
        print(f"\n✅ 完成：已更新 {len(entries)} 个入口节点映射")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="更新 WorkflowRoute intent_schema")
    parser.add_argument("--workflow-id", help="只更新指定 workflow_id")
    parser.add_argument("--tenant-id", help="只更新指定租户下的 workflow")
    args = parser.parse_args()

    asyncio.run(main(args.workflow_id, args.tenant_id))