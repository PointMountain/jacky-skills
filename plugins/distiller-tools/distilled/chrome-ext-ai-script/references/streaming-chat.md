# 流式对话实现

> Vercel AI SDK 统一处理各服务商的流式响应差异
> Prompt 构建注入真实 DOM 快照，防止 AI 编造选择器

---

## Vercel AI SDK 用法

### 对话 Hook 封装

```typescript
// src/sidepanel/hooks/useAIChat.ts
import { useChat } from 'ai/react'

export function useAIChat() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: '/api/chat',

    // 自定义 body，注入 DOM 快照
    body: {
      domSnapshot: getCurrentSnapshot(),
    },

    // 流式渲染回调
    onFinish(message) {
      // 检测到代码块，自动展示预览
      if (message.content.includes('==UserScript==')) {
        extractAndPreviewScript(message.content)
      }
    },
  })

  return { messages, input, handleInputChange, handleSubmit, isLoading }
}
```

### 支持图片输入

```typescript
async function handleImageUpload(file: File) {
  const base64 = await convertFileToBase64(file)
  // Vercel AI SDK 支持多模态消息
  append({
    role: 'user',
    content: [
      { type: 'text', text: '看看这个页面，帮我写个脚本' },
      { type: 'image', image: base64 },
    ],
  })
}
```

---

## System Prompt 构建

> 来源：Monkey `sidepanel.js:403-438`
> 核心设计：注入真实 DOM 快照，让 AI 基于真实数据写选择器

```typescript
// lib/ai/prompt-builder.ts

export function buildSystemPrompt(
  snapshot: DOMSnapshot | null,
  pageContent?: string
): string {
  const selectorSection = snapshot
    ? formatSelectorInfo(snapshot)
    : '（无法获取页面结构）'

  const contentSection = pageContent
    ? `\n\n--- 页面正文内容 ---\n${pageContent.slice(0, 3000)}`
    : ''

  return `你是一个 Tampermonkey 脚本生成器。用户描述他们想在网页上做什么，你生成对应的脚本。

--- 当前页面真实 DOM 结构 ---
${selectorSection}
${contentSection}

重要规则：
- 使用上面出现的真实 ID、class 名、元素结构来写选择器
- 不要编造选择器，只使用上面 DOM 结构中出现的
- 只用原生 JS，不依赖 jQuery 或外部库
- 代码注释用中文

请用以下格式回复：
\`\`\`userscript
// ==UserScript==
// @name        脚本名称
// @match       https://example.com/*
// @run-at      document-end
// ==/UserScript==
(function() {
  'use strict';
  // 代码
})();
\`\`\``
}

function formatSelectorInfo(snap: DOMSnapshot): string {
  return [
    `页面标题: ${snap.title}`,
    `URL: ${snap.url}`,
    '',
    `页面 ID 列表: ${snap.ids.join(', ') || '无'}`,
    '',
    '交互元素:',
    ...snap.interactive.map(s => '  ' + s),
    '',
    '标题与地标:',
    ...snap.landmarks.map(s => '  ' + s),
    '',
    '链接:',
    ...snap.links.slice(0, 12).map(s => '  ' + s),
  ].join('\n')
}
```

---

## 完整数据流

```
用户在 SidePanel 对话框输入
    ↓
① SidePanel 请求 DOM 快照（Content Script 执行提取）
    ↓
② 构建 System Prompt（DOM 快照 + Turndown 页面内容）
    ↓
③ 调用 AI API（Vercel AI SDK → 流式输出到对话框）
    ↓
④ AI 回复中检测到 ==UserScript== 代码块
    ↓
⑤ 展示代码预览 + "在页面中执行"按钮
    ↓
⑥ 用户点击执行 → world:MAIN 注入到目标页面
    ↓
⑦ 页面内直接看到效果
```
