import { useState, useEffect, useMemo } from 'react'
import { Table, Button, Select, Modal, Form, Input, Tag, message } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { workflowApi } from '@/api/workflow'

// agent 节点（post-action）post_action_config 的默认模板（price-band）
const PRICE_BAND_TEMPLATE = JSON.stringify(
  {
    enabled: true,
    api_path: '/v1/price-band/analyze',
    method: 'POST',
    timeout_sec: 120,
    request_body_template: {
      userId: '${user_id}',
      sessionId: '${session_id}',
      salesData: '${artifact.processedData.salesData}',
      options: {},
    },
  },
  null,
  2
)

// agent 节点 artifact_schema（AMIS JSON）的默认模板 - 5 卡片布局
// 留空时 agent 节点结果展示走内置硬编码白名单（向后兼容）
const PRICE_BAND_OUTPUT_SCHEMA = JSON.stringify(
  {
    type: 'page',
    body: [
      {
        type: 'card',
        header: { title: '执行状态' },
        body: { type: 'static', name: 'status', label: '状态码' },
      },
      {
        type: 'card',
        header: { title: '模型 & 输入' },
        body: [
          { type: 'static', name: 'model', label: '模型' },
          { type: 'static', name: 'rowCount', label: '行数' },
          { type: 'static', name: 'sha256', label: 'SHA-256' },
          { type: 'static', name: 'userId', label: '用户' },
        ],
      },
      {
        type: 'card',
        header: { title: '产物路径' },
        body: [
          { type: 'static', name: 'dataPath', label: '数据路径' },
          { type: 'static', name: 'reportPath', label: '报告路径' },
          { type: 'static', name: 'intermediateDir', label: '中间产物' },
        ],
      },
      {
        type: 'card',
        header: { title: '价格带矩阵' },
        body: { type: 'json', name: 'matrix' },
      },
      {
        type: 'card',
        header: { title: '分析报告' },
        body: { type: 'markdown', name: 'finalMessage' },
      },
    ],
  },
  null,
  2
)

