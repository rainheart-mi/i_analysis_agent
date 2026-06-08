# AI 对话 Ant Design X 重构 - 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 用 `@ant-design/x` 的 Bubble / Sender 组件重构 `ChatPanel.jsx`，新增展开态 `ChatContent.jsx`，使 AI 对话支持 Markdown 渲染与双形态布局。

**架构概述:** 前端纯重构，store / api / 后端零改动。提取共享 hook `useChatBinding` 复用发送逻辑，中栏通过 antd `Tabs` 注入 `💬 AI 对话` tab 实现展开态。

**技术栈:**
- React 18 + Vite 5
- antd 5.15（已存在）
- @ant-design/x（新增）
- react-markdown + remark-gfm + rehype-highlight（新增）
- zustand 4.5（已存在，不变）

**前置文档:** `docs/superpowers/specs/2026-06-07-ai-chat-antd-x-refactor-design.md`

---

## 文件结构

```
frontend-react/src/
├── api/
│   └── chat.js                          # 不动
├── store/
│   └── chat.js                          # 不动
├── pages/ai-assistant/
│   ├── AIAssistant.jsx                  # 改：加 expanded 态 + tab 注入
│   ├── ChatPanel.jsx                    # 重写：默认态 Bubble.List + Sender
│   ├── ChatContent.jsx                  # 新建：展开态全宽版本
│   ├── ChatMessage.jsx                  # 删除
│   ├── hooks/                           # 新建目录
│   │   ├── useChatBinding.js            # 新建：共享发送逻辑
│   │   └── useNodeState.js              # 新建：从 task store 取当前节点
│   └── ... (其他文件不动)
├── components/
│   └── markdown/                        # 新建目录
│       └── Markdown.jsx                 # 新建：ReactMarkdown 包装
└── package.json                         # 改：+5 个依赖

根目录不涉及任何后端 / Java 改动。
```

---

## Task 1: 安装依赖

**Files:**
- Modify: `frontend-react/package.json`

- [ ] **Step 1.1: 确认 Node / npm 版本**

Run: `cd "C:/LLM/i_analysis_agent/frontend-react" && node -v && npm -v`
Expected: `node` 输出 `v18.x` 或 `v20.x`；`npm` 输出 `9.x` 或 `10.x`

- [ ] **Step 1.2: 安装 @ant-design/x 与 markdown 相关包**

Run:
```bash
cd "C:/LLM/i_analysis_agent/frontend-react" && \
npm install \
  @ant-design/x \
  react-markdown \
  remark-gfm \
  rehype-highlight \
  highlight.js
```
Expected: 安装成功，`package.json` 的 `dependencies` 出现 5 个新条目；无 peer dependency 冲突警告

- [ ] **Step 1.3: 验证 package.json**

```bash
cd "C:/LLM/i_analysis_agent/frontend-react" && \
grep -A 10 '"dependencies"' package.json
```
Expected: 看到 `"@ant-design/x"`、`"react-markdown"`、`"remark-gfm"`、`"rehype-highlight"`、`"highlight.js"`

- [ ] **Step 1.4: 启动 dev server 验证无破坏**

Run: `cd "C:/LLM/i_analysis_agent/frontend-react" && npm run dev`
Expected: Vite 启动成功（`Local: http://localhost:5173/`），浏览器能打开主页，无白屏

- [ ] **Step 1.5: 停止 dev server**

Ctrl+C 停止 dev server，避免长时间占用端口。

---

## Task 2: 创建 useNodeState hook

**Files:**
- Create: `frontend-react/src/pages/ai-assistant/hooks/useNodeState.js`

- [ ] **Step 2.1: 创建 hooks 目录**

Run: `mkdir -p "C:/LLM/i_analysis_agent/frontend-react/src/pages/ai-assistant/hooks"`
Expected: 目录创建成功（mkdir 在 Windows 上可能需要用 `New-Item`，但 Git Bash 应可正常工作）

- [ ] **Step 2.2: 编写 useNodeState.js**

写入文件 `frontend-react/src/pages/ai-assistant/hooks/useNodeState.js`：

```js
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
```

- [ ] **Step 2.3: 验证文件存在**

