-- =============================================================
-- 为 n8n_environments 表加 Basic Auth 凭据列
-- =============================================================
-- 用途：N8N webhook 触发节点的"Generic Auth > Basic Auth"凭据
--      即 Authorization: Basic base64(username:password)
--
-- 两条都 nullable：保留"只 api_key 不要 basic auth"的场景
-- 用 IF NOT EXISTS 幂等，可重复执行
--
-- 执行方式（手动 psql，不要用 ORM 跑）：
--   psql "$DATABASE_URL" -f scripts/migrate_add_n8n_basic_auth.sql
--
-- 验证（执行后可选）：
--   psql "$DATABASE_URL" -c "\d n8n_environments" \
--     | grep -E "username|password_enc"
--   应输出两行：
--     username      | character varying(255)
--     password_enc  | character varying(500)
-- =============================================================

ALTER TABLE n8n_environments
    ADD COLUMN IF NOT EXISTS username     VARCHAR(255),
    ADD COLUMN IF NOT EXISTS password_enc VARCHAR(500);