function NodeMappings() {
  const [workflows, setWorkflows] = useState([])
  const [mappings, setMappings] = useState([])
  const [selectedRouteId, setSelectedRouteId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [dialogVisible, setDialogVisible] = useState(false)
  const [dialogTitle, setDialogTitle] = useState('新建映射')
  // 表单节点类型：决定哪些字段显示。默认 n8n。
  const [nodeType, setNodeType] = useState('n8n')
  const [formData, setFormData] = useState({
    node_id: '',
    node_name: '',
    n8n_workflow_id: '',
    intent_schema: '',
    artifact_schema: '',
    previous_node_id: undefined,
    post_action_config: '',
  })
  const [editingId, setEditingId] = useState(null)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchWorkflows()
  }, [])

  const fetchWorkflows = async () => {
    try {
      const data = await workflowApi.getWorkflows()
      const list = Array.isArray(data) ? data : (data?.items || [])
      setWorkflows(list)
    } catch (e) {
      message.error('获取工作流列表失败')
    }
  }

  const fetchMappings = async () => {
    if (!selectedRouteId) return
    setLoading(true)
    try {
      const data = await workflowApi.getMappings(selectedRouteId)
      setMappings(data?.items || [])
    } catch (e) {
      message.error('获取映射列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (selectedRouteId) {
      fetchMappings()
    } else {
      setMappings([])
    }
  }, [selectedRouteId])

  // 同 route 下、节点类型=n8n 的 mapping 可作为 agent 节点的上游
  const upstreamCandidates = useMemo(() => {
    return mappings.filter(m => m.node_type === 'n8n')
  }, [mappings])

  // 找到 mapping 对应的 node_id 用于显示"上游节点"列
  const mappingById = useMemo(() => {
    const map = {}
    mappings.forEach(m => { map[m.id] = m })
    return map
  }, [mappings])

  const handleCreate = () => {
    setFormData({
      node_id: '',
      node_name: '',
      n8n_workflow_id: '',
      intent_schema: '',
      artifact_schema: '',
      previous_node_id: undefined,
      post_action_config: '',
    })
    setNodeType('n8n')
    setEditingId(null)
    setDialogTitle('新建映射')
    setDialogVisible(true)
  }

  const handleEdit = (record) => {
    setNodeType(record.node_type || 'n8n')
    setFormData({
      node_id: record.node_id || '',
      node_name: record.node_name || '',
      n8n_workflow_id: record.n8n_workflow_id || '',
      intent_schema: record.intent_schema
        ? JSON.stringify(record.intent_schema, null, 2)
        : '',
      artifact_schema: record.artifact_schema
        ? JSON.stringify(record.artifact_schema, null, 2)
        : '',
      previous_node_id: record.previous_node_id || undefined,
      post_action_config: record.post_action_config
        ? JSON.stringify(record.post_action_config, null, 2)
        : '',
    })
    setEditingId(record.id)
    setDialogTitle('编辑映射')
    setDialogVisible(true)
  }

  const handleDelete = (record) => {
    Modal.confirm({
      title: '确认删除',
      content: `确认删除映射 "${record.node_id}" 吗？下游 agent 节点的 previous_node_id 将被自动置空。`,
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          await workflowApi.deleteMapping(record.id)
          message.success('删除成功')
          fetchMappings()
        } catch (e) {
          message.error('删除失败')
        }
      }
    })
  }

  const handleSave = async () => {
    // 先做 JSON 解析校验（仅 n8n 节点的 schema / agent 节点的 config 需要）
    let payload
    try {
      payload = {
        node_id: formData.node_id,
        node_name: formData.node_name,
        node_type: nodeType,
      }
      if (nodeType === 'n8n') {
        payload.n8n_workflow_id = (formData.n8n_workflow_id || '').trim()
        payload.intent_schema = formData.intent_schema.trim()
          ? JSON.parse(formData.intent_schema)
          : null
        payload.artifact_schema = formData.artifact_schema.trim()
          ? JSON.parse(formData.artifact_schema)
          : null
      } else {
        // agent
        payload.previous_node_id = formData.previous_node_id || null
        const pacText = (formData.post_action_config || '').trim()
        payload.post_action_config = pacText ? JSON.parse(pacText) : null
        // artifact_schema：留空 → null → 前端走回退白名单
        const asText = (formData.artifact_schema || '').trim()
        payload.artifact_schema = asText ? JSON.parse(asText) : null
      }
    } catch (e) {
      message.error(`JSON 格式错误: ${e.message}`)
      return
    }

    try {
      if (editingId) {
        await workflowApi.updateMapping(editingId, payload)
        message.success('更新成功')
      } else {
        await workflowApi.createMapping(selectedRouteId, payload)
        message.success('创建成功')
      }
      setDialogVisible(false)
      fetchMappings()
    } catch (e) {
      // 后端 400 含具体原因（cycle / 跨 route / 缺字段）
      const detail = e.response?.data?.detail || e.message || '操作失败'
      message.error(detail)
    }
  }

  const columns = [
    { title: '节点ID', dataIndex: 'node_id', key: 'node_id' },
    { title: '节点名称', dataIndex: 'node_name', key: 'node_name' },
    {
      title: '节点类型',
      dataIndex: 'node_type',
      key: 'node_type',
      width: 110,
      render: (v) => v === 'agent'
        ? <Tag color="purple">agent</Tag>
        : <Tag color="blue">n8n</Tag>
    },
    {
      title: '上游节点',
      dataIndex: 'previous_node_id',
      key: 'previous_node_id',
      width: 160,
      render: (v) => {
        if (!v) return <Tag>—</Tag>
        const prev = mappingById[v]
        if (!prev) return <Tag color="warning">上游缺失</Tag>
        return <Tag color="cyan">{prev.node_id}</Tag>
      }
    },
    {
      title: 'N8N Webhook ID', dataIndex: 'n8n_workflow_id', key: 'n8n_workflow_id', ellipsis: true,
      render: (v) => v ? <Tag color="blue">{v}</Tag> : <Tag color="red">未配置</Tag>
    },
    {
      title: '意图表单 Schema', dataIndex: 'intent_schema', key: 'intent_schema',
      render: (v) => v ? <Tag color="green">已配置</Tag> : <Tag>未配置</Tag>
    },
    {
      title: '生成物表单 Schema', dataIndex: 'artifact_schema', key: 'artifact_schema',
      render: (v) => v ? <Tag color="green">已配置</Tag> : <Tag>未配置</Tag>
    },
    {
      title: 'Post-Action',
      dataIndex: 'post_action_config',
      key: 'post_action_config',
      render: (v) => {
        if (!v) return <Tag>未配置</Tag>
        return <Tag color="purple">{v.api_path || '?'}</Tag>
      }
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            style={{ color: '#5C7CFF' }}
          >
            编辑
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </>
      )
    }
  ]

  return (
    <div style={{ padding: 20 }}>
      {/* Toolbar */}
      <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
        <Select
          placeholder="选择工作流"
          value={selectedRouteId}
          onChange={(val) => setSelectedRouteId(val)}
          style={{ width: 240 }}
          options={workflows.map(w => ({ value: w.id, label: w.title || w.name }))}
        />
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleCreate}
          disabled={!selectedRouteId}
          style={{ background: '#5C7CFF', border: 'none', borderRadius: 8 }}
        >
          新建映射
        </Button>
      </div>

      {/* Table */}
      <Table
        dataSource={mappings}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={false}
        locale={{
          emptyText: '请选择工作流查看映射'
        }}
      />

      {/* Dialog */}
      <Modal
        title={dialogTitle}
        open={dialogVisible}
        onOk={handleSave}
        onCancel={() => setDialogVisible(false)}
        okText="保存"
        cancelText="取消"
        width={760}
      >
        <Form layout="vertical" form={form}>
          {/* 节点类型 Select（顶部） */}
          <Form.Item
            label="节点类型"
            required
            tooltip="n8n：普通 n8n webhook 节点；agent：调用 AgentScope 同步端点（v1 即 post-action）"
          >
            <Select
              value={nodeType}
              onChange={setNodeType}
              options={[
                { value: 'n8n', label: 'n8n — 普通 n8n workflow 节点' },
                { value: 'agent', label: 'agent — AgentScope 同步端点调用节点（post-action）' },
              ]}
            />
          </Form.Item>

          <Form.Item label="节点ID" required>
            <Input
              value={formData.node_id}
              onChange={(e) => setFormData({ ...formData, node_id: e.target.value })}
              placeholder={nodeType === 'agent' ? 'node_priceband_agent' : 'node_priceband'}
            />
          </Form.Item>
          <Form.Item label="节点名称">
            <Input
              value={formData.node_name}
              onChange={(e) => setFormData({ ...formData, node_name: e.target.value })}
              placeholder={nodeType === 'agent' ? '价段分析（AgentScope 调用）' : '价段分析（n8n 节点）'}
            />
          </Form.Item>

          {/* ---- n8n 节点字段 ---- */}
          {nodeType === 'n8n' && (
            <>
              <Form.Item
                label="N8N Webhook ID"
                required
                tooltip="n8n 中实际注册的 webhook path(如 demo-category-analysis);用于 execute_node 时调用 n8n"
                extra={
                  <span style={{ color: 'var(--text-tertiary, #86909C)' }}>
                    来源：数据库（workflow_node_mappings.n8n_workflow_id）
                  </span>
                }
              >
                <Input
                  value={formData.n8n_workflow_id}
                  onChange={(e) => setFormData({ ...formData, n8n_workflow_id: e.target.value })}
                  placeholder="demo-category-analysis"
                />
              </Form.Item>
              <Form.Item
                label="意图表单 Schema (JSON)"
                tooltip="amis form schema 对象；保存时会做 JSON.parse 校验"
                extra={
                  <span style={{ color: 'var(--text-tertiary, #86909C)' }}>
                    来源：数据库（intent_schema 列）
                  </span>
                }
              >
                <Input.TextArea
                  value={formData.intent_schema}
                  onChange={(e) => setFormData({ ...formData, intent_schema: e.target.value })}
                  placeholder='{"type": "form", "body": [...]}'
                  autoSize={{ minRows: 8, maxRows: 30 }}
                  style={{ fontFamily: 'ui-monospace, SFMono-Regular, monospace', fontSize: 12 }}
                />
              </Form.Item>
              <Form.Item
                label="生成物表单 Schema (JSON)"
                tooltip="amis service / form schema 对象；保存时会做 JSON.parse 校验"
                extra={
                  <span style={{ color: 'var(--text-tertiary, #86909C)' }}>
                    来源：数据库（artifact_schema 列）
                  </span>
                }
              >
                <Input.TextArea
                  value={formData.artifact_schema}
                  onChange={(e) => setFormData({ ...formData, artifact_schema: e.target.value })}
                  placeholder='{"type": "service", "body": [...]}'
                  autoSize={{ minRows: 8, maxRows: 30 }}
                  style={{ fontFamily: 'ui-monospace, SFMono-Regular, monospace', fontSize: 12 }}
                />
              </Form.Item>
            </>
          )}

          {/* ---- agent 节点字段 ---- */}
          {nodeType === 'agent' && (
            <>
              <Form.Item
                label="上游节点 (previous_node_id)"
                required
                tooltip="同工作流下的 n8n 节点；agent 节点完成后由 Celery 自动派发"
                extra={
                  <span style={{ color: 'var(--text-tertiary, #86909C)' }}>
                    当前工作流下的 n8n 节点；保存时会做 cycle 检测
                  </span>
                }
              >
                <Select
                  value={formData.previous_node_id}
                  onChange={(val) => setFormData({ ...formData, previous_node_id: val })}
                  placeholder="选择上游 n8n 节点"
                  options={upstreamCandidates.map(m => ({
                    value: m.id,
                    label: `${m.node_id}${m.node_name ? ' (' + m.node_name + ')' : ''}`,
                  }))}
                  showSearch
                  optionFilterProp="label"
                />
              </Form.Item>
              <div style={{
                margin: '8px 0 16px',
                padding: '8px 12px',
                background: '#F0F1FF',
                borderRadius: 6,
                fontSize: 12,
                color: '#5C7CFF',
              }}>
                Agent：本节点在上游 n8n 节点完成后由 Celery 自动派发，调用 AgentScope HTTP 端点，
                请求体注入上游节点 artifact_data，结果落为独立一行 node_execution。
              </div>
              <Form.Item
                label="Artifact Schema (AMIS JSON，可选)"
                extra={
                  <span style={{ color: 'var(--text-tertiary, #86909C)' }}>
                    驱动该节点 artifact_data 的渲染布局（卡片 / 表格 / markdown 等）。留空时 agent 节点结果展示走内置白名单。
                  </span>
                }
              >
                <Input.TextArea
                  value={formData.artifact_schema}
                  onChange={(e) => setFormData({ ...formData, artifact_schema: e.target.value })}
                  placeholder={PRICE_BAND_OUTPUT_SCHEMA}
                  autoSize={{ minRows: 8, maxRows: 30 }}
                  style={{ fontFamily: 'ui-monospace, SFMono-Regular, monospace', fontSize: 12 }}
                />
              </Form.Item>
              <Form.Item
                label="Post-Action 配置 (JSON)"
                required
                tooltip="api_path 必须在后端白名单内（当前：/v1/price-band/analyze）；request_body_template 支持 ${user_id} / ${session_id} / ${artifact.<点路径>} 占位符"
                extra={
                  <span style={{ color: 'var(--text-tertiary, #86909C)' }}>
                    DAG 模型：agent 节点自带配置，不再回查上游
                  </span>
                }
              >
                <Input.TextArea
                  value={formData.post_action_config}
                  onChange={(e) => setFormData({ ...formData, post_action_config: e.target.value })}
                  placeholder={PRICE_BAND_TEMPLATE}
                  autoSize={{ minRows: 10, maxRows: 20 }}
                  style={{ fontFamily: 'ui-monospace, SFMono-Regular, monospace', fontSize: 12 }}
                />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>
    </div>
  )
}

export default NodeMappings