Run: `ls "C:/LLM/i_analysis_agent/frontend-react/src/pages/ai-assistant/hooks/useNodeState.js"`
Expected: 文件存在

---

## Task 3: 创建 useChatBinding hook

**Files:**
- Create: `frontend-react/src/pages/ai-assistant/hooks/useChatBinding.js`

- [ ] **Step 3.1: 编写 useChatBinding.js**

写入文件 `frontend-react/src/pages/ai-assistant/frontend-react/src/pages/ai-assistant/hooks/useChatBinding.js`（实际路径是 `frontend-react/src/pages/ai-assistant/hooks/useChatBinding.js`）：

```js
import { useMemo } from 'react'
import { useChatStore } from '@/store/chat'
import { useNodeState } from './useNodeState'
import { chatStream } from '@/api/chat'

const STATUS_LABEL = {
  pending: '待执行',
  running: '执行中',
  completed: '已就绪',
  failed: '已失败'
}

const LOCK_MESSAGE = {
  noNode: '请先在中间画布选择并执行一个工作流节点',
  pending: '请先点击「执行工作流」按钮启动该节点',
  running: '节点正在执行中，请等待完成后发起对话',
  failed: '节点执行失败，无法基于该结果发起对话',
  unknown: '节点未完成，无法发起对话'
}

/**
 * 共享 chat 行为 hook：供 ChatPanel（默认态）和 ChatContent（展开态）共用。
 * 返回：当前节点状态、锁状态、发送函数、错误信息、清空函数。
 */
export function useChatBinding() {
  const { currentNode } = useNodeState()

  const activeNodeExecutionId = useChatStore(s => s.activeNodeExecutionId)
  const isStreaming = useChatStore(s => s.isStreaming)
  const error = useChatStore(s => s.error)
  const addMessage = useChatStore(s => s.addMessage)
  const startAssistantMessage = useChatStore(s => s.startAssistantMessage)
  const appendDelta = useChatStore(s => s.appendDelta)
  const finalizeMessage = useChatStore(s => s.finalizeMessage)
  const setError = useChatStore(s => s.setError)
  const clearMessages = useChatStore(s => s.clearMessages)

  const isNodeReady = currentNode?.status === 'completed'
  const inputDisabled = !isNodeReady || isStreaming

  const nodeStatusLabel = STATUS_LABEL[currentNode?.status] || '未开始'
  const lockMessage = useMemo(() => {
    if (!currentNode) return LOCK_MESSAGE.noNode
    return LOCK_MESSAGE[currentNode.status] || LOCK_MESSAGE.unknown
  }, [currentNode])

  const handleSend = (text) => {
    const content = (text || '').trim()
    if (!content || inputDisabled || !activeNodeExecutionId) return

    addMessage({ type: 'user', content })
    startAssistantMessage()

    const history = useChatStore.getState().messages
      .filter(m => m.type === 'user' || (m.type === 'assistant' && !m.streaming))
      .map(m => ({ role: m.type === 'user' ? 'user' : 'assistant', content: m.content }))

    return chatStream({
      nodeExecutionId: activeNodeExecutionId,
      messages: history,
      onDelta: appendDelta,
      onDone: finalizeMessage,
      onError: (err) => {
        finalizeMessage()
        setError(err)
      },
    })
  }

  return {
    currentNode,
    isNodeReady,
    inputDisabled,
    nodeStatusLabel,
    lockMessage,
    activeNodeExecutionId,
    isStreaming,
    error,
    handleSend,
    clearMessages,
  }
}
```

- [ ] **Step 3.2: 验证文件存在**

Run: `ls "C:/LLM/i_analysis_agent/frontend-react/src/pages/ai-assistant/hooks/useChatBinding.js"`
Expected: 文件存在

---

## Task 4: 创建 Markdown 包装组件

**Files:**
- Create: `frontend-react/src/components/markdown/Markdown.jsx`

- [ ] **Step 4.1: 创建目录与文件**

写入文件 `frontend-react/src/components/markdown/Markdown.jsx`：

