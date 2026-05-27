import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Button, Card, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { authApi } from '@/api/auth'
import { useUserStore } from '@/store/user'

function Login() {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const setUser = useUserStore(state => state.setUser)
  const setToken = useUserStore(state => state.setToken)

  const onFinish = async (values) => {
    setLoading(true)
    try {
      const res = await authApi.login(values.username, values.password)
      setUser(res.data.user)
      setToken(res.data.token)
      message.success('登录成功')
      navigate('/dashboard')
    } catch (e) {
      message.error('登录失败：' + e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      height: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-secondary)',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Background Decoration */}
      <div style={{
        position: 'absolute',
        inset: 0,
        background: `
          radial-gradient(ellipse 100% 80% at 50% -20%, rgba(59, 130, 246, 0.06) 0%, transparent 50%),
          radial-gradient(ellipse 80% 60% at 80% 80%, rgba(99, 102, 241, 0.05) 0%, transparent 50%)
        `,
        pointerEvents: 'none'
      }} />

      {/* Floating Shapes */}
      <div style={{
        position: 'absolute',
        top: '15%',
        left: '10%',
        width: 400,
        height: 400,
        background: 'radial-gradient(circle, rgba(59, 130, 246, 0.04) 0%, transparent 70%)',
        borderRadius: '50%',
        filter: 'blur(60px)'
      }} />
      <div style={{
        position: 'absolute',
        bottom: '20%',
        right: '10%',
        width: 300,
        height: 300,
        background: 'radial-gradient(circle, rgba(99, 102, 241, 0.04) 0%, transparent 70%)',
        borderRadius: '50%',
        filter: 'blur(50px)'
      }} />

      <Card
        className="animate-fade-in-up"
        style={{
          width: 400,
          background: 'var(--bg-primary)',
          border: '1px solid var(--border-color)',
          borderRadius: 20,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.08)',
          position: 'relative',
          zIndex: 1
        }}
        styles={{ body: { padding: '48px 40px' } }}
      >
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          {/* Logo Icon */}
          <div style={{
            width: 56,
            height: 56,
            margin: '0 auto 20px',
            background: 'var(--accent-gradient)',
            borderRadius: 14,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 16px rgba(59, 130, 246, 0.25)'
          }}>
            <span style={{ fontSize: 26, color: '#fff' }}>📊</span>
          </div>

          <h1 style={{
            fontSize: '1.5rem',
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: 8
          }}>
            智能分析助手
          </h1>
          <p style={{ color: 'var(--text-tertiary)', fontSize: '0.875rem' }}>
            登录您的账号以继续
          </p>
        </div>

        <Form
          name="login"
          onFinish={onFinish}
          layout="vertical"
          requiredMark={false}
          size="large"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
            style={{ marginBottom: 20 }}
          >
            <Input
              prefix={<UserOutlined style={{ color: 'var(--text-tertiary)' }} />}
              placeholder="用户名"
              style={{
                height: 48,
                borderRadius: 10,
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)'
              }}
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
            style={{ marginBottom: 24 }}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: 'var(--text-tertiary)' }} />}
              placeholder="密码"
              style={{
                height: 48,
                borderRadius: 10,
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)'
              }}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{
                height: 48,
                fontSize: '0.95rem',
                fontWeight: 600,
                borderRadius: 10,
                background: 'var(--accent-gradient)',
                border: 'none',
                boxShadow: '0 4px 12px rgba(59, 130, 246, 0.2)'
              }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default Login