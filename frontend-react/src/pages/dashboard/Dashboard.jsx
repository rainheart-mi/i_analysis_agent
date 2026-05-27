import { Card, Row, Col, Button } from 'antd'
import { ReloadOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import { useTaskStore } from '@/store/task'
import { useWorkflowStore } from '@/store/workflow'
import { useEffect, useState } from 'react'

function Dashboard() {
  const tasks = useTaskStore(s => s.tasks)
  const fetchTasks = useTaskStore(s => s.fetchTasks)
  const fetchWorkflows = useWorkflowStore(s => s.fetchWorkflows)
  const workflows = useWorkflowStore(s => s.workflows)

  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    fetchTasks()
    fetchWorkflows()
  }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    await Promise.all([fetchTasks(), fetchWorkflows()])
    setRefreshing(false)
  }

  const taskList = tasks || []
  const workflowList = workflows || []

  const stats = [
    { label: '工作流总数', value: workflowList.length, trend: 'up', change: '+2', color: '#5C7CFF', bg: 'rgba(92, 124, 255, 0.1)', icon: '📊' },
    { label: '今日执行', value: taskList.length, trend: 'up', change: '+12%', color: '#52C41A', bg: 'rgba(82, 196, 26, 0.1)', icon: '⚡' },
    { label: '进行中', value: taskList.filter(t => t.status === 'running').length, trend: 'down', change: '-1', color: '#FAAD14', bg: 'rgba(250, 173, 20, 0.1)', icon: '🔄' },
    { label: '已完成', value: taskList.filter(t => t.status === 'completed').length, trend: 'up', change: '+3', color: '#722ED1', bg: 'rgba(114, 46, 209, 0.1)', icon: '✅' }
  ]

  // Mock trend data
  const weekData = [65, 72, 58, 80, 75, 88, 92]
  const maxValue = Math.max(...weekData)

  return (
    <div style={{ padding: 24, background: '#F5F7FA', minHeight: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: '0 0 4px', fontSize: '1.5rem', fontWeight: 700, color: '#1D2129' }}>
            中控仪表盘
          </h1>
          <p style={{ margin: 0, fontSize: '14px', color: '#86909C' }}>实时监控系统运行状态</p>
        </div>
        <Button
          icon={<ReloadOutlined spin={refreshing} />}
          onClick={handleRefresh}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            borderRadius: 8,
            border: '1px solid #E5E6EB',
            background: '#fff'
          }}
        >
          刷新数据
        </Button>
      </div>

      {/* Stats Grid */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {stats.map((stat, index) => (
          <Col span={6} key={index}>
            <Card
              style={{
                borderRadius: 14,
                background: '#fff',
                border: '1px solid #E5E6EB',
                transition: 'all 0.2s'
              }}
              styles={{ body: { padding: 20 } }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{
                  width: 48,
                  height: 48,
                  borderRadius: 12,
                  background: stat.bg,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 20
                }}>
                  {stat.icon}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '1.75rem', fontWeight: 700, color: stat.color, lineHeight: 1.2 }}>
                    {stat.value}
                  </div>
                  <div style={{ fontSize: '13px', color: '#86909C', marginTop: 4 }}>
                    {stat.label}
                  </div>
                </div>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 2,
                  fontSize: '12px',
                  fontWeight: 600,
                  padding: '4px 8px',
                  borderRadius: 6,
                  color: stat.trend === 'up' ? '#52C41A' : '#FF4D4F',
                  background: stat.trend === 'up' ? 'rgba(82, 196, 26, 0.1)' : 'rgba(255, 77, 79, 0.1)'
                }}>
                  {stat.trend === 'up' ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                  {stat.change}
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Content Grid */}
      <Row gutter={[16, 16]}>
        {/* Chart Card */}
        <Col span={16}>
          <Card
            style={{ borderRadius: 14, border: '1px solid #E5E6EB' }}
            title={<span style={{ fontWeight: 600, fontSize: '15px', color: '#1D2129' }}>执行趋势</span>}
            extra={
              <div style={{ display: 'flex', gap: 8 }}>
                <span style={{ padding: '4px 12px', fontSize: '12px', borderRadius: 6, background: '#F0F1FF', color: '#5C7CFF', fontWeight: 500 }}>本周</span>
                <span style={{ padding: '4px 12px', fontSize: '12px', borderRadius: 6, color: '#86909C' }}>本月</span>
              </div>
            }
            styles={{ header: { padding: '16px 20px', borderBottom: '1px solid #E5E6EB' }, body: { padding: '20px' } }}
          >
            <div style={{ height: 200, display: 'flex', alignItems: 'flex-end', padding: '20px 0' }}>
              <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', width: '100%', height: '100%', gap: 12 }}>
                {weekData.map((value, index) => (
                  <div key={index} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                    <div
                      style={{
                        width: '100%',
                        height: `${(value / maxValue) * 100}%`,
                        background: 'linear-gradient(180deg, #5C7CFF 0%, #7B91FF 100%)',
                        borderRadius: '8px 8px 0 0',
                        animation: 'growUp 0.6s ease-out forwards',
                        animationDelay: `${index * 0.1}s`
                      }}
                    />
                    <span style={{ fontSize: '12px', color: '#86909C' }}>周{index + 1}</span>
                  </div>
                ))}
              </div>
            </div>
            <style>{`
              @keyframes growUp {
                from { transform: scaleY(0); transform-origin: bottom; }
                to { transform: scaleY(1); transform-origin: bottom; }
              }
            `}</style>
          </Card>
        </Col>

        {/* Activity Card */}
        <Col span={8}>
          <Card
            style={{ borderRadius: 14, border: '1px solid #E5E6EB', height: '100%' }}
            title={<span style={{ fontWeight: 600, fontSize: '15px', color: '#1D2129' }}>最近活动</span>}
            styles={{ header: { padding: '16px 20px', borderBottom: '1px solid #E5E6EB' }, body: { padding: '16px 20px' } }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {taskList.slice(0, 5).map((task, index) => (
                <div key={index} style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  <div style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: task.status === 'completed' ? '#52C41A' : task.status === 'running' ? '#5C7CFF' : '#86909C',
                    marginTop: 6,
                    flexShrink: 0
                  }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '14px', fontWeight: 500, color: '#1D2129' }}>
                      {task.name || '未命名任务'}
                    </div>
                    <div style={{ fontSize: '12px', color: '#86909C', marginTop: 2 }}>
                      {task.status === 'completed' ? '已完成' : task.status === 'running' ? '进行中' : '待执行'}
                    </div>
                  </div>
                </div>
              ))}
              {taskList.length === 0 && (
                <div style={{ textAlign: 'center', color: '#86909C', padding: 20 }}>
                  暂无活动记录
                </div>
              )}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard