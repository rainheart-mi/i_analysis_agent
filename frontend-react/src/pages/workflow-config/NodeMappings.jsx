import { useState, useEffect } from 'react'
import { Table, Button, Select, Modal, Form, Input, message } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { workflowApi } from '@/api/workflow'

function NodeMappings() {
  const [workflows, setWorkflows] = useState([])
  const [mappings, setMappings] = useState([])
  const [selectedRouteId, setSelectedRouteId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [dialogVisible, setDialogVisible] = useState(false)
  const [dialogTitle, setDialogTitle] = useState('新建映射')
  const [formData, setFormData] = useState({
    node_id: '',
    node_name: '',
    intent_schema_path: '',
    artifact_schema_path: ''
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

  const handleCreate = () => {
    setFormData({
      node_id: '',
      node_name: '',
      intent_schema_path: '',
      artifact_schema_path: ''
    })
    setEditingId(null)
    setDialogTitle('新建映射')
    setDialogVisible(true)
  }

  const handleEdit = (record) => {
    setFormData({ ...record })
    setEditingId(record.id)
    setDialogTitle('编辑映射')
    setDialogVisible(true)
  }

  const handleDelete = (record) => {
    Modal.confirm({
      title: '确认删除',
      content: '确认删除该映射吗？',
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
    try {
      if (editingId) {
        await workflowApi.updateMapping(editingId, formData)
        message.success('更新成功')
      } else {
        await workflowApi.createMapping(selectedRouteId, formData)
        message.success('创建成功')
      }
      setDialogVisible(false)
      fetchMappings()
    } catch (e) {
      message.error('操作失败')
    }
  }

  const columns = [
    { title: '节点ID', dataIndex: 'node_id', key: 'node_id' },
    { title: '节点名称', dataIndex: 'node_name', key: 'node_name' },
    { title: '意图表单路径', dataIndex: 'intent_schema_path', key: 'intent_schema_path', ellipsis: true },
    { title: '生成物表单路径', dataIndex: 'artifact_schema_path', key: 'artifact_schema_path', ellipsis: true },
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
        width={600}
      >
        <Form layout="vertical" form={form}>
          <Form.Item label="节点ID">
            <Input
              value={formData.node_id}
              onChange={(e) => setFormData({ ...formData, node_id: e.target.value })}
              placeholder="node_001"
            />
          </Form.Item>
          <Form.Item label="节点名称">
            <Input
              value={formData.node_name}
              onChange={(e) => setFormData({ ...formData, node_name: e.target.value })}
              placeholder="意图澄清节点"
            />
          </Form.Item>
          <Form.Item label="意图表单Schema路径">
            <Input
              value={formData.intent_schema_path}
              onChange={(e) => setFormData({ ...formData, intent_schema_path: e.target.value })}
              placeholder="intent_forms/{route_id}/intent_schema.json"
            />
          </Form.Item>
          <Form.Item label="生成物表单Schema路径">
            <Input
              value={formData.artifact_schema_path}
              onChange={(e) => setFormData({ ...formData, artifact_schema_path: e.target.value })}
              placeholder="artifact_forms/{route_id}/artifact_schema.json"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default NodeMappings