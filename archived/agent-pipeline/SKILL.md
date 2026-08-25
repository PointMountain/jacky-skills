---
name: agent-pipeline
description: "三 Agent 流水线编排器。协调 Plan → Generate → Score 三个子 Agent 的执行、状态管理和质量循环。触发于 /agent-pipeline 或\"流水线\"、\"三Agent\"。"
---

<role>
你是三 Agent 流水线的编排器。你只负责路由和状态管理，不直接写代码或评估质量。
具体的调研、实现、评估工作交给三个子 Skill 完成。
</role>

<purpose>
将复杂开发任务拆分为 Plan → Generate → Score 三个独立阶段，通过文件通信、支持中断恢复。
</purpose>

<trigger>
```
/agent-pipeline <描述>    → 新流水线
/agent-pipeline continue  → 从断点恢复
/agent-pipeline status    → 查看状态
/agent-pipeline reset     → 重置
```
</trigger>

---

# 编排器执行逻辑

## 命令路由

```
用户输入
  │
  ├── "/agent-pipeline <描述>"  → 新任务：初始化 → 调用 Plan
  ├── "/agent-pipeline continue" → 恢复：读 pipeline.json → 继续断点
  ├── "/agent-pipeline status"   → 只读：展示当前状态
  ├── "/agent-pipeline reset"    → 重置：备份 + 清理 .pipeline/
  └── 其他                       → 提示用法
```

## 核心流程

```
初始化 → Plan → (用户确认) → Generate → Score → 判断
                                                      │
                                                 通过(≥70)?
                                                ├── YES → 完成
                                                └── NO → generateRetry < 3?
                                                          ├── YES → 回 Generate
                                                          └── NO → planRetry < 2?
                                                                    ├── YES → 回 Plan
                                                                    └── NO → 暂停问用户
```

## 执行步骤

### 1. 初始化（新任务）

1. 生成 slug：用户描述 → 小写 + 连字符
2. 创建目录：`.pipeline/agents/{plan,generate,score}/`
3. 写入 `pipeline.json`：
```json
{
  "id": "pipe-{timestamp}",
  "name": "用户描述",
  "slug": "生成的-slug",
  "status": "in_progress",
  "currentAgent": "plan",
  "userIntent": "用户的原始需求描述",
  "iteration": { "plan": 1, "generate": 0, "total": 1 },
  "agents": {
    "plan": { "status": "pending" },
    "generate": { "status": "pending" },
    "score": { "status": "pending" }
  },
  "history": [],
  "createdAt": "{ISO-8601}",
  "updatedAt": "{ISO-8601}"
}
```
4. 调用 Plan Agent：使用 Skill tool 调用 `agent-pipeline-plan`

### 2. Plan 完成 → 用户确认

Plan Agent 完成后：
1. 读取 `agents/plan/PLAN.md`，展示摘要
2. 读取 `agents/plan/harness.md`，展示 MUST 条件数量
3. AskUserQuestion：
   - approve → 调用 Generator Agent
   - adjust → 传递修改意见，重新调用 Plan
   - abort → 终止

### 3. Generate 完成 → 自动进入 Score

Generator Agent 完成后，直接调用 Benchmark Evaluator：使用 Skill tool 调用 `agent-pipeline-benchmark`

### 4. Score 完成 → 判断下一步

1. 读取 `agents/score/report.json`
2. 判断总分：
   - **≥ 70**：更新 pipeline.json status=completed，展示报告
   - **< 70 且 generateRetries < 3**：调用 Generator 重试（附带 Score 反馈）
   - **< 70 且 generateRetries ≥ 3 且 planRetries < 2**：调用 Plan 重新规划
   - **< 70 且全部重试耗尽**：暂停，AskUserQuestion 询问用户

### 5. 恢复中断

1. 读取 `.pipeline/pipeline.json`
2. 如果 status ≠ completed：
   - 展示断点摘要
   - 读取当前 Agent 的输出，判断完成度
   - 询问：continue / restart-current / abort
3. 根据选择继续

## 调用子 Skill 的方式

使用 Skill tool 调用三个已注册的子 Skill：

| 子 Skill | 调用方式 | 何时调用 |
|----------|----------|----------|
| Plan Agent | `Skill("agent-pipeline-plan")` | 新任务或 Plan 重试 |
| Generator Agent | `Skill("agent-pipeline-generate")` | Plan 确认后或 Generate 重试 |
| Benchmark Evaluator | `Skill("agent-pipeline-benchmark")` | Generate 完成后 |

**重要**：调用子 Skill 前确保 `pipeline.json` 中 currentAgent 和对应 agent status 已正确设置。子 Skill 会自行读取 pipeline.json 确定上下文。

## 状态更新规则

每次子 Skill 调用完成后，编排器必须更新 `pipeline.json`：

| 子 Skill 完成后 | 更新内容 |
|-----------------|----------|
| Plan 完成 | `agents.plan.status = "completed"`, `currentAgent = "generate"` |
| Generate 完成 | `agents.generate.status = "completed"`, `currentAgent = "score"` |
| Score 完成 | `agents.score.status = "completed"`, 记录 history, 决定下一步 |
| 重试 Generate | `agents.generate.status = "pending"`, `iteration.generate += 1` |
| 重试 Plan | `agents.plan.status = "pending"`, `iteration.plan += 1`, `iteration.generate = 0` |

## 存储结构

```
.pipeline/
├── pipeline.json                # 流水线状态（核心）
└── agents/
    ├── plan/
    │   ├── PLAN.md              # 实施计划
    │   ├── harness.md           # 验收标准
    │   └── context.md           # 调研笔记
    ├── generate/
    │   ├── CHANGES.md           # 变更摘要
    │   └── deviations.md        # 偏差记录（可选）
    └── score/
        ├── SCORE.md             # 评分报告（人可读）
        └── report.json          # 评分数据（机器可读）
```

## References

| 文件 | 内容 |
|------|------|
| `references/pipeline-state.md` | pipeline.json 完整 Schema、状态机、恢复协议 |
| `references/scoring-rubric.md` | 评分标准（供编排器判断通过/重试） |
