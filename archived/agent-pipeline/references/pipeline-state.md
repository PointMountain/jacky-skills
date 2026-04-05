# pipeline.json 状态管理与恢复协议

> 定义流水线状态文件的结构、状态机转换和中断恢复机制。

## pipeline.json 完整 Schema

```json
{
  "$schema": "./pipeline.schema.json",
  "id": "pipe-2026-03-29-001",
  "name": "任务名称",
  "slug": "task-slug",
  "status": "in_progress",
  "currentAgent": "plan",
  "userIntent": "用户的原始需求描述",

  "iteration": {
    "plan": 1,
    "generate": 0,
    "total": 1
  },

  "agents": {
    "plan": {
      "status": "completed",
      "startedAt": "2026-03-29T10:00:00Z",
      "completedAt": "2026-03-29T10:30:00Z",
      "outputFiles": [
        "agents/plan/PLAN.md",
        "agents/plan/harness.md",
        "agents/plan/context.md"
      ]
    },
    "generate": {
      "status": "in_progress",
      "startedAt": "2026-03-29T10:30:00Z",
      "completedAt": null,
      "retryCount": 0,
      "outputFiles": []
    },
    "score": {
      "status": "pending",
      "startedAt": null,
      "completedAt": null,
      "outputFiles": []
    }
  },

  "history": [
    {
      "iteration": 1,
      "plan": { "version": 1, "completedAt": "..." },
      "generate": { "version": 1, "retryCount": 0, "completedAt": "..." },
      "score": {
        "overallScore": 65,
        "passed": false,
        "dimensions": {
          "functionality": 60,
          "tests": 70,
          "visual": 50,
          "codeQuality": 80,
          "planAdherence": 90
        }
      },
      "decision": "retry-generate",
      "feedback": "视觉评分不达标，需修复布局问题"
    }
  ],

  "createdAt": "2026-03-29T10:00:00Z",
  "updatedAt": "2026-03-29T10:30:00Z"
}
```

---

## 状态机

### Agent 状态

| 状态 | 含义 |
|------|------|
| `pending` | 未开始 |
| `in_progress` | 执行中 |
| `completed` | 已完成 |
| `failed` | 已失败（重试次数耗尽） |

### Pipeline 状态

| 状态 | 含义 |
|------|------|
| `in_progress` | 流水线进行中 |
| `completed` | 流水线完成（Score 通过） |
| `paused` | 暂停（重试次数耗尽，等用户决策） |
| `aborted` | 用户手动终止 |

### 状态转换图

```
                    ┌─────────────────────────────────────────────┐
                    │                                             │
                    ▼                                             │
┌──────────┐  plan  ┌──────────┐  generate  ┌──────────┐  score  │
│   INIT   │───────▶│   PLAN   │──────────▶│ GENERATE │─────────┤
└──────────┘       └──────────┘           └──────────┘         │
                         ▲                      ▲                │
                         │                      │                │
                         │    retry (≤3)        │                │
                         │◄─────────────────────┤                │
                         │                      │                │
                         │    re-plan (≤2)      │                │
                         │◄─────────────────────┘                │
                         │                                       │
                         │                                       ▼
                    ┌────┴─────┐                          ┌──────────┐
                    │  PAUSED  │                          │ COMPLETED│
                    └──────────┘                          └──────────┘
```

---

## Agent 交接协议

### Plan → Generator

**触发条件**：plan.status = completed + 用户确认

**交接内容**：
1. `agents/plan/PLAN.md` — 任务列表
2. `agents/plan/harness.md` — 验收标准
3. `pipeline.json` 更新 currentAgent = "generate"

**Generator 启动检查**：
```
✓ agents/plan/PLAN.md 存在且非空
✓ agents/plan/harness.md 存在且非空
✓ pipeline.json agents.plan.status = "completed"
```

### Generator → Score

**触发条件**：generate.status = completed

**交接内容**：
1. `agents/generate/CHANGES.md` — 变更摘要
2. `agents/generate/deviations.md` — 偏差记录（如有）
3. `pipeline.json` 更新 currentAgent = "score"

**Score 启动检查**：
```
✓ agents/generate/CHANGES.md 存在且非空
✓ pipeline.json agents.generate.status = "completed"
```

### Score → Generator（重试）

**触发条件**：score.overallScore < 70 AND generate.retryCount < 3

**交接内容**：
1. `agents/score/SCORE.md` — 问题清单和改进建议
2. `agents/score/report.json` — 具体分数和失败项
3. `pipeline.json` 更新：
   - currentAgent = "generate"
   - generate.status = "pending"
   - generate.retryCount += 1

**Generator 重试检查**：
```
✓ agents/score/SCORE.md 存在（包含上次反馈）
✓ generate.retryCount < 3
✓ 读取反馈后针对性修复
```

### Score → Plan（回退）

**触发条件**：score.overallScore < 70 AND generate.retryCount >= 3 AND plan.retryCount < 2

**交接内容**：
1. 完整 history（所有迭代的 Score 报告）
2. `pipeline.json` 更新：
   - currentAgent = "plan"
   - plan.status = "pending"
   - plan.retryCount += 1
   - generate.retryCount = 0

**Plan 重试检查**：
```
✓ history 非空（有失败历史）
✓ plan.retryCount < 2
✓ 分析历史失败原因后重新规划
```

---

## 恢复协议

### 检测中断

启动时检查 `.pipeline/pipeline.json`：

```python
if pipeline.status == "in_progress":
    # 有中断的任务
    agent = pipeline.currentAgent
    if pipeline.agents[agent].status == "in_progress":
        # Agent 执行中被中断
        resume_from_agent(agent)
    elif pipeline.agents[agent].status == "completed":
        # Agent 完成，但没来得及切换到下一个
        advance_to_next_agent(agent)
```

### 恢复策略

| 场景 | 处理方式 |
|------|----------|
| Plan 执行中中断 | 检查已生成的文件，从不完整的步骤继续 |
| Generator 执行中中断 | 检查代码变更，从最后一个完成的任务继续 |
| Score 执行中中断 | 重新运行评分（评分是幂等的） |
| Agent 交接时中断 | 读取两边的状态文件，执行交接 |

### 恢复流程

```
用户: /agent-pipeline continue

AI:
  1. 读取 pipeline.json
  2. 确定中断点和 Agent 状态
  3. 展示摘要：
     ┌────────────────────────────────────┐
     │ 流水线恢复: {name}                 │
     │                                    │
     │ Plan:     ✅ 已完成 (v1)           │
     │ Generate: 🔄 进行中 (2/4 任务)     │
     │ Score:    ⏳ 待执行                │
     │                                    │
     │ 迭代: 第 1 次                      │
     │ 中断于: Generator T3              │
     └────────────────────────────────────┘
  4. 询问恢复策略:
     - continue: 从 T3 继续
     - restart-current: 重新运行 Generator
     - abort: 终止流水线
```

### 损坏修复

如果 pipeline.json 或 Agent 输出文件损坏：

1. **pipeline.json 损坏** — 尝试从 history 重建
2. **Agent 输出丢失** — 重新运行该 Agent
3. **无法恢复** — 建议用户 reset

---

## 重置协议

`/agent-pipeline reset` 清理流程：

1. 确认用户意图（AskUserQuestion）
2. 备份当前 `.pipeline/` 到 `.pipeline.backup.{timestamp}/`
3. 删除 `.pipeline/`
4. 清理完成，可重新启动
