import { useEffect, useState } from 'react'
import { Table, Button, Switch, Tag, Space } from 'antd'
import { workflowApi } from '@/api/workflow'

function WorkflowRoutes() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await workflowApi.getWorkflows()
      setData(res.data.items || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  const columns = [
    { title: '名称', dataIndex: 'title' },
    { title: '描述', dataIndex: 'description' },
    { title: '是否激活', dataIndex: 'is_active', render: v => <Switch checked={v} /> },
    { title: '节点数', dataIndex: 'node_count' },
    {
      title: '操作',
      render: () => (
        <Space>
          <Button size="small">配置节点</Button>
        </Space>
      )
    }
  ]

  return (
    <Table
      columns={columns}
      dataSource={data}
      loading={loading}
      rowKey="id"
      style={{ background: '#fff', borderRadius: 12 }}
    />
  )
}

export default WorkflowRoutes