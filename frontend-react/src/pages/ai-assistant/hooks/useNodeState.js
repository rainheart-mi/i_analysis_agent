import { useMemo } from 'react'
import { useTaskStore } from '@/store/task'

/**
 * 计算"当前激活节点"：从 useTaskStore 取出 currentTask + currentNodeId，
 * 找到对应的 NodeExecution 行。Memoize 避免无关重渲染。
 */
export function useNodeState() {
  const currentTask = useTaskStore(s => s.currentTask)
  const currentNodeId = useTaskStore(s => s.currentNodeId)

  const currentNode = useMemo(() => {
    return currentTask?.node_executions?.find(n => n.node_id === currentNodeId)
  }, [currentTask?.node_executions, currentNodeId])

  return { currentNode, currentTask }
}
