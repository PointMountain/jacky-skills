# Todo POC：Markdown 任务中心

> 将现有 `todo.md + @context` 方案改造成由 Node CLI 驱动、可被 Agent 和本地 Web 看板共同操作的结构化 Markdown 任务系统。

## 一、目标

Todo POC 面向两类使用者：

1. 人工用户：通过交互式终端或本地 Web 看板快速记录、查看和维护任务。
2. Agent：通过非交互 CLI 稳定地新增任务、修改 YAML、更新正文和读取可执行任务。

成功标准是：任务仍然是可直接阅读和编辑的 Markdown 文件，但所有确定性操作统一经过 CLI；同一份数据可以被终端、Skill 和 Web 看板消费。

## 二、范围

### 2.1 本期实现

1. 每个任务一个 Markdown 文件，YAML Frontmatter 保存结构化字段。
2. 使用稳定且唯一的 `TSK-xxxxxxxx` Task ID，文件名使用 Task ID。
3. 支持全局与项目级两种目录，默认全局。
4. 支持任务状态、Durable 判断依据和按状态统计。
5. 支持安全更新指定 Markdown 章节。
6. 自动生成可重建的 `index.md`。
7. 支持本地 Reference 文件和 Obsidian `OBA-xxxxxxxx` 引用。
8. 提供交互式 CUI、非交互 CLI 和本地 Web 看板。
9. 改造 Todo Skill，使其只调用 CLI，不直接编辑任务文件。
10. 提供基础完整性检查和尽力迁移旧格式的能力。

### 2.2 本期不实现

- SQLite 或其他数据库
- 夜间 Agent 和自动任务执行
- 多 Agent 调度、抢占和租约
- 登录、权限、远程访问和多用户协作
- 云端部署和跨设备同步
- 完整运行日志、审计日志和复杂备份
- 多个任务目录在同一个 Web 页面聚合

## 三、目录结构

全局目录：

```text
~/.agent-tasks/
├── index.md
├── tasks/
│   └── TSK-k7m3x9p2.md
├── references/
│   ├── index.md
│   └── durable-task-checklist.md
└── archive/
```

项目目录：

```text
{git-root}/.agent-tasks/
├── index.md
├── tasks/
├── references/
└── archive/
```

路径解析规则：

1. 无参数时始终使用全局目录。
2. `--current-project` 使用当前 Git 根目录下的 `.agent-tasks/`。
3. `--project <path>` 使用指定项目根目录下的 `.agent-tasks/`。
4. 无法解析明确指定的项目时返回错误，不静默退回全局。

## 四、任务格式

### 4.1 YAML

```yaml
---
task_id: TSK-k7m3x9p2
title: 改造 Todo Skill
status: shaping
project: jacky-skills
workspace: /path/to/jacky-skills
created: 2026-07-26
updated: 2026-07-26
references:
  - references/todo-status-design.md
  - OBA-w8s3k7p2
---
```

必填字段：

- `task_id`
- `title`
- `status`
- `created`
- `updated`

可选字段：

- `project`
- `workspace`
- `references`
- `durable_basis`

### 4.2 Task ID

- 格式：`TSK-` 加 8 位小写字母或数字。
- 由 Node 安全随机生成。
- 文件名固定为 `{task_id}.md`。
- 标题修改不改变 ID 或文件名。
- 创建和移动时检查目标目录内是否重复。

### 4.3 状态

```text
idea
shaping
canDurable
doing
waitingHuman
done
```

`canDurable` 表示任务上下文已经足够，让 AI 可以持续执行长程任务。进入该状态时必须记录判断依据：

```text
poc-passed
human-confirmed
ai-assessed
```

POC 是推荐验证，不是强制门槛。用户确认或 AI 自主评估也可以进入 `canDurable`，但界面必须显示判断依据。

`durable_basis` 与执行状态正交：任务进入 `doing`、`waitingHuman` 或 `done` 后继续保留 Durable 标记；退回 `idea` / `shaping` 时才移除。短任务仍可以不带标记直接执行。

`waitingHuman` 不是常规阶段状态，只用于：

1. 最终可交互/可观看/可调用产物已经就绪，必须由用户体验判断。
2. 继续执行需要新的高风险权限、缺失凭据或会改变最终产品结果的关键选择。
3. 安全诊断、重试和替代路径均已耗尽。

中间文档、阶段报告和普通技术决策不得进入 `waitingHuman`。

### 4.4 Markdown 正文

初始想法只要求：

```markdown
# 标题

## 想法

## 下一步
```

任务成熟过程中按需增加：

```markdown
## 上下文
## 当前设计
## 关键决定
## 待确认问题
```

准备长程执行时建议补充：

```markdown
## 目标
## 明确产物
## 完成标准
## 执行路线
## 所需能力
## 最终验收
## 执行记录
## POC 验证
```

CLI 不强制初级想法填写空模板。

## 五、Reference

本地知识使用普通相对路径：

```yaml
references:
  - references/durable-task-checklist.md
```

Obsidian 知识使用现有文章 ID：

