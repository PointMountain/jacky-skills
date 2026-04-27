# 文件格式说明

## 概述

TODO v2 使用三种文件：`todo.md`（主文件）、`todo-N.md`（批次文件）、`cp-xxx.md`（checkpoint 快照）。均存储在项目根目录。

## todo.md（主文件）

用户的操作入口。两个分区。

```markdown
# TODO

最后更新: 2026-04-27

## 📋 Todo
- [ ] 完成 CDP Proxy 笔记的 WebSocket 管理部分 @context:cp-20260427-143000.md
  已完成 HTTP API 部分，还差超时处理和重连逻辑

- [ ] 重构 API 错误处理逻辑 @context:cp-20260427-150000.md

## 💡 Ideas
- [ ] 用 WebSocket 实现实时通知
- [ ] 考虑给 demo 加 fallback 处理
```

### 两个分区

| 分区 | 标题 | 用途 |
|------|------|------|
| 📋 Todo | `## 📋 Todo` | 待办事项，每条可带 `@context:` 引用 checkpoint |
| 💡 Ideas | `## 💡 Ideas` | 未来想法，纯文本，无 checkpoint |

### 条目格式

```
- [ ] 描述文字 @context:cp-{timestamp}.md
  可选续行补充细节
```

- `- [ ]` 未完成
- `@context:` 引用 checkpoint 文件路径（相对项目根目录）
- 续行缩进 2 空格，补充上下文

## todo-N.md（批次文件）

resolve 时自动生成，存储提取出的条目。

```markdown
---
source: todo.md
created: "2026-04-27"
status: pending
---

## 📋 Todo
- [ ] 完成 CDP Proxy 笔记 @context:cp-20260427-143000.md
  已完成 HTTP API 部分，还差超时处理

## 💡 Ideas
- [ ] 用 WebSocket 实现实时通知
```

### Frontmatter 字段

| 字段 | 说明 | 值 |
|------|------|-----|
| source | 来源文件 | `todo.md` |
| created | 创建日期 | `YYYY-MM-DD` |
| status | 处理状态 | `pending` → `done` |

## cp-xxx.md（checkpoint 文件）

add 时自动生成，存储 add 那一刻的会话上下文快照。存储在项目根目录。

```markdown
---
type: checkpoint
created: "2026-04-27T14:30:00"
---

## 当前任务
写 06-cdp-proxy-code-walkthrough.md 笔记

## 进度
- 已完成 HTTP API 端点对照表
- 正在写 WebSocket 连接管理部分
- 代码行 120-180 已分析完毕

## 关键决策
- 选择逐行精读而非概览，因为代码细节多且互相引用
- Pending Map 模式是核心机制，需要详细展开

## 下一步
1. 补充 WebSocket 超时处理逻辑（代码行 145-160）
2. 添加重连机制分析
3. 补充 HTTP API 端点对照表

## 正在编辑的文件
- explorer/06-cdp-proxy-code-walkthrough.md
```

### Checkpoint 内容结构

| 区域 | 说明 | 重要性 |
|------|------|--------|
| 当前任务 | 一句话描述在做什么 | 必须 |
| 进度 | 已完成 + 正在进行 | 必须 |
| 关键决策 | 为什么选 A 不选 B | 必须 |
| 下一步 | 具体操作列表 | 必须 |
| 正在编辑的文件 | 当前工作集文件路径 | 必须 |

## 文件命名规则

| 文件 | 命名 | 示例 |
|------|------|------|
| 主文件 | `todo.md` | 固定名称 |
| 批次文件 | `todo-{N}.md` | `todo-1.md`, `todo-2.md` |
| Checkpoint | `cp-{YYYYMMDD-HHmmss}.md` | `cp-20260427-143000.md` |

## 生命周期

```
add 阶段:
  todo.md + cp-xxx.md 创建

resolve 阶段:
  todo.md → todo-N.md（提取）
  todo.md 清空（可继续新增）
  cp-xxx.md 被 Claude 读取

完成阶段:
  todo-N.md → status: done
  cp-xxx.md → 删除（任务完成后清理）
```
