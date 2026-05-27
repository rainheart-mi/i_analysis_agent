import { Outlet } from 'react-router-dom'
import { Layout } from 'antd'
import Header from './Header'
import Sidebar from './Sidebar'

const { Content } = Layout

function AppLayout() {
  return (
    <Layout className="app-layout">
      <Header />
      <Layout>
        <Sidebar />
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default AppLayout