-- =============================================================
-- node_executions 表 schema 字段全链路切换到 JSON
-- =============================================================
-- 背景：WorkflowNodeMapping 已把 schema 直接以 JSON 形式存到
--      intent_schema / artifact_schema 列；旧 node_executions
--      上的 *_schema_path 字段已无意义，导致 POST /api/v1/tasks 500。
-- 本脚本：
--   1) 新增 intent_schema / artifact_schema JSON 列
--   2) 删除旧的 intent_schema_path / artifact_schema_path 列
-- 用 IF NOT EXISTS / DROP COLUMN IF EXISTS 幂等，可重复执行
--
-- 执行方式（任选其一）：
--   A) psql:    psql "$DATABASE_URL" -f scripts/migrate_node_executions_to_json_schema.sql
--   B) DB 后台: 把脚本内容粘到查询窗口执行
--
-- 验证（执行后可选）：
--   \d node_executions
--   应只剩 intent_schema / artifact_schema 两个 schema 相关列，
--   不应再出现 *_schema_path。
-- =============================================================

-- 1. 新增 JSON 列
ALTER TABLE node_executions
    ADD COLUMN IF NOT EXISTS intent_schema   JSON,
    ADD COLUMN IF NOT EXISTS artifact_schema JSON;

-- 2. 删除旧 path 列
ALTER TABLE node_executions
    DROP COLUMN IF EXISTS intent_schema_path;

ALTER TABLE node_executions
    DROP COLUMN IF EXISTS artifact_schema_path;