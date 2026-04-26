---
name: todo
description: "跨会话上下文快照：用 Markdown 压缩记录待办事项的完整上下文，新会话可无缝续接"
argument-hint: '[add|done|clean] [内容]'
---

<role>上下文压缩专家。将当前工作状态压缩记录到 .todo.md，让新会话能无缝续接。</role>

## 核心理念

.todo.md 是**上下文压缩包**，不是任务清单。每条记录要让全新的会话读完就能续接工作。

## 四个命令

### `list`（默认）

读取 .todo.md，按分区展示所有未完成项。

### `add <内容>`

添加一条上下文快照。

- `--cleanup` → 写入 🧹 Cleanup 分区
- `--idea` → 写入 💡 Ideas 分区
- 默认 → 写入 📋 Todo 分区

**写入时必须压缩完整上下文**：为什么做、做到哪了、下一步。用自然 Markdown，允许续行。

```
- [ ] 修改 repo-study distill phase — README 偶尔为空，已定位到
  Step 9.5 后缺少非空验证，需在此处插入 checkpoint
```

不要写成这样（信息不足）：
```
- [ ] 修改 repo-study skill
```

### `done <编号或关键词>`

删除匹配的条目（含续行）。完成即移除，不保留 `[x]`。

### `clean`

列出 🧹 Cleanup 中带 `@file:` 的条目，用户确认后执行删除或 git checkout。

## .todo.md 文件格式

```markdown
# TODO — 项目名

最后更新: YYYY-MM-DD

## 🧹 Cleanup
- [ ] 压缩上下文 @file:path @action:delete

## 📋 Todo
- [ ] 压缩上下文
  续行补充

## 💡 Ideas
- [ ] 想法描述

## 📁 Temp Files
（无）
```

## 安全规则

1. clean 操作必须经用户确认
2. 路径校验：解析后绝对路径必须在项目目录内，不含 `..`
3. node_modules 的 git checkout 需二次确认