```yaml
references:
  - OBA-w8s3k7p2
```

POC 不创建 `REF-` ID 体系。`references/index.md` 是可重建的文件导航。

## 六、CLI 与 CUI

核心命令：

```text
todo add
todo list
todo show
todo set
todo status
todo edit
todo stats
todo index
todo doctor
todo move
todo delete
todo section set
todo section append
todo section show
todo migrate
todo web
```

人工调用缺少必要参数时进入交互式 CUI。Skill 和脚本必须提供完整参数，使用非交互模式。

`section` 命令只修改指定二级标题的内容，不重写其他正文。

所有写操作完成后：

1. 自动更新 `updated`。
2. 自动重建当前作用域的 `index.md`。

`index.md` 只是一份生成视图，`tasks/*.md` 才是唯一数据源。

## 七、本地 Web 看板

启动方式：

```bash
todo web
todo web --current-project
todo web --project /path/to/repo
```

POC 功能：

1. 按状态展示任务数量和任务列表。
2. 快速新增任务。
3. 查看任务 YAML 摘要和 Markdown 正文。
4. 编辑标题、状态、项目、Workspace、Durable 判断依据和正文。
5. 归档任务。
6. 刷新后从 Markdown 重新读取，不维护独立数据库。

Web 默认仅监听 `127.0.0.1`，不提供登录和远程访问。

视觉方向采用 Terminal Noir：深色背景、霓虹绿主色、琥珀色 Durable 标识、等宽技术字体、克制的网格和扫描线效果。界面必须支持键盘操作、焦点可见和窄屏布局。

## 八、Skill 行为

Todo Skill 是自然语言适配层：

1. 默认操作全局目录。
2. 只有用户明确说“当前项目”或指定项目时才传项目参数。
3. 只调用 CLI，不直接修改 Markdown。
4. `list` 只列出任务，不执行任务。
5. 添加任务后返回 Task ID 和文件位置。
6. 更新上下文时使用 `section set/append`。
7. 进入 `canDurable` 时记录 `durable_basis`。
8. 第一阶段移除旧 `resolve` 的多 Agent 执行职责。
9. 中间文档完成后继续执行，不生成例行人工验收门。
10. 最终验收根据产物类型提供 URL、E2E 视频、Skill 触发提示词或可复制命令。
11. `waitingHuman` 只用于最终体验回归或真实权限/输入阻塞。
12. 用户只要求“进入 Durable”时，任务到达 `canDurable` 后停止，不自动进入 `doing`。
13. `canDurable` 前记录预计执行耗时、主要阶段与最大不确定性，让用户可以安排无人值守时间。
14. POC 属于 `shaping` 内的可选昂贵验证；开始前必须展示理由、时间预算、边界、副作用和替代路径，并获得用户明确确认。
15. POC 通过后只负责提供 `poc-passed` 依据，不自动授权长程执行。

## 九、旧格式

`migrate` 只做尽力转换：

- Ideas → `idea`
- 未完成 Todo → `shaping`
- 已完成条目 → `done`
- 能找到 checkpoint 时把内容合并进任务正文

迁移失败不阻塞 POC，也不为旧格式开发复杂兼容层。

## 十、验收标准

### 10.1 CLI

1. 可以创建全局和项目级任务，默认全局。
2. Task ID 唯一，文件名与 `task_id` 一致。
3. 可以筛选状态、查看详情、修改 YAML 和指定章节。
4. `canDurable` 必须带合法 `durable_basis`。
5. `stats --format yaml` 可以输出状态统计。
6. 手工修改任务后，`todo index` 可以重建索引。
7. `todo doctor` 可以发现非法 YAML、重复 ID、文件名不一致、非法状态和失效本地 Reference。
8. 删除命令把任务移动到 `archive/`。

### 10.2 Web

1. Web 与 CLI 读取同一个目录。
2. Web 新增任务后，CLI 能立即列出。
3. Web 修改状态和正文后，Markdown 文件同步变化。
4. Web 归档任务后，文件进入 `archive/`。
5. 页面刷新后数据不丢失。
6. 桌面和窄屏均可完成新增、编辑和归档。

### 10.3 Skill

1. 自然语言新增任务时默认写全局。
2. 明确指定当前项目时写项目级。
3. Skill 的文件写操作全部通过 CLI。
4. Skill 返回真实 Task ID、状态和文件位置。

## 十一、实现约束

- Node.js、ESM、`node:test`
- 优先使用 Node 标准库
- YAML 使用 `yaml`
- 命令解析使用 `cac`
- 交互输入使用 `@clack/prompts`
- Web 使用 Node 内置 HTTP 服务和原生 HTML/CSS/JavaScript
- 不引入数据库、前端框架或构建工具
- CLI 和 Web 的文件访问必须限制在已解析的 `.agent-tasks/` 根目录内
- Web API 只接受合法 `TSK-xxxxxxxx`，拒绝路径分隔符和目录穿越
- Web API 限制 JSON 请求体大小，非法 YAML 或字段不完整时不得覆盖原文件
- 不包含真实用户绝对路径、密钥或私密信息
