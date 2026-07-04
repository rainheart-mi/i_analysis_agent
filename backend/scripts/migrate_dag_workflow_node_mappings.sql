-- =============================================================
-- 迁移：workflow_node_mappings 改造成真 DAG 模型
-- =============================================================
-- 背景：
--   旧版用"1 条 n8n mapping + 后端自动派生的 child mapping (node_type='post_action')"
--   表达"n8n 节点之后调 AgentScope"。
--   新版把 child 视为一等节点（DAG 边 previous_node_id），配置自包含。
--
-- 变更点：
--   1) 列重命名  parent_mapping_id → previous_node_id
--   2) FK 行为  ON DELETE CASCADE → ON DELETE SET NULL
--   3) 索引重命名 ix_workflow_node_mappings_parent_mapping_id → ..._previous_node_id
--   4) node_type='post_action' → 'agent'（语义统一）
--   5) 父 n8n mapping 的 post_action_config 复制到 child agent mapping；
--      然后清空父的 config（DAG 模型下 agent 节点自包含，避免双写漂移）
--
-- 幂等：可重复执行。已经升级过（即 previous_node_id 已存在）的库再跑是 no-op。
--
-- ⚠️ 旧版 child mapping 的 previous_node_id 在新版下指向其上游 n8n 节点；
--   上游节点在 (5) 中将清空 post_action_config；agent 节点在 (5) 中填入相同 config。
--   结果：父子两边语义自洽，前端 UI 不需任何手工迁移。
--
-- 使用：psql -f migrate_dag_workflow_node_mappings.sql
-- 完成后需重启 uvicorn + Celery worker 让 ORM 看到新 schema。
-- =============================================================

BEGIN;

-- ---- 1) 列重命名（仅在还是旧列名时） ----
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'workflow_node_mappings' AND column_name = 'parent_mapping_id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'workflow_node_mappings' AND column_name = 'previous_node_id'
    ) THEN
        ALTER TABLE workflow_node_mappings
            RENAME COLUMN parent_mapping_id TO previous_node_id;
        RAISE NOTICE 'renamed column parent_mapping_id -> previous_node_id';
    ELSE
        RAISE NOTICE 'column previous_node_id already present, skip rename';
    END IF;
END $$;


-- ---- 2) FK 重建：CASCADE → SET NULL ----
-- 旧版约束名（无论默认/手工命名都尝试 DROP）：
DO $$
DECLARE
    v_conname text;
BEGIN
    -- 找到指向 workflow_node_mappings.id 的外键约束
    SELECT conname INTO v_conname
    FROM pg_constraint
    WHERE conrelid = 'workflow_node_mappings'::regclass
      AND contype = 'f'
      AND pg_get_constraintdef(oid) LIKE '%previous_node_id%'
    LIMIT 1;

    IF v_conname IS NOT NULL THEN
        -- 已经叫 previous_node_id_fkey 但 ON DELETE 行为可能不是 SET NULL
        -- 直接 DROP 后重建（幂等）
        EXECUTE format('ALTER TABLE workflow_node_mappings DROP CONSTRAINT %I', v_conname);
        RAISE NOTICE 'dropped FK constraint %', v_conname;
    END IF;
END $$;

-- 兜底：旧版可能叫 parent_mapping_id_fkey
ALTER TABLE workflow_node_mappings
    DROP CONSTRAINT IF EXISTS workflow_node_mappings_parent_mapping_id_fkey;

-- 重建 FK（SET NULL）
ALTER TABLE workflow_node_mappings
    ADD CONSTRAINT workflow_node_mappings_previous_node_id_fkey
        FOREIGN KEY (previous_node_id) REFERENCES workflow_node_mappings(id) ON DELETE SET NULL;


-- ---- 3) 索引重命名 ----
ALTER INDEX IF EXISTS ix_workflow_node_mappings_parent_mapping_id
    RENAME TO ix_workflow_node_mappings_previous_node_id;


-- ---- 4) node_type 语义统一 ----
UPDATE workflow_node_mappings
SET node_type = 'agent'
WHERE node_type = 'post_action';


-- ---- 5) post_action_config 从父复制到 child，再清空父 ----
-- 5a) 把父 n8n mapping 上的 post_action_config 复制到其 child agent mapping
--     （仅在 child 自己还没有 config 时覆盖，避免误覆盖手工改过的）
UPDATE workflow_node_mappings child
SET post_action_config = parent.post_action_config
FROM workflow_node_mappings parent
WHERE child.previous_node_id = parent.id
  AND child.node_type = 'agent'
  AND child.post_action_config IS NULL
  AND parent.post_action_config IS NOT NULL;

-- 5b) 清空父 n8n mapping 的 post_action_config（DAG 模型下 agent 节点自包含）
--     仅清空"自己有 child agent"的那部分父；无下游 agent 的父保留 config
--     （这通常意味着历史数据污染，留给人工核对）
UPDATE workflow_node_mappings parent
SET post_action_config = NULL
WHERE parent.node_type = 'n8n'
  AND parent.post_action_config IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM workflow_node_mappings child
      WHERE child.previous_node_id = parent.id
        AND child.node_type = 'agent'
  );


-- ---- 6) 兜底审计：列出本应配 post_action_config 但子还没拿到的 agent 节点 ----
--     （如果上一轮 (5a) 因 child.config 非 NULL 跳过覆盖；说明父子各持一份，
--      需要人工 review。）
DO $$
DECLARE
    v_count int;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM workflow_node_mappings child
    JOIN workflow_node_mappings parent ON child.previous_node_id = parent.id
    WHERE child.node_type = 'agent'
      AND (child.post_action_config IS NULL OR child.post_action_config = '{}'::jsonb)
      AND (parent.post_action_config IS NOT NULL);
    IF v_count > 0 THEN
        RAISE NOTICE '⚠️  % agent 节点没有 post_action_config 但其父 n8n 仍有 config；'
                     '请人工 review 是否要合并配置（脚本为幂等不覆盖）', v_count;
    END IF;
END $$;


COMMIT;


-- =============================================================
-- 验证（升级后跑一遍）：
--   1) 列名应是 previous_node_id
--       \d workflow_node_mappings
--   2) FK 行为应是 SET NULL
--       SELECT conname, pg_get_constraintdef(oid)
--       FROM pg_constraint
--       WHERE conrelid = 'workflow_node_mappings'::regclass AND contype = 'f';
--   3) node_type 应只出现 'n8n' / 'agent' 两值
--       SELECT node_type, COUNT(*) FROM workflow_node_mappings GROUP BY node_type;
--   4) 不应再有"父有 config 且子无 config"的情况（除上面 (6) 警告的人工 review 项）
-- =============================================================