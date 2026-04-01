# 关键架构决策

> 从 Monkey 项目蒸馏提炼的关键设计决策，每个决策都有明确的"为什么"。

---

## 1. CSP 绕过 — 怎么在别人的页面里执行代码

### 问题

大部分网站设置了 Content-Security-Policy（CSP），会拦截 `<script>` 标签注入和 `eval()` 调用。

### 解决方案

`chrome.scripting.executeScript` 的 `world: 'MAIN'` 参数不受 CSP 限制，代码直接运行在页面的主世界。

配合间接 eval `(0, eval)(src)` 确保代码在全局作用域而非闭包中执行：

```typescript
await chrome.scripting.executeScript({
  target: { tabId },
  world: 'MAIN',
  func: (src: string) => (0, eval)(src),
  args: [code],
})
```

### 为什么不用其他方案

| 方案 | 问题 |
|------|------|
| `<script>` 标签注入 | 被 CSP 拦截 |
| 直接 `eval()` | 在闭包作用域，访问不到页面全局变量 |
| `world: 'ISOLATED'`（默认） | 在扩展隔离世界，访问不到页面 JS 上下文 |

---

## 2. MV3 SW 超时 — 为什么 AI 调用不能放 Service Worker

### 问题

Manifest V3 的 Service Worker 有 **30 秒空闲超时**。AI 流式调用可能持续数十秒，如果在 SW 中发起请求，SW 可能被浏览器杀掉导致流中断。

### 解决方案

AI 调用逻辑放在 **SidePanel**（持久页面，不受超时限制），SW 只做消息路由。

```
SidePanel（持久页面）          Service Worker（可能被杀）
├── AI 流式调用 ← 放这里 ✓    ├── Tab 状态监听 ← 放这里 ✓
├── useChat Hook              ├── 消息路由转发
├── DOM 快照管理              └── 生命周期管理
└── 代码预览渲染
```

---

## 3. AI 幻觉选择器 — 怎么让 AI 不编造 class 名

### 问题

AI 不知道用户正在看什么页面，会凭空编造 CSS 选择器（如 `document.querySelector('.ad-container')`，但实际页面可能用的是 `.sidebar-ad`）。

### 解决方案

每次调用 AI 前，注入**真实的 DOM 快照**到 System Prompt，包含页面的实际 ID、交互元素、标题结构，让 AI 基于真实数据写选择器。

```
用户输入 "隐藏广告"
    ↓
提取 DOM 快照：
  ID 列表: #sidebar, #content, #ad-banner
  交互元素: <div#ad-banner class="promo">"广告"</div>
  标题: <h1>"文章标题"</h1>
    ↓
System Prompt 包含上面的真实数据
    ↓
AI 生成: document.querySelector('#ad-banner').style.display = 'none'
         ↑ 基于真实 ID，不是编造的
```

---

## 4. Tab 定位 — SidePanel 怎么知道用户在看哪个页面

### 问题

SidePanel 不属于 `chrome.tabs` 体系，`currentWindow` 查询不可靠（可能查到侧边栏自己的窗口）。

### 解决方案

使用 `lastFocusedWindow` 获取用户正在浏览的 Tab：

```typescript
// ✓ 正确
const [tab] = await chrome.tabs.query({
  active: true,
  lastFocusedWindow: true,
})

// ✗ 不可靠
const [tab] = await chrome.tabs.query({
  active: true,
  currentWindow: true,
})
```

另外，Tab ID 应在用户点击操作时就捕获，异步操作后可能变化。

---

## 5. 多服务商 SSE 差异 — 为什么用 Vercel AI SDK

### 问题

不同 AI 服务商的流式响应格式完全不同：

| 服务商 | SSE 数据格式 | 流式字段路径 |
|--------|-------------|-------------|
| OpenAI | `data: {"choices":[{"delta":{"content":"..."}}]}` | `choices[0].delta.content` |
| Claude | `data: {"type":"content_block_delta","delta":{"text":"..."}}` | `delta.text` |
| Google | `data: {"candidates":[{"content":{"parts":[{"text":"..."}]}}]}` | `candidates[0].content.parts[0].text` |

### 解决方案

Vercel AI SDK 在底层统一了这些差异，上层只用 `useChat()` 一个 hook：

```typescript
import { useChat } from 'ai/react'

const { messages, input, handleSubmit } = useChat({
  api: '/api/chat',
})
```

SDK 自动处理各服务商的 SSE 格式解析，无需手写。
