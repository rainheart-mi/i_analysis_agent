# AI 对话前端升级：Ant Design X 整合方案

> **设计日期:** 2026-06-07
> **状态:** 已确认，待写实施计划
> **范围:** 仅前端，后端 / API / Java AgentScope 零改动

## 1. 背景与目标

### 1.1 当前问题
- `frontend-react/src/pages/ai-assistant/ChatPanel.jsx`（10KB）使用手写 `div + css` 渲染消息和输入框
- `ChatMessage.jsx` 是简单的纯文本气泡，不支持 Markdown 渲染，代码块/表格/列表被压平成字符串
- 长对话（>100 条）下 React 频繁重渲染，div 滚动卡顿
- 用户已与 Ant Design v5 体系深度集成（`antd@^5.15.0`），但缺乏 LLM 流式场景专用组件

### 1.2 目标
- 引入 `@ant-design/x`，用 `Bubble` / `Sender` 替换手写 UI
- Markdown 渲染：标题/列表/代码块/表格全部正确呈现
- 长对话性能：`Bubble.List` 内置虚拟列表
- 双形态布局：默认右栏 360px 紧凑态 + 展开后中栏 tab 接管

### 1.3 约束
- **不引入** Prompts 组件
- **不引入** Conversations（沿用单会话 / NodeExecution 模型）
- **不引入** 文件上传 / 附件
- **不引入** localStorage 持久化（保持 zustand 内存）
- **不动** 后端 / API / Java AgentScope

## 2. 架构与组件

### 2.1 组件映射

| 当前实现 | 重构后 | 复用现有 |
|---|---|---|
| `ChatMessage.jsx`（div+css 纯文本） | `Bubble.List` + `Bubble` + `Bubble.Content` | — |
| `<Input.TextArea>` + 自定义按钮 | `Sender`（快捷键 / loading / disabled） | — |
| `chatStream({...})` 包装 fetch+ReadableStream | **签名不动**，调用方从 `ChatPanel` 移到 `useChatBinding` hook | `src/api/chat.js` |
| `useChatStore` | 不动 | `src/store/chat.js` |
| 节点状态徽标 + 锁定 UI（手写） | 保留手写 | — |
| `Select` 工作流选择器 | 保留 | — |

### 2.2 引入方式（方案 2）
```js
// 命名导入，Vite tree-shaking 处理
import { Bubble, Sender } from '@ant-design/x'
```
起步用方案 2；`npm run build` 跑通后看 dist 体积；超过 500KB 再切到 subpath 路径或加 `@umijs/plugin-antd`。

### 2.3 依赖增量

```jsonc
{
  "dependencies": {
    "@ant-design/x": "^1.x",           // 主组件
    "react-markdown": "^9.x",          // Markdown 解析
    "remark-gfm": "^4.x",              // 表格 / 删除线 / 任务列表
    "rehype-highlight": "^7.x",        // 代码块语法高亮（基于 highlight.js）
    "highlight.js": "^11.x"            // 语法高亮样式（CSS 导入可选）
  }
}
```
预期包体积增量：+约 250-350KB minified（含 @ant-design/x 的 Bubble/Sender 子集）。

> 取消 `react-syntax-highlighter`（+150KB）改用 `rehype-highlight`（+30KB），体积更优。

## 3. 布局设计

### 3.1 默认态（未展开）

完全保留 3 栏结构：
```
┌──────────┬─────────────────────────┬──────────┐
│ 任务实例  │    节点画布              │ AI 对话  │
│ (280px)  │ (NodeTabs + NodeContent)│ (360px)  │
│          │                         │  ChatPanel│
│          │                         │  紧凑态   │
└──────────┴─────────────────────────┴──────────┘
```

- 头部右上角放 `⤢ 展开` 按钮（替换现有的 `ExpandOutlined` 占位按钮）
- 工作流选择器保留在头部下方
- 锁定态（节点未 completed）保留 LockOutlined 提示

### 3.2 展开态