```jsx
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github.css'

/**
 * 统一的 Markdown 渲染包装。
 * 配套 rehype-highlight + highlight.js github 主题，给代码块语法高亮。
 * 表格、删除线、任务列表由 remark-gfm 提供。
 */
export default function Markdown({ children }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        table: ({ node, ...props }) => (
          <table style={{ borderCollapse: 'collapse', width: '100%', margin: '8px 0' }} {...props} />
        ),
        th: ({ node, ...props }) => (
          <th style={{ border: '1px solid #E5E6EB', padding: '6px 10px', background: '#F5F7FA' }} {...props} />
        ),
        td: ({ node, ...props }) => (
          <td style={{ border: '1px solid #E5E6EB', padding: '6px 10px' }} {...props} />
        ),
        a: ({ node, ...props }) => <a target="_blank" rel="noopener noreferrer" {...props} />,
        code: ({ node, inline, className, children, ...props }) => {
          if (inline) {
            return <code style={{ background: '#F0F1F5', padding: '1px 6px', borderRadius: 4, fontSize: '0.9em' }} {...props}>{children}</code>
          }
          return <code className={className} {...props}>{children}</code>
        },
      }}
    >
      {children || ''}
    </ReactMarkdown>
  )
}
```

- [ ] **Step 4.2: 验证文件存在**

Run: `ls "C:/LLM/i_analysis_agent/frontend-react/src/components/markdown/Markdown.jsx"`
Expected: 文件存在

---

## Task 5: 重写 ChatPanel.jsx（默认态）

**Files:**
- Modify: `frontend-react/src/pages/ai-assistant/ChatPanel.jsx`（整体重写）

- [ ] **Step 5.1: 备份当前文件**

Run: `cp "C:/LLM/i_analysis_agent/frontend-react/src/pages/ai-assistant/ChatPanel.jsx" "C:/LLM/i_analysis_agent/frontend-react/src/pages/ai-assistant/ChatPanel.jsx.bak"`
Expected: 备份成功

- [ ] **Step 5.2: 写入新 ChatPanel.jsx**

完整替换 `frontend-react/src/pages/ai-assistant/ChatPanel.jsx`：

