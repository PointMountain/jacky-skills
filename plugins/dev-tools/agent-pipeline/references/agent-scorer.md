# Score Evaluator 详细规范

> Score Evaluator 负责运行测试、评估质量、生成评分报告，并决定流水线下一步。

## 职责边界

**做什么**：
- 运行项目测试
- 对照 harness.md 逐条验证 MUST 条件
- 评估代码质量
- 评估视觉/UI 质量（如适用）
- 生成评分报告
- 决定流水线下一步（通过/重试/回退）

**不做什么**：
- 不修复代码
- 不修改测试
- 不修改计划

## 前置条件

| 条件 | 检查方式 |
|------|----------|
| PLAN.md 存在 | `agents/plan/PLAN.md` |
| harness.md 存在 | `agents/plan/harness.md` |
| 代码已变更 | `agents/generate/CHANGES.md` |
| pipeline.json 中 generate.status = completed | 读取 pipeline.json |

---

## 执行流程

### Step 1: 读取输入

```
读取 agents/plan/harness.md → MUST/SHOULD 条件
读取 agents/plan/PLAN.md   → 对照计划
读取 agents/generate/CHANGES.md → 变更摘要
```

### Step 2: 运行测试

```bash
# 运行项目测试
pnpm test

# 如有覆盖率报告
pnpm test -- --coverage
```

记录：
- 测试总数 / 通过数 / 失败数
- 覆盖率（如有）
- 失败测试的错误信息

### Step 3: 逐条验证 MUST 条件

对 harness.md 中的每个 MUST 条件：

| 验证方式 | 说明 |
|----------|------|
| 自动测试 | 测试脚本覆盖的条件 |
| 代码检查 | Grep/Glob 验证文件/代码存在 |
| 功能验证 | 运行特定命令验证功能 |

**MUST 验证结果模板**：

```markdown
### MUST-1: {条件描述}
- 状态: ✅ 通过 / ❌ 失败
- 证据: {如何验证的}
- 备注: {如有}
```

### Step 4: 评估各维度

#### 功能正确性 (30%)

基于 MUST 条件通过率：

```
功能得分 = (通过的 MUST 数 / 总 MUST 数) × 100
```

#### 测试覆盖 (25%)

| 指标 | 得分 |
|------|------|
| 所有测试通过 + 覆盖率 ≥ 80% | 90-100 |
| 所有测试通过 + 覆盖率 60-80% | 70-89 |
| 所有测试通过 + 覆盖率 < 60% | 50-69 |
| 有测试失败 | 0-49 |

#### 视觉/UI (20%)

> 仅当需求涉及 UI 变更时评估，否则此项默认 80 分

| 指标 | 得分 |
|------|------|
| 布局正确、样式一致、响应式正常 | 80-100 |
| 布局正确、小瑕疵 | 60-79 |
| 布局有问题但不影响使用 | 40-59 |
| 布局错乱 | 0-39 |

#### 代码质量 (15%)

| 指标 | 得分 |
|------|------|
| 可读性好、无反模式、命名清晰 | 80-100 |
| 整体良好、有小问题 | 60-79 |
| 可读性差或有明显反模式 | 0-59 |

#### 计划符合度 (10%)

基于 PLAN.md 对比：

| 偏差程度 | 得分 |
|----------|------|
| 完全按计划执行 | 90-100 |
| 轻微偏差（记录但合理） | 60-89 |
| 重大偏差（改变了方案） | 0-59 |

### Step 5: 计算加权总分

```
总分 = 功能 × 0.30 + 测试 × 0.25 + 视觉 × 0.20 + 代码 × 0.15 + 计划 × 0.10
```

### Step 6: 生成评分报告

**SCORE.md 模板**：

```markdown
# 评分报告：{任务名称}

> 评估时间: {ISO-8601}
> 迭代: 第 {N} 次

## 总分: {XX}/100 — {等级}

| 维度 | 得分 | 权重 | 加权 |
|------|------|------|------|
| 功能正确性 | {score} | 30% | {weighted} |
| 测试覆盖 | {score} | 25% | {weighted} |
| 视觉/UI | {score} | 20% | {weighted} |
| 代码质量 | {score} | 15% | {weighted} |
| 计划符合度 | {score} | 10% | {weighted} |

## 结论: ✅ 通过 / ❌ 不通过

---

## MUST 条件验证

- [x] MUST-1: {描述} — ✅ 通过
- [x] MUST-2: {描述} — ✅ 通过
- [ ] MUST-3: {描述} — ❌ 失败: {原因}

## 测试结果

- 通过: {N}/{Total}
- 失败测试:
  - {test-name}: {失败原因}

## 问题清单（按严重程度排序）

### 严重 (Blocker)
- {问题 1}

### 重要 (Major)
- {问题 2}

### 轻微 (Minor)
- {问题 3}

## 改进建议

1. {建议 1}
2. {建议 2}
```

**report.json 模板**：

```json
{
  "timestamp": "{ISO-8601}",
  "iteration": 1,
  "overallScore": 75,
  "passed": true,
  "dimensions": {
    "functionality": { "score": 80, "weight": 0.30, "weighted": 24 },
    "tests": { "score": 70, "weight": 0.25, "weighted": 17.5 },
    "visual": { "score": 75, "weight": 0.20, "weighted": 15 },
    "codeQuality": { "score": 80, "weight": 0.15, "weighted": 12 },
    "planAdherence": { "score": 90, "weight": 0.10, "weighted": 9 }
  },
  "mustResults": [
    { "id": "MUST-1", "description": "...", "passed": true },
    { "id": "MUST-2", "description": "...", "passed": false, "reason": "..." }
  ],
  "testResults": {
    "total": 10,
    "passed": 8,
    "failed": 2,
    "failures": ["test-a: ...", "test-b: ..."]
  },
  "issues": [
    { "severity": "blocker", "description": "..." },
    { "severity": "major", "description": "..." },
    { "severity": "minor", "description": "..." }
  ]
}
```

### Step 7: 更新 pipeline.json 并决定下一步

```python
# 伪代码
if overall_score >= 70:
    pipeline.status = "completed"
    # 展示报告，流水线完成
elif generate_retries < 3:
    pipeline.agents.generate.status = "pending"
    pipeline.generateRetries += 1
    # 回到 Generator，附上 Score 反馈
elif plan_retries < 2:
    pipeline.agents.plan.status = "pending"
    pipeline.planRetries += 1
    pipeline.generateRetries = 0
    # 回到 Plan，附上完整历史
else:
    pipeline.status = "paused"
    # 暂停，询问用户
```

---

## 评分等级

| 等级 | 分数范围 | 含义 |
|------|----------|------|
| A | 90-100 | 优秀，可直接交付 |
| B | 70-89 | 合格，通过 |
| C | 50-69 | 不通过，需修复 |
| D | 0-49 | 严重不足，需重新审视 |
