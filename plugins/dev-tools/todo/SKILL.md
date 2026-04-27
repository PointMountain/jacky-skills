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

提取条目到批次文件，读取 checkpoint 上下文，执行任务。

**执行步骤**：

1. 读取 `todo.md`，展示所有待处理条目
2. 用户确认要处理的条目
3. 扫描已有 `todo-N.md`，取最大 N+1
4. 将选中条目提取到 `todo-{N}.md`（带 `@context` 路径）
5. 清空 `todo.md`（保留模板结构），用户可继续新增条目
6. **逐条读取 `@context` 指向的 `cp-xxx.md` 文件**
7. 带着 checkpoint 中的完整上下文，开始处理任务
8. 处理完成后：
   - 标记 `todo-{N}.md` 中已完成条目
   - 清理对应的 `cp-xxx.md` 文件

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
todo.md                    cp-20260427-143000.md
   │                              │
   └──── resolve ─────────────────┤
           │                      │
           ▼                      ▼
      todo-1.md  ←──── 读取 @context 路径
           │
           ▼
      Claude 处理（带着 cp 文件的上下文）
           │
           ▼
      完成 → 清理 todo-1.md + cp-xxx.md
```

## 安全规则

1. resolve 前必须经用户确认
2. checkpoint 文件路径必须在项目目录内
3. 清理 checkpoint 前确认任务已完成