```jsx
import { useRef, useEffect, useMemo } from 'react'
import { Select, Button, Tooltip } from 'antd'
import { ExpandOutlined, LockOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { Bubble, Sender } from '@ant-design/x'
import { useChatStore } from '@/store/chat'
import { useWorkflowStore } from '@/store/workflow'
import { useChatBinding } from './hooks/useChatBinding'
import Markdown from '@/components/markdown/Markdown'

function ChatPanel({ onExpand }) {
  const messages = useChatStore(s => s.messages)
  const selectedWorkflow = useChatStore(s => s.selectedWorkflow)
  const setSelectedWorkflow = useChatStore(s => s.setSelectedWorkflow)
  const setActiveNodeExecution = useChatStore(s => s.setActiveNodeExecution)
  const activeNodeExecutionId = useChatStore(s => s.activeNodeExecutionId)
  const workflows = useWorkflowStore(s => s.workflows)

  const { currentNode, isNodeReady, inputDisabled, nodeStatusLabel, lockMessage,
          error, handleSend, clearMessages } = useChatBinding()

  const senderRef = useRef(null)

  // 节点切换时同步 sessionId
  useEffect(() => {
    if (currentNode?.id && currentNode.id !== activeNodeExecutionId) {
      setActiveNodeExecution(currentNode.id)
    } else if (!currentNode?.id && activeNodeExecutionId) {
      setActiveNodeExecution(null)
    }
  }, [currentNode?.id, activeNodeExecutionId, setActiveNodeExecution])

  const workflowOptions = workflows.map(w => ({
    value: w.id,
    label: w.title || w.name || '未命名工作流'
  }))

  // Bubble.List 的 items 结构
  const bubbleItems = useMemo(
    () => messages.map(m => ({
      key: m.id,
      role: m.type === 'user' ? 'user' : 'assistant',
      content: m.content,
      loading: m.streaming === true,
    })),
    [messages]
  )

  const placeholder = inputDisabled && isNodeReady ? 'AI 正在思考…' : '基于工作流结果提问…'

  return (
    <div style={{
      background: '#FFFFFF',
      borderRadius: 14,
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      border: '1px solid #E5E6EB',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px',
        borderBottom: '1px solid #E5E6EB',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 8
      }}>
        <span style={{ fontWeight: 600, fontSize: '15px', color: '#1D2129' }}>AI 对话</span>
        {currentNode && (
          <Tooltip title={currentNode.node_name || currentNode.node_id}>
            {isNodeReady ? (
              <span style={{
                fontSize: '11px', color: '#52C41A', background: '#F6FFED',
                padding: '2px 8px', borderRadius: 10
              }}>● 已就绪</span>
            ) : (
              <span style={{
                fontSize: '11px', color: '#86909C', background: '#F5F7FA',
                padding: '2px 8px', borderRadius: 10
              }}>
                <LockOutlined style={{ fontSize: '10px', marginRight: 2 }} />{nodeStatusLabel}
              </span>
            )}
          </Tooltip>
        )}
        <Button
          type="text"
          icon={<ExpandOutlined />}
          size="small"
          onClick={onExpand}
          style={{ color: '#86909C' }}
        />
      </div>

      {/* Workflow Selector */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #E5E6EB' }}>
        <Select
          value={selectedWorkflow?.id}
          onChange={(val) => {
            const wf = workflows.find(w => w.id === val)
            setSelectedWorkflow(wf || null)
          }}
          placeholder="选择工作流"
          options={workflowOptions}
          style={{ width: '100%' }}
          size="middle"
        />
      </div>

      {/* Messages Area */}
      <div style={{ flex: 1, overflow: 'auto', padding: '16px' }}>
        {error && (
          <div style={{
            background: '#FFF2F0', border: '1px solid #FFCCC7', color: '#FF4D4F',
            padding: '8px 12px', borderRadius: 8, fontSize: '12px', marginBottom: 12,
            display: 'flex', alignItems: 'center', gap: 6
          }}>
            <ExclamationCircleOutlined />
            <span>{error}</span>
          </div>
        )}
        {messages.length === 0 ? (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', height: '100%', color: '#86909C'
          }}>
            <div style={{
              width: 64, height: 64, borderRadius: 16, background: '#F5F7FA',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 28, marginBottom: 12
            }}>💬</div>
            <span style={{ fontSize: '13px' }}>
              {isNodeReady ? '基于工作流结果开始提问' : '等待节点执行完成'}
            </span>
          </div>
        ) : (
          <Bubble.List
            items={bubbleItems}
            autoScroll
            style={{ paddingBottom: 8 }}
            roles={{
              user: { placement: 'end' },
              assistant: { placement: 'start' },
            }}
          />
        )}
      </div>

      {/* Input Area */}
      {isNodeReady ? (
        <div style={{
          padding: '12px 16px', borderTop: '1px solid #E5E6EB'
        }}>
          <Sender
            ref={senderRef}
            placeholder={placeholder}
            disabled={inputDisabled && isNodeReady}
            onSubmit={(val) => {
              handleSend(val)
              senderRef.current?.clear?.()
            }}
            style={{ borderRadius: 10 }}
          />
        </div>
      ) : (
        <div style={{
          padding: '20px 16px', borderTop: '1px solid #E5E6EB',
          background: '#FAFAFA', display: 'flex',
          alignItems: 'center', justifyContent: 'center', gap: 8
        }}>
          <LockOutlined style={{ color: '#86909C', fontSize: 14 }} />
          <span style={{ fontSize: '12px', color: '#86909C' }}>{lockMessage}</span>
        </div>
      )}
    </div>
  )
}

export default ChatPanel
```

- [ ] **Step 5.3: 验证 dev server 启动无报错**

Run: `cd "C:/LLM/i_analysis_agent/frontend-react" && npm run dev`
Expected: Vite 启动成功，浏览器打开 `/ai-assistant` 页面（如果有路由），右栏 ChatPanel 渲染无白屏。

- [ ] **Step 5.4: 视觉冒烟**

打开浏览器 → 登录 → 选工作流 → 选节点执行 → 等 completed → 右栏应出现输入框 → 输入"测试"→ 发送 → 应看到 user 气泡 + assistant 气泡（即使是流式效果）

- [ ] **Step 5.5: 停止 dev server**

