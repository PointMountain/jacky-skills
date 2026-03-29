# Generator Agent 详细规范

> Generator Agent 负责基于 Plan Agent 的输出实现代码。

## 职责边界

**做什么**：
- 读取 PLAN.md，按任务顺序实现代码
- 遵循 TDD 红→绿流程
- 记录变更和偏差

**不做什么**：
- 不修改计划
- 不做验收评估（那是 Score 的职责）
- 不跳过任务

## 前置条件

| 条件 | 检查方式 |
|------|----------|
| PLAN.md 存在 | `agents/plan/PLAN.md` |
| harness.md 存在 | `agents/plan/harness.md` |
| pipeline.json 中 plan.status = completed | 读取 pipeline.json |

如果前置条件不满足，提示用户先运行 Plan Agent。

---

## 执行流程

### Step 1: 读取输入

```
读取 agents/plan/PLAN.md → 获取任务列表
读取 agents/plan/harness.md → 获取验收标准
```

### Step 2: 按任务顺序执行

对 PLAN.md 中的每个任务（T1, T2, ...），按 TDD 流程执行：

#### 2.1 Red（写失败测试）

1. 根据 harness.md 的 MUST 条件，编写测试用例
2. 运行测试，确认失败
3. 记录期望行为

#### 2.2 Green（写最小实现）

1. 编写最小代码使测试通过
2. 不过度设计
3. 不过早优化

#### 2.3 下一个任务

重复 2.1-2.2 直到所有任务完成。

### Step 3: 记录变更

**CHANGES.md 模板**：

```markdown
# 变更摘要：{任务名称}

> 生成时间: {ISO-8601}
> 基于 PLAN: agents/plan/PLAN.md

## 任务完成情况

| 任务 | 状态 | 说明 |
|------|------|------|
| T1 | ✅ 完成 | {简要说明} |
| T2 | ✅ 完成 | {简要说明} |
| T3 | ⚠️ 偏差 | {偏差说明，见 deviations.md} |

## 修改的文件

| 文件 | 操作 | 变更说明 |
|------|------|----------|
| src/foo.ts | created | {说明} |
| src/bar.ts | modified | {说明} |

## 新增的测试

| 测试文件 | 覆盖的 MUST 条件 |
|----------|-----------------|
| tests/foo.test.ts | MUST-1, MUST-2 |
```

### Step 4: 记录偏差（如有）

当实现与 PLAN.md 不一致时，记录偏差：

**deviations.md 模板**：

```markdown
# 偏差记录

## T3: {任务名称}

**计划**: {PLAN.md 中的描述}
**实际**: {实际做了什么}
**原因**: {为什么偏差}

## 影响

- {对后续任务的影响}
- {对验收标准的影响}
```

### Step 5: 更新 pipeline.json

```json
{
  "agents": {
    "generate": {
      "status": "completed",
      "completedAt": "{ISO-8601}",
      "outputFiles": ["agents/generate/CHANGES.md"],
      "taskResults": {
        "T1": "completed",
        "T2": "completed",
        "T3": "deviated"
      }
    }
  }
}
```

---

## 重试场景

当 Score Evaluator 不通过，回退到 Generator 时：

### 首次重试

1. **读取 Score 反馈** — `agents/score/SCORE.md` 中标记的问题
2. **针对性修复**：
   - 测试失败 → 修复测试或修复代码
   - 视觉问题 → 调整样式/布局
   - 功能缺失 → 补充实现
3. **更新 CHANGES.md** — 追加重试修改记录

### 后续重试

同首次重试，但附带更多上下文：
- 前几次 Score 的反馈
- 前几次 Generator 的修改
- 避免重复相同错误

### 3 次重试后仍失败

1. **更新 pipeline.json**：
   ```json
   {
     "agents": {
       "generate": {
         "status": "failed",
         "retryCount": 3,
         "lastFeedback": "..."
       }
     }
   }
   ```
2. **触发 Plan 回退** — 附带完整历史

---

## 偏差处理原则

| 偏差类型 | 处理方式 |
|----------|----------|
| 文件路径变化 | 记录实际路径，继续执行 |
| 实现方案调整 | 记录原因，继续执行 |
| 任务合并 | 记录合并原因，继续执行 |
| 发现新依赖 | 记录依赖，继续执行 |
| 发现计划错误 | 记录问题，继续执行（Score 会评估） |
