import { Spin, Result } from 'antd'
import { useTaskStore } from '@/store/task'

/**
 * AI 智能体 tab 内的「工作流执行中 / 失败」占位视图。
 * ChatContent 不会渲染（因为 isNodeReady=false），改用此视图让用户知道：
 * - running: 工作流还在跑，AI 智能体将在工作流完成后开放
 * - failed: 工作流失败了，去节点 tab 排查
 */
function WaitingView() {
  const currentTask = useTaskStore(s => s.currentTask)
  const status = currentTask?.status
  const isRunning = status === 'running' || status === 'pending'
  const isFailed = status === 'failed'

  if (isRunning) {
    return (
      <div style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#FAFAFA',
      }}>
        <Result
          icon={<Spin size="large" />}
          title="工作流执行中…"
          subTitle="请等待节点执行完成，AI 智能体将在工作流完成后开放"
          style={{ maxWidth: 520 }}
        />
      </div>
    )
  }

  if (isFailed) {
    return (
      <div style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#FAFAFA',
      }}>
        <Result
          status="error"
          title="工作流执行失败"
          subTitle="请前往节点 tab 查看失败原因，修复后可重新执行"
          style={{ maxWidth: 520 }}
        />
      </div>
    )
  }

  return null
}

export default WaitingView