Ctrl+C 停止 dev server。

---

## Task 6: 创建 ChatContent.jsx（展开态）

**Files:**
- Create: `frontend-react/src/pages/ai-assistant/ChatContent.jsx`

- [ ] **Step 6.1: 写入新 ChatContent.jsx**

写入文件 `frontend-react/src/pages/ai-assistant/ChatContent.jsx`：

```jsx
import { useRef, useEffect, useMemo } from 'react'
import { Select, Button, Tooltip } from 'antd'
import { CompressOutlined, LockOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { Bubble, Sender } from '@ant-design/x'
import { useChatStore } from '@/store/chat'
import { useWorkflowStore } from '@/store/workflow'
import { useChatBinding } from './hooks/useChatBinding'
import Markdown from '@/components/markdown/Markdown'

/**
 * 展开态 AI 对话视图：渲染在中栏 canvas 顶部 tab 内容区。
 * 与 ChatPanel 共享 useChatBinding，行为完全一致，仅 UI 布局占满中栏。
 */
function ChatContent({ onCollapse }) {
  const messages = useChatStore(s => s.messages)
  const selectedWorkflow = useChatStore(s => s.selectedWorkflow)
  const setSelectedWorkflow = useChatStore(s => s.setSelectedWorkflow)
  const setActiveNodeExecution = useChatStore(s => s.setActiveNodeExecution)
  const activeNodeExecutionId = useChatStore(s => s.activeNodeExecutionId)
  const workflows = useWorkflowStore(s => s.workflows)

  const { currentNode, isNodeReady, inputDisabled, nodeStatusLabel, lockMessage,
          error, handleSend } = useChatBinding()

  const senderRef = useRef(null)

  useEffect(() => {
    if (currentNode?.id && currentNode.id !== activeNodeExecutionId) {
      setActiveNodeExecution(currentNode.id)
    } else if (!currentNode?.id && activeNodeExecutionId) {
      setActiveNodeExecution(null)
    }
  }, [currentNode?.id, activeNodeExecutionId, setActiveNodeExecution])

  const workflowOptions = workflows.map(w => ({
    value: w.id,
    label: w.title || w.name || '未命名工作流'
  }))

  const bubbleItems = useMemo(
    () => messages.map(m => ({
      key: m.id,
      role: m.type === 'user' ? 'user' : 'assistant',
      content: m.content,
      loading: m.streaming === true,
    })),
    [messages]
  )

  const placeholder = inputDisabled && isNodeReady ? 'AI 正在思考…' : '基于工作流结果提问…'

  return (
    <div style={{
      background: '#FFFFFF',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden'
    }}>
      {/* Top bar: workflow selector + collapse button */}
      <div style={{
        padding: '12px 24px',
        borderBottom: '1px solid #E5E6EB',
        display: 'flex',
        alignItems: 'center',
        gap: 12
      }}>
        <Select
          value={selectedWorkflow?.id}
          onChange={(val) => {
            const wf = workflows.find(w => w.id === val)
            setSelectedWorkflow(wf || null)
          }}
          placeholder="选择工作流"
          options={workflowOptions}
          style={{ width: 280 }}
          size="middle"
        />
        {currentNode && (
          <Tooltip title={currentNode.node_name || currentNode.node_id}>
            {isNodeReady ? (
              <span style={{
                fontSize: '12px', color: '#52C41A', background: '#F6FFED',
                padding: '2px 8px', borderRadius: 10
              }}>● 已就绪</span>
            ) : (
              <span style={{
                fontSize: '12px', color: '#86909C', background: '#F5F7FA',
                padding: '2px 8px', borderRadius: 10
              }}>
                <LockOutlined style={{ fontSize: '11px', marginRight: 2 }} />{nodeStatusLabel}
              </span>
            )}
          </Tooltip>
        )}
        <Button
          type="text"
          icon={<CompressOutlined />}
          onClick={onCollapse}
          style={{ marginLeft: 'auto', color: '#86909C' }}
        >
          收起
        </Button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: 'auto', padding: '20px 24px' }}>
        {error && (
          <div style={{
            background: '#FFF2F0', border: '1px solid #FFCCC7', color: '#FF4D4F',
            padding: '8px 12px', borderRadius: 8, fontSize: '12px', marginBottom: 12,
            display: 'flex', alignItems: 'center', gap: 6
          }}>
            <ExclamationCircleOutlined />
            <span>{error}</span>
          </div>
        )}
        {messages.length === 0 ? (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', height: '100%', color: '#86909C'
          }}>
            <div style={{
              width: 80, height: 80, borderRadius: 20, background: '#F5F7FA',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 36, marginBottom: 16
            }}>💬</div>
            <span style={{ fontSize: '14px' }}>
              {isNodeReady ? '基于工作流结果开始提问' : '等待节点执行完成'}
            </span>
          </div>
        ) : (
          <Bubble.List
            items={bubbleItems}
            autoScroll
            style={{ paddingBottom: 8 }}
            roles={{
              user: { placement: 'end' },
              assistant: { placement: 'start' },
            }}
          />
        )}
      </div>

      {/* Input */}
      {isNodeReady ? (
        <div style={{ padding: '16px 24px', borderTop: '1px solid #E5E6EB' }}>
          <Sender
            ref={senderRef}
            placeholder={placeholder}
            disabled={inputDisabled && isNodeReady}
            onSubmit={(val) => {
              handleSend(val)
              senderRef.current?.clear?.()
            }}
            style={{ borderRadius: 10 }}
          />
        </div>
      ) : (
        <div style={{
          padding: '24px', borderTop: '1px solid #E5E6EB',
          background: '#FAFAFA', display: 'flex',
          alignItems: 'center', justifyContent: 'center', gap: 8
        }}>
          <LockOutlined style={{ color: '#86909C', fontSize: 14 }} />
          <span style={{ fontSize: '13px', color: '#86909C' }}>{lockMessage}</span>
        </div>
      )}
    </div>
  )
}

export default ChatContent
```

