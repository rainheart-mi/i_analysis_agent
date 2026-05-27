import { Layout, Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import { DashboardOutlined, RobotOutlined, SettingOutlined } from '@ant-design/icons'

const { Sider } = Layout

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/ai-assistant', icon: <RobotOutlined />, label: '智能分析' },
  { key: '/workflow-config', icon: <SettingOutlined />, label: '工作流配置' }
]

function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Sider
      className="app-sidebar"
      width={240}
      style={{ flexShrink: 0 }}
    >
      <div style={{
        height: 64,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderBottom: '1px solid var(--border-color)'
      }}>
        <div style={{
          fontWeight: 700,
          fontSize: '1.1rem',
          color: 'var(--text-primary)',
          letterSpacing: '-0.02em'
        }}>
          智能分析平台
        </div>
      </div>
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        style={{ border: 'none', marginTop: 12, padding: '0 8px' }}
      />
    </Sider>
  )
}

export default Sidebar