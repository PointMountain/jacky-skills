---
name: todo
description: "上下文快照 + 批次处理：add 时自动保存会话上下文到 checkpoint 文件，resolve 时读取 checkpoint 无缝续接"
argument-hint: '[add|resolve] [内容]'
---

<role>上下文快照 + 批次调度。add 时自动冻结当前会话状态，resolve 时解冻上下文并执行任务。</role>

## 核心理念

`todo.md` 是任务入口，`cp-{timestamp}.md` 是上下文快照。add 时存快照、写死路径；resolve 时读路径、还原上下文、执行任务。

## 两个命令

### `add <内容>`

添加一条待办，**同时自动生成 checkpoint 文件**。

**执行步骤**：

1. 生成 checkpoint 文件 `cp-{YYYYMMDD-HHmmss}.md`（项目根目录）
2. 将当前会话上下文写入 checkpoint：
   - 当前任务（在做什么）
   - 进度（做到哪了）
   - 关键决策（为什么选 A 不选 B）
   - 下一步（具体操作）
   - 正在编辑的文件（工作集）
3. 在 `todo.md` 添加条目，**写死 checkpoint 路径**：

```
- [ ] 完成用户认证模块 @context:cp-20260427-143000.md
  已写完 3 个 case，还差错误处理分支
```

- `--idea` → 写入 💡 Ideas 分区（不生成 checkpoint）
- 默认 → 写入 📋 Todo 分区（自动生成 checkpoint）

**注意**：checkpoint 是 add 那一刻的会话快照，不是 todo 条目本身。条目可以写续行补充细节。

### `resolve`

提取条目到批次文件，**使用 Multi Teams 并行处理**：每个条目分配一个 teammate，各自带着 checkpoint 上下文独立执行。

**执行步骤**：

1. 读取 `todo.md`，展示所有待处理条目
2. 用户确认要处理的条目
3. 扫描已有 `todo-N.md`，取最大 N+1
4. 将选中条目提取到 `todo-{N}.md`（带 `@context` 路径）
5. 清空 `todo.md`（保留模板结构），用户可继续新增条目
6. **创建团队**：`TeamCreate` 创建 `todo-resolve-{N}` 团队
7. **创建任务**：为每个条目调用 `TaskCreate`，描述中包含 checkpoint 路径和续行上下文
8. **并行派发 teammates**：每个条目 spawn 一个 `general-purpose` 类型 teammate（带 `team_name` 和 `name`，如 `todo-task-1`）：
   - teammate 读取自己的 `cp-xxx.md` 还原上下文
   - teammate 独立执行任务
   - 完成后 `TaskUpdate` 标记已完成，通过 `SendMessage` 向 team lead 汇报结果
9. **主会话监控**：通过 `TaskList` 跟踪进度，接收 teammate 消息
10. **全部完成后**：
    - 标记 `todo-{N}.md` 中已完成条目
    - 清理对应的 `cp-xxx.md` 文件
    - `SendMessage` shutdown 所有 teammates
    - `TeamDelete` 清理团队资源

**teammate prompt 模板**：

```
你是一个独立执行任务的 agent。请完成以下工作：

1. 读取 checkpoint 文件还原上下文：{cp-xxx.md 路径}
2. 根据 checkpoint 中的「下一步」和「正在编辑的文件」，继续完成任务
3. 任务完成后，通过 SendMessage 向 team lead 汇报：
   - 完成了什么
   - 修改了哪些文件
   - 是否有问题需要 team lead 处理
4. 通过 TaskUpdate 将任务标记为 completed

**Checkpoint 文件**: {cp-xxx.md 完整路径}
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
todo.md                    cp-xxx.md (多个)
   │                              │
   └──── resolve ─────────────────┤
           │                      │
           ▼                      ▼
      todo-1.md  ←──── 提取 @context 路径
           │
           ▼
      TeamCreate("todo-resolve-1")
           │
           ├─→ TaskCreate(条目1) ──→ teammate-1 读 cp-A → 执行 → 完成
           ├─→ TaskCreate(条目2) ──→ teammate-2 读 cp-B → 执行 → 完成
           └─→ TaskCreate(条目3) ──→ teammate-3 读 cp-C → 执行 → 完成
           │
           ▼
      全部完成 → 清理 cp-xxx.md + shutdown teammates + TeamDelete
```

## 安全规则

1. resolve 前必须经用户确认
2. checkpoint 文件路径必须在项目目录内
3. 清理 checkpoint 前确认任务已完成
4. 所有 teammates 完成后必须 shutdown 并 TeamDelete，避免资源残留
5. 单个 teammate 失败不影响其他 teammate，team lead 负责收集失败结果并报告
