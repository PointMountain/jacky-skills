# 命令详细说明

## 命令列表

| 命令 | 用途 | 参数 |
|------|------|------|
| `/todo add <内容>` | 添加 Todo 条目（自动生成 checkpoint） | `--idea` 添加到 Ideas 区 |
| `/todo resolve` | 提取批次 → 读取 checkpoint → 执行任务 | 交互式选择 |

## /todo add

添加新的待办条目，**同时自动生成 checkpoint 文件**。

**默认行为**：添加到 `## 📋 Todo` 分区，并生成 `cp-{timestamp}.md`

**选项**：
- `--idea`：添加到 `## 💡 Ideas` 分区（不生成 checkpoint）

**checkpoint 自动生成的内容**：
- 当前任务描述
- 做到哪了（进度）
- 为什么选 A 不选 B（关键决策）
- 下一步具体操作
- 正在编辑的文件列表

**示例**：
```
/todo add 完成 CDP Proxy 笔记的 WebSocket 管理部分
  → 自动生成 cp-20260427-143000.md（当前会话快照）
  → todo.md 新增：- [ ] 完成 CDP Proxy 笔记... @context:cp-20260427-143000.md

/todo add --idea 用 WebSocket 实现实时通知
  → 只添加 Ideas 条目，不生成 checkpoint
```

## /todo resolve

提取待办条目到批次文件，读取 checkpoint 上下文，执行任务。

**流程**：
1. 读取 `todo.md`，展示所有待处理条目
2. 用户确认要处理的条目（全部或选择部分）
3. 扫描已有 `todo-N.md`，取最大 N+1 作为新批次号
4. 将选中条目写入 `todo-{N}.md`（status: pending）
5. 清空 `todo.md` 已提取的条目（用户可继续新增）
6. 逐条读取 `@context` 指向的 checkpoint 文件
7. 带着完整上下文执行任务
8. 完成后：
   - 标记 `todo-{N}.md` 中已完成条目，status → done
   - 删除对应的 `cp-xxx.md` 文件

**示例**：
```
用户: /todo resolve
Claude:
  📋 待处理条目：
    [1] 完成 CDP Proxy 笔记 @context:cp-20260427-143000.md
    [2] 重构 API 错误处理 @context:cp-20260427-150000.md

  确认处理哪些？[全部/编号/取消]
用户: 全部
Claude:
  ✅ 提取到 todo-1.md，清空 todo.md
  📖 读取 cp-20260427-143000.md → 恢复上下文
  🔧 开始处理任务...
```

## 使用场景示例

### 场景 1：上下文快满了，保存状态

```
用户: /todo add 完成笔记的 WebSocket 管理部分，还差超时处理和重连逻辑
Claude:
  📸 生成 checkpoint: cp-20260427-143000.md
  ✅ 添加到 todo.md: - [ ] 完成笔记... @context:cp-20260427-143000.md

  checkpoint 记录了：
  - 当前任务：写 06-cdp-proxy-code-walkthrough.md
  - 进度：已完成 HTTP API 部分，正在写 WebSocket
  - 决策：选择逐行精读而非概览方式
  - 下一步：补充超时处理、重连逻辑、错误码对照表
```

### 场景 2：新会话恢复上下文并处理

```
# 新会话启动，SessionStart hook 显示有 2 个待办

用户: /todo resolve
Claude:
  📋 待处理条目：
    [1] 完成笔记 WebSocket 部分 @context:cp-20260427-143000.md

  确认处理？[全部/编号/取消]
用户: 全部
Claude:
  ✅ 提取到 todo-1.md
  📖 读取 checkpoint → 恢复上下文：
    - 任务：写 06-cdp-proxy-code-walkthrough.md
    - 进度：WebSocket 管理部分写到一半
    - 下一步：补充超时处理和重连逻辑

  🔧 开始处理...
  （带着完整上下文继续工作）
```

### 场景 3：记录想法

```
用户: /todo add --idea 考虑给 demo 加 fallback 处理
Claude: ✅ 已记录到 Ideas（不生成 checkpoint）
```