- 右栏 `display: none`
- 中栏顶部 `NodeTabs` 末尾追加 `💬 AI 对话` tab
- tab 内容渲染 `ChatContent`（与 `ChatPanel` 共享同一 store + hook）
- 展开后头部右上角变为 `⤡ 收起` 按钮
```
┌──────────┬──────────────────────────────────────┐
│ 任务实例  │ [节点1] [节点2] [💬 AI 对话]  ⤡收起  │
│ (280px)  ├──────────────────────────────────────┤
│          │                                       │
│          │       ChatContent（占满中栏）          │
│          │       Bubble.List + Sender            │
│          │                                       │
└──────────┴──────────────────────────────────────┘
```

### 3.3 状态管理

- `expanded` 状态保存在 `AIAssistant` 组件本地 `useState`（**不**进 zustand，理由：纯 UI 态、不跨页面持久）
- 通过 props 传给 `ChatPanel`（紧凑态）和 `ChatContent`（展开态）
- 切换展开：`setExpanded(true/false)`，初始 `false`

## 4. 数据流

### 4.1 现有链路（不动）
```
用户输入 → handleSend
  → useChatStore.addMessage (user)
  → useChatStore.startAssistantMessage (空 assistant)
  → chatStream({ nodeExecutionId, messages, onDelta, onDone, onError })
  → fetch POST /api/v1/chat/stream (SSE)
  → FastAPI 代理 → Java AgentScope
  → 流式回调 onDelta → useChatStore.appendDelta
  → onDone → useChatStore.finalizeMessage
```

### 4.2 新增 hook：`useChatBinding()`

封装"取当前节点 + 锁状态 + 发送逻辑"，让 `ChatPanel` 和 `ChatContent` 共用：

```js
// src/pages/ai-assistant/hooks/useChatBinding.js
function useChatBinding() {
  const { activeNodeExecutionId, isStreaming, error,
          addMessage, startAssistantMessage, appendDelta,
          finalizeMessage, setError, clearMessages } = useChatStore()
  const { currentNode } = useNodeState()  // 来自 task store

  const isNodeReady = currentNode?.status === 'completed'
  const inputDisabled = !isNodeReady || isStreaming

  const handleSend = (text) => {
    if (!text.trim() || inputDisabled || !activeNodeExecutionId) return
    addMessage({ type: 'user', content: text })
    startAssistantMessage()
    const history = useChatStore.getState().messages
      .filter(m => m.type === 'user' || (m.type === 'assistant' && !m.streaming))
      .map(m => ({ role: m.type === 'user' ? 'user' : 'assistant', content: m.content }))
    return chatStream({
      nodeExecutionId: activeNodeExecutionId,
      messages: history,
      onDelta: appendDelta,
      onDone: finalizeMessage,
      onError: (err) => { finalizeMessage(); setError(err) },
    })
  }

  return { isNodeReady, inputDisabled, handleSend, error, isStreaming,
           activeNodeExecutionId, clearMessages }
}
```

### 4.3 Bubble.List 渲染

```jsx
<Bubble.List
  items={messages.map(m => ({
    key: m.id,
    role: m.type,
    content: m.content,
    loading: m.streaming,
    // typing 效果由 Bubble 内置，无需手写
  }))}
/>
```

### 4.4 Markdown 渲染

`Bubble.Content` 内部包裹 ReactMarkdown：
```jsx
<Bubble.Content>
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    rehypePlugins={[rehypeHighlight]}
    components={{
      table: ({node, ...props}) => <table style={{borderCollapse:'collapse',width:'100%'}} {...props} />,
      a: ({node, ...props}) => <a target="_blank" rel="noopener" {...props} />,
    }}
  >
    {message.content}
  </ReactMarkdown>
</Bubble.Content>
```

流式时（`m.streaming === true`）继续用 markdown 渲染；如果中途出现错位，流结束后自愈。

## 5. 文件改动清单

