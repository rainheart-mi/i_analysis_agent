import { useEffect, useState } from 'react'
import {
  Table, Button, Modal, Form, Input, InputNumber, Switch, Select,
  message, Popconfirm, Space,
} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { workflowApi } from '@/api/workflow'

const EMPTY_FORM = {
  environment_id: undefined,
  title: '',
  description: '',
  n8n_workflow_id: '',
  is_active: true,
  sort_order: 0,
}

function WorkflowRoutes() {
  const [data, setData] = useState([])
  const [environments, setEnvironments] = useState([])
  const [loading, setLoading] = useState(false)
  const [dialogVisible, setDialogVisible] = useState(false)
  const [dialogTitle, setDialogTitle] = useState('新建工作流')
  const [formData, setFormData] = useState(EMPTY_FORM)
  const [editingId, setEditingId] = useState(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      // ！api/index.js 的 response interceptor 已解包 axios response
      const list = await workflowApi.getWorkflows()
      setData(Array.isArray(list) ? list : (list?.items || []))
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const fetchEnvironments = async () => {
    try {
      const list = await workflowApi.getEnvironments()
      setEnvironments(Array.isArray(list) ? list : [])
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    fetchData()
    fetchEnvironments()
  }, [])

  const handleCreate = () => {
    setFormData(EMPTY_FORM)
    setEditingId(null)
    setDialogTitle('新建工作流')
    setDialogVisible(true)
  }

  const handleEdit = (record) => {
    setFormData({
      environment_id: record.environment_id,
      title: record.title || '',
      description: record.description || '',
      n8n_workflow_id: record.n8n_workflow_id || '',
      is_active: record.is_active !== false,
      sort_order: record.sort_order ?? 0,
    })
    setEditingId(record.id)
    setDialogTitle('编辑工作流')
    setDialogVisible(true)
  }

  const handleDelete = async (record) => {
    try {
      // model workflow.py:18 级联删除 node_mappings
      await workflowApi.deleteWorkflow(record.id)
      message.success('删除成功')
      fetchData()
    } catch (e) {
      message.error('删除失败')
    }
  }

  const handleSave = async () => {
    if (!formData.title.trim()) {
      message.error('请输入名称')
      return
    }
    if (!formData.environment_id) {
      message.error('请选择所属环境')
      return
    }
    try {
      if (editingId) {
        await workflowApi.updateWorkflow(editingId, formData)
        message.success('更新成功')
      } else {
        await workflowApi.createWorkflow(formData)
        message.success('创建成功')
      }
      setDialogVisible(false)
      fetchData()
    } catch (e) {
      message.error('操作失败')
    }
  }

  const columns = [
    { title: '名称', dataIndex: 'title', width: 180 },
    {
      title: '所属环境', dataIndex: 'environment_id', width: 160,
      render: (id) => environments.find(e => e.id === id)?.name || id || '—',
    },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    {
      title: 'N8N Workflow ID', dataIndex: 'n8n_workflow_id', width: 200, ellipsis: true,
      render: v => v || '—',
    },
    { title: '排序', dataIndex: 'sort_order', width: 80, align: 'center' },
    {
      title: '是否激活', dataIndex: 'is_active', width: 100,
      render: v => <Switch checked={!!v} disabled />,
    },
    {
      title: '操作', width: 180, fixed: 'right',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除"
            description="删除工作流将级联删除其下所有节点映射"
            onConfirm={() => handleDelete(record)}
            okText="确认"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新增工作流
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={data}
        loading={loading}
        rowKey="id"
        scroll={{ x: 1100 }}
        style={{ background: '#fff', borderRadius: 12 }}
      />
      <Modal
        title={dialogTitle}
        open={dialogVisible}
        onOk={handleSave}
        onCancel={() => setDialogVisible(false)}
        okText="保存"
        cancelText="取消"
        width={600}
        destroyOnClose
      >
        <Form layout="vertical">
          <Form.Item label="所属环境" required>
            <Select
              value={formData.environment_id}
              onChange={v => setFormData({ ...formData, environment_id: v })}
              placeholder="选择 N8N 环境"
              options={environments.map(e => ({ value: e.id, label: e.name }))}
            />
          </Form.Item>
          <Form.Item label="名称" required>
            <Input
              value={formData.title}
              onChange={e => setFormData({ ...formData, title: e.target.value })}
              placeholder="品类运营分析"
              maxLength={200}
            />
          </Form.Item>
          <Form.Item label="描述">
            <Input.TextArea
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              placeholder="分析指定品类的销售数据，生成运营报告"
              autoSize={{ minRows: 2, maxRows: 4 }}
            />
          </Form.Item>
          <Form.Item label="N8N Workflow ID" tooltip="N8N 后台的工作流标识（webhook 路由用）">
            <Input
              value={formData.n8n_workflow_id}
              onChange={e => setFormData({ ...formData, n8n_workflow_id: e.target.value })}
              placeholder="demo-category-analysis"
            />
          </Form.Item>
          <Form.Item label="排序" tooltip="数字越小越靠前">
            <InputNumber
              value={formData.sort_order}
              onChange={v => setFormData({ ...formData, sort_order: v ?? 0 })}
              min={0}
              style={{ width: 120 }}
            />
          </Form.Item>
          <Form.Item label="是否激活">
            <Switch
              checked={formData.is_active}
              onChange={v => setFormData({ ...formData, is_active: v })}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default WorkflowRoutes
