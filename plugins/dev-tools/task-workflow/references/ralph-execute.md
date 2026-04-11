# Ralph Execute 模式

> EXECUTE 阶段的 ralph-loop 循环执行模式，解决 context 溢出问题。

## 为什么需要 Ralph 模式

Standard execute 在单个会话中跑完所有 TDD 循环。当任务数 > 5 时，context 必然溢出：
- AI 来不及更新状态就被截断
- 用户恢复后 `current.json` 可能未更新到最新
- 重复执行已完成的 task

**Ralph 模式**利用 stop-hook 机制，每轮循环只处理一个 task，天然解决 context 问题。

## 工作原理

```
┌─────────────────────────────────────────────────┐
│              Ralph Loop 执行流程                   │
└─────────────────────────────────────────────────┘

INIT/BRAINSTORM/HARNESS/PLAN
  （正常执行，与 standard 相同）
         │
         ▼
EXECUTE 阶段开始
         │
         ▼
  ┌──────────────┐
  │ 启动 ralph-loop│  ← /ralph-loop 或回复 "ralph"
  └──────┬───────┘
         │
         ▼
  ┌──────────────────────────────┐
  │ 循环第 N 轮（全新 context）    │
  │                              │
  │ 1. 读取 progress.md          │
  │    → 找到下一个未完成 task     │
  │ 2. 读取 PLAN.md 的 task 详情  │
  │ 3. TDD 红绿循环               │
  │ 4. Checkpoint 写入            │
  │    → progress.md / current.json│
  │    → workflow.json            │
  │ 5. 输出 <promise>TASK_DONE</promise> │
  └──────────────┬───────────────┘
                 │
         ┌───────┴───────┐
         │               │
         ▼               ▼
   还有未完成 task    所有 task 完成
   → stop-hook 触发   → <promise>ALL_TASKS_COMPLETE</promise>
   → 新一轮循环       → 退出 ralph，进入 REVIEW
```

## 启动方式

### 方式 1：从一开始指定 ralph 模式

```
/task-workflow ralph 开发 GitHub 热榜页面
```

前四个阶段（INIT → BRAINSTORM → HARNESS → PLAN）正常执行，到 EXECUTE 时自动进入 ralph 模式。

### 方式 2：EXECUTE 阶段动态切换

在 EXECUTE 阶段开始时，如果任务数 > 5，AI 会提示切换。回复 `ralph` 即可。

### 方式 3：恢复时选择 ralph

断点恢复时，选择 `ralph` 策略从断点继续。

## 每轮循环的 Prompt 模板

EXECUTE 阶段进入 ralph 模式时，构造如下 prompt 传给 `/ralph-loop`：

```
Task Workflow EXECUTE — 逐任务执行（{task-slug}）

## 进度读取
1. 读取 .harness/tasks/{slug}/execute/progress.md → 获取已完成/未完成 task
2. 读取 .harness/tasks/{slug}/plan/PLAN.md → 获取当前 task 的详细信息
3. 如果所有 task 已完成，输出 <promise>ALL_TASKS_COMPLETE</promise> 并停止

## 执行当前 task（TDD 红绿循环）
1. Red: 运行对应的 BDD 测试确认红灯
2. Green: 写最小实现代码，测试通过
3. 如果重试 >= 5 次仍失败，记录偏差并跳过（标记为 failed）

## 强制 Checkpoint（task 完成后立即执行）
1. 更新 execute/progress.md — 标记 [x] + 时间戳
2. 更新 workflow.json 的 executeProgress
3. 更新 .harness/current.json 的 executeCheckpoint
4. 如有偏差写入 execute/deviations.md

## 完成信号
- 单个 task 完成: <promise>TASK_DONE</promise>
- 所有 task 完成: <promise>ALL_TASKS_COMPLETE</promise>
```

## 循环控制

| 参数 | 说明 |
|------|------|
| `--max-iterations` | 最大循环次数（建议设为 task 数量 + 2） |
| `--completion-promise` | `ALL_TASKS_COMPLETE`（全部完成时输出） |
| 取消 | `/cancel-ralph` |

### 推荐启动命令

```
/ralph-loop <prompt> --max-iterations 12 --completion-promise 'ALL_TASKS_COMPLETE'
```

## 与 Standard Execute 的对比

| 维度 | Standard Execute | Ralph Execute |
|------|-----------------|---------------|
| 执行方式 | 单会话内顺序执行 | 多轮循环，每轮一个 task |
| Context 压力 | 累积式，task 多时溢出 | 每轮全新 context |
| 状态持久化 | 依赖 checkpoint（可能遗漏） | 每轮结束时强制写入 |
| 断点恢复 | 需手动恢复 | 天然支持（读 progress.md） |
| 适用场景 | task ≤ 5 个 | task > 5 个或复杂任务 |
| 取消方式 | 正常对话 | `/cancel-ralph` |

## 断点恢复

Ralph 模式下如果中途被取消或出错：

1. 运行 `/task-workflow status` 查看进度
2. progress.md 中已完成的 task 标记为 `[x]`
3. 再次启动 ralph 模式，自动从第一个 `[ ]` 的 task 继续

## 注意事项

1. **不要在单轮中执行多个 task** — 每轮只处理一个，保持 context 充裕
2. **Checkpoint 必须在每轮结束时写入** — 这是 ralph 模式的核心保障
3. **偏差记录不要跳过** — 即使在 ralph 模式，偏差也要记录到 deviations.md
4. **ralph 循环结束后** — 自动进入 REVIEW 阶段，生成复盘报告
