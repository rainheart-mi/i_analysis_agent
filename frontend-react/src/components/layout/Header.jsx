import { Layout } from 'antd'

const { Header: AntHeader } = Layout

function Header() {
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
    />
  )
}

export default Header