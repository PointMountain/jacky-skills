# Todo CLI 命令

> 人工使用全局 `todo` 命令；Agent 使用 `node <skill-dir>/bin/todo.mjs`。所有命令默认操作全局目录。

## 作用域参数

| 参数 | 作用 |
|---|---|
| 无 | `~/.agent-tasks/` |
| `--current-project` | 当前 Git 根目录下的 `.agent-tasks/` |
| `--project <path>` | 指定 Git 根目录下的 `.agent-tasks/` |
| `--root <path>` | 直接指定任务根目录，主要用于测试 |

## 命令速查

```bash
# 新增
todo add "任务标题"
todo add "任务标题" --current-project
todo add "任务标题" --status canDurable --basis human-confirmed

# 查询
todo list
todo list --status shaping
todo show TSK-k7m3x9p2
todo stats --format yaml

# 修改字段
todo set TSK-k7m3x9p2 --title "新标题"
todo set TSK-k7m3x9p2 --project-name jacky-skills
todo set TSK-k7m3x9p2 --workspace /path/to/repo
todo set TSK-k7m3x9p2 --references "references/设计.md,OBA-w8s3k7p2"

# 状态
todo status TSK-k7m3x9p2 shaping
todo status TSK-k7m3x9p2 canDurable --basis ai-assessed

# 正文
todo section show TSK-k7m3x9p2 "目标"
todo section set TSK-k7m3x9p2 "目标" --content "形成可运行 POC"
printf '%s' "补充决定" | todo section append TSK-k7m3x9p2 "关键决定"

# 维护
todo index
todo doctor
todo delete TSK-k7m3x9p2
todo move TSK-k7m3x9p2 --to-current-project

# Web
todo web
todo web --current-project

# 旧格式
todo migrate
todo migrate --apply
```

## 输出格式

`add`、`list`、`show`、`set`、`status` 和 `doctor` 支持 `--json` 时，脚本应优先使用 JSON。

`stats` 支持：

```text
table
json
yaml
```

## CUI

人工运行时，以下缺参场景进入交互式输入：

- `todo add`
- `todo status <TSK-ID>`
- `todo delete <TSK-ID>` 未传 `--yes`

Agent 必须补齐参数，避免停在交互输入。
