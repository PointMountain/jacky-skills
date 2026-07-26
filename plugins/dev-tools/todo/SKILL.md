---
name: todo
description: "通过 Node CLI 管理结构化 Markdown 任务：默认全局，可显式使用项目级；支持状态、Durable 准备度、上下文章节、统计、索引、完整性检查和本地 Web 看板。"
---

# Todo

Todo 是自然语言适配层。任务数据保存在 `.agent-tasks/tasks/*.md`，确定性读写全部交给本 Skill 自带的 Node CLI。

## 硬约束

1. **禁止直接编辑任务文件、YAML、`index.md` 或归档目录。**
2. 新增、修改、查询、移动、归档和正文更新都必须调用 CLI。
3. 未明确指定范围时始终使用全局 `~/.agent-tasks/`，即使当前位于 Git 仓库。
4. 只有用户明确说“当前项目”或提供项目路径时才使用项目级目录。
5. 用户只要求记录、查看或修改任务时，不得执行任务本身。
6. `list` 只查询，不调研、不实现、不创建额外上下文文件。
7. `index.md` 是生成视图，`tasks/*.md` 是唯一数据源。

## CLI 调用

Skill 内调用：

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" <command> [options]
```

如果宿主没有注入 `CLAUDE_SKILL_DIR`，使用当前 `SKILL.md` 所在目录的绝对路径。不要假设系统已经存在全局 `todo` 命令。

人工安装全局命令、依赖检查和 Web 启动方法见 [`references/setup-guide.md`](references/setup-guide.md)。

## 作用域

| 用户表达 | CLI 参数 | 存储位置 |
|---|---|---|
| “添加待办”“全局待办”或未说明 | 无 | `~/.agent-tasks/` |
| “当前项目待办” | `--current-project` | `{当前 git-root}/.agent-tasks/` |
| “某项目待办”并提供路径 | `--project <path>` | `{指定 git-root}/.agent-tasks/` |

明确项目无法解析时报告错误，不静默写入全局。

## 意图映射

### 新增任务

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" add "<标题>" \
  --status idea \
  --json
```

添加当前项目任务时追加 `--current-project`。添加指定项目任务时追加 `--project <git-root>`。

创建后向用户返回：

- `task_id`
- 标题和状态
- 实际文件路径

### 查询任务

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" list
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" list --status canDurable
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" show <TSK-ID>
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" stats --format yaml
```

### 修改 YAML

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" set <TSK-ID> \
  --project-name "<项目名>" \
  --workspace "<路径>"
```

Reference 使用逗号分隔：

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" set <TSK-ID> \
  --references "references/设计.md,OBA-w8s3k7p2"
```

### 修改 Markdown 章节

Skill 更新上下文时使用标准输入，避免 shell 引号破坏正文：

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" section set <TSK-ID> "目标"
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" section append <TSK-ID> "关键决定"
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" section show <TSK-ID> "当前进度"
```

将正文通过标准输入传入。`set` 替换指定二级章节，`append` 保留旧内容后追加；两者不得影响其他章节。

### 修改状态

状态流：

```text
idea → shaping → canDurable → doing → waitingHuman → done
```

状态可以按真实进展前后调整，不强制线性迁移。

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" status <TSK-ID> shaping
```

进入 `canDurable` 必须记录判断依据：

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" status <TSK-ID> canDurable \
  --basis human-confirmed
```

合法依据：

- `poc-passed`
- `human-confirmed`
- `ai-assessed`

## Durable 判断

`canDurable` 表示上下文已经足够，让 AI 可以持续执行长程任务，并且明确：

- 目标与产物
- 完成标准
- 执行路线
- 所需能力与前置检查
- 人工介入点

当内容基本完整时：

1. 建议用户先跑一次最小闭环 POC，并询问现在是否有时间参与。
2. POC 通过时使用 `poc-passed`。
3. 用户不跑 POC但明确确认时使用 `human-confirmed`。
4. 用户不在场时允许 AI 自主评估；信息充分则使用 `ai-assessed`，并向用户标明可靠性较低。
5. AI 判断信息不足时保持 `shaping`，列出缺失内容。

POC 是推荐路径，不是硬门槛。

## 移动、归档与检查

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" move <TSK-ID> \
  --to-current-project

node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" delete <TSK-ID> --yes
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" index
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" doctor
```

`delete` 实际移动到 `archive/`，不永久删除。

## Web 看板

当用户要求打开或启动 Todo 看板时：

```bash
node "${CLAUDE_SKILL_DIR}/bin/todo.mjs" web
```

项目级看板显式追加作用域参数。Web 只监听 `127.0.0.1`，与 CLI 读取同一份 Markdown 数据。

## 渐进式资料

- 需要完整命令参数时读 [`references/commands.md`](references/commands.md)。
- 需要任务 YAML、正文和目录格式时读 [`references/file-format.md`](references/file-format.md)。
- 需要安装、依赖或 Web 启动排查时读 [`references/setup-guide.md`](references/setup-guide.md)。
- 需要产品范围和验收条件时读 [`references/poc-spec.md`](references/poc-spec.md)。

## 错误处理

1. CLI 返回非零退出码时报告真实错误，不绕过 CLI 直接改文件。
2. Task ID 必须是 `TSK-xxxxxxxx`；标题不能代替 ID。
3. `canDurable` 缺少合法依据时不得强行写入。
4. `doctor` 报告非法 YAML、重复 ID、文件名不一致或 Reference 失效时，先修复数据再继续。
5. 旧格式只通过 `migrate` 尽力转换；迁移失败不阻塞新系统使用。