| 文件 | 操作 | 关键改动 |
|---|---|---|
| `frontend-react/package.json` | 修改 | `+@ant-design/x` `+react-markdown` `+remark-gfm` `+rehype-highlight` `+highlight.js` |
| `frontend-react/src/api/chat.js` | **不动** | 函数签名兼容 |
| `frontend-react/src/store/chat.js` | **不动** | 已含 streamingMessageId 等流式状态 |
| `frontend-react/src/pages/ai-assistant/ChatPanel.jsx` | **重写** | 用 Bubble.List + Sender + Markdown 包装 |
| `frontend-react/src/pages/ai-assistant/ChatContent.jsx` | **新建** | 展开态全宽版本，复用 `useChatBinding` |
| `frontend-react/src/pages/ai-assistant/AIAssistant.jsx` | **改** | 加 `expanded` 本地态 + 把 `💬 AI 对话` tab 注入到中栏 |
| `frontend-react/src/pages/ai-assistant/hooks/useChatBinding.js` | **新建** | 共享 hook |
| `frontend-react/src/pages/ai-assistant/hooks/useNodeState.js` | **新建** | 从 `useTaskStore` 提取当前节点计算 |
| `frontend-react/src/pages/ai-assistant/ChatMessage.jsx` | **删除** | 被 Bubble 取代 |
| `frontend-react/src/components/markdown/Markdown.jsx` | **新建**（可选） | 抽出 ReactMarkdown 包装，便于复用 |

## 6. 风险与边界

### 6.1 不做（YAGNI）
- ❌ Prompts 组件
- ❌ Conversations 组件
- ❌ 文件上传 / 附件
- ❌ localStorage 持久化
- ❌ 流式 markdown 错位优化
- ❌ 后端 / API / Java AgentScope 改动

### 6.2 已知风险
- **包体积**：方案 2 起步约 +350KB。`npm run build` 后看 `dist/assets/*.js` 实际数字
- **样式冲突**：@ant-design/x 与 antd v5 共享 design token，但 `Bubble` 内部样式可能与现有紫色主题（`#5C7CFF`）不一致，需要 `theme` prop 调色
- **Bubble 流式打字效果**：`loading: true` 时 Bubble 内部有动画，与"节点未完成锁定"叠加时容易让用户误以为可输入，需 `inputDisabled` 同步 disable
- **代码高亮 CSS**：highlight.js 需要导入 `highlight.js/styles/github.css` 之类，否则高亮 class 不生效

### 6.3 验证方式
1. 视觉冒烟：登录 → 选工作流 → 执行节点 → 右栏 AI 对话输入 → 验证 Bubble 渲染
2. 展开测试：点击 `⤢ 展开` → 右栏消失 → 中栏出现 `💬 AI 对话` tab → 切换 tab
3. Markdown 测试：让 AI 输出含代码块、表格、列表的回复
4. 锁定测试：节点未 completed 时，输入框 disable + 锁定文案
5. 切节点测试：切换到另一节点 → 消息清空 + 输入框重新锁定
6. 体积测试：`npm run build` → 检查 dist 大小

## 7. 关键参考

- @ant-design/x 官方文档：https://x.ant.design/
- Bubble 组件：https://x.ant.design/components/bubble
- Sender 组件：https://x.ant.design/components/sender
- 钉钉 AI 助理参考实现：内部已对齐交互范式
- 现有 ChatPanel 实现：`frontend-react/src/pages/ai-assistant/ChatPanel.jsx`
- 现有 chatStream 封装：`frontend-react/src/api/chat.js`
- 现有 useChatStore：`frontend-react/src/store/chat.js`

## 8. 实施顺序（建议）

1. 安装依赖（`npm i @ant-design/x react-markdown remark-gfm rehype-highlight highlight.js`）
2. 写 `useChatBinding` + `useNodeState` hook
3. 重写 `ChatPanel.jsx`（先保证默认态工作）
4. 新建 `ChatContent.jsx`（展开态全宽版本）
5. 改 `AIAssistant.jsx`（加 expanded 态 + 注入 tab）
6. 删 `ChatMessage.jsx`
7. 跑 `npm run build` 看体积
8. 手动冒烟

每步独立可测，不阻塞下游。
