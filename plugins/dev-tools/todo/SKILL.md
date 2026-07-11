---
name: todo
description: "上下文快照 + 批次处理：add 时自动保存会话上下文到 checkpoint 文件，resolve 时读取 checkpoint 无缝续接"
---

<role>上下文快照 + 批次调度。add 时自动冻结当前会话状态，resolve 时解冻上下文并执行任务。</role>

## 核心理念

`todo.md` 是任务入口，`cp-{timestamp}.md` 是上下文快照。add 时存快照、写死路径；resolve 时读路径、还原上下文、执行任务。

## 存储位置

`.agent-tasks/` 目录是 AI 智能体专用的待办存储，可被 Claude Code、Codex、Gemini CLI 等所有 agent 识别和读写。

## 语义映射（新增）

为减少口头指令歧义，以下自然语言应映射为固定行为：

1. 用户说“全局待办任务 / 全局 Todo / global todo”：
   - 强制等价于 `--global`
   - 固定操作文件：`~/.agent-tasks/todo.md`
   - 忽略当前是否位于 git 仓库
2. 用户说“项目待办任务 / 当前项目待办”：
   - 强制使用项目级路径 `{git-root}/.agent-tasks/todo.md`
   - 若当前不在 git 仓库，提示无法使用项目级并建议改用全局
3. 用户只说”待办任务 / todo”未指定范围：
   - 按路径解析规则处理（在 git 项目内时需询问用户选择项目级还是全局）

### 双层结构

| 层级 | 路径 | 用途 |
|------|------|------|
| **全局** | `~/.agent-tasks/` | 跨项目待办，所有环境共享 |
| **项目级** | `{git-root}/.agent-tasks/` | 项目相关待办，跟随项目走 |

### 路径解析规则

1. 检测当前目录是否在 git 仓库内（向上查找 `.git/`）
2. 若命中“全局待办任务”语义 → 强制使用全局 `~/.agent-tasks/`
3. 若命中“项目待办任务”语义 → 强制使用 `{git-root}/.agent-tasks/`
4. **在 git 项目内**（且未命中强制语义）→ **通过 AskUserQuestion 询问用户**选择项目级还是全局（仅 `add` 和 `resolve` 时询问，`list` 默认项目级）
5. **不在 git 项目内** → 使用全局 `~/.agent-tasks/`
6. `--global` 标志 → 强制使用全局路径，忽略项目

### 目录结构

```
.agent-tasks/
├── todo.md              # 任务入口
├── cp-20260429-143000.md  # 上下文快照（checkpoint）
├── cp-20260429-153000.md
└── todo-1.md            # 批次文件（resolve 时生成）
```

### 初始化

首次使用时，如果 `.agent-tasks/` 目录不存在，自动创建并生成 `todo.md` 模板。

## 三个命令

### `list`

仅列出当前待办，**绝不创建 checkpoint、绝不执行任务、绝不触发任何调研或实现动作**。

**执行步骤**：

1. 解析存储路径（项目级 or 全局，遵循“语义映射”优先）
2. 若 `todo.md` 不存在，仅初始化模板文件
3. 输出 Todo/Ideas 条目清单
4. 结束，不做任何额外操作

### `add <内容>`

添加一条待办，**同时自动生成 checkpoint 文件**。

**执行步骤**：

1. 解析存储路径（项目级 or 全局，遵循”语义映射”优先）。若在 git 项目内且未命中强制语义，**必须通过 AskUserQuestion 询问用户**选择项目级还是全局
2. 确保 `.agent-tasks/` 目录存在（不存在则创建）
3. 生成 checkpoint 文件 `{storage}/cp-{YYYYMMDD-HHmmss}.md`
4. 将当前会话上下文写入 checkpoint：
   - 当前任务（在做什么）
   - 进度（做到哪了）
   - 关键决策（为什么选 A 不选 B）
   - 下一步（具体操作）
   - 正在编辑的文件（工作集）
5. 在 `{storage}/todo.md` 添加条目，**写死 checkpoint 路径**：

```
- [ ] 完成用户认证模块 @context:cp-20260427-143000.md
  已写完 3 个 case，还差错误处理分支
```

- `--idea` → 写入 💡 Ideas 分区（不生成 checkpoint）
- `--global` → 强制写入全局 `~/.agent-tasks/`
- 默认 → 写入 📋 Todo 分区（自动生成 checkpoint）

**注意**：checkpoint 是 add 那一刻的会话快照，不是 todo 条目本身。条目可以写续行补充细节。

### `resolve`

提取条目到批次文件，**使用 Multi Teams 并行处理**：每个条目分配一个 teammate，各自带着 checkpoint 上下文独立执行。

**执行步骤**：

