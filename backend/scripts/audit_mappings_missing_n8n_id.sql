-- =============================================================
-- 审计:workflow_node_mappings 表中 n8n_workflow_id 为空的记录
-- =============================================================
-- 背景:前端 NodeMappings 表单原本没有 n8n_workflow_id 输入框,
--      导致存量 mapping 的 n8n_workflow_id 全是 NULL,
--      execute_node 时拼成 /webhook/None 触发 n8n 404。
-- 本脚本只做 SELECT 审计 + 提供 UPDATE 模板,不会自动改数据。
--
-- 使用步骤:
--   1) 先跑 SELECT,看哪些 mapping 需要补值
--   2) 在 n8n 后台查每个 mapping 对应的真实 webhook path
--   3) 用 UPDATE 模板逐条补值(注意替换 <webhook-id-here>)
--   4) 重跑 SELECT,应返回 0 行
-- =============================================================

-- 1. 列出所有 n8n_workflow_id 为空的 mapping
SELECT
    m.id,
    m.route_id,
    r.title              AS workflow_title,
    m.node_id,
    m.node_name,
    m.n8n_workflow_id,
    m.tenant_id,
    m.created_at
FROM workflow_node_mappings m
LEFT JOIN workflow_routes r ON r.id = m.route_id
WHERE m.n8n_workflow_id IS NULL OR m.n8n_workflow_id = ''
ORDER BY m.route_id, m.created_at;

-- =============================================================
-- 2. UPDATE 模板(根据 SELECT 结果逐条复制执行)
-- =============================================================
-- 注意:
--   - 把 <webhook-id-here> 替换为 n8n 中实际注册的 webhook path
--   - 用 node_id + route_id 联合定位,避免误改
--   - 同一 (route_id, node_id) 组合如果有重复,建议加 LIMIT 1

-- 示例:为"价格带分析"工作流的 node_priceband 节点补 webhook
-- UPDATE workflow_node_mappings
-- SET n8n_workflow_id = '<webhook-id-here>'
-- WHERE node_id = 'node_priceband'
--   AND route_id = '74edc97a-20cc-4ff0-ab98-6df55774b2c3';

-- =============================================================
-- 3. 验证:重跑 SELECT,应返回 0 行
-- =============================================================
-- SELECT COUNT(*) FROM workflow_node_mappings
-- WHERE n8n_workflow_id IS NULL OR n8n_workflow_id = '';
-- 预期:0