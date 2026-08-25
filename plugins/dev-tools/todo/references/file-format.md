# Todo 文件格式

## 目录

```text
.agent-tasks/
├── index.md
├── tasks/
│   └── TSK-k7m3x9p2.md
├── references/
│   ├── index.md
│   └── durable-task-checklist.md
└── archive/
```

`tasks/*.md` 是唯一数据源；两个 `index.md` 都由 CLI 自动生成。

## 任务

```markdown
---
task_id: TSK-k7m3x9p2
title: 改造 Todo Skill
status: canDurable
project: jacky-skills
workspace: /path/to/repo
created: 2026-07-26
updated: 2026-07-26
references:
  - references/durable-task-checklist.md
  - OBA-w8s3k7p2
durable_basis: human-confirmed
---

# 改造 Todo Skill

## 目标

形成一个可以由 CLI、Skill 和 Web 共用的 Markdown 任务系统。

## 明确产物

- Node CLI
- 本地 Web 看板

## 完成标准

- 自动化测试通过
- CLI 与 Web 可以修改同一任务

## 最终验收

- 最终产物：本地 Web 看板
- 回归入口：http://127.0.0.1:4173
- 用户动作：新增任务并修改状态，确认 CLI 可以读取同一结果
- 自动验证：CLI、Store 和 Web 测试全部通过

## 执行记录

### Skills 与工具
- `todo`：维护任务状态与恢复上下文

### 验证
- `npm test`：通过
```

## 字段

必填：

- `task_id`
- `title`
- `status`
- `created`
- `updated`

可选：

- `project`
- `workspace`
- `references`
- `durable_basis`

`durable_basis` 表示任务已经通过 Durable 准备度判断：

- `canDurable` 必须设置。
- 进入 `doing`、`waitingHuman` 或 `done` 后继续保留，作为任务曾具备无人值守条件的证据。
- 退回 `idea` 或 `shaping` 时自动移除。
- 普通短任务可以直接进入 `doing` / `done`，此时不要求设置。

`## 最终验收` 与 `## 执行记录` 是推荐的 Durable 正文章节，不新增 YAML 工作流字段：

- `最终验收` 定义最终回归入口，不罗列中间文档检查点。
- `执行记录` 保存 Skills/工具、关键决策、问题、验证和提效机会。
- 中间文档只进入 `references`，不自动触发 `waitingHuman`。

## Reference

- `references/...` 指向当前任务根目录里的本地 Markdown。
- `OBA-xxxxxxxx` 指向 Obsidian 知识文章。
- POC 不提供 `REF-` ID。

## 归档

归档保留原 Task ID 和文件内容，只把文件从 `tasks/` 移动到 `archive/`。