1. 解析存储路径（项目级 or 全局，遵循”语义映射”优先）。若在 git 项目内且未命中强制语义，**通过 AskUserQuestion 询问用户**选择项目级还是全局
2. 读取 `{storage}/todo.md`，展示所有待处理条目
3. 用户确认要处理的条目
4. 扫描已有 `{storage}/todo-N.md`，取最大 N+1
5. 将选中条目提取到 `{storage}/todo-{N}.md`（带 `@context` 路径）
6. 清空 `{storage}/todo.md`（保留模板结构），用户可继续新增条目
7. **创建团队**：`TeamCreate` 创建 `todo-resolve-{N}` 团队
8. **创建任务**：为每个条目调用 `TaskCreate`，描述中包含 checkpoint 完整路径和续行上下文
9. **并行派发 teammates**：每个条目 spawn 一个 `general-purpose` 类型 teammate（带 `team_name` 和 `name`，如 `todo-task-1`）：
   - teammate 读取自己的 `{storage}/cp-xxx.md` 还原上下文
   - teammate 独立执行任务
   - 完成后 `TaskUpdate` 标记已完成，通过 `SendMessage` 向 team lead 汇报结果
10. **主会话监控**：通过 `TaskList` 跟踪进度，接收 teammate 消息
11. **全部完成后**：
    - 标记 `{storage}/todo-{N}.md` 中已完成条目
    - 清理对应的 `{storage}/cp-xxx.md` 文件
    - `SendMessage` shutdown 所有 teammates
    - `TeamDelete` 清理团队资源

**teammate prompt 模板**：

```
你是一个独立执行任务的 agent。请完成以下工作：

1. 读取 checkpoint 文件还原上下文：{storage}/cp-xxx.md
2. 根据 checkpoint 中的「下一步」和「正在编辑的文件」，继续完成任务
3. 任务完成后，通过 SendMessage 向 team lead 汇报：
   - 完成了什么
   - 修改了哪些文件
   - 是否有问题需要 team lead 处理
4. 通过 TaskUpdate 将任务标记为 completed

**Checkpoint 文件**: {storage 的完整绝对路径}/cp-xxx.md
**任务描述**: {todo 条目内容 + 续行上下文}
```

## todo.md 文件格式

```markdown
# TODO

最后更新: YYYY-MM-DD

## 📋 Todo
- [ ] 任务描述 @context:cp-20260427-143000.md
  续行补充上下文

## 💡 Ideas
- [ ] 想法描述
```

## todo-N.md 批次文件格式

```markdown
---
source: todo.md
created: "2026-04-27"
status: pending
---

## 📋 Todo
- [ ] 任务描述 @context:cp-20260427-143000.md
  续行补充上下文

## 💡 Ideas
- [ ] 想法描述
```

## cp-xxx.md checkpoint 格式

```markdown
---
type: checkpoint
created: "2026-04-27T14:30:00"
---

## 当前任务
一句话描述在做什么

## 进度
- 已完成的事项
- 正在进行的事项

## 关键决策
- 为什么选 A 不选 B

## 下一步
1. 具体操作
2. 具体操作

## 正在编辑的文件
- path/to/file1
- path/to/file2
```

## resolve 流程图

```
.agent-tasks/
├── todo.md                    cp-xxx.md (多个)
│     │                              │
│     └──── resolve ─────────────────┤
│             │                      │
│             ▼                      ▼
│        todo-1.md  ←──── 提取 @context 路径
│             │
│             ▼
│        TeamCreate("todo-resolve-1")
│             │
│             ├─→ TaskCreate(条目1) ──→ teammate-1 读 cp-A → 执行 → 完成
│             ├─→ TaskCreate(条目2) ──→ teammate-2 读 cp-B → 执行 → 完成
│             └─→ TaskCreate(条目3) ──→ teammate-3 读 cp-C → 执行 → 完成
│             │
│             ▼
│        全部完成 → 清理 cp-xxx.md + shutdown teammates + TeamDelete
```

## 安全规则

1. resolve 前必须经用户确认
2. checkpoint 文件路径必须在 `.agent-tasks/` 目录内
3. 清理 checkpoint 前确认任务已完成
4. 所有 teammates 完成后必须 shutdown 并 TeamDelete，避免资源残留
5. 单个 teammate 失败不影响其他 teammate，team lead 负责收集失败结果并报告
6. `.agent-tasks/` 应加入 `.gitignore`，避免待办数据进入版本控制（除非团队有意共享）
7. 当用户只要求 `list` 或“添加待办”时，禁止执行待办内容本身；仅允许文件级增删改查
8. 未收到用户明确授权前，禁止调研系统、禁止创建守护进程、禁止落地自动化脚本

## 推荐触发词（新增）

建议优先使用下列短语，模型更容易稳定命中正确路径：

- 列表查询：`全局待办`、`看下全局待办`、`列出全局待办任务`
- 添加任务：`加到全局待办：<内容>`、`全局待办新增：<内容>`
- 完成批次：`处理全局待办`、`resolve 全局待办`
- 项目范围：`当前项目待办`、`这个仓库的待办`

其中“全局待办任务”是最高优先级别名，默认指向 `~/.agent-tasks/todo.md`。
