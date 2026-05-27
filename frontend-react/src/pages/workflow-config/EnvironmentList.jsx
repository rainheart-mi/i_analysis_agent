import { useEffect, useState } from 'react'
import { Table, Button, Tag, message, Space } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { workflowApi } from '@/api/workflow'

function EnvironmentList() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await workflowApi.getEnvironments()
      setData(res.data)
    } catch (e) {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  const columns = [
    { title: '名称', dataIndex: 'name' },
    { title: '类型', dataIndex: 'type' },
    { title: 'URL', dataIndex: 'url' },
    { title: '状态', dataIndex: 'status', render: s => <Tag>{s || '未配置'}</Tag> },
    {
      title: '操作',
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} />
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Space>
      )
    }
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />}>
          新增环境
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={data}
        loading={loading}
        rowKey="id"
        style={{ background: '#fff', borderRadius: 12 }}
      />
    </div>
  )
}

export default EnvironmentList