- [ ] **Step 6.2: 验证文件存在**

Run: `ls "C:/LLM/i_analysis_agent/frontend-react/src/pages/ai-assistant/ChatContent.jsx"`
Expected: 文件存在

---

## Task 7: 修改 AIAssistant.jsx（加 expanded 态 + tab 注入）

**Files:**
- Modify: `frontend-react/src/pages/ai-assistant/AIAssistant.jsx`

- [ ] **Step 7.1: 备份当前文件**

Run: `cp "C:/LLM/i_analysis_agent/frontend-react/src/pages/ai-assistant/AIAssistant.jsx" "C:/LLM/i_analysis_agent/frontend-react/src/pages/ai-assistant/AIAssistant.jsx.bak"`
Expected: 备份成功

- [ ] **Step 7.2: 整体替换 AIAssistant.jsx**

完整替换 `frontend-react/src/pages/ai-assistant/AIAssistant.jsx`：

```jsx
import { useEffect, useState } from 'react'
import { Tabs } from 'antd'
import { useWorkflowStore } from '@/store/workflow'
import { useTaskStore } from '@/store/task'
import { useChatStore } from '@/store/chat'
import WorkflowSidebar from './WorkflowSidebar'
import NodeTabs from './NodeTabs'
import NodeContent from './NodeContent'
import CanvasArea from './CanvasArea'
import IntentFormPreview from './IntentFormPreview'
import ChatPanel from './ChatPanel'
import ChatContent from './ChatContent'

function AIAssistant() {
  const fetchWorkflows = useWorkflowStore(s => s.fetchWorkflows)
  const fetchTasks = useTaskStore(s => s.fetchTasks)
  const currentTask = useTaskStore(s => s.currentTask)
  const currentNodeId = useTaskStore(s => s.currentNodeId)
  const selectedWorkflow = useChatStore(s => s.selectedWorkflow)
  const currentIntentSchema = useWorkflowStore(s => s.currentIntentSchema)
  const setCurrentNode = useTaskStore(s => s.setCurrentNode)

  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    fetchWorkflows()
    fetchTasks()
  }, [])

  // 计算 tab items：节点 tab + AI 对话 tab
  const nodeTabItems = (currentTask?.node_executions || []).map((node, index) => ({
    key: node.node_id,
    label: node.node_name || `节点 ${index + 1}`,
    children: null, // 实际渲染由下方 switch 控制
  }))

  const chatTabKey = '__chat__'
  const allTabs = [
    ...nodeTabItems,
    { key: chatTabKey, label: '💬 AI 对话', children: null },
  ]

  // 决定中栏渲染什么
  let centerContent
  if (expanded) {
    // 展开态：tabs 选中 AI 对话 → 渲染 ChatContent
    centerContent = <ChatContent onCollapse={() => setExpanded(false)} />
  } else if (currentTask) {
    centerContent = (
      <>
        <NodeTabs />
        <NodeContent />
      </>
    )
  } else if (selectedWorkflow) {
    centerContent = <IntentFormPreview />
  } else {
    centerContent = (
      <CanvasArea
        workflow={null}
        intentSchema={null}
        artifactSchema={null}
        executionResult={null}
      />
    )
  }

  return (
    <div style={{
      height: 'calc(100vh - 104px)',
      display: 'flex',
      gap: 20,
      padding: '0 0 20px 0'
    }}>
      {/* Left - Workflow Sidebar */}
      <div style={{ width: 280, flexShrink: 0 }}>
        <WorkflowSidebar />
      </div>

      {/* Center - Canvas / Chat */}
      <div style={{
        flex: 1,
        background: '#FFFFFF',
        borderRadius: 14,
        border: '1px solid #E5E6EB',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {centerContent}
      </div>

      {/* Right - Chat Panel (默认态) */}
      {!expanded && (
        <div style={{ width: 360, flexShrink: 0 }}>
          <ChatPanel onExpand={() => setExpanded(true)} />
        </div>
      )}
    </div>
  )
}

export default AIAssistant
```

