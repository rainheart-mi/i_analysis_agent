import { useState, useEffect } from 'react'
import { Button, Spin } from 'antd'
import DynamicForm from './DynamicForm'

function CanvasArea({ workflow, intentSchema, artifactSchema, executionResult, onSubmit }) {
  const [intentFormData, setIntentFormData] = useState({})
  const [isExecuting, setIsExecuting] = useState(false)

  useEffect(() => {
    if (executionResult && artifactSchema) {
      setIntentFormData(executionResult)
    }
  }, [executionResult, artifactSchema])

  const handleSubmit = () => {
    setIsExecuting(true)
    onSubmit?.(intentFormData)
  }

  const handleReset = () => {
    setIntentFormData({})
  }

  const handleBack = () => {
    setIntentFormData({})
  }

  // Empty State
  if (!workflow) {
    return (
      <div style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#FAFAFA'
      }}>
        <div style={{
          textAlign: 'center',
          padding: 48,
          background: '#FFFFFF',
          borderRadius: 20,
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.04)',
          border: '1px solid #E5E6EB',
          maxWidth: 400
        }}>
          <div style={{ marginBottom: 24, opacity: 0.8 }}>
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
              <circle cx="32" cy="32" r="28" stroke="#5C7CFF" strokeWidth="2" strokeDasharray="6 4"/>
              <path d="M24 28h16M24 36h10" stroke="#5C7CFF" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <h3 style={{ margin: '0 0 8px', fontSize: '1.1rem', fontWeight: 600, color: '#1D2129' }}>
            选择一个工作流开始分析
          </h3>
          <p style={{ margin: 0, fontSize: '14px', color: '#86909C' }}>
            从右侧面板选择工作流，系统将为您构建分析表单
          </p>
        </div>
      </div>
    )
  }

  // Loading State
  if (isExecuting) {
    return (
      <div style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#FAFAFA'
      }}>
        <div style={{
          textAlign: 'center',
          padding: 48,
          background: '#FFFFFF',
          borderRadius: 20,
          boxShadow: '0 4px 24px rgba(0, 0, 0, 0.06)',
          border: '1px solid #E5E6EB'
        }}>
          <div style={{ marginBottom: 24 }}>
            <div style={{
              width: 80,
              height: 80,
              borderRadius: '50%',
              border: '3px solid #E5E6EB',
              borderTopColor: '#5C7CFF',
              animation: 'spin 1s linear infinite',
              margin: '0 auto 24px'
            }} />
          </div>
          <h3 style={{ margin: '0 0 8px', fontSize: '1.1rem', fontWeight: 600, color: '#1D2129' }}>
            工作流执行中
          </h3>
          <p style={{ margin: 0, fontSize: '14px', color: '#86909C' }}>
            正在处理您的请求，请稍候...
          </p>
          <style>{`
            @keyframes spin {
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      </div>
    )
  }

  // Intent Form (before execution)
  if (intentSchema && !executionResult) {
    return (
      <div style={{ padding: 24, overflow: 'auto', height: '100%', background: '#F5F7FA' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20 }}>
          {/* Main Form Card */}
          <div style={{
            background: '#FFFFFF',
            borderRadius: 20,
            boxShadow: '0 4px 24px rgba(0, 0, 0, 0.06)',
            border: '1px solid #E5E6EB',
            overflow: 'hidden'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 16,
              padding: 24,
              background: 'linear-gradient(135deg, rgba(92, 124, 255, 0.04) 0%, rgba(123, 145, 255, 0.04) 100%)',
              borderBottom: '1px solid #E5E6EB'
            }}>
              <div style={{
                width: 48,
                height: 48,
                borderRadius: 14,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'rgba(92, 124, 255, 0.1)',
                color: '#5C7CFF',
                flexShrink: 0
              }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="3"/>
                  <path d="M9 9h6M9 13h4" strokeLinecap="round"/>
                </svg>
              </div>
              <div>
                <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, color: '#1D2129' }}>
                  {workflow.title}
                </h2>
                <p style={{ margin: '4px 0 0', fontSize: '14px', color: '#4E5969' }}>
                  {workflow.description}
                </p>
              </div>
            </div>
            <div style={{ padding: 24 }}>
              <DynamicForm
                schema={intentSchema}
                modelValue={intentFormData}
                onChange={setIntentFormData}
              />
            </div>
            <div style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 12,
              padding: 20,
              background: '#FAFAFA',
              borderTop: '1px solid #E5E6EB'
            }}>
              <Button onClick={handleReset} style={{ borderRadius: 10 }}>重置</Button>
              <Button
                type="primary"
                onClick={handleSubmit}
                style={{
                  borderRadius: 10,
                  background: '#5C7CFF',
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M13 5l7 7-7 7M5 12h15"/>
                </svg>
                执行工作流
              </Button>
            </div>
          </div>

          {/* Guide Card */}
          <div style={{
            background: '#FFFFFF',
            borderRadius: 16,
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.04)',
            border: '1px solid #E5E6EB',
            height: 'fit-content',
            position: 'sticky',
            top: 24
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: 16,
              background: 'linear-gradient(135deg, rgba(92, 124, 255, 0.06) 0%, rgba(123, 145, 255, 0.06) 100%)',
              borderBottom: '1px solid #E5E6EB',
              color: '#5C7CFF',
              fontWeight: 600,
              fontSize: '14px'
            }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 16v-4M12 8h.01" strokeLinecap="round"/>
              </svg>
              <span>填写指南</span>
            </div>
            <ul style={{ listStyle: 'none', margin: 0, padding: '16px 20px' }}>
              <li style={{ position: 'relative', paddingLeft: 16, marginBottom: 12, fontSize: '14px', color: '#4E5969', lineHeight: 1.5 }}>
                <span style={{ position: 'absolute', left: 0, top: 8, width: 6, height: 6, borderRadius: '50%', background: '#5C7CFF' }} />
                选择分析的大类和时间范围
              </li>
              <li style={{ position: 'relative', paddingLeft: 16, marginBottom: 12, fontSize: '14px', color: '#4E5969', lineHeight: 1.5 }}>
                <span style={{ position: 'absolute', left: 0, top: 8, width: 6, height: 6, borderRadius: '50%', background: '#5C7CFF' }} />
                支持按门店和品类筛选
              </li>
              <li style={{ position: 'relative', paddingLeft: 16, marginBottom: 0, fontSize: '14px', color: '#4E5969', lineHeight: 1.5 }}>
                <span style={{ position: 'absolute', left: 0, top: 8, width: 6, height: 6, borderRadius: '50%', background: '#5C7CFF' }} />
                设置完成后点击执行工作流
              </li>
            </ul>
            <div style={{ padding: '12px 20px 20px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '13px', color: '#4E5969' }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#52C41A', flexShrink: 0 }} />
                <span>销售达成率 ≥100% 为优秀</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '13px', color: '#4E5969' }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#FAAD14', flexShrink: 0 }} />
                <span>80% ≤ 达成率 &lt;100% 为正常</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '13px', color: '#4E5969' }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#FF4D4F', flexShrink: 0 }} />
                <span>达成率 &lt;80% 需关注</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Execution Result (after execution)
  if (executionResult && artifactSchema) {
    return (
      <div style={{ padding: 24, overflow: 'auto', height: '100%', background: '#F5F7FA' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20 }}>
          {/* Result Card */}
          <div style={{
            background: '#FFFFFF',
            borderRadius: 20,
            boxShadow: '0 4px 24px rgba(0, 0, 0, 0.06)',
            border: '1px solid #E5E6EB',
            borderTop: '3px solid #52C41A',
            overflow: 'hidden'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 16,
              padding: 24,
              background: 'linear-gradient(135deg, rgba(82, 196, 26, 0.04) 0%, rgba(82, 196, 26, 0.04) 100%)',
              borderBottom: '1px solid #E5E6EB'
            }}>
              <div style={{
                width: 48,
                height: 48,
                borderRadius: 14,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'rgba(82, 196, 26, 0.1)',
                color: '#52C41A'
              }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M8 12l3 3 5-6" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div>
                <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, color: '#1D2129' }}>
                  执行结果
                </h2>
                <p style={{ margin: '4px 0 0', fontSize: '14px', color: '#4E5969' }}>
                  工作流执行完成，以下是生成的数据
                </p>
              </div>
            </div>
            <div style={{ padding: 24 }}>
              <DynamicForm
                schema={artifactSchema}
                modelValue={executionResult}
                readonly
              />
            </div>
            <div style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 12,
              padding: 20,
              background: '#FAFAFA',
              borderTop: '1px solid #E5E6EB'
            }}>
              <Button onClick={handleBack} style={{ borderRadius: 10 }}>返回表单</Button>
              <Button
                type="primary"
                style={{
                  borderRadius: 10,
                  background: '#5C7CFF',
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
                </svg>
                导出结果
              </Button>
            </div>
          </div>

          {/* Insights Card */}
          <div style={{
            background: '#FFFFFF',
            borderRadius: 16,
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.04)',
            border: '1px solid #E5E6EB',
            borderTop: '3px solid #52C41A',
            height: 'fit-content',
            position: 'sticky',
            top: 24
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: 16,
              background: 'linear-gradient(135deg, rgba(82, 196, 26, 0.06) 0%, rgba(82, 196, 26, 0.06) 100%)',
              borderBottom: '1px solid #E5E6EB',
              color: '#52C41A',
              fontWeight: 600,
              fontSize: '14px'
            }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
                <path d="M22 4L12 14.01l-3-3"/>
              </svg>
              <span>数据洞察</span>
            </div>
            <ul style={{ listStyle: 'none', margin: 0, padding: '16px 20px' }}>
              <li style={{ position: 'relative', paddingLeft: 16, marginBottom: 12, fontSize: '14px', color: '#4E5969', lineHeight: 1.5 }}>
                <span style={{ position: 'absolute', left: 0, top: 8, width: 6, height: 6, borderRadius: '50%', background: '#52C41A' }} />
                点击大类名称可下钻到商品明细
              </li>
              <li style={{ position: 'relative', paddingLeft: 16, marginBottom: 12, fontSize: '14px', color: '#4E5969', lineHeight: 1.5 }}>
                <span style={{ position: 'absolute', left: 0, top: 8, width: 6, height: 6, borderRadius: '50%', background: '#52C41A' }} />
                销售达成率100%以上为绿色
              </li>
              <li style={{ position: 'relative', paddingLeft: 16, marginBottom: 12, fontSize: '14px', color: '#4E5969', lineHeight: 1.5 }}>
                <span style={{ position: 'absolute', left: 0, top: 8, width: 6, height: 6, borderRadius: '50%', background: '#52C41A' }} />
                80-100%为黄色，80%以下为红色
              </li>
              <li style={{ position: 'relative', paddingLeft: 16, marginBottom: 0, fontSize: '14px', color: '#4E5969', lineHeight: 1.5 }}>
                <span style={{ position: 'absolute', left: 0, top: 8, width: 6, height: 6, borderRadius: '50%', background: '#52C41A' }} />
                周环比：上升箭头绿色，下降红色
              </li>
            </ul>
          </div>
        </div>
      </div>
    )
  }

  return null
}

export default CanvasArea