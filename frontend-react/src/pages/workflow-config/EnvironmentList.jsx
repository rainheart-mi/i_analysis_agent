import { useEffect, useState } from 'react'
import { Table, Button, Tag, message, Space, Modal, Form, Input, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, ApiOutlined } from '@ant-design/icons'
import { workflowApi } from '@/api/workflow'

function EnvironmentList() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  // 提交态（防重复点击）
  const [submitting, setSubmitting] = useState(false)
  // Modal & 表单
  const [modalOpen, setModalOpen] = useState(false)
  // 用 formMode 区分新增/编辑（替代 editingRecord 引用，规避 stale closure 风险）
  const [formMode, setFormMode] = useState('create')  // 'create' | 'edit'
  const [editingId, setEditingId] = useState(null)
  const [form] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    try {
      // ！api/index.js 的 response interceptor 已经把 axios response 解包成 response.data
      // 这里是 array，不是 {data: array} —— 用 res.data 会拿到 undefined
      const list = await workflowApi.getEnvironments()
      setData(Array.isArray(list) ? list : [])
    } catch (e) {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  // 打开新增 / 编辑 Modal（只 set state，让 useEffect 负责回填）
  const openCreateModal = () => {
    setFormMode('create')
    setEditingId(null)
    setModalOpen(true)
  }

  const openEditModal = (record) => {
    setFormMode('edit')
    setEditingId(record.id)
    setModalOpen(true)
  }

  // Modal 打开后回填表单（useEffect 保证 form 已挂载）
  // 必须在 [modalOpen, formMode, editingId] 变化时执行 — antd Modal 的 destroyOnClose
  // 会让 Form 每次打开都重新挂载，useEffect 是唯一可靠时机
  useEffect(() => {
    if (!modalOpen) return
    if (formMode === 'edit' && editingId) {
      const record = data.find(r => r.id === editingId)
      if (record) {
        form.setFieldsValue({
          name: record.name,
          base_url: record.base_url,
          api_key: record.api_key || '',
          username: record.username || '',
          password: '',  // 留空：用户输入才覆盖
        })
      }
    } else {
      // 新增：清空，置默认值
      form.resetFields()
      form.setFieldsValue({ api_key: '', password: '' })
    }
  }, [modalOpen, formMode, editingId, data, form])

  // 关闭 Modal
  const closeModal = () => {
    setModalOpen(false)
    setFormMode('create')
    setEditingId(null)
  }

  // 提交新增 / 编辑
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      // 过滤空白 password：
      // - 后端 exclude_unset + 非空 → 覆盖；空字符串/缺失 → 不动
      // - 前端实现：把空白 password 从 payload 里删掉（让后端认为"未传"）
      const payload = { ...values }
      if (!payload.password) delete payload.password
      if (!payload.api_key) payload.api_key = ''

      setSubmitting(true)
      if (formMode === 'edit' && editingId) {
        await workflowApi.updateEnvironment(editingId, payload)
        message.success('已更新')
      } else {
        await workflowApi.createEnvironment(payload)
        message.success('已新增')
      }
      closeModal()
      fetchData()
    } catch (e) {
      if (e?.errorFields) {
        // antd Form 校验失败 — 不弹 toast（字段红框已提示）
        return
      }
      message.error(`${formMode === 'edit' ? '更新' : '新增'}失败: ${e?.message || '未知错误'}`)
    } finally {
      setSubmitting(false)
    }
  }

  // 删除
  const handleDelete = async (record) => {
    try {
      await workflowApi.deleteEnvironment(record.id)
      message.success('已删除')
      fetchData()
    } catch (e) {
      message.error(`删除失败: ${e?.message || '未知错误'}`)
    }
  }

  // 测试连接
  const handleTest = async (record) => {
    const hide = message.loading('正在测试连接...', 0)
    try {
      const res = await workflowApi.testEnvironment(record.id)
      hide()
      if (res?.success) {
        message.success(res.message || '连接成功')
      } else {
        message.error(res?.message || '连接失败')
      }
    } catch (e) {
      hide()
      // 后端 4xx/5xx 时 response interceptor 会 reject，把 detail 拿出来
      const detail = e?.response?.data?.message || e?.response?.data?.detail || e?.message
      message.error(`测试失败: ${detail || '未知错误'}`)
    }
  }

  const columns = [
    { title: '名称', dataIndex: 'name', width: 160 },
    { title: 'URL', dataIndex: 'base_url', ellipsis: true },
    {
      title: '用户名',
      dataIndex: 'username',
      width: 140,
      render: (v) => v ? <span style={{ fontFamily: 'monospace' }}>{v}</span> : <span style={{ color: '#bfbfbf' }}>—</span>,
    },
    {
      title: '状态', dataIndex: 'is_active', width: 100,
      render: v => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '停用'}</Tag>
    },
    {
      title: '操作',
      width: 300,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button
            size="small"
            icon={<ApiOutlined />}
            onClick={() => handleTest(record)}
          >
            测试
          </Button>
          <Button
            size="small"
            type="primary"
            ghost
            icon={<EditOutlined />}
            onClick={() => openEditModal(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除该环境？"
            description="删除后引用此环境的工作流将无法执行"
            onConfirm={() => handleDelete(record)}
            okText="确定"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      )
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
          新增环境
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={data}
        loading={loading}
        rowKey="id"
        scroll={{ x: 800 }}
        style={{ background: '#fff', borderRadius: 12 }}
      />

      <Modal
        title={formMode === 'edit' ? '编辑环境' : '新增环境'}
        open={modalOpen}
        onCancel={closeModal}
        onOk={handleSubmit}
        okText="保存"
        cancelText="取消"
        confirmLoading={submitting}
        destroyOnClose
        width={560}
      >
        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
          preserve={false}
        >
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入环境名称' }, { max: 100 }]}
          >
            <Input placeholder="如：本地开发环境" />
          </Form.Item>

          <Form.Item
            name="base_url"
            label="N8N Base URL"
            rules={[
              { required: true, message: '请输入 Base URL' },
              { type: 'url', message: '请输入合法的 URL（http/https）' },
            ]}
          >
            <Input placeholder="http://localhost:5678" />
          </Form.Item>

          <Form.Item
            name="api_key"
            label="API Key"
            extra="可选。N8N 内部 API 用的 X-N8N-API-Key"
          >
            <Input.Password placeholder="留空表示不修改" autoComplete="new-password" />
          </Form.Item>

          <div style={{ background: '#fafafa', padding: 12, borderRadius: 8, marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
              Basic Auth 凭据（用于 N8N webhook 触发节点的"Generic Auth &gt; Basic Auth"）
            </div>
            <Form.Item
              name="username"
              label="用户名"
              style={{ marginBottom: 12 }}
            >
              <Input placeholder="如：n8nuser" autoComplete="off" />
            </Form.Item>

            <Form.Item
              name="password"
              label="密码"
              extra="明文传输 + 落库前 Fernet 加密。编辑时留空表示不修改。"
              style={{ marginBottom: 0 }}
            >
              <Input.Password placeholder="编辑时留空保持原密码不变" autoComplete="new-password" />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </div>
  )
}

export default EnvironmentList
