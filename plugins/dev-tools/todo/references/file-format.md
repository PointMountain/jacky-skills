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

`durable_basis` 只能与 `status: canDurable` 同时存在。

## Reference

- `references/...` 指向当前任务根目录里的本地 Markdown。
- `OBA-xxxxxxxx` 指向 Obsidian 知识文章。
- POC 不提供 `REF-` ID。

## 归档

归档保留原 Task ID 和文件内容，只把文件从 `tasks/` 移动到 `archive/`。
