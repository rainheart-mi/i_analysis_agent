import { Layout, Dropdown, Avatar } from 'antd'
import { UserOutlined, LogoutOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useUserStore } from '@/store/user'

const { Header: AntHeader } = Layout

function Header() {
  const navigate = useNavigate()
  const logout = useUserStore(state => state.logout)

  const items = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: () => {
        logout()
        navigate('/login')
      }
    }
  ]

  return (
    <AntHeader
      className="app-header"
      style={{
        height: 64,
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end'
      }}
    >
      <Dropdown menu={{ items }} placement="bottomRight" trigger={['click']}>
        <Avatar
          icon={<UserOutlined />}
          style={{
            cursor: 'pointer',
            background: 'var(--accent-gradient)',
            boxShadow: '0 2px 8px rgba(59, 130, 246, 0.2)',
            transition: 'all 0.15s ease'
          }}
        />
      </Dropdown>
    </AntHeader>
  )
}

export default Header