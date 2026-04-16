---
name: ob-topic
description: "对话中快速收藏通用知识点到 Obsidian 知识库。触发词：/save、/collect、收藏、记录一下、ob-topic。"
---

<role>Obsidian 知识点快速收藏助手。从对话上下文中提取知识点，精炼概括后保存到 Obsidian wiki 主题目录。</role>
<purpose>两种模式：1) 手动触发：用户说触发词 + 知识点描述，立即收藏；2) 自动提醒：对话中识别到通用知识点时主动询问是否收藏。</purpose>
<trigger>

```text
触发词：
- /save / /collect / 收藏 / 记录一下 / ob-topic
- 把这个收藏 / 保存到知识库 / 记录一下这个知识点

示例：
- "/save React Server Components 的流式渲染原理"
- "收藏一下：Tauri Sidecar 的启动流程"
- "记录一下：Node.js SEA 编译的局限性"
```

</trigger>

# Obsidian 知识点收藏 (ob-topic)

## 配置检查

**执行前必读**：本 skill 需要使用 Obsidian 仓库路径。

1. 首先检查全局 CLAUDE.md 中是否定义了 `OBSIDIAN_REPO` 配置变量
2. 如果未定义，使用 AskUserQuestion 询问用户
3. 将用户提供的路径保存为 `$OBSIDIAN_REPO` 变量供后续使用

## 收藏流程

### 1. 提取内容

- 从用户触发词描述中提取知识点
- 检查当前对话上下文是否有相关讨论内容，有则一并提取
- 精炼概括，核心内容 ≤ 500 字

### 2. 主题分类

根据知识点关键词自动匹配主题目录：

| 主题 | 目录 | 关键词 |
|------|------|--------|
| AI 技术 | `wiki/ai/` | AI, LLM, GPT, transformer, 机器学习, 深度学习, RAG, agent |
| Claude 生态 | `wiki/claude/` | Claude, Claude Code, Skills, MCP, hooks, Subagents, Tauri |
| 开发工具 | `wiki/dev-tools/` | VSCode, IDE, 编辑器, CLI, 终端, Git, Zed |
| 前端开发 | `wiki/front-end/` | React, JavaScript, TypeScript, CSS, 前端, Next.js, Vue |
| 时事分析 | `wiki/current-affairs/` | 经济, 政治, 国际, 金融, 投资, 时事 |
| 职业发展 | `wiki/career/` | 职级, 面试, 求职, 职业规划, 大厂 |
| Obsidian | `wiki/obsidian/` | Obsidian, 知识管理, 笔记, 双链 |
| 综合 | `wiki/synthesis/` | 兜底（无明确匹配时） |

匹配后直接使用，不询问用户确认（全自动模式）。

### 3. 写入笔记

文件名：`{YYYY-MM-DD}-{slug}.md`，slug 用英文短横线连接。

```markdown
---
tags: [{主题标签}, {关键词}]
type: topic
created_at: {YYYY-MM-DD}
source: conversation
---

# {知识点标题}

> 从对话中整理 · {主题分类}

## 核心内容

{精炼概括，≤ 500 字}

## 关键要点

1. {要点一}
2. {要点二}
3. {要点三}
```

### 4. 更新索引

- 更新 `wiki/{theme}/index.md`：追加新条目到对应分类下
- 新主题目录时创建 `wiki/{theme}/index.md`
- 新主题分类时更新 `wiki/index.md` 全局索引

### 5. 返回结果

简短返回：文件路径、主题分类、标题。

## 与其他 skill 的区别

| 维度 | ob-topic | ob-collect | ob-project-log |
|------|----------|------------|----------------|
| 来源 | 对话上下文 | 外部 URL/视频/PDF | 对话上下文（项目相关） |
| 绑定 | 不绑定项目 | 不绑定项目 | 绑定 git 项目 |
| 触发 | 手动 + 自动提醒 | 手动 | Stop hook 自动 |
| 目标 | wiki/{theme}/ | raw/ → wiki/{theme}/ | wiki/projects/{project}/ |