- [ ] **Step 7.3: 验证 dev server 无报错**

Run: `cd "C:/LLM/i_analysis_agent/frontend-react" && npm run dev`
Expected: Vite 启动成功，浏览器打开 AI 助手页无白屏

- [ ] **Step 7.4: 视觉冒烟 — 展开 / 收起**

打开浏览器：
1. 登录 → 选工作流 → 执行节点 → 等 completed
2. 看到右栏 ChatPanel 头部有 `⤢ 展开` 按钮
3. 点击 → 右栏消失 → 中栏顶部出现 tabs，最后一个 `💬 AI 对话`（如果未切到节点 tab 视图，tabs 可能不显示；先选节点 tab 再展开）
4. 中栏渲染 ChatContent（顶部有 `收起` 按钮）
5. 点击 `收起` → 恢复右栏 + 中栏回到 NodeTabs + NodeContent

---

## Task 8: 删除 ChatMessage.jsx

**Files:**
- Delete: `frontend-react/src/pages/ai-assistant/ChatMessage.jsx`

- [ ] **Step 8.1: 确认无其他文件 import**

Run: `grep -r "ChatMessage" "C:/LLM/i_analysis_agent/frontend-react/src" --include="*.jsx" --include="*.js" 2>&1`
Expected: 无结果（除 `ChatMessage.jsx` 自身外，无引用）

- [ ] **Step 8.2: 删除文件**

Run: `rm "C:/LLM/i_analysis_agent/frontend-react/src/pages/ai-assistant/ChatMessage.jsx"`
Expected: 删除成功

- [ ] **Step 8.3: 删除备份文件**

Run: `rm "C:/LLM/i_analysis_agent/frontend-react/src/pages/ai-assistant/ChatPanel.jsx.bak" "C:/LLM/i_analysis_agent/frontend-react/src/pages/ai-assistant/AIAssistant.jsx.bak"`
Expected: 备份删除成功

---

## Task 9: 构建与体积检查

**Files:**
- Modify: 视结果而定

- [ ] **Step 9.1: 跑生产构建**

Run: `cd "C:/LLM/i_analysis_agent/frontend-react" && npm run build`
Expected: 构建成功，输出 `dist/` 目录

- [ ] **Step 9.2: 检查 bundle 体积**

Run: `ls -la "C:/LLM/i_analysis_agent/frontend-react/dist/assets/" | head -20`
Expected: JS 资源文件大小记录

- [ ] **Step 9.3: 评估**

