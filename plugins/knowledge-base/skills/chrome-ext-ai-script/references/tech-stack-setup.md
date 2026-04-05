# 技术栈选型与项目初始化

> 来源：从 Monkey 蒸馏，结合现代前端工具链

---

## 技术栈总览

| 维度 | 选择 | 备选 | 选择理由 |
|------|------|------|---------|
| 扩展框架 | **Plasmo** | CRXJS / 原生 | HMR + 自动 manifest + React+TS 开箱即用 |
| AI SDK | **Vercel AI SDK** | LangChain / 自写 fetch | useChat hook 直连 React，自动兼容各服务商 SSE |
| 页面感知 | **Turndown + Readability** | 自写 DOM 遍历 | 轻量纯浏览器端，HTML→Markdown 成熟 |
| 样式 | **Tailwind CSS** | CSS Modules / 设计令牌 | 原子化，快速迭代，不需要额外文件 |
| 包管理 | **pnpm** | npm / yarn | 速度快、磁盘小 |

---

## 为什么选 Plasmo

Plasmo 自动识别以下文件约定：

| 文件路径 | Plasmo 自动识别为 |
|----------|-----------------|
| `src/background/index.ts` | Service Worker |
| `src/contents/dom-snapshot.ts` | Content Script（注入所有页面） |
| `src/sidepanel/index.tsx` | Side Panel 页面 |
| `src/options/index.tsx` | Options 设置页 |
| `src/assets/icon.png` | 扩展图标 |

SidePanel 声明示例：

```tsx
// src/sidepanel/index.tsx
export default function SidePanel() {
  return <ChatView />
}
// Plasmo 会自动在 manifest.json 中生成 side_panel 配置
```

---

## 为什么选 Vercel AI SDK

不同 AI 服务商的 SSE 格式差异：

| 服务商 | SSE 数据格式 | 流式字段路径 |
|--------|-------------|-------------|
| OpenAI | `data: {"choices":[{"delta":{"content":"..."}}]}` | `choices[0].delta.content` |
| Claude | `data: {"type":"content_block_delta","delta":{"text":"..."}}` | `delta.text` |
| Google | `data: {"candidates":[{"content":{"parts":[{"text":"..."}]}}]}` | `candidates[0].content.parts[0].text` |

自写 fetch 需要为每个服务商写一套解析逻辑。Vercel AI SDK 在底层统一了这些差异。

---

## 初始化命令

```bash
# 1. 创建项目
pnpm create plasmo script-copilot
cd script-copilot

# 2. 安装核心依赖
pnpm add ai @ai-sdk/openai @ai-sdk/anthropic @ai-sdk/google
pnpm add turndown @mozilla/readability
pnpm add -D @types/turndown

# 3. 安装 Tailwind CSS（可选，推荐）
pnpm add tailwindcss @tailwindcss/vite

# 4. 启动开发
pnpm dev
# 打开 chrome://extensions → 开发者模式 → 加载 dist/ 目录

# 5. 构建
pnpm build
```

---

## 与 Monkey 的对比

| 维度 | Monkey（原项目） | 新项目 |
|------|-----------------|--------|
| 框架 | 原生 JS，零依赖 | **Plasmo**（React + TS + HMR） |
| UI 模式 | 生成→确认→执行（单向流程） | **对话框式交互**（多轮对话） |
| AI 输入 | 纯文本 | 文本 + **图片** + 对话上下文 |
| AI 服务商 | OpenAI / Claude / 自定义 | **插件化注册**，可无限扩展 |
| 输出方式 | 保存后手动执行 | **页面内直接展示 + 执行** |
| 脚本管理 | 内置 CRUD 列表 | 去除（或后期按需加回） |
| 工程复杂度 | ~1600 行，4 个 JS 文件 | Plasmo 组件化，模块更清晰 |