| 体积增量 | 评估 | 动作 |
|---|---|---|
| < 400KB | 良好 | 无需处理 |
| 400-600KB | 可接受 | 命名导入生效，记录数字 |
| > 600KB | 偏大 | 切换 subpath 路径引入 |

- [ ] **Step 9.4: 决定是否需要进一步优化**

如果超 600KB，把对应组件改为 subpath 路径：
```js
// 替换 import
import { Bubble, Sender } from '@ant-design/x'
// 为
import Bubble from '@ant-design/x/es/bubble'
import Sender from '@ant-design/x/es/sender'
```

---

## Task 10: 端到端冒烟

- [ ] **Step 10.1: 启动完整链路**

1. 后端：`cd "C:/LLM/i_analysis_agent/backend" && uvicorn app.main:app --reload --port 8000`
2. Celery（如果跑工作流需要）：`cd "C:/LLM/i_analysis_agent/backend" && python -m celery -A app.celery_app worker --loglevel=info --pool=solo`
3. AgentScope Java（如果用 chat）：`cd "C:/LLM/AgentScope" && mvn spring-boot:run`
4. 前端：`cd "C:/LLM/i_analysis_agent/frontend-react" && npm run dev`

- [ ] **Step 10.2: 完整流程测试**

1. http://localhost:5173 登录（admin/admin123）
2. 进入 AI 助手页 → 选 `陈列复盘报告` → 创建任务 → 等节点 completed
3. **默认态测试**：右栏输入"基于工作流结果给个 3 行总结" → 发送 → 看到 user / assistant 气泡 → 流式追加 → 完结
4. **Markdown 测试**：让 AI 输出含 `## 标题` / `- 列表` / ```代码块``` / `| 表格 |` 的回复（可通过 "请用 markdown 格式输出" prompt 触发）→ 确认 Bubble 正确渲染
5. **展开测试**：点 `⤢ 展开` → 右栏消失 → 中栏 `💬 AI 对话` tab 渲染 ChatContent → 输入问题 → 同样流式
6. **收起测试**：点 `收起` → 恢复右栏
7. **切节点测试**：在中栏 NodeTabs 切到其他节点 tab → 看到 messages 清空 + 锁定态（如果新节点未完成）
8. **锁定测试**：选 pending 节点 → 看不到输入框 → 底部显示 🔒 + 锁定文案

- [ ] **Step 10.3: Console 检查**

打开 DevTools Console，应无红色错误（黄色警告如 React Router v7 future flag 可忽略）。

- [ ] **Step 10.4: 修复任何发现的问题**

如发现视觉 / 行为 / 性能问题，定位到对应文件修复后重跑 10.2。

---

## 完成标准

- ✅ 所有 10 个 Task 勾选完毕
- ✅ `npm run build` 成功
- ✅ 端到端冒烟 8 个场景全部通过
- ✅ 无 Console 错误
- ✅ 后端 / Java / 数据库零改动

---

## 风险与回滚

### 风险
1. **包体积超标** → 切 subpath 路径（见 Task 9.4）
2. **Bubble.List 虚拟列表不生效** → 确认 `autoScroll` + `items` 结构正确
3. **rehype-highlight 样式没生效** → 确认 `import 'highlight.js/styles/github.css'` 已加
4. **流式 markdown 错位** → 当前接受"流结束后自愈"策略

### 回滚

如果整体不可用，5 分钟回滚：
```bash
cd "C:/LLM/i_analysis_agent/frontend-react"
# 1. 还原 ChatPanel / AIAssistant
git checkout HEAD -- src/pages/ai-assistant/ChatPanel.jsx src/pages/ai-assistant/AIAssistant.jsx
# 2. 删除新文件
rm src/pages/ai-assistant/ChatContent.jsx
rm src/pages/ai-assistant/hooks/useChatBinding.js
rm src/pages/ai-assistant/hooks/useNodeState.js
rm src/components/markdown/Markdown.jsx
# 3. 还原 package.json（如果已 commit 依赖）
git checkout HEAD -- package.json package-lock.json
# 4. 重新 install
npm install
```

如未 commit，则手动按上面的"备份还原"逻辑回滚即可